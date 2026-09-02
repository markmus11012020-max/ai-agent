# agent/agent.py (обновить импорты)

import os
from dotenv import load_dotenv

# LangChain / LLM
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent




# Импорт инструментов. Поддерживаем запуск как из пакета, так и напрямую.
try:
    from .tools import (  # type: ignore
        web_search_tool,
        http_request_tool,
        read_file_tool,
        write_file_tool,
        run_command_tool,
        get_weather_tool,
        get_crypto_price_tool,
        save_interaction_tool,
        multitour_search_tours_tool,
        search_flights_tool,
        # Универсальный фасад агрегаторов (sletat | multitour)
        list_aggregators_tool,
        search_tours_tool,
        search_sletat_tool,
        search_multitour_tool,
        get_depart_cities_tool,
        get_countries_tool,
        get_resorts_tool,
        get_hotels_tool,
        get_hotel_stars_tool,
        get_meals_tool,
        get_tour_operators_tool,
        get_tour_dates_tool,
        get_tour_load_state_tool,
        get_tour_results_tool,
        actualize_tour_price_tool,
        save_tour_order_tool,
        format_sletat_tour_tool,
    )
except ImportError:  # запуск как скрипт
    from tools import (  # type: ignore
        web_search_tool,
        http_request_tool,
        read_file_tool,
        write_file_tool,
        run_command_tool,
        get_weather_tool,
        get_crypto_price_tool,
        save_interaction_tool,
        multitour_search_tours_tool,
        search_flights_tool,
        # Универсальный фасад агрегаторов (sletat | multitour)
        list_aggregators_tool,
        search_tours_tool,
        search_sletat_tool,
        search_multitour_tool,
        get_depart_cities_tool,
        get_countries_tool,
        get_resorts_tool,
        get_hotels_tool,
        get_hotel_stars_tool,
        get_meals_tool,
        get_tour_operators_tool,
        get_tour_dates_tool,
        get_tour_load_state_tool,
        get_tour_results_tool,
        actualize_tour_price_tool,
        save_tour_order_tool,
        format_sletat_tour_tool,
    )

# Загрузка переменных окружения
load_dotenv()

tools = [
    web_search_tool,
    http_request_tool,
    read_file_tool,
    write_file_tool,
    run_command_tool,
    get_weather_tool,
    get_crypto_price_tool,
    save_interaction_tool,
    multitour_search_tours_tool,
    search_flights_tool,
    # Универсальный фасад агрегаторов туров (sletat | multitour)
    list_aggregators_tool,
    search_tours_tool,
    search_sletat_tool,
    search_multitour_tool,
    get_depart_cities_tool,
    get_countries_tool,
    get_resorts_tool,
    get_hotels_tool,
    get_hotel_stars_tool,
    get_meals_tool,
    get_tour_operators_tool,
    get_tour_dates_tool,
    get_tour_load_state_tool,
    get_tour_results_tool,
    actualize_tour_price_tool,
    save_tour_order_tool,
    format_sletat_tour_tool,
]


# Инициализация LLM
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "minimax/minimax-m3"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE"),
)

# Системный промпт
SYSTEM_PROMPT = (
    "Вы — AI-ассистент экосистемы Multitour / Sletat. "
    "У вас есть набор инструментов (web_search, http_request, чтение/запись файлов, "
    "выполнение команд, погода, криптовалюты, поиск туров, оформление заявок и т.д.). "
    "Используйте инструменты, когда они действительно нужны для ответа. "
    "Отвечайте на русском языке, кратко и по делу. "
    "Если инструмент вернул ошибку или пустой результат — сообщите об этом пользователю.\n\n"
    "=== ПРАВИЛА ДОСТОВЕРНОСТИ (ОБЯЗАТЕЛЬНО) ===\n"
    "1. ЗАПРЕЩЕНО выдумывать факты, цифры, даты, имена, цены, курсы валют, погоду, новости, "
    "свойства отелей, наличие туров и т.п. Если данных нет в контексте и инструмент их не вернул — "
    "прямо скажите «не нашёл подтверждения».\n"
    "2. Перед ЛЮБЫМ фактическим утверждением (новости, статистика, цены, курсы, погода, рейтинги, "
    "адреса, контакты, расписания) — сначала вызовите инструмент `web_search` (поиск через DuckDuckGo: https://duckduckgo.com/). "
    "Если DuckDuckGo вернул пусто/ошибку — попробуйте `http_request` к https://duckduckgo.com/html/?q=... "
    "или к нужному первоисточнику, и только потом формулируйте ответ со ссылкой на источник.\n"
    "3. Всегда указывайте источник: название/URL, откуда взят факт. Без источника факт не приводите.\n"
    "4. Если пользователь просит «узнай/найди/сколько стоит/какая погода/последние новости» — "
    "это сигнал, что НУЖНО вызвать инструмент, а не отвечать по памяти.\n"
    "5. Если инструмент недоступен или вернул ошибку — честно сообщите об этом, не подменяйте данные догадками.\n"
    "6. НЕ вызывайте `run_command` для проверки фактов (новости, курсы, цены, погода и т.п.) — "
    "под Windows это приводит к зависанию на 30 сек. Используйте только `web_search` (DuckDuckGo) "
    "и при необходимости `http_request` к нужному URL."
)

# Создание агента (используем встроенный системный промпт prebuilt-агента)
agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


class _AgentExecutorWrapper:
    """Совместимость со старым API: invoke({'input': str}) -> {'output': str}."""

    def __init__(self, graph):
        self._graph = graph
        self.tools = tools

    def invoke(self, payload, config=None):
        user_input = payload.get("input", "") if isinstance(payload, dict) else str(payload)

        # Извлекаем temperature из config (если передан)
        temperature = None
        if isinstance(config, dict):
            temperature = config.get("temperature")

        # Подменяем LLM с нужной температурой при необходимости
        if temperature is not None:
            try:
                # Пересоздаём агента с LLM нужной температуры
                from langchain_openai import ChatOpenAI
                import os as _os

                temp_llm = ChatOpenAI(
                    model=_os.getenv("LLM_MODEL", "minimax/minimax-m3"),
                    openai_api_key=_os.getenv("OPENAI_API_KEY"),
                    openai_api_base=_os.getenv("OPENAI_API_BASE"),
                    temperature=float(temperature),
                )
                graph = create_react_agent(temp_llm, self.tools, prompt=SYSTEM_PROMPT)
                result = graph.invoke({"messages": [{"role": "user", "content": user_input}]})
            except Exception:
                result = self._graph.invoke(
                    {"messages": [{"role": "user", "content": user_input}]}
                )
        else:
            result = self._graph.invoke(
                {"messages": [{"role": "user", "content": user_input}]}
            )

        # Достаём последний текст из сообщений
        output = ""
        if isinstance(result, dict) and "messages" in result:
            for msg in reversed(result["messages"]):
                content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                if content:
                    output = content if isinstance(content, str) else str(content)
                    break
        return {"output": output}


agent_executor = _AgentExecutorWrapper(agent)