# sletat/sletat_api.py
"""Клиент для JSON-шлюза поиска туров Sletat.ru.
Документация: https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json)
Базовый URL: https://module.sletat.ru/Main.svc/
Авторизация: параметры login/password от личного кабинета Sletat.ru.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class SletatAPIError(RuntimeError):
    """Ошибка при обращении к API Sletat.ru."""


class SletatClient:
    """Синхронный клиент к JSON-шлюзу Sletat.ru."""

    BASE_URL = "https://module.sletat.ru/Main.svc"
    STATE_NOT_LOADED = 0
    STATE_LOADED = 1
    STATE_LOADING = 2
    STATE_INTERRUPTED = 3
    STATE_NOT_FOUND = 4

    def __init__(
        self,
        login: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        poll_timeout: int = 180,
        poll_interval: int = 3,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.login = login or os.getenv("SLETAT_LOGIN", "")
        self.password = password or os.getenv("SLETAT_PASSWORD", "")
        self.base_url = (base_url or os.getenv("SLETAT_BASE_URL") or self.BASE_URL).rstrip("/")
        try:
            self.poll_timeout = int(os.getenv("SLETAT_POLL_TIMEOUT", poll_timeout))
        except ValueError:
            self.poll_timeout = poll_timeout
        try:
            self.poll_interval = int(os.getenv("SLETAT_POLL_INTERVAL", poll_interval))
        except ValueError:
            self.poll_interval = poll_interval
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def is_auth_configured(self) -> bool:
        return bool(self.login and self.password)

    def _auth_params(self) -> Dict[str, str]:
        if not self.is_auth_configured:
            raise SletatAPIError(
                "Не заданы SLETAT_LOGIN/SLETAT_PASSWORD в .env "
                "(логин/пароль от личного кабинета Sletat.ru)."
            )
        return {"login": self.login, "password": self.password}

    def _call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{method}"
        merged = self._auth_params()
        if params:
            for k, v in params.items():
                if v is None or v == "":
                    continue
                merged[k] = v
        try:
            safe = {k: v for k, v in merged.items() if k != "password"}
            logger.debug("Sletat request: %s params=%s", url, safe)
            resp = self.session.get(url, params=merged, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SletatAPIError(f"Сетевая ошибка: {exc}") from exc
        if resp.status_code != 200:
            raise SletatAPIError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise SletatAPIError(f"JSON parse error: {exc}\n{resp.text[:300]}") from exc
        result_key = next((k for k in data.keys() if k.endswith("Result")), None)
        if result_key is None:
            return data
        payload = data.get(result_key, {})
        if isinstance(payload, dict) and payload.get("IsError"):
            raise SletatAPIError(
                f"Sletat error in {method}: "
                f"{payload.get('ErrorMessage') or payload.get('ErrorCode')}"
            )
        return payload

    # ---------- Справочники ----------
    def get_depart_cities(self) -> List[Dict[str, Any]]:
        return self._call("GetDepartCities").get("Data", [])

    def get_countries(self) -> List[Dict[str, Any]]:
        return self._call("GetCountries").get("Data", [])

    def get_resorts(self, country_id: int) -> List[Dict[str, Any]]:
        return self._call("GetCities", {"countryId": country_id}).get("Data", [])

    def get_hotels(
        self,
        country_id: Optional[int] = None,
        resort_id: Optional[int] = None,
        star: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if country_id is not None:
            params["countryId"] = country_id
        if resort_id is not None:
            params["cityId"] = resort_id
        if star is not None:
            params["stars"] = star
        return self._call("GetHotels", params).get("Data", [])

    def get_hotel_stars(self) -> List[Dict[str, Any]]:
        return self._call("GetHotelStars").get("Data", [])

    def get_meals(self) -> List[Dict[str, Any]]:
        return self._call("GetMeals").get("Data", [])

    def get_tour_operators(self) -> List[Dict[str, Any]]:
        return self._call("GetTourOperators").get("Data", [])

    def get_tour_dates(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
    ) -> List[str]:
        params: Dict[str, Any] = {"cityFromId": city_from_id, "countryId": country_id}
        if resort_id is not None:
            params["resortId"] = resort_id
        return self._call("GetTourDates", params).get("Data", [])

    def get_available_features(self) -> List[Dict[str, Any]]:
        return self._call("GetAvailableFeatures").get("Data", [])

    # ---------- Поиск туров ----------
    def create_search_request(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
        hotel_stars: Optional[int] = None,
        meal_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        nights_from: Optional[int] = None,
        nights_to: Optional[int] = None,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        price_from: Optional[int] = None,
        price_to: Optional[int] = None,
        tour_operator_ids: Optional[List[int]] = None,
        hotel_ids: Optional[List[int]] = None,
        include_oil_taxes_and_visa: bool = True,
        show_hotel_facilities: bool = False,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "cityFromId": city_from_id,
            "countryId": country_id,
            "adults": adults,
            "children": children,
        }
        if resort_id is not None:
            params["resortId"] = resort_id
        if hotel_stars is not None:
            params["stars"] = hotel_stars
        if meal_id is not None:
            params["mealId"] = meal_id
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if nights_from is not None:
            params["nightsFrom"] = nights_from
        if nights_to is not None:
            params["nightsTo"] = nights_to
        if children_ages:
            ages = (list(children_ages) + [None, None, None])[:3]
            for i, age in enumerate(ages, start=1):
                if age is not None:
                    params[f"childAge{i}"] = age
        if price_from is not None:
            params["priceFrom"] = price_from
        if price_to is not None:
            params["priceTo"] = price_to
        if tour_operator_ids:
            params["touoperatorId"] = ",".join(str(i) for i in tour_operator_ids)
        if hotel_ids:
            params["hotelId"] = ",".join(str(i) for i in hotel_ids)
        if include_oil_taxes_and_visa:
            params["includeOilTaxesAndVisa"] = 1
        if show_hotel_facilities:
            params["showHotelFacilities"] = 1
        return self._call("GetTours", params)

    def get_load_state(self, request_id: str) -> Dict[str, Any]:
        return self._call("GetLoadState", {"requestId": request_id})

    def get_results(self, request_id: str, package_number: int = 0) -> Dict[str, Any]:
        return self._call(
            "GetTours",
            {"requestId": request_id, "updateResult": 1, "packageNumber": package_number},
        )

    def _poll_until_loaded(self, request_id: str) -> Dict[str, Any]:
        deadline = time.time() + self.poll_timeout
        last_state: Dict[str, Any] = {}
        while time.time() < deadline:
            last_state = self.get_load_state(request_id)
            if not isinstance(last_state, dict):
                break
            states = last_state.get("States") or []
            if not states:
                break
            pending = [
                s for s in states
                if s.get("State") not in (self.STATE_LOADED, self.STATE_NOT_FOUND)
            ]
            if not pending:
                break
            time.sleep(self.poll_interval)
        return last_state

    def search_and_collect(self, **kwargs: Any) -> Dict[str, Any]:
        """Создать поиск, дождаться готовности и вернуть туры."""
        created = self.create_search_request(**kwargs)
        request_id = str(created.get("requestId") or "")
        if not request_id:
            return {
                "requestId": None,
                "loadState": None,
                "tours": [],
                "raw": created,
                "error": "Sletat не вернул requestId",
            }
        state = self._poll_until_loaded(request_id)
        results = self.get_results(request_id)
        tours = results.get("aaData", []) if isinstance(results, dict) else []
        return {
            "requestId": request_id,
            "loadState": state,
            "tours": tours,
            "raw": results,
        }

    # ---------- Заказ ----------
    def actualize_price(self, request_id: str, tour_id: str) -> Dict[str, Any]:
        return self._call(
            "ActualizePrice",
            {"requestId": request_id, "tourId": tour_id},
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
        return self._call(
            "SaveTourOrder",
            {
                "requestId": request_id,
                "tourId": tour_id,
                "name": user_name,
                "phone": user_phone,
                "email": user_email,
                "comment": comment,
            },
        )


# Индексы aaData (наиболее используемые поля; полный список — в документации Sletat)
TOUR_FIELD_NAMES: Dict[int, str] = {
    0: "tour_internal_id",
    1: "tour_id",
    2: "hotel_name",
    3: "hotel_stars",
    4: "resort",
    5: "country",
    6: "arrival_city",
    7: "departure_date",
    8: "nights",
    9: "room_type",
    10: "meal",
    11: "price",
    12: "price_currency",
    13: "price_with_fees",
    14: "price_with_fees_currency",
    15: "operator",
    16: "operator_id",
    17: "hotel_url",
    18: "hotel_rating",
    19: "nights_alt",
    79: "cache_hash",
    86: "base_price",
    88: "full_price",
    89: "tripadvisor_rating",
    90: "tripadvisor_reviews",
    96: "popularity_rating",
}


def parse_tour_row(row: List[Any]) -> Dict[str, Any]:
    """Преобразует aaData-строку в словарь с понятными ключами."""
    out: Dict[str, Any] = {}
    for idx, name in TOUR_FIELD_NAMES.items():
        if idx < len(row):
            out[name] = row[idx]
    out["_raw"] = row
    return out


def format_tour_for_human(parsed: Dict[str, Any], max_chars: int = 900) -> str:
    """Человеко-читаемое представление тура."""
    price = parsed.get("price")
    cur = parsed.get("price_currency") or ""
    full_price = parsed.get("full_price")
    lines = [
        f"🏨 {parsed.get('hotel_name') or '?'} {parsed.get('hotel_stars') or ''}".strip(),
        f"📍 {parsed.get('resort') or ''}, {parsed.get('country') or ''}".strip(", "),
        f"✈️ Вылет {parsed.get('departure_date') or '?'}, {parsed.get('nights') or '?'} ноч.",
        f"🛏️ {parsed.get('room_type') or '?'}, 🍽️ {parsed.get('meal') or '?'}",
        f"💰 Цена: {price} {cur}".strip(),
    ]
    if full_price and full_price != price:
        lines.append(f"💵 Полная цена (с учётом сборов ТО): {full_price} {cur}")
    op = parsed.get("operator")
    if op:
        lines.append(f"🏢 Туроператор: {op}")
    rating = parsed.get("tripadvisor_rating") or parsed.get("hotel_rating")
    if rating not in (None, "", "0", 0):
        reviews = parsed.get("tripadvisor_reviews")
        rating_str = f"{rating}/5"
        if reviews:
            rating_str += f" ({reviews} отзывов)"
        lines.append(f"⭐ Рейтинг: {rating_str}")
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"



