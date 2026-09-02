# AI-Agent (Streamlit + LangChain + Multitour / Sletat)

AI-агент с набором инструментов (веб-поиск, погода, криптовалюты,
**поиск туров через Multitour API v2 и Sletat JSON-шлюз**, авиабилеты Multitour,
файлы, терминал, память).

Документация по туристическим шлюзам:
- Multitour API v2: <https://www.multitour.ru/api/v2/>
- Sletat JSON-шлюз: <https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json)>.

## Возможности

- 🎯 Общий вопрос — ReAct-агент на базе langgraph + OpenAI-совместимый API.
- 🌤️ Погода — Multitour API.
- 💰 Криптовалюта — CoinGecko.
- ✈️ Подобрать тур — диалоговый турагент с системным промптом.
- 🔎 **Поиск туров через Multitour API v2 и Sletat JSON-шлюз** — структурированный поиск:
  - Выбор агрегатора (Sletat / Multitour) прямо в UI.
  - Справочники (города вылета, страны, курорты, отели, типы питания, туроператоры).
  - Полноценный поиск.
  - Человеко-читаемое превью результатов (цены, рейтинги, отели, даты).
  - Актуализация цены (`ActualizePrice` / `Actualize`).
  - Сохранение заявки (`SaveTourOrder` / `CreateOrder`).

## Структура

```
.
├── agent.py              # ReAct-агент (langgraph)
├── tools.py              # Все инструменты (включая Sletat и Multitour через адаптеры)
├── run.py                # CLI-режим
├── streamlit_app.py      # UI на Streamlit (5 вкладок)
├── aggregators/
│   ├── __init__.py
│   ├── base.py            # Базовый класс TourAggregator
│   ├── factory.py         # get_aggregator() / list_aggregators()
│   ├── sletat_adapter.py  # Адаптер над sletat.SletatClient
│   └── multitour_adapter.py # Адаптер над Multitour API v2 (по токену)
├── sletat/
│   ├── __init__.py
│   └── sletat_api.py     # Клиент Sletat JSON-шлюза + парсер aaData
├── requirements.txt
├── start.bat             # Установка + запуск под Windows
├── .env                  # Переменные окружения
└── README.md
```

## Быстрый старт (Windows)

1. Установите Python 3.10+ и убедитесь, что `python` доступен в `PATH`.
2. Заполните `.env`:
   ```ini
   OPENAI_API_KEY=sk-...
   OPENAI_API_BASE=https://api.aitunnel.ru/v1
   LLM_MODEL=minimax/minimax-m3

   MULTITOUR_API_URL=https://www.multitour.ru/api/v2/
   API_KEY=<ваш_токен_Multitour>

   SLETAT_LOGIN=ваш_логин_на_sletat_ru
   SLETAT_PASSWORD=ваш_пароль
   SLETAT_BASE_URL=https://module.sletat.ru/Main.svc
   ```
   Без `API_KEY` Multitour-инструменты работать не будут.
   Без `SLETAT_LOGIN`/`SLETAT_PASSWORD` Sletat-инструменты работать не будут.
   По умолчанию агенты используют Sletat (см. `TOUR_AGGREGATOR`).
3. Запустите `start.bat`. Скрипт:
   - создаст `.venv`,
   - установит зависимости,
   - проверит синтаксис,
   - откроет `http://localhost:8501`.

## Ручной запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Использование адаптеров агрегаторов программно

```python
from aggregators import (
    get_aggregator, list_aggregators,
    SletatAggregator, MultitourAggregator,
    TourSearchParams,
)

# Инициализация любого агрегатора
for agg in list_aggregators():
    print(agg.name, agg.is_auth_configured)

agg = get_aggregator("multitour")  # или "sletat"

# Справочники
countries = agg.get_countries()
resorts = agg.get_resorts(country_id=40)

# Поиск туров
result = agg.search_and_collect(TourSearchParams(
    city_from_id=1,    # Москва
    country_id=40,     # Турция
    date_from="2026-09-01",
    nights_from=7,
    nights_to=14,
    adults=2,
))
for offer in (result["offers"] or [])[:5]:
    print(offer.to_human())
```

## Использование Sletat-инструмента напрямую

```python
from sletat import SletatClient, parse_tour_row, format_tour_for_human

client = SletatClient()  # читает SLETAT_LOGIN/SLETAT_PASSWORD из .env

# Справочники
cities = client.get_depart_cities()       # [{'Id': 1, 'Name': 'Москва'}, ...]
countries = client.get_countries()        # [{'Id': 40, 'Name': 'Турция'}, ...]

# Поиск туров
result = client.search_and_collect(
    city_from_id=1, country_id=40,
    date_from="2026-09-01", nights_from=7, adults=2,
)
```

## Инструменты агента

Имя | Описание
----|---------
`web_search` | Поиск DuckDuckGo
`http_request` | Произвольный HTTP-запрос
`read_file` / `write_file` | Файловая система
`run_command` | Терминал (с таймаутом 30 с)
`get_weather` | Погода Multitour
`get_crypto_price` | CoinGecko
`save_interaction` | Сохранить обмен в `memory.json`
`search_tours_multitour` | Ссылка на поиск туров Multitour (без API-ключа)
`search_flights` | Авиабилеты Multitour (без API-ключа)
`tours_list_aggregators` | Список агрегаторов и статус авторизации
`tours_search` | Универсальный поиск (Sletat / Multitour), параметр `aggregator='sletat'|'multitour'`
`sletat_search_tours` | Поиск только через Sletat
`multitour_search_tours_api` | Поиск только через Multitour API v2
`tours_get_depart_cities` | Справочник городов вылета (опц. `aggregator`)
`tours_get_countries` | Справочник стран (опц. `aggregator`)
`tours_get_resorts` | Курорты страны (опц. `aggregator`)
`tours_get_hotels` | Отели (опц. `aggregator`)
`tours_get_hotel_stars` | Категории отелей (опц. `aggregator`)
`tours_get_meals` | Типы питания (опц. `aggregator`)
`tours_get_tour_operators` | Туроператоры (опц. `aggregator`)
`tours_get_tour_dates` | Даты вылетов (опц. `aggregator`)
`tours_get_load_state` | Состояние поиска (опц. `aggregator`)
`tours_get_results` | Получить туры по `requestId` (опц. `aggregator`)
`tours_actualize_price` | Актуализировать цену (опц. `aggregator`)
`tours_save_order` | Сохранить заявку (опц. `aggregator`)
`sletat_format_tour` | Отформатировать строку aaData

## Документация

- [Multitour API v2](https://www.multitour.ru/api/v2/)
- [Sletat JSON-шлюз](https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json))
- [LangGraph create_react_agent](https://langchain-ai.github.io/langgraph/reference/agents/)
