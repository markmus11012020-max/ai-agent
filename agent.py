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
    "Если инструмент вернул ошибку или пустой результат — сообщите об этом пользователю."
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
        result = self._graph.invoke({"messages": [{"role": "user", "content": user_input}]})
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