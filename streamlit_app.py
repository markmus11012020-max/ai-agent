# streamlit_app.py
import streamlit as st
import json
from datetime import datetime, timedelta

# Импортируем исполнителя агента из пакета agent
from agent import agent_executor

st.set_page_config(page_title="AI-агент с инструментами", layout="wide")
st.title("🌍 AI-агент с поддержкой инструментов")

# Инициализация сессии для хранения состояния чата турагента
if "tour_chat_history" not in st.session_state:
    st.session_state.tour_chat_history = []

if "tour_stage" not in st.session_state:
    st.session_state.tour_stage = "greeting"  # greeting, questions, recommendations

# Создаем четыре вкладки
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Общий вопрос",
    "🌤️ Погода",
    "💰 Криптовалюта",
    "✈️ Подобрать тур",
    "🔎 Поиск туров Sletat",
])

# =====================================================================
# Вкладка 1 – Общий вопрос
# =====================================================================
with tab1:
    st.header("Запросы общего характера")
    example = """- Кратко расскажите последние новости об ИИ.
- Напишите короткое стихотворение о Python.
- Перечислите файлы в текущей директории."""
    st.markdown("Примеры запросов:")
    st.code(example)

    user_input = st.text_input("Ваш вопрос:", key="gen")
    if st.button("Спросить", key="gen_btn"):
        if user_input:
            with st.spinner("Агент обрабатывает запрос..."):
                result = agent_executor.invoke({"input": user_input})
                st.write("**Агент:**", result.get("output", str(result)))
        else:
            st.warning("Пожалуйста, введите вопрос.")

# =====================================================================
# Вкладка 2 – Погода
# =====================================================================
with tab2:
    st.header("🌤️ Информация о погоде")
    col1, col2 = st.columns(2)
    with col1:
        country = st.text_input("Страна", key="weather_country")
    with col2:
        city = st.text_input("Город", key="weather_city")
    date = st.date_input("Дата (необязательно)", key="weather_date")

    if st.button("Получить погоду", key="weather_btn"):
        if country and city:
            query = f"Какая погода в {city}, {country} на {date}?"
            with st.spinner("Получаю информацию о погоде..."):
                result = agent_executor.invoke({"input": query})
                st.write("**Агент:**", result.get("output", str(result)))
        else:
            st.error("Пожалуйста, укажите страну и город.")

# =====================================================================
# Вкладка 3 – Криптовалюта
# =====================================================================
with tab3:
    st.header("💰 Цены криптовалют")
    col1, col2 = st.columns(2)
    with col1:
        coin = st.selectbox(
            "Выберите криптовалюту",
            ["bitcoin", "ethereum", "ripple", "cardano", "solana"],
            key="crypto_coin",
        )
    with col2:
        currency = st.selectbox(
            "Валюта",
            ["usd", "eur", "rub"],
            key="crypto_currency",
        )
    if st.button("Получить цену", key="crypto_btn"):
        with st.spinner("Получаю цену..."):
            query = f"Сколько стоит {coin} в {currency}?"
            result = agent_executor.invoke({"input": query})
            st.write("**Агент:**", result.get("output", str(result)))

# =====================================================================
# Вкладка 4 – Подобрать тур (НОВАЯ)
# =====================================================================
with tab4:
    st.header("✈️ Подбор идеального тура")

    # Системный промпт для турагента
    TOUR_AGENT_SYSTEM_PROMPT = """Действуй как высококлассный профессиональный турагент и эксперт по международному туризму с 20-летним опытом работы. Твоя цель — подбирать идеальные путешествия, комбинируя глубокое знание рынка, искреннюю заботу о клиенте и безупречный сервис.

Твои ключевые качества и подход:

1. **Экспертность**: Ты знаешь тонкости направлений, сезонность, скрытые комиссии, особенности отельных сетей, визовые нюансы и лайфхаки для путешественников (о которых не пишут в путеводителях).

2. **Клиентоориентированность**: Ты не просто продаешь тур, ты создаешь индивидуальный опыт. Задавай уточняющие вопросы, чтобы понять скрытые потребности клиента (бюджет, состав семьи, предпочтения по пляжу, питанию, темпу поездки, активности).

3. **Практичность и честность**: Если клиент выбирает неподходящее направление (например, сезон дождей), мягко, но аргументированно предупреди об этом и предложи альтернативу. Всегда приводи конкретные цены (или ценовые диапазоны) и обосновывай, за что переплачивает или на чем экономит клиент.

4. **Стиль общения**: Профессиональный, дружелюбный, уверенный, без лишней «воды». Говори на понятном языке, структурируй информацию списками и таблицами для удобства.

**Инструкция к действию**: 
- Если это первое сообщение клиента, начни с приветствия и задай 3-4 уточняющих вопроса о его планах (бюджет, даты, состав семьи, интересы).
- После получения вводных данных предоставь структурированный разбор вариантов, включая:
  * Рекомендуемые направления/курорты с обоснованием «почему именно они»
  * Точечные рекомендации по отелям (с указанием плюсов, минусов и ценового сегмента)
  * Советы по логистике (перелеты, трансферы, виза)
  * Важные нюансы (погода, безопасность, валюта)
  * Примерный бюджет и что входит/не входит в стоимость

- Если информации недостаточно, задай дополнительные вопросы.
- Предложи ссылки на поиск авиабилетов: https://www.multitour.ru/tickets/avia/
"""

    st.markdown("""
    ### 🎯 Добро пожаловать к профессиональному турагенту!

    Я помогу вам подобрать идеальное путешествие, учитывая все ваши пожелания и бюджет.
    Расскажите о ваших планах, и я дам вам экспертные рекомендации.
    """)

    # Вывод истории чата
    st.markdown("---")
    st.subheader("💬 Диалог с турагентом")

    # Контейнер для чата
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.tour_chat_history:
            if msg["role"] == "user":
                st.write(f"**Вы:** {msg['content']}")
            else:
                st.write(f"**🧳 Турагент:** {msg['content']}")

    st.markdown("---")

    # Ввод сообщения
    col1, col2 = st.columns([4, 1])

    with col1:
        user_message = st.text_input(
            "Ваше сообщение:",
            key="tour_input",
            placeholder="Расскажите о ваших планах путешествия..."
        )

    with col2:
        send_button = st.button("📤 Отправить", key="tour_send")

    # Обработка отправки сообщения
    if send_button and user_message:
        # Добавляем сообщение пользователя в историю
        st.session_state.tour_chat_history.append({
            "role": "user",
            "content": user_message
        })

        # Формируем контекст для агента
        chat_context = "\n".join([
            f"{'Клиент' if msg['role'] == 'user' else 'Турагент'}: {msg['content']}"
            for msg in st.session_state.tour_chat_history
        ])

        # Формируем запрос к агенту с системным промптом
        full_prompt = f"""{TOUR_AGENT_SYSTEM_PROMPT}

=== ИСТОРИЯ ДИАЛОГА ===
{chat_context}

=== ОТВЕТ ТУРАГЕНТА ==="""

        with st.spinner("🔄 Турагент подбирает лучшие варианты..."):
            try:
                result = agent_executor.invoke({"input": full_prompt})
                agent_response = result.get("output", str(result))

                # Добавляем ответ агента в историю
                st.session_state.tour_chat_history.append({
                    "role": "assistant",
                    "content": agent_response
                })

                # Перезагружаем страницу для обновления чата
                st.rerun()

            except Exception as e:
                st.error(f"❌ Ошибка при обработке запроса: {e}")

    # Кнопка для очистки истории
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Начать заново", key="tour_reset"):
            st.session_state.tour_chat_history = []
            st.rerun()

    with col2:
        st.markdown("[✈️ Поиск авиабилетов](https://www.multitour.ru/tickets/avia/)", unsafe_allow_html=True)

    with col3:
        if st.button("💾 Сохранить в памяти", key="tour_save"):
            if st.session_state.tour_chat_history:
                # Сохраняем в memory.json через агент
                summary = f"Тур-сессия: {len(st.session_state.tour_chat_history)} сообщений"
                query = f"Сохрани в памяти: {summary}"
                agent_executor.invoke({"input": query})
                st.success("✅ Сохранено в памяти!")

    # Подсказки по вводу
    st.markdown("---")
    with st.expander("💡 Подсказки для быстрого поиска"):
        st.markdown("""
        **Примеры запросов:**
        - "Хочу на море в июле на 2 недели, бюджет 150k рублей на двоих"
        - "Ищу горнолыжный курорт на новый год для семьи с двумя детьми"
        - "Интересует Таиланд в январе, люблю дайвинг и острова"
        - "Нужен экономный вариант в Европу на 10 дней, я путешествую один"
        - "Хочу экзотику: Мальдивы, Бали или Карибы? Что посоветуешь?"

        **Важно указать:**
        - 📅 Даты путешествия (или месяцы)
        - 👥 Состав группы (кол-во людей, возраст детей)
        - 💰 Бюджет на человека или на всех
        - 🏖️ Тип отдыха (пляж, горы, город, активный туризм)
        - 🎯 Регион или страна интереса (если есть)
        """)

# =====================================================================
# Вкладка 5 – Поиск туров Sletat (структурированный поиск)
# =====================================================================
with tab5:
    st.header("🔎 Поиск туров через Sletat JSON-шлюз")
    st.markdown(
        "Прямая интеграция с [API Sletat.ru](https://wiki.sletat.ru/w/Шлюз_поиска_туров_(json)). "
        "Загрузите справочники, выберите параметры и получите реальные туры от 130+ туроператоров."
    )

    if "sletat_cities" not in st.session_state:
        st.session_state.sletat_cities = None
    if "sletat_countries" not in st.session_state:
        st.session_state.sletat_countries = None
    if "sletat_resorts" not in st.session_state:
        st.session_state.sletat_resorts = None
    if "sletat_meals" not in st.session_state:
        st.session_state.sletat_meals = None
    if "sletat_last_results" not in st.session_state:
        st.session_state.sletat_last_results = None
    if "sletat_last_request_id" not in st.session_state:
        st.session_state.sletat_last_request_id = None

    col_load, col_check = st.columns([1, 2])
    with col_load:
        if st.button("🔄 Загрузить справочники", key="sletat_load_dicts"):
            from sletat import SletatClient
            client = SletatClient()
            if not client.is_auth_configured:
                st.error(
                    "❌ Не заданы SLETAT_LOGIN/SLETAT_PASSWORD в `.env`.\n\n"
                    "Укажите логин и пароль от личного кабинета Sletat.ru."
                )
            else:
                with st.spinner("Загружаю города вылета и страны..."):
                    try:
                        st.session_state.sletat_cities = client.get_depart_cities()
                        st.session_state.sletat_countries = client.get_countries()
                        st.success(
                            f"OK: {len(st.session_state.sletat_cities)} городов, "
                            f"{len(st.session_state.sletat_countries)} стран"
                        )
                    except Exception as exc:
                        st.error(f"Ошибка загрузки: {exc}")
    with col_check:
        st.caption(
            "Справочники кешируются на время сессии. "
            "Требуется авторизация в `.env`: `SLETAT_LOGIN` и `SLETAT_PASSWORD`."
        )

    if st.session_state.sletat_countries:
        st.markdown("---")
        st.subheader("📋 Параметры поиска")

        countries = st.session_state.sletat_countries
        cities = st.session_state.sletat_cities or []
        c1, c2 = st.columns(2)
        with c1:
            city_options = {f"{c.get('Name','?')} (id={c.get('Id')})": c.get("Id") for c in cities}
            city_labels = ["— выберите —"] + list(city_options.keys())
            chosen_city_label = st.selectbox(
                "Город вылета", city_labels, key="sletat_city_sel"
            )
            chosen_city_id = city_options.get(chosen_city_label) if chosen_city_label != "— выберите —" else None
        with c2:
            country_options = {f"{c.get('Name','?')} (id={c.get('Id')})": c.get("Id") for c in countries}
            country_labels = ["— выберите —"] + list(country_options.keys())
            chosen_country_label = st.selectbox(
                "Страна", country_labels, key="sletat_country_sel"
            )
            chosen_country_id = country_options.get(chosen_country_label) if chosen_country_label != "— выберите —" else None

        if chosen_country_id and (
            not st.session_state.sletat_resorts
            or st.session_state.get("sletat_resorts_country") != chosen_country_id
        ):
            from sletat import SletatClient
            try:
                with st.spinner("Загружаю курорты и питания..."):
                    client = SletatClient()
                    st.session_state.sletat_resorts = client.get_resorts(chosen_country_id)
                    st.session_state.sletat_resorts_country = chosen_country_id
                    if not st.session_state.sletat_meals:
                        st.session_state.sletat_meals = client.get_meals()
            except Exception as exc:
                st.error(f"Ошибка загрузки курортов: {exc}")

        resorts = st.session_state.sletat_resorts or []
        meals = st.session_state.sletat_meals or []

        r1, r2, r3 = st.columns(3)
        with r1:
            resort_options = {f"{r.get('Name','?')} (id={r.get('Id')})": r.get("Id") for r in resorts}
            resort_labels = ["— любой —"] + list(resort_options.keys())
            chosen_resort_label = st.selectbox(
                "Курорт", resort_labels, key="sletat_resort_sel"
            )
            chosen_resort_id = resort_options.get(chosen_resort_label) if chosen_resort_label != "— любой —" else None
        with r2:
            stars_choice = st.selectbox(
                "Категория отеля", ["любая", "5*", "4*", "3*", "2*", "1*"], key="sletat_stars_sel"
            )
            chosen_stars = int(stars_choice[0]) if stars_choice != "любая" else None
        with r3:
            meal_options = {f"{m.get('Name','?')} (id={m.get('Id')})": m.get("Id") for m in meals}
            meal_labels = ["— любое —"] + list(meal_options.keys())
            chosen_meal_label = st.selectbox("Питание", meal_labels, key="sletat_meal_sel")
            chosen_meal_id = meal_options.get(chosen_meal_label) if chosen_meal_label != "— любое —" else None

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            date_from = st.date_input("Дата вылета (от)", key="sletat_date_from")
        with d2:
            nights_from = st.number_input("Ночей от", min_value=1, max_value=30, value=7, key="sletat_nights_from")
        with d3:
            nights_to = st.number_input("Ночей до", min_value=1, max_value=30, value=14, key="sletat_nights_to")
        with d4:
            adults = st.number_input("Взрослых", min_value=1, max_value=10, value=2, key="sletat_adults")

        p1, p2 = st.columns(2)
        with p1:
            price_from = st.number_input("Цена от", min_value=0, value=0, step=10000, key="sletat_price_from")
        with p2:
            price_to = st.number_input("Цена до", min_value=0, value=0, step=10000, key="sletat_price_to")

        if st.button("🚀 Найти туры", key="sletat_search_btn", type="primary"):
            if not (chosen_city_id and chosen_country_id):
                st.warning("Выберите город вылета и страну.")
            else:
                from sletat import SletatClient
                client = SletatClient()
                if not client.is_auth_configured:
                    st.error("Не заданы SLETAT_LOGIN/SLETAT_PASSWORD в `.env`")
                else:
                    kwargs = dict(
                        city_from_id=chosen_city_id,
                        country_id=chosen_country_id,
                        adults=int(adults),
                        nights_from=int(nights_from),
                        nights_to=int(nights_to),
                    )
                    if chosen_resort_id:
                        kwargs["resort_id"] = chosen_resort_id
                    if chosen_stars:
                        kwargs["hotel_stars"] = f"{chosen_stars}*"
                    if chosen_meal_id:
                        kwargs["meal_id"] = chosen_meal_id
                    if date_from:
                        kwargs["date_from"] = date_from.isoformat()
                    if price_from > 0:
                        kwargs["price_from"] = int(price_from)
                    if price_to > 0:
                        kwargs["price_to"] = int(price_to)

                    with st.spinner("⏳ Идёт поиск туров у туроператоров..."):
                        try:
                            res = client.search_and_collect(**kwargs)
                            st.session_state.sletat_last_results = res
                            st.session_state.sletat_last_request_id = res.get("requestId")
                            if res.get("error"):
                                st.error(f"Sletat: {res['error']}")
                            else:
                                tours = res.get("tours", []) or []
                                st.success(
                                    f"✅ Найдено {len(tours)} туров "
                                    f"(requestId: {res.get('requestId')})"
                                )
                        except Exception as exc:
                            st.error(f"Ошибка поиска: {exc}")

        res = st.session_state.sletat_last_results
        if res and res.get("tours"):
            st.markdown("---")
            st.subheader(f"🏖️ Результаты поиска ({len(res['tours'])})")
            from sletat import parse_tour_row, format_tour_for_human
            for i, row in enumerate(res["tours"][:30], start=1):
                with st.expander(
                    f"#{i} {format_tour_for_human(parse_tour_row(row), max_chars=200)}",
                    expanded=(i <= 3),
                ):
                    st.text(format_tour_for_human(parse_tour_row(row)))

            st.markdown("---")
            st.subheader("💳 Актуализация цены и заказ")
            tour_idx = st.number_input(
                "Номер тура из списка выше",
                min_value=1,
                max_value=min(len(res["tours"]), 30),
                value=1,
                key="sletat_tour_idx",
            )
            tour_row = res["tours"][tour_idx - 1]
            parsed = parse_tour_row(tour_row)
            tour_id = str(parsed.get("tour_id") or "")
            request_id = st.session_state.sletat_last_request_id

            if st.button("🔄 Актуализировать цену", key="sletat_actualize_btn"):
                if not (request_id and tour_id):
                    st.warning("Не удалось получить requestId/tourId.")
                else:
                    from sletat import SletatClient
                    try:
                        price_info = SletatClient().actualize_price(request_id, tour_id)
                        st.json(price_info)
                    except Exception as exc:
                        st.error(f"Ошибка: {exc}")

            with st.form(key="sletat_order_form"):
                st.markdown("##### 📝 Оформить заявку (без онлайн-оплаты)")
                name = st.text_input("Имя")
                phone = st.text_input("Телефон")
                email = st.text_input("Email (опц.)", value="")
                comment = st.text_area("Комментарий", value="")
                submitted = st.form_submit_button("📨 Отправить заявку")
                if submitted:
                    if not (name and phone):
                        st.warning("Заполните имя и телефон.")
                    elif not (request_id and tour_id):
                        st.warning("Сначала выполните поиск.")
                    else:
                        from sletat import SletatClient
                        try:
                            order_res = SletatClient().save_tour_order(
                                request_id, tour_id, name, phone, email, comment
                            )
                            st.success("✅ Заявка отправлена!")
                            st.json(order_res)
                        except Exception as exc:
                            st.error(f"Ошибка: {exc}")
    else:
        st.info("👆 Нажмите «Загрузить справочники», чтобы начать.")

# =====================================================================
# Боковая панель (Sidebar)
# =====================================================================
with st.sidebar:
    st.markdown("### ℹ️ Об агенте")
    st.info("""
    **AI-агент с инструментами**

    Версия: 1.0

    Возможности:
    - 🔍 Веб-поиск
    - 🌤️ Погода в реальном времени
    - 💰 Цены криптовалют
    - ✈️ Подбор туров
    - 🔎 Поиск туров Sletat
    - 💾 Сохранение истории
    """)

    st.markdown("---")
    st.markdown("### 🔗 Полезные ссылки")
    st.markdown("""
    - [Multitour - Авиабилеты](https://www.multitour.ru/tickets/avia/)
    - [CoinGecko - Крипто](https://coingecko.com/)
    - [Погода - Multitour](https://www.multitour.ru/)
    - [Sletat.ru Wiki](https://wiki.sletat.ru/)
    """)

    st.markdown("---")
    st.markdown("### 🔗 Полезные ссылки")
    st.markdown("""
    - [Multitour - Авиабилеты](https://www.multitour.ru/tickets/avia/)
    - [CoinGecko - Крипто](https://coingecko.com/)
    - [Погода - Multitour](https://www.multitour.ru/)
    """)