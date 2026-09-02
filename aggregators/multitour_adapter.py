# aggregators/multitour_adapter.py
"""Адаптер агрегатора Multitour.ru (API v2).

Базовый URL: ``https://www.multitour.ru/api/v2/``
Авторизация: токен в ``header.token`` (``MULTITOUR_TOKEN`` / ``API_KEY``).

Запрос (POST-JSON):
    {
      "header":  {"token": "...", "method": "<имя_метода>"},
      "request": { ... }
    }

Ответ:
    {
      "header": {...}, "request": {...},
      "response": {...}, "is_success": bool, "error": []
    }

⚠️ Реально доступные методы (проверено в _probe3.py / _probe4.py): только
``Geo.Country`` и ``Geo.City``. Все остальные ``Geo.*`` и любые ``Tour.*``
возвращают ``{"is_success": false, "error": ["Method not found"]}``. Алиасов
у шлюза нет — он не принимает ни ``GetCountries``, ни ``GetResorts``, ни
``Tour.Create`` и т.п. Поэтому справочные вызовы реализованы через два
рабочих метода, а любые попытки обращения к несуществующим методам
(поиск туров, отели, актуализация цены, заказ) поднимают
``MultitourMethodUnsupported``.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from .base import TourAggregator, TourOffer, TourSearchParams

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.multitour.ru/api/v2/"

SUPPORTED_METHODS = frozenset({"Geo.Country", "Geo.City"})


class MultitourAPIError(RuntimeError):
    """Ошибка обращения к Multitour API v2."""


class MultitourMethodUnsupported(MultitourAPIError):
    """Метод не поддерживается Multitour API v2 на этом тарифе/токене."""


class MultitourAggregator(TourAggregator):
    """Унифицированный фасад для Multitour API v2.

    Текущий партнёрский доступ поддерживает только два справочных метода —
    список стран и список гео-городов. Поиск туров и заказы недоступны.
    """

    name = "multitour"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        session: Optional[requests.Session] = None,
        poll_timeout: int = 180,
        poll_interval: int = 3,
    ) -> None:
        self.token = (
            token
            or os.getenv("MULTITOUR_TOKEN")
            or os.getenv("API_KEY")
            or ""
        ).strip()
        self.base_url = (
            base_url or os.getenv("MULTITOUR_API_URL") or DEFAULT_BASE_URL
        ).rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self._available_methods: Optional[set] = None

    # ---------- introspection ----------
    @property
    def is_auth_configured(self) -> bool:
        return bool(self.token)

    @property
    def available_methods(self) -> set:
        """Множество методов, которые API реально принимает (lazy ping)."""
        if self._available_methods is not None:
            return self._available_methods
        ok: set = set()
        if not self.token:
            return ok
        for m in SUPPORTED_METHODS:
            try:
                resp = self.session.post(
                    self.base_url,
                    json={"header": {"token": self.token, "method": m}, "request": {}},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("is_success"):
                        ok.add(m)
            except requests.RequestException as exc:
                logger.warning("Multitour ping %s failed: %s", m, exc)
        self._available_methods = ok
        return ok

    @property
    def is_search_available(self) -> bool:
        """Поиск туров (``Tour.*``) недоступен на текущем тарифе."""
        return False

    # ---------- transport ----------
    def _call(
        self,
        method: str,
        request: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.token:
            raise MultitourAPIError(
                "Не задан MULTITOUR_TOKEN (или API_KEY) в .env — "
                "получите токен в личном кабинете Multitour.ru."
            )
        payload = {
            "header": {"token": self.token, "method": method},
            "request": request or {},
        }
        try:
            resp = self.session.post(
                self.base_url, json=payload, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise MultitourAPIError(f"Сетевая ошибка: {exc}") from exc
        if resp.status_code != 200:
            raise MultitourAPIError(
                f"HTTP {resp.status_code}: {resp.text[:300]}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise MultitourAPIError(
                f"JSON parse error: {exc}\\n{resp.text[:300]}"
            ) from exc
        if data.get("is_success", False):
            if self._available_methods is not None:
                self._available_methods.add(method)
            return data.get("response") or {}
        errs = data.get("error") or []
        err_text = "; ".join(errs) if errs else "неизвестная ошибка"
        if any("method" in e.lower() for e in errs):
            raise MultitourMethodUnsupported(
                f"Метод '{method}' не поддерживается Multitour API v2 "
                f"на текущем тарифе. Доступные: "
                f"{sorted(self.available_methods) or 'нет'}"
            )
        raise MultitourAPIError(f"Multitour: {err_text}")

    def _get(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        out = self._call(method, params)
        if isinstance(out, (list, str, int, float, bool)):
            return out
        if isinstance(out, dict):
            for k in ("Data", "data", "Items", "items", "Result", "result"):
                if k in out:
                    return out[k]
            return out
        return out

    @staticmethod
    def _coerce_list(value: Any) -> List[Dict[str, Any]]:
        """Нормализация ответа справочников к списку словарей."""
        if value is None:
            return []
        if isinstance(value, list):
            return [
                v if isinstance(v, dict) else {"Name": str(v), "Id": idx}
                for idx, v in enumerate(value, start=1)
            ]
        if isinstance(value, dict):
            return [value]
        return [{"Name": str(value)}]

    # ---------- Справочники (рабочие) ----------
    def get_countries(self) -> List[Dict[str, Any]]:
        """Список стран (``Geo.Country`` → [{id, name}])."""
        return self._coerce_list(self._get("Geo.Country"))

    def get_cities(self) -> List[Dict[str, Any]]:
        """Список гео-городов (``Geo.City`` → [{id, name, resort_*, region_*}]).

        Multitour API v2 возвращает в ``Geo.City`` справочник городов/курортов/
        регионов единым списком, **не** города вылета. Для фильтрации курортов
        конкретной страны используйте ``get_resorts(country_id)``.
        """
        return self._coerce_list(self._get("Geo.City"))

    # ---------- Справочники (не работают на этом тарифе) ----------
    def get_depart_cities(self) -> List[Dict[str, Any]]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: 'GetDepartCities'/'Geo.DepartCity' недоступен на тарифе"
        )

    def get_resorts(self, country_id: int) -> List[Dict[str, Any]]:
        """Курорты конкретной страны: фильтруем из ``Geo.City``.

        ``Geo.Resort`` возвращает ``Method not found``, но в ``Geo.City`` каждый
        элемент имеет ``resort_id``/``resort_name``. Возвращаем дедуплицированный
        список только с непустым ``resort_id``.
        """
        cities = self.get_cities()
        out: List[Dict[str, Any]] = []
        seen: set = set()
        for c in cities:
            rid = c.get("resort_id") or c.get("ResortId")
            if rid in (None, "", 0) or rid in seen:
                continue
            seen.add(rid)
            out.append(
                {
                    "Id": rid,
                    "Name": c.get("resort_name") or c.get("ResortName"),
                    "CountryId": country_id,
                }
            )
        return out

    def get_hotels(
        self,
        country_id: Optional[int] = None,
        resort_id: Optional[int] = None,
        stars: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: справочник отелей (Geo.Hotel*) недоступен на тарифе"
        )

    def get_hotel_stars(self) -> List[Dict[str, Any]]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: категории отелей (Geo.HotelStar*) недоступны на тарифе"
        )

    def get_meals(self) -> List[Dict[str, Any]]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: типы питания (Geo.Meal*) недоступны на тарифе"
        )

    def get_tour_operators(self) -> List[Dict[str, Any]]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: туроператоры (Geo.TourOperator*) недоступны на тарифе"
        )

    def get_tour_dates(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
    ) -> List[str]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: даты вылетов (Geo.TourDate*) недоступны на тарифе"
        )

    # ---------- Поиск (недоступен) ----------
    def _build_search_request(self, params: TourSearchParams) -> Dict[str, Any]:
        """Сборка payload — нужна только для диагностики; сам вызов упадёт."""
        req: Dict[str, Any] = {}
        if params.city_from_id is not None:
            req["cityFromId"] = params.city_from_id
        if params.country_id is not None:
            req["countryId"] = params.country_id
        if params.resort_id is not None:
            req["resortId"] = params.resort_id
        if params.hotel_stars is not None:
            req["stars"] = params.hotel_stars
        if params.meal_id is not None:
            req["mealId"] = params.meal_id
        if params.date_from:
            req["dateFrom"] = params.date_from
        if params.date_to:
            req["dateTo"] = params.date_to
        if params.nights_from is not None:
            req["nightsFrom"] = params.nights_from
        if params.nights_to is not None:
            req["nightsTo"] = params.nights_to
        if params.adults:
            req["adults"] = params.adults
        if params.children:
            req["children"] = params.children
        if params.price_from is not None:
            req["priceFrom"] = params.price_from
        if params.price_to is not None:
            req["priceTo"] = params.price_to
        req.update(params.extra or {})
        return req

    def create_search_request(self, params: TourSearchParams) -> Dict[str, Any]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: 'Tour.Create'/'CreateSearch' не поддерживается "
            "на тарифе — поиск туров через Multitour сейчас невозможен."
        )

    def get_load_state(self, request_id: str) -> Dict[str, Any]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: методы опроса состояния поиска (Tour.GetState*) "
            "не поддерживаются на тарифе."
        )

    @staticmethod
    def _to_offer(raw_offer: Any, idx: int) -> TourOffer:
        """Превращает произвольный объект тура Multitour в ``TourOffer``.

        Multitour сейчас не возвращает туры, метод оставлен как утилита для
        будущих релизов / прямого ответа API.
        """
        if not isinstance(raw_offer, dict):
            raw_offer = {"Name": str(raw_offer)}
        hotel = raw_offer.get("Hotel") or raw_offer.get("hotel") or {}
        if not isinstance(hotel, dict):
            hotel = {"Name": str(hotel)}
        resort = (
            raw_offer.get("Resort")
            or raw_offer.get("resort")
            or (hotel.get("Resort") if isinstance(hotel.get("Resort"), str) else "")
            or raw_offer.get("City")
            or ""
        )
        country = raw_offer.get("Country") or raw_offer.get("country") or ""

        def _num(key: str) -> Optional[float]:
            v = (
                raw_offer.get(key)
                or (hotel.get(key) if isinstance(hotel, dict) else None)
            )
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        return TourOffer(
            source="multitour",
            tour_id=str(
                raw_offer.get("Id")
                or raw_offer.get("id")
                or raw_offer.get("TourId")
                or idx
            ),
            hotel_name=str(
                (hotel.get("Name") if isinstance(hotel, dict) else hotel) or ""
            ) or str(raw_offer.get("HotelName") or ""),
            hotel_stars=hotel.get("Stars") if isinstance(hotel, dict) else None,
            resort=str(resort),
            country=str(country),
            departure_date=str(
                raw_offer.get("DepartureDate") or raw_offer.get("DateFrom") or ""
            ),
            nights=raw_offer.get("Nights") or raw_offer.get("nights") or None,
            room_type=str(raw_offer.get("RoomType") or raw_offer.get("Room") or ""),
            meal=str(raw_offer.get("Meal") or raw_offer.get("Board") or ""),
            price=_num("Price"),
            price_currency=str(raw_offer.get("Currency") or "RUB"),
            full_price=_num("FullPrice"),
            operator=str(
                raw_offer.get("Operator")
                or raw_offer.get("TourOperator")
                or "Multitour"
            ),
            hotel_rating=hotel.get("Rating") if isinstance(hotel, dict) else None,
            raw=raw_offer,
        )

    def get_results(
        self, request_id: str, max_results: int = 10
    ) -> List[TourOffer]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: 'Tour.GetResult'/'GetSearchResult' не "
            "поддерживается на тарифе — результаты поиска туров получить нельзя."
        )

    def search_and_collect(
        self, params: TourSearchParams, **kwargs: Any
    ) -> Dict[str, Any]:
        """Поиск Multitour сейчас недоступен — возвращаем структурированную ошибку."""
        err = (
            "Multitour API v2: методы Tour.* (Create/GetState/GetResult) не "
            "поддерживаются на текущем тарифе — поиск туров невозможен."
        )
        logger.warning("search_and_collect(multitour): %s", err)
        return {
            "requestId": None,
            "loadState": None,
            "offers": [],
            "raw": None,
            "error": err,
        }

    # ---------- Заказ (недоступен) ----------
    def actualize_price(self, request_id: str, tour_id: str) -> Dict[str, Any]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: 'Tour.Actualize*' не поддерживается на тарифе."
        )

    def save_tour_order(
        self,
        request_id: str,
        tour_id: str,
        user_name: str,
        user_phone: str,
        user_email: str = "",
        comment: str = "",
    ) -> Dict[str, Any]:
        raise MultitourMethodUnsupported(
            "Multitour API v2: 'Tour.SaveOrder'/'CreateOrder' не "
            "поддерживается на тарифе."
        )
