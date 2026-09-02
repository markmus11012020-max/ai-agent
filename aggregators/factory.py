# aggregators/factory.py
"""Фабрика адаптеров агрегаторов туров.

Читает переменные окружения:
  TOUR_AGGREGATOR=sletat|multitour   — какой использовать по умолчанию
  SLETAT_LOGIN / SLETAT_PASSWORD     — авторизация Sletat (опц., см. base)
  MULTITOUR_TOKEN / API_KEY          — токен Multitour API v2
"""
from __future__ import annotations

import os
from typing import List

from .base import TourAggregator
from .sletat_adapter import SletatAggregator
from .multitour_adapter import MultitourAggregator

# Порядок отображения в UI
_KNOWN = ("sletat", "multitour")


def list_aggregators() -> List[TourAggregator]:
    """Возвращает инстансы всех известных агрегаторов (для UI настройки)."""
    return [
        SletatAggregator(),
        MultitourAggregator(),
    ]


def get_aggregator(name: str | None = None) -> TourAggregator:
    """Возвращает адаптер агрегатора по имени (``sletat``/``multitour``).

    Если ``name`` не указан, берётся ``TOUR_AGGREGATOR`` из окружения,
    либо первый доступный (sletat).
    """
    target = (name or os.getenv("TOUR_AGGREGATOR", "sletat")).lower().strip()
    if target not in _KNOWN:
        target = "sletat"
    if target == "sletat":
        return SletatAggregator()
    return MultitourAggregator()
