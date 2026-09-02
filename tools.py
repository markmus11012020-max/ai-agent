# agent/tools.py — единый реестр LangChain-инструментов.
from __future__ import annotations

import os
import json
import shlex
import datetime
import subprocess

import requests
from duckduckgo_search import DDGS
from langchain_core.tools import StructuredTool

from aggregators import (
    get_aggregator,
    list_aggregators,
    TourSearchParams,
)

# === Память ===
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory.json")


def _load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    return []


def _save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=2)


# === Фасад агрегаторов ===
_AGG_CACHE = {}


def _agg(name):
    key = (name or os.getenv("TOUR_AGGREGATOR", "sletat")).lower().strip()
    if key not in ("sletat", "multitour"):
        key = "sletat"
    if key not in _AGG_CACHE:
        try:
            _AGG_CACHE[key] = get_aggregator(key)
        except Exception:
            _AGG_CACHE[key] = get_aggregator("sletat")
    return _AGG_CACHE[key]


def _norm(name):
    if name is None:
        return None
    s = str(name).strip().lower()
    return s if s in ("sletat", "multitour") else None


def list_aggregators_status():
    out = []
    for a in list_aggregators():
        try:
            cfg = bool(getattr(a, "is_auth_configured", False))
        except Exception as exc:
            cfg = "ошибка: " + str(exc)
        out.append({"aggregator": a.name, "auth_configured": cfg})
    return json.dumps(out, ensure_ascii=False)


def _offers_to_payload(result, max_results=5):
    offers = (result or {}).get("offers") or []
    return {
        "requestId": (result or {}).get("requestId"),
        "aggregator": (result or {}).get("_aggregator"),
        "found": len(offers),
        "shown": min(len(offers), max_results),
        "tours_preview": [o.to_human() for o in offers[:max_results]],
        "error": (result or {}).get("error"),
    }


# === 1. Веб-поиск (DuckDuckGo) ===
def web_search(query):
    """Поиск через DuckDuckGo. Используется как основной инструмент верификации фактов."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as exc:
        return f"Ошибка поиска DuckDuckGo: {exc}"
    if not results:
        return "По DuckDuckGo ничего не найдено. Уточните запрос."
    lines = []
    for r in results:
        title = r.get("title") or r.get("Title") or ""
        body = r.get("body") or r.get("Body") or ""
        href = r.get("href") or r.get("Url") or r.get("url") or ""
        lines.append(f"{title}: {body}\nСсылка: {href}")
    return "\n\n".join(lines)


# === 2. HTTP ===
def http_request(url, method="GET", headers=None, body=None):
    resp = requests.request(method, url, headers=headers, json=body)
    return resp.text


# === 3. Файлы ===
def read_file(path):
    with open(path, "r") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"Written to {path}"


# === 4. Терминал ===
# Безопасный whitelist команд: блокируем попытки запуска произвольных бинарников
# (например, "date" под Windows, которые вешают subprocess на 30 секунд).
_ALLOWED_CMDS = {
    # Windows
    "dir", "cd", "echo", "type", "copy", "move", "del", "ren", "cls",
    "where", "whoami", "hostname", "ver", "systeminfo", "tasklist",
    "set", "findstr", "more", "sort", "powershell", "cmd", "python", "pip",
    # POSIX
    "ls", "pwd", "cat", "head", "tail", "grep", "find", "wc", "echo",
    "ps", "uname", "whoami", "date", "env", "which",
}


def run_command(cmd):
    # Кроссплатформенный split: POSIX (shlex) — иначе fallback на Windows-режим.
    try:
        args = shlex.split(cmd, posix=(os.name != "nt"))
    except ValueError:
        args = cmd.split()
    if not args:
        return "error: пустая команда"
    exe = os.path.basename(args[0]).lower()
    # Снимаем расширение .exe/.cmd/.bat для сравнения с whitelist
    for ext in (".exe", ".cmd", ".bat", ".ps1"):
        if exe.endswith(ext):
            exe = exe[: -len(ext)]
            break
    if exe not in _ALLOWED_CMDS:
        return (
            f"error: команда '{exe}' запрещена политикой безопасности. "
            "Используйте web_search / http_request для проверки фактов."
        )
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=15, shell=False
        )
    except FileNotFoundError:
        return f"error: команда '{exe}' не найдена в PATH"
    except subprocess.TimeoutExpired:
        return f"error: команда '{exe}' превысила таймаут 15 сек"
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\nreturncode:{result.returncode}"


# === 5. Погода ===
def get_weather(country, city, date=None):
    url = "https://www.multitour.ru/api/weather"
    params = {"country": country, "city": city}
    if date:
        params["date"] = date
    return requests.get(url, params=params).json()


# === 6. Криптовалюты ===
def get_crypto_price(coin="bitcoin", currency="usd"):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"
    return requests.get(url).json()[coin][currency]


# === 7. Память ===
def load_memory():
    return _load_memory()


def save_interaction(user_input, agent_output):
    memory = _load_memory()
    memory.append({"timestamp": datetime.datetime.now().isoformat(),
                   "user": user_input, "assistant": agent_output})
    _save_memory(memory)
    return "Interaction saved."


# === 8. Multitour (web-only) ===
def search_tours(destination, departure_date, return_date,
                 budget=None, travelers=1):
    url = (f"https://www.multitour.ru/tours/?destination={destination}"
           f"&from={departure_date}&to={return_date}")
    return (
        f"\n🏨 Поиск туров для {travelers} чел. в {destination}\n"
        f"📅 Даты: {departure_date} - {return_date}\n"
        f"💰 Бюджет: {budget or 'не указан'}\n\n"
        f"🔗 Ссылка: {url}\n"
    )


def search_flights(departure_city, destination_city,
                   departure_date, return_date=None):
    url = (f"https://www.multitour.ru/tickets/avia/?from={departure_city}"
           f"&to={destination_city}&date={departure_date}")
    if return_date:
        url += f"&return={return_date}"
    return f"\n✈️ Авиа: {departure_city} → {destination_city} ({departure_date})\n🔗 {url}\n"


# === 9. Универсальный фасад агрегаторов туров ===
def search_tours_universal(aggregator=None, city_from_id=None, country_id=None,
                           resort_id=None, hotel_stars=None, meal_id=None,
                           date_from=None, date_to=None,
                           nights_from=None, nights_to=None,
                           adults=2, children=0,
                           price_from=None, price_to=None,
                           max_results=5):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    agg = _agg(name)
    params = TourSearchParams(
        city_from_id=city_from_id, country_id=country_id,
        resort_id=resort_id, hotel_stars=hotel_stars, meal_id=meal_id,
        date_from=date_from, date_to=date_to,
        nights_from=nights_from, nights_to=nights_to,
        adults=adults, children=children,
        price_from=price_from, price_to=price_to,
    )
    result = agg.search_and_collect(params)
    result["_aggregator"] = agg.name
    return json.dumps(_offers_to_payload(result, max_results), ensure_ascii=False)


def search_sletat(city_from_id, country_id,
                  resort_id=None, hotel_stars=None, meal_id=None,
                  date_from=None, date_to=None,
                  nights_from=None, nights_to=None,
                  adults=2, children=0,
                  price_from=None, price_to=None,
                  max_results=5):
    return search_tours_universal(
        "sletat", city_from_id, country_id, resort_id, hotel_stars,
        meal_id, date_from, date_to, nights_from, nights_to,
        adults, children, price_from, price_to, max_results,
    )


def search_multitour_api(city_from_id, country_id,
                         resort_id=None, hotel_stars=None, meal_id=None,
                         date_from=None, date_to=None,
                         nights_from=None, nights_to=None,
                         adults=2, children=0,
                         price_from=None, price_to=None,
                         max_results=5):
    return search_tours_universal(
        "multitour", city_from_id, country_id, resort_id, hotel_stars,
        meal_id, date_from, date_to, nights_from, nights_to,
        adults, children, price_from, price_to, max_results,
    )


# === Справочники (универсальные) ===
def get_depart_cities(aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_depart_cities(), ensure_ascii=False)


def get_countries(aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_countries(), ensure_ascii=False)


def get_resorts(country_id, aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_resorts(country_id), ensure_ascii=False)


def get_hotels(aggregator=None, country_id=None, resort_id=None, stars=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(
        _agg(name).get_hotels(country_id=country_id, resort_id=resort_id, stars=stars),
        ensure_ascii=False,
    )


def get_hotel_stars(aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_hotel_stars(), ensure_ascii=False)


def get_meals(aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_meals(), ensure_ascii=False)


def get_tour_operators(aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_tour_operators(), ensure_ascii=False)


def get_tour_dates(city_from_id, country_id, aggregator=None, resort_id=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(
        _agg(name).get_tour_dates(city_from_id, country_id, resort_id),
        ensure_ascii=False,
    )


# === Состояние / Результаты / Заказ ===
def get_tour_load_state(request_id, aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(_agg(name).get_load_state(request_id), ensure_ascii=False)


def get_tour_results(request_id, aggregator=None, max_results=10):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    offers = _agg(name).get_results(request_id, max_results=max_results)
    payload = {
        "requestId": request_id,
        "aggregator": name,
        "found": len(offers),
        "tours_preview": [o.to_human() for o in offers[:max_results]],
    }
    return json.dumps(payload, ensure_ascii=False)


def actualize_tour_price(request_id, tour_id, aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(
        _agg(name).actualize_price(request_id, tour_id), ensure_ascii=False
    )


def save_tour_order(request_id, tour_id, user_name, user_phone,
                    user_email="", comment="", aggregator=None):
    name = _norm(aggregator) or os.getenv("TOUR_AGGREGATOR", "sletat")
    return json.dumps(
        _agg(name).save_tour_order(
            request_id, tour_id, user_name, user_phone, user_email, comment
        ),
        ensure_ascii=False,
    )


def format_sletat_tour(aa_data_row_json):
    try:
        from sletat import parse_tour_row, format_tour_for_human
        row = json.loads(aa_data_row_json)
        return format_tour_for_human(parse_tour_row(row))
    except Exception as exc:
        return f"Ошибка разбора JSON: {exc}"


# === Обёртки LangChain StructuredTool ===
web_search_tool = StructuredTool.from_function(
    web_search, name="web_search",
    description="Поиск в интернете (DuckDuckGo).",
)
http_request_tool = StructuredTool.from_function(
    http_request, name="http_request",
    description="Произвольный HTTP-запрос (method, headers, body).",
)
read_file_tool = StructuredTool.from_function(
    read_file, name="read_file",
    description="Считать файл по абсолютному пути.",
)
write_file_tool = StructuredTool.from_function(
    write_file, name="write_file",
    description="Записать текст в файл.",
)
run_command_tool = StructuredTool.from_function(
    run_command, name="run_command",
    description="Выполнить терминальную команду (timeout=30 с).",
)
get_weather_tool = StructuredTool.from_function(
    get_weather, name="get_weather",
    description="Погода через Multitour API (country, city, опц. date).",
)
get_crypto_price_tool = StructuredTool.from_function(
    get_crypto_price, name="get_crypto_price",
    description="Цена криптовалюты CoinGecko.",
)
save_interaction_tool = StructuredTool.from_function(
    save_interaction, name="save_interaction",
    description="Сохранить обмен user→assistant в memory.json.",
)
multitour_search_tours_tool = StructuredTool.from_function(
    search_tours, name="search_tours_multitour",
    description="Ссылка на поиск туров Multitour (без API-ключа).",
)
search_flights_tool = StructuredTool.from_function(
    search_flights, name="search_flights",
    description="Ссылка на поиск авиа Multitour.",
)
list_aggregators_tool = StructuredTool.from_function(
    list_aggregators_status, name="tours_list_aggregators",
    description="Список агрегаторов туров и статус авторизации.",
)
search_tours_tool = StructuredTool.from_function(
    search_tours_universal, name="tours_search",
    description="Поиск туров через агрегатор. aggregator='sletat'|'multitour'.",
)
search_sletat_tool = StructuredTool.from_function(
    search_sletat, name="sletat_search_tours",
    description="Поиск туров строго через Sletat (SLETAT_LOGIN/SLETAT_PASSWORD).",
)
search_multitour_tool = StructuredTool.from_function(
    search_multitour_api, name="multitour_search_tours_api",
    description="Поиск туров через Multitour API v2 (MULTITOUR_TOKEN/API_KEY).",
)
get_depart_cities_tool = StructuredTool.from_function(
    get_depart_cities, name="tours_get_depart_cities",
    description="Города вылета (опц. aggregator).",
)
get_countries_tool = StructuredTool.from_function(
    get_countries, name="tours_get_countries",
    description="Справочник стран (опц. aggregator).",
)
get_resorts_tool = StructuredTool.from_function(
    get_resorts, name="tours_get_resorts",
    description="Курорты страны (country_id, опц. aggregator).",
)
get_hotels_tool = StructuredTool.from_function(
    get_hotels, name="tours_get_hotels",
    description="Отели (опц. aggregator, country_id, resort_id, stars).",
)
get_hotel_stars_tool = StructuredTool.from_function(
    get_hotel_stars, name="tours_get_hotel_stars",
    description="Категории отелей (опц. aggregator).",
)
get_meals_tool = StructuredTool.from_function(
    get_meals, name="tours_get_meals",
    description="Типы питания (опц. aggregator).",
)
get_tour_operators_tool = StructuredTool.from_function(
    get_tour_operators, name="tours_get_tour_operators",
    description="Туроператоры (опц. aggregator).",
)
get_tour_dates_tool = StructuredTool.from_function(
    get_tour_dates, name="tours_get_tour_dates",
    description="Даты вылетов (city_from_id, country_id, опц. aggregator, resort_id).",
)
get_tour_load_state_tool = StructuredTool.from_function(
    get_tour_load_state, name="tours_get_load_state",
    description="Состояние загрузки (requestId, опц. aggregator).",
)
get_tour_results_tool = StructuredTool.from_function(
    get_tour_results, name="tours_get_results",
    description="Получить туры по requestId (опц. aggregator, max_results).",
)
actualize_tour_price_tool = StructuredTool.from_function(
    actualize_tour_price, name="tours_actualize_price",
    description="Актуализировать цену тура (requestId, tour_id, опц. aggregator).",
)
save_tour_order_tool = StructuredTool.from_function(
    save_tour_order, name="tours_save_order",
    description="Сохранить заявку (requestId, tour_id, имя, телефон, опц. aggregator).",
)
format_sletat_tour_tool = StructuredTool.from_function(
    format_sletat_tour, name="sletat_format_tour",
    description="Преобразовать строку Sletat aaData (JSON) в человеко-читаемое описание.",
)

__all__ = [
    "web_search_tool", "http_request_tool", "read_file_tool", "write_file_tool",
    "run_command_tool", "get_weather_tool", "get_crypto_price_tool",
    "save_interaction_tool", "multitour_search_tours_tool", "search_flights_tool",
    "list_aggregators_tool", "search_tours_tool", "search_sletat_tool",
    "search_multitour_tool", "get_depart_cities_tool", "get_countries_tool",
    "get_resorts_tool", "get_hotels_tool", "get_hotel_stars_tool",
    "get_meals_tool", "get_tour_operators_tool", "get_tour_dates_tool",
    "get_tour_load_state_tool", "get_tour_results_tool",
    "actualize_tour_price_tool", "save_tour_order_tool",
    "format_sletat_tour_tool",
]
