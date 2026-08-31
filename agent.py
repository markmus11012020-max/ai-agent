# agent/agent.py (обновить импорты)

import os
from dotenv import load_dotenv

# LangChain / LLM
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import PromptTemplate

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
        # Sletat
        search_tours_tool,
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
        # Sletat
        search_tours_tool,
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

# Инициализация LLM
llm = ChatOpenAI(
    model="minimax/minimax-m3",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base="https://api.aitunnel.ru/v1",
)

# Набор инструментов
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
    # Sletat
    search_tours_tool,
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

# Системный промпт
prompt = PromptTemplate.from_template("""
Вы — AI-ассистент с доступом к следующим инструментам:

{tools}

Используйте следующий формат:

Question: вопрос пользователя
Thought: обдумайте вопрос и выберите инструмент
Action: название инструмента, должно быть одним из [{tool_names}]
Action Input: входные данные для инструмента
Observation: результат действия
... повторяйте при необходимости ...

Final Answer: окончательный ответ на вопрос

Начнем!

Question: {input}
""")

# Создание агента
agent = create_react_agent(llm, tools, prompt=prompt)


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