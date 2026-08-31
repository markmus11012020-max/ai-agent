# AI-Agent (Streamlit + LangChain + Sletat.ru)

AI-агент с набором инструментов (веб-поиск, погода, криптовалюты, **поиск туров
через Sletat JSON-шлюз**, авиабилеты Multitour, файлы, терминал, память).

Документация по туристическому шлюзу: <https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json)>.

## Возможности

- 🎯 Общий вопрос — ReAct-агент на базе langgraph + OpenAI-совместимый API.
- 🌤️ Погода — Multitour API.
- 💰 Криптовалюта — CoinGecko.
- ✈️ Подобрать тур — диалоговый турагент с системным промптом.
- 🔎 **Поиск туров Sletat** — структурированный поиск:
  - Справочники (города вылета, страны, курорты, отели, типы питания, туроператоры).
  - Полноценный поиск с поллингом состояния у 130+ туроператоров.
  - Человеко-читаемое превью результатов (цены, рейтинги, отели, даты).
  - Актуализация цены (`ActualizePrice`).
  - Сохранение заявки (`SaveTourOrder`).

## Структура

```
.
├── agent.py              # ReAct-агент (langgraph), 24 инструмента
├── tools.py              # Все инструменты (включая Sletat)
├── run.py                # CLI-режим
├── streamlit_app.py      # UI на Streamlit (5 вкладок)
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

   SLETAT_LOGIN=ваш_логин_на_sletat_ru
   SLETAT_PASSWORD=ваш_пароль
   SLETAT_BASE_URL=https://module.sletat.ru/Main.svc
   ```
   *(Логин/пароль — от личного кабинета Sletat.ru. Без них поиск туров работать не будет.)*
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

## Использование Sletat-инструмента программно

```python
from sletat import SletatClient, parse_tour_row, format_tour_for_human

client = SletatClient()  # читает SLETAT_LOGIN/SLETAT_PASSWORD из .env

# 1) Справочники
cities = client.get_depart_cities()       # [{'Id': 1, 'Name': 'Москва'}, ...]
countries = client.get_countries()        # [{'Id': 40, 'Name': 'Турция'}, ...]
resorts = client.get_resorts(country_id=40)

# 2) Поиск туров (выполняется асинхронно внутри API,
#    клиент сам дожидается готовности)
result = client.search_and_collect(
    city_from_id=1,         # Москва
    country_id=40,          # Турция
    date_from="2026-09-01",
    nights_from=7,
    nights_to=14,
    adults=2,
)

print("requestId:", result["requestId"])
for row in result["tours"][:5]:
    print(format_tour_for_human(parse_tour_row(row)))
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
`search_tours_multitour` | Поиск тура по URL Multitour
`search_flights` | Авиабилеты Multitour
`sletat_get_depart_cities` | Sletat: города вылета
`sletat_get_countries` | Sletat: страны
`sletat_get_resorts` | Sletat: курорты
`sletat_get_hotels` | Sletat: отели
`sletat_get_hotel_stars` | Sletat: категории отелей
`sletat_get_meals` | Sletat: типы питания
`sletat_get_tour_operators` | Sletat: туроператоры
`sletat_get_tour_dates` | Sletat: даты вылетов
`sletat_search_tours` | Sletat: поиск туров (с поллингом)
`sletat_get_load_state` | Sletat: статус загрузки
`sletat_get_results` | Sletat: получить туры по requestId
`sletat_actualize_price` | Sletat: актуализировать цену
`sletat_save_order` | Sletat: сохранить заявку
`sletat_format_tour` | Отформатировать строку aaData

## Документация

- [Sletat JSON-шлюз](https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json))
- [LangGraph create_react_agent](https://langchain-ai.github.io/langgraph/reference/agents/)
