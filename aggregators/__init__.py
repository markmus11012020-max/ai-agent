# aggregators/__init__.py
"""Универсальная обёртка над агрегаторами туров (Sletat.ru и Multitour.ru)."""
from .base import TourAggregator, TourSearchParams, TourOffer
from .sletat_adapter import SletatAggregator
from .multitour_adapter import MultitourAggregator
from .factory import get_aggregator, list_aggregators

__all__ = [
    "TourAggregator",
    "TourSearchParams",
    "TourOffer",
    "SletatAggregator",
    "MultitourAggregator",
    "get_aggregator",
    "list_aggregators",
]
