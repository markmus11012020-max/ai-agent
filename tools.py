# agent/tools.py
import os
import json
import shlex
import datetime
import subprocess
import requests
from duckduckgo_search import DDGS
from langchain_core.tools import StructuredTool

# ----------------------------------------------------------------------
# Вспомогательные инструменты
# ----------------------------------------------------------------------
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory.json")

def _load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    return []

def _save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=2)

# ----------------------------------------------------------------------
# 1. Веб-поиск (DuckDuckGo)
# ----------------------------------------------------------------------
def web_search(query: str) -> str:
    """Поиск в интернете с помощью DuckDuckGo. Возвращает фрагменты результатов."""
    ddgs = DDGS()
    results = ddgs.text(query, max_results=5)
    return "\n".join([f"{r['title']}: {r['body']}" for r in results])

# ----------------------------------------------------------------------
# 2. HTTP-запросы (requests)
# ----------------------------------------------------------------------
def http_request(url: str, method: str = "GET", headers: dict = None, body: dict = None) -> str:
    """Выполняет произвольный HTTP-запрос. Возвращает текст ответа."""
    resp = requests.request(method, url, headers=headers, json=body)
    return resp.text

# ----------------------------------------------------------------------
# 3. Работа с файловой системой
# ----------------------------------------------------------------------
def read_file(path: str) -> str:
    """Считывает файл и возвращает его содержимое."""
    with open(path, "r") as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    """Записывает содержимое в файл. Возвращает сообщение об успехе."""
    with open(path, "w") as f:
        f.write(content)
    return f"Written to {path}"

# ----------------------------------------------------------------------
# 4. Выполнение терминальных команд (ограничено, безопасно)
# ----------------------------------------------------------------------
def run_command(cmd: str) -> str:
    """
    Выполняет терминальную команду с помощью subprocess.
    Ограничено таймаутом 30 секунд.
    """
    result = subprocess.run(
        shlex.split(cmd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\nreturncode:{result.returncode}"

# ----------------------------------------------------------------------
# 5. Получить погоду (Multitour API)
# ----------------------------------------------------------------------
def get_weather(country: str, city: str, date: str = None) -> str:
    """
    Получает информацию о погоде с помощью бесплатного API multitour.ru.
    Ожидает параметры: country, city, необязательно date.
    """
    url = "https://www.multitour.ru/api/weather"
    params = {"country": country, "city": city}
    if date:
        params["date"] = date
    resp = requests.get(url, params=params)
    return resp.json()

# ----------------------------------------------------------------------
# 6. Узнать курс криптовалюты (CoinGecko API, без ключа)
# ----------------------------------------------------------------------
def get_crypto_price(coin: str, currency: str = "usd") -> float:
    """
    Возвращает цену криптовалюты от CoinGecko.
    Пример: coin='bitcoin', currency='usd'.
    """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"
    resp = requests.get(url).json()
    return resp[coin][currency]

# ----------------------------------------------------------------------
# 7. Работа с памятью (сохранение истории диалога)
# ----------------------------------------------------------------------
def load_memory() -> list:
    """Загружает историю диалога из memory.json."""
    return _load_memory()

def save_interaction(user_input: str, agent_output: str) -> str:
    """Сохраняет один обмен в память. Возвращает сообщение об успехе."""
    memory = _load_memory()
    memory.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user_input,
        "assistant": agent_output,
    })
    _save_memory(memory)
    return "Interaction saved."

# ----------------------------------------------------------------------
# Создание LangChain-инструментов
# ----------------------------------------------------------------------
web_search_tool = StructuredTool.from_function(
    web_search,
    name="web_search",
    description="Поиск в интернете для получения информации",
)

http_request_tool = StructuredTool.from_function(
    http_request,
    name="http_request",
    description="Выполняет произвольный HTTP-запрос",
)

read_file_tool = StructuredTool.from_function(
    read_file,
    name="read_file",
    description="Считывает файл с файловой системы",
)

write_file_tool = StructuredTool.from_function(
    write_file,
    name="write_file",
    description="Записывает содержимое в файл",
)

run_command_tool = StructuredTool.from_function(
    run_command,
    name="run_command",
    description="Выполняет терминальную команду (ограничено, безопасно)",
)

get_weather_tool = StructuredTool.from_function(
    get_weather,
    name="get_weather",
    description="Получает информацию о погоде с помощью multitour.ru",
)

get_crypto_price_tool = StructuredTool.from_function(
    get_crypto_price,
    name="get_crypto_price",
    description="Получает цену криптовалюты с помощью CoinGecko API",
)

save_interaction_tool = StructuredTool.from_function(
    save_interaction,
    name="save_interaction",
    description="Сохраняет обмен между пользователем и агентом в память",
)

# agent/tools.py (добавить в конец файла)

# -----------------------------------------------------------------------
# 8. Поиск туров (интеграция с Multitour)
# -----------------------------------------------------------------------
def search_tours(destination: str, departure_date: str, return_date: str, 
                 budget: str = None, travelers: int = 1) -> str:
    """
    Поиск туров на Multitour.
    Возвращает ссылку на поиск и рекомендации.
    """
    # Формируем URL для поиска туров
    url = f"https://www.multitour.ru/tours/?destination={destination}&from={departure_date}&to={return_date}"

    response = f"""
    🏨 Поиск туров для {travelers} чел. в {destination}
    📅 Даты: {departure_date} - {return_date}
    💰 Бюджет: {budget or 'не указан'}

    🔗 Ссылка для поиска: {url}

    Рекомендую также проверить:
    - ✈️ Авиабилеты: https://www.multitour.ru/tickets/avia/
    - 🏨 Отели напрямую: booking.com, agoda.com
    """
    return response

def search_flights(departure_city: str, destination_city: str, 
                   departure_date: str, return_date: str = None) -> str:
    """
    Поиск авиабилетов на Multitour.
    """
    url = f"https://www.multitour.ru/tickets/avia/?from={departure_city}&to={destination_city}&date={departure_date}"
    if return_date:
        url += f"&return={return_date}"

    return f"""
    ✈️ Поиск авиабилетов
    📍 Маршрут: {departure_city} → {destination_city}
    📅 Дата вылета: {departure_date}
    {f'📅 Дата возврата: {return_date}' if return_date else ''}

    🔗 Перейти к поиску: {url}
    """

# Создание инструментов LangChain
multitour_search_tours_tool = StructuredTool.from_function(
    search_tours,
    name="search_tours_multitour",
    description="Поиск туров по направлениям, датам и бюджету (Multitour URL)",
)

search_flights_tool = StructuredTool.from_function(
    search_flights,
    name="search_flights",
    description="Поиск авиабилетов на Multitour",
)


# -----------------------------------------------------------------------
# 8. Sletat.ru — JSON-шлюз поиска туров
# Документация: https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json)
# -----------------------------------------------------------------------
from sletat import (
    SletatClient,
    parse_tour_row,
    format_tour_for_human,
)

_client_cache: dict = {}


def _client() -> SletatClient:
    """Ленивая инициализация клиента Sletat."""
    if "client" not in _client_cache:
        _client_cache["client"] = SletatClient()
    return _client_cache["client"]


def get_depart_cities() -> str:
    """Список городов вылета Sletat (Id, Name). JSON-строка."""
    return json.dumps(_client().get_depart_cities(), ensure_ascii=False)


def get_countries() -> str:
    """Список направлений (стран) Sletat (Id, Name). JSON-строка."""
    return json.dumps(_client().get_countries(), ensure_ascii=False)


def get_resorts(country_id: int) -> str:
    """Список курортов выбранной страны Sletat."""
    return json.dumps(_client().get_resorts(country_id), ensure_ascii=False)


def get_hotels(country_id: int = None, resort_id: int = None, stars: int = None) -> str:
    """Список отелей Sletat с фильтрами по стране/курорту/категории."""
    return json.dumps(
        _client().get_hotels(country_id=country_id, resort_id=resort_id, star=stars),
        ensure_ascii=False,
    )


def get_hotel_stars() -> str:
    """Категории отелей Sletat (Id, Name)."""
    return json.dumps(_client().get_hotel_stars(), ensure_ascii=False)


def get_meals() -> str:
    """Справочник типов питания Sletat (AI, HB, BB)."""
    return json.dumps(_client().get_meals(), ensure_ascii=False)


def get_tour_operators() -> str:
    """Справочник туроператоров Sletat (Id, Name)."""
    return json.dumps(_client().get_tour_operators(), ensure_ascii=False)


def get_tour_dates(city_from_id: int, country_id: int, resort_id: int = None) -> str:
    """Список доступных дат вылетов (YYYY-MM-DD)."""
    return json.dumps(
        _client().get_tour_dates(city_from_id, country_id, resort_id),
        ensure_ascii=False,
    )


def search_tours(
    city_from_id: int,
    country_id: int,
    resort_id: int = None,
    hotel_stars: int = None,
    meal_id: int = None,
    date_from: str = None,
    date_to: str = None,
    nights_from: int = None,
    nights_to: int = None,
    adults: int = 2,
    children: int = 0,
    price_from: int = None,
    price_to: int = None,
    max_results: int = 5,
) -> str:
    """Полноценный поиск туров через Sletat. Возвращает requestId и превью туров."""
    result = _client().search_and_collect(
        city_from_id=city_from_id,
        country_id=country_id,
        resort_id=resort_id,
        hotel_stars=hotel_stars,
        meal_id=meal_id,
        date_from=date_from,
        date_to=date_to,
        nights_from=nights_from,
        nights_to=nights_to,
        adults=adults,
        children=children,
        price_from=price_from,
        price_to=price_to,
    )
    if result.get("error"):
        return json.dumps(
            {"error": result["error"], "requestId": result.get("requestId")},
            ensure_ascii=False,
        )
    tours = result.get("tours", []) or []
    head = [
        format_tour_for_human(parse_tour_row(row)) for row in tours[:max_results]
    ]
    payload = {
        "requestId": result.get("requestId"),
        "found": len(tours),
        "shown": min(len(tours), max_results),
        "tours_preview": head,
    }
    return json.dumps(payload, ensure_ascii=False)


def get_tour_load_state(request_id: str) -> str:
    """Состояние загрузки результатов поиска по requestId."""
    return json.dumps(_client().get_load_state(request_id), ensure_ascii=False)


def get_tour_results(request_id: str, max_results: int = 10) -> str:
    """Возвращает туры по requestId в человеко-читаемом виде."""
    raw = _client().get_results(request_id)
    aa = raw.get("aaData", []) if isinstance(raw, dict) else []
    head = [format_tour_for_human(parse_tour_row(r)) for r in aa[:max_results]]
    return json.dumps(
        {"requestId": request_id, "found": len(aa), "tours_preview": head},
        ensure_ascii=False,
    )


def actualize_tour_price(request_id: str, tour_id: str) -> str:
    """Актуализация цены тура. tour_id — значение поля aaData[i][1]."""
    return json.dumps(
        _client().actualize_price(request_id, tour_id), ensure_ascii=False
    )


def save_tour_order(
    request_id: str,
    tour_id: str,
    user_name: str,
    user_phone: str,
    user_email: str = "",
    comment: str = "",
) -> str:
    """Сохраняет заявку на тур (без онлайн-оплаты) в системе Sletat."""
    return json.dumps(
        _client().save_tour_order(
            request_id, tour_id, user_name, user_phone, user_email, comment
        ),
        ensure_ascii=False,
    )


def format_sletat_tour(aa_data_row_json: str) -> str:
    """Преобразует одну строку aaData (JSON-массив) в человеко-читаемое описание тура."""
    try:
        row = json.loads(aa_data_row_json)
    except Exception as exc:
        return f"Ошибка разбора JSON: {exc}"
    return format_tour_for_human(parse_tour_row(row))


# Обёртки LangChain
get_depart_cities_tool = StructuredTool.from_function(
    get_depart_cities, name="sletat_get_depart_cities",
    description="Список городов вылета Sletat (Id, Name)",
)
get_countries_tool = StructuredTool.from_function(
    get_countries, name="sletat_get_countries",
    description="Список стран Sletat (Id, Name)",
)
get_resorts_tool = StructuredTool.from_function(
    get_resorts, name="sletat_get_resorts",
    description="Список курортов Sletat по country_id (int)",
)
get_hotels_tool = StructuredTool.from_function(
    get_hotels, name="sletat_get_hotels",
    description="Список отелей Sletat (опц. country_id, resort_id, stars)",
)
get_hotel_stars_tool = StructuredTool.from_function(
    get_hotel_stars, name="sletat_get_hotel_stars",
    description="Категории отелей Sletat",
)
get_meals_tool = StructuredTool.from_function(
    get_meals, name="sletat_get_meals",
    description="Справочник типов питания Sletat",
)
get_tour_operators_tool = StructuredTool.from_function(
    get_tour_operators, name="sletat_get_tour_operators",
    description="Справочник туроператоров Sletat",
)
get_tour_dates_tool = StructuredTool.from_function(
    get_tour_dates, name="sletat_get_tour_dates",
    description="Даты вылетов Sletat (city_from_id, country_id, опц. resort_id)",
)
search_tours_tool = StructuredTool.from_function(
    search_tours, name="sletat_search_tours",
    description=(
        "Полноценный поиск туров Sletat. Обязательные: city_from_id, country_id. "
        "Опц.: resort_id, hotel_stars, meal_id, date_from/to (YYYY-MM-DD), "
        "nights_from/to, adults, children, price_from/to. "
        "Возвращает requestId и превью туров."
    ),
)
get_tour_load_state_tool = StructuredTool.from_function(
    get_tour_load_state, name="sletat_get_load_state",
    description="Статус загрузки туров по requestId",
)
get_tour_results_tool = StructuredTool.from_function(
    get_tour_results, name="sletat_get_results",
    description="Получить туры по requestId",
)
actualize_tour_price_tool = StructuredTool.from_function(
    actualize_tour_price, name="sletat_actualize_price",
    description="Актуализировать цену тура (requestId, tour_id)",
)
save_tour_order_tool = StructuredTool.from_function(
    save_tour_order, name="sletat_save_order",
    description="Сохранить заявку на тур в Sletat (без онлайн-оплаты)",
)
format_sletat_tour_tool = StructuredTool.from_function(
    format_sletat_tour, name="sletat_format_tour",
    description="Преобразовать строку aaData в человеко-читаемое описание тура",
)

# Обновляем экспорт
__all__ = [
    "web_search_tool",
    "http_request_tool",
    "read_file_tool",
    "write_file_tool",
    "run_command_tool",
    "get_weather_tool",
    "get_crypto_price_tool",
    "save_interaction_tool",
    "multitour_search_tours_tool",
    "search_flights_tool",
    # Sletat
    "get_depart_cities_tool",
    "get_countries_tool",
    "get_resorts_tool",
    "get_hotels_tool",
    "get_hotel_stars_tool",
    "get_meals_tool",
    "get_tour_operators_tool",
    "get_tour_dates_tool",
    "get_tour_load_state_tool",
    "get_tour_results_tool",
    "actualize_tour_price_tool",
    "save_tour_order_tool",
    "format_sletat_tour_tool",
]


def actualize_tour_price(request_id: str, tour_id: str) -> str:
    """Актуализация цены тура. tour_id — значение поля aaData[i][1]."""
    return json.dumps(
        _client().actualize_price(request_id, tour_id), ensure_ascii=False
    )


def save_tour_order(
    request_id: str,
    tour_id: str,
    user_name: str,
    user_phone: str,
    user_email: str = "",
    comment: str = "",
) -> str:
    """Сохраняет заявку на тур (без онлайн-оплаты) в системе Sletat."""
    return json.dumps(
        _client().save_tour_order(
            request_id, tour_id, user_name, user_phone, user_email, comment
        ),
        ensure_ascii=False,
    )


def format_sletat_tour(aa_data_row_json: str) -> str:
    """Преобразует одну строку aaData (JSON-массив) в человеко-читаемое описание тура."""
    try:
        row = json.loads(aa_data_row_json)
    except Exception as exc:
        return f"Ошибка разбора JSON: {exc}"
    return format_tour_for_human(parse_tour_row(row))

