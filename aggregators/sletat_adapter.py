# aggregators/sletat_adapter.py
"""Адаптер агрегатора Sletat.ru поверх существующего JSON-шлюза."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import TourAggregator, TourOffer, TourSearchParams

logger = logging.getLogger(__name__)


class SletatAggregator(TourAggregator):
    """Унифицированный фасад над ``sletat.SletatClient``."""

    name = "sletat"

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from sletat import SletatClient  # type: ignore

            self._client = SletatClient()
        return self._client

    @property
    def is_auth_configured(self) -> bool:
        return self._get_client().is_auth_configured

    # ---------- Справочники ----------
    def get_depart_cities(self) -> List[Dict[str, Any]]:
        return self._get_client().get_depart_cities()

    def get_countries(self) -> List[Dict[str, Any]]:
        return self._get_client().get_countries()

    def get_resorts(self, country_id: int) -> List[Dict[str, Any]]:
        return self._get_client().get_resorts(country_id)

    def get_hotels(
        self,
        country_id: Optional[int] = None,
        resort_id: Optional[int] = None,
        stars: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return self._get_client().get_hotels(
            country_id=country_id, resort_id=resort_id, star=stars
        )

    def get_hotel_stars(self) -> List[Dict[str, Any]]:
        return self._get_client().get_hotel_stars()

    def get_meals(self) -> List[Dict[str, Any]]:
        return self._get_client().get_meals()

    def get_tour_operators(self) -> List[Dict[str, Any]]:
        return self._get_client().get_tour_operators()

    def get_tour_dates(
        self,
        city_from_id: int,
        country_id: int,
        resort_id: Optional[int] = None,
    ) -> List[str]:
        return self._get_client().get_tour_dates(city_from_id, country_id, resort_id)

    # ---------- Поиск ----------
    def search_and_collect(
        self, params: TourSearchParams, **kwargs: Any
    ) -> Dict[str, Any]:
        from sletat import parse_tour_row  # type: ignore

        client = self._get_client()
        kw: Dict[str, Any] = dict(kwargs)
        if params.city_from_id is not None:
            kw.setdefault("city_from_id", params.city_from_id)
        if params.country_id is not None:
            kw.setdefault("country_id", params.country_id)
        for src_key, dst_key in (
            ("resort_id", "resort_id"),
            ("hotel_stars", "hotel_stars"),
            ("meal_id", "meal_id"),
            ("date_from", "date_from"),
            ("date_to", "date_to"),
            ("nights_from", "nights_from"),
            ("nights_to", "nights_to"),
            ("adults", "adults"),
            ("children", "children"),
            ("price_from", "price_from"),
            ("price_to", "price_to"),
        ):
            v = getattr(params, src_key)
            if v is not None:
                kw.setdefault(dst_key, v)
        result = client.search_and_collect(**kw)
        tours = result.get("tours", []) if isinstance(result, dict) else []
        offers: List[TourOffer] = []
        for row in tours:
            p = parse_tour_row(row)
            offers.append(
                TourOffer(
                    source="sletat",
                    tour_id=str(p.get("tour_id") or ""),
                    hotel_name=str(p.get("hotel_name") or ""),
                    hotel_stars=p.get("hotel_stars"),
                    resort=str(p.get("resort") or ""),
                    country=str(p.get("country") or ""),
                    departure_date=str(p.get("departure_date") or ""),
                    nights=p.get("nights"),
                    room_type=str(p.get("room_type") or ""),
                    meal=str(p.get("meal") or ""),
                    price=p.get("price"),
                    price_currency=str(p.get("price_currency") or ""),
                    full_price=p.get("full_price"),
                    operator=str(p.get("operator") or ""),
                    hotel_rating=p.get("hotel_rating") or p.get("tripadvisor_rating"),
                    raw=row,
                )
            )
        result["offers"] = offers
        return result

    def get_load_state(self, request_id: str) -> Dict[str, Any]:
        return self._get_client().get_load_state(request_id)

    def get_results(
        self, request_id: str, max_results: int = 10
    ) -> List[TourOffer]:
        from sletat import parse_tour_row  # type: ignore

        raw = self._get_client().get_results(request_id)
        aa = raw.get("aaData", []) if isinstance(raw, dict) else []
        offers: List[TourOffer] = []
        for row in aa[:max_results]:
            p = parse_tour_row(row)
            offers.append(
                TourOffer(
                    source="sletat",
                    tour_id=str(p.get("tour_id") or ""),
                    hotel_name=str(p.get("hotel_name") or ""),
                    hotel_stars=p.get("hotel_stars"),
                    resort=str(p.get("resort") or ""),
                    country=str(p.get("country") or ""),
                    departure_date=str(p.get("departure_date") or ""),
                    nights=p.get("nights"),
                    room_type=str(p.get("room_type") or ""),
                    meal=str(p.get("meal") or ""),
                    price=p.get("price"),
                    price_currency=str(p.get("price_currency") or ""),
                    full_price=p.get("full_price"),
                    operator=str(p.get("operator") or ""),
                    hotel_rating=p.get("hotel_rating") or p.get("tripadvisor_rating"),
                    raw=row,
                )
            )
        return offers

    # ---------- Заказ ----------
    def actualize_price(self, request_id: str, tour_id: str) -> Dict[str, Any]:
        return self._get_client().actualize_price(request_id, tour_id)

    def save_tour_order(
        self,
        request_id: str,
        tour_id: str,
        user_name: str,
        user_phone: str,
        user_email: str = "",
        comment: str = "",
    ) -> Dict[str, Any]:
        return self._get_client().save_tour_order(
            request_id, tour_id, user_name, user_phone, user_email, comment
        )
