@echo off
chcp 65001 >nul
setlocal ENABLEDELAYEDEXPANSION

REM ============================================================
REM   AI-Agent launcher (Streamlit)
REM   - создаёт venv при первом запуске
REM   - устанавливает зависимости
REM   - запускает streamlit_app.py
REM ============================================================

cd /d "%~dp0"

REM --- Остановка процессов и очистка кэша ---
echo [INFO] Останавливаю запущенные процессы streamlit/python...
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
echo [INFO] Очищаю кэш (__pycache__, .streamlit)...
if exist "__pycache__" rd /s /q "__pycache__" >nul 2>&1
for /d /r "%~dp0" %%d in (__pycache__) do @rd /s /q "%%d" >nul 2>&1
if exist ".streamlit\cache" rd /s /q ".streamlit\cache" >nul 2>&1
if exist "%LOCALAPPDATA%\streamlit\Cache" rd /s /q "%LOCALAPPDATA%\streamlit\Cache" >nul 2>&1
del /s /q "%~dp0*.pyc" >nul 2>&1
echo [OK] Очистка завершена.
echo.

set "PYTHON=python"
set "VENV_DIR=.venv"
set "PORT=8501"

echo ===========================================================
echo   AI-Agent ^(Sletat + LLM + Streamlit^)
echo ===========================================================
echo.

REM 1. Проверка Python
where %PYTHON% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python не найден в PATH. Установите Python 3.10+ и повторите.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYTHON% --version 2^>^&1') do set "PYVER=%%v"
echo [OK] Python %PYVER%

REM 2. Виртуальное окружение
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Создаю виртуальное окружение %VENV_DIR%...
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Не удалось создать venv.
        pause
        exit /b 1
    )
)
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

REM 3. Установка/обновление зависимостей
echo [INFO] Проверяю зависимости...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade pip >nul
"%VENV_PY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [WARN] Установка из requirements.txt не удалась. Пробую базовый набор...
    "%VENV_PY%" -m pip install --disable-pip-version-check ^
        openai langchain langchain-core langchain-community ^
        langchain-openai langgraph ^
        duckduckgo-search requests python-dotenv streamlit
)
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости.
    pause
    exit /b 1
)
echo [OK] Зависимости установлены.

REM 4. Проверка .env
if not exist ".env" goto SKIP_ENV
goto AFTER_ENV
:SKIP_ENV
echo [WARN] Файл .env не найден. Создаю шаблон...
break > .env
echo OPENAI_API_KEY=your_key_here>> .env
echo OPENAI_API_BASE=https://api.aitunnel.ru/v1>> .env
echo LLM_MODEL=minimax/minimax-m3>> .env
echo.>> .env
echo # Логин/пароль от личного кабинета Sletat.ru>> .env
echo SLETAT_LOGIN=>> .env
echo SLETAT_PASSWORD=>> .env
echo SLETAT_BASE_URL=https://module.sletat.ru/Main.svc>> .env
echo [INFO] Заполните .env (OPENAI_API_KEY, SLETAT_LOGIN, SLETAT_PASSWORD) и перезапустите.
notepad .env
pause
exit /b 0
:AFTER_ENV

REM 5. Проверка синтаксиса
echo [INFO] Проверяю синтаксис...
"%VENV_PY%" -m py_compile agent.py tools.py run.py streamlit_app.py
if errorlevel 1 (
    echo [ERROR] Синтаксические ошибки в файлах проекта.
    pause
    exit /b 1
)
echo [OK] Синтаксис в порядке.

REM 6. Запуск Streamlit
echo.
echo ===========================================================
echo   Откройте http://localhost:%PORT% в браузере
echo   Для остановки нажмите Ctrl+C
echo ===========================================================
echo.

"%VENV_PY%" -m streamlit run streamlit_app.py --server.port %PORT% --server.headless false

pause
endlocal
