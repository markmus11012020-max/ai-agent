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


class MultitourAPIError(RuntimeError):
    """Ошибка обращения к Multitour API v2."""


class MultitourAggregator(TourAggregator):
    """Унифицированный фасад для Multitour API v2."""

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

    @property
    def is_auth_configured(self) -> bool:
        return bool(self.token)

    # ---------- транспорт ----------
    def _call(self, method: str, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                f"JSON parse error: {exc}\n{resp.text[:300]}"
            ) from exc
        if not data.get("is_success", False):
            raise MultitourAPIError(
                "Multitour: " + "; ".join(data.get("error") or ["неизвестная ошибка"])
            )
        return data.get("response") or {}

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

    # ---------- Справочники ----------
    def get_depart_cities(self) -> List[Dict[str, Any]]:
        return self._coerce_list(self._get("GetDepartCities"))

    def get_countries(self) -> List[Dict[str, Any]]:
        return self._coerce_list(self._get("GetCountries"))

    def get_resorts(self, country_id: int) -> List[Dict[str, Any]]:
        return self._coerce_list(
            self._get("GetResorts", {"countryId": country_id})
        )

    def get_hotels(
        self,
        country_id: Optional[int] = None,
        resort_id: Optional[int] = None,
        stars: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if country_id is not None:
            params["countryId"] = country_id
        if resort_id is not None:
            params["resortId"] = resort_id
        if stars is not None:
            params["stars"] = stars
        return self._coerce_list(self._get("GetHotels", params))

    def get_hotel_stars(self) -> List[Dict[str, Any]]:
        return self._coerce_list(self._get("GetHotelStars"))

    def get_meals(self) -> List[Dict[str, Any]]:
        return self._coerce_list(self._get("GetMeals"))

    def get_tour_operators(self) -> List[Dict[str, Any]]:
        return self._coerce_list(self._get("GetTourOperators"))

    def get_tour_dates(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
    ) -> List[str]:
        params: Dict[str, Any] = {
            "cityFromId": city_from_id,
            "countryId": country_id,
        }
        if resort_id is not None:
            params["resortId"] = resort_id
        out = self._get("GetTourDates", params)
        return out if isinstance(out, list) else self._coerce_list(out)

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

    # ---------- Поиск ----------
    def _build_search_request(self, params: TourSearchParams) -> Dict[str, Any]:
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
        """Создать поиск тура в Multitour. Возвращает ``requestId``."""
        resp = self._call("CreateSearch", self._build_search_request(params))
        request_id = str(
            resp.get("requestId") or resp.get("RequestId") or resp.get("id") or ""
        )
        return {"requestId": request_id, "raw": resp}

    def get_load_state(self, request_id: str) -> Dict[str, Any]:
        """Состояние загрузки результатов поиска."""
        try:
            return self._call("GetSearchState", {"requestId": request_id})
        except MultitourAPIError:
            # Фолбэк для альтернативного имени метода
            return self._call("GetLoadState", {"requestId": request_id})

    @staticmethod
    def _to_offer(raw_offer: Any, idx: int) -> TourOffer:
        """Превращает произвольный объект тура Multitour в ``TourOffer``."""
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
            v = raw_offer.get(key) or hotel.get(key) if isinstance(hotel, dict) else None
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
            hotel_name=str(hotel.get("Name") if isinstance(hotel, dict) else hotel) or str(raw_offer.get("HotelName") or ""),
            hotel_stars=hotel.get("Stars") if isinstance(hotel, dict) else None,
            resort=str(resort),
            country=str(country),
            departure_date=str(raw_offer.get("DepartureDate") or raw_offer.get("DateFrom") or ""),
            nights=raw_offer.get("Nights") or raw_offer.get("nights") or None,
            room_type=str(raw_offer.get("RoomType") or raw_offer.get("Room") or ""),
            meal=str(raw_offer.get("Meal") or raw_offer.get("Board") or ""),
            price=_num("Price"),
            price_currency=str(raw_offer.get("Currency") or "RUB"),
            full_price=_num("FullPrice"),
            operator=str(raw_offer.get("Operator") or raw_offer.get("TourOperator") or "Multitour"),
            hotel_rating=hotel.get("Rating") if isinstance(hotel, dict) else None,
            raw=raw_offer,
        )

    def get_results(
        self, request_id: str, max_results: int = 10
    ) -> List[TourOffer]:
        resp = self._call("GetSearchResult", {"requestId": request_id})
        items = (
            resp.get("Tours")
            or resp.get("tours")
            or resp.get("Results")
            or resp.get("results")
            or resp.get("Items")
            or (resp if isinstance(resp, list) else [])
        )
        if not isinstance(items, list):
            return []
        return [self._to_offer(o, i) for i, o in enumerate(items[:max_results])]

    def search_and_collect(
        self, params: TourSearchParams, **kwargs: Any
    ) -> Dict[str, Any]:
        """Создать поиск, опросить состояние и собрать ``TourOffer``."""
        created = self.create_search_request(params)
        request_id = created.get("requestId") or ""
        if not request_id:
            return {
                "requestId": None,
                "loadState": None,
                "offers": [],
                "raw": created,
                "error": "Multitour не вернул requestId",
            }
        # Multitour обычно возвращает готовые результаты прямо в CreateSearch;
        # если их нет — пробуем опросить и забрать.
        try:
            offers = self.get_results(request_id, max_results=kwargs.get("max_results", 30))
        except MultitourAPIError as exc:
            return {
                "requestId": request_id,
                "loadState": None,
                "offers": [],
                "raw": created,
                "error": str(exc),
            }
        return {
            "requestId": request_id,
            "loadState": None,
            "offers": offers,
            "raw": created,
        }

    # ---------- Заказ ----------
    def actualize_price(self, request_id: str, tour_id: str) -> Dict[str, Any]:
        try:
            return self._call(
                "ActualizePrice",
                {"requestId": request_id, "tourId": tour_id},
            )
        except MultitourAPIError:
            return self._call(
                "Actualize", {"requestId": request_id, "tourId": tour_id}
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
        req = {
            "requestId": request_id,
            "tourId": tour_id,
            "name": user_name,
            "phone": user_phone,
            "email": user_email,
            "comment": comment,
        }
        for method in ("CreateOrder", "SaveOrder", "AddToCart"):
            try:
                return self._call(method, req)
            except MultitourAPIError as exc:
                last_exc = exc  # type: ignore
        raise last_exc  # type: ignore[misc]
