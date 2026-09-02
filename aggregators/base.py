# aggregators/base.py
"""Базовые классы и общие типы для адаптеров агрегаторов туров."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TourSearchParams:
    """Унифицированные параметры поиска тура для любого агрегатора."""

    city_from_id: Optional[int] = None
    city_from_name: Optional[str] = None
    country_id: Optional[int] = None
    country_name: Optional[str] = None
    resort_id: Optional[int] = None
    resort_name: Optional[str] = None
    hotel_stars: Optional[int] = None
    meal_id: Optional[int] = None
    meal_name: Optional[str] = None
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None
    nights_from: Optional[int] = None
    nights_to: Optional[int] = None
    adults: int = 2
    children: int = 0
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TourOffer:
    """Унифицированное представление тура из любого агрегатора."""

    source: str  # "sletat" | "multitour"
    tour_id: str  # идентификатор тура у агрегатора
    hotel_name: str = ""
    hotel_stars: Optional[Any] = None
    resort: str = ""
    country: str = ""
    departure_date: str = ""
    nights: Optional[int] = None
    room_type: str = ""
    meal: str = ""
    price: Optional[float] = None
    price_currency: str = ""
    full_price: Optional[float] = None
    operator: str = ""
    hotel_rating: Optional[Any] = None
    raw: Any = None  # сырой ответ от агрегатора (список/словарь)

    def to_human(self) -> str:
        stars = f" {self.hotel_stars}" if self.hotel_stars else ""
        loc = ", ".join(filter(None, [self.resort, self.country]))
        nights = f", {self.nights} ноч." if self.nights else ""
        price = f"{self.price} {self.price_currency}".strip()
        lines = [
            f"🏨 {self.hotel_name or '?'}{stars}",
            f"📍 {loc}".rstrip(", "),
            f"✈️ Вылет {self.departure_date or '?'}{nights}",
            f"🛏️ {self.room_type or '?'}, 🍽️ {self.meal or '?'}",
            f"💰 Цена: {price or '?'}",
        ]
        if self.full_price and self.full_price != self.price:
            lines.append(
                f"💵 Полная цена (с учётом сборов ТО): {self.full_price} {self.price_currency}"
            )
        if self.operator:
            lines.append(f"🏢 Туроператор: {self.operator}")
        if self.hotel_rating not in (None, "", "0", 0):
            lines.append(f"⭐ Рейтинг: {self.hotel_rating}")
        lines.append(f"🔖 Источник: {self.source}")
        return "\n".join(lines)


class TourAggregator:
    """Базовый класс адаптера агрегатора. Все метододы — заглушки."""

    name: str = "base"

    # ---------- Справочники ----------
    def get_depart_cities(self) -> List[Dict[str, Any]]: ...
    def get_countries(self) -> List[Dict[str, Any]]: ...
    def get_resorts(self, country_id: int) -> List[Dict[str, Any]]: ...
    def get_hotels(
        self,
        country_id: Optional[int] = None,
        resort_id: Optional[int] = None,
        stars: Optional[int] = None,
    ) -> List[Dict[str, Any]]: ...
    def get_hotel_stars(self) -> List[Dict[str, Any]]: ...
    def get_meals(self) -> List[Dict[str, Any]]: ...
    def get_tour_operators(self) -> List[Dict[str, Any]]: ...
    def get_tour_dates(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
    ) -> List[str]: ...

    # ---------- Поиск ----------
    def search_and_collect(self, params: TourSearchParams, **kwargs: Any) -> Dict[str, Any]:
        """Создать поиск, дождаться результатов, вернуть
        ``{"requestId", "loadState", "offers": [TourOffer], "raw"}``.
        """

    def get_load_state(self, request_id: str) -> Dict[str, Any]: ...
    def get_results(
        self, request_id: str, max_results: int = 10
    ) -> List[TourOffer]: ...

    # ---------- Заказ ----------
    def actualize_price(self, request_id: str, tour_id: str) -> Dict[str, Any]: ...
    def save_tour_order(
        self,
        request_id: str,
        tour_id: str,
        user_name: str,
        user_phone: str,
        user_email: str = "",
        comment: str = "",
    ) -> Dict[str, Any]: ...
