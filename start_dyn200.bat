@echo off
chcp 65001 >nul
echo ===========================================
echo   DYN-200 Torque Sensor Monitor
echo ===========================================
echo.

REM Проверка существования необходимых файлов
if not exist "requirements.txt" (
    echo [ОШИБКА] Файл requirements.txt не найден!
    echo Убедитесь, что вы запускаете батник из папки с программой.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ОШИБКА] Файл main.py не найден!
    echo Убедитесь, что вы запускаете батник из папки с программой.
    pause
    exit /b 1
)

REM Проверка установки Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.8 или выше: https://python.org
    pause
    exit /b 1
)

echo [OK] Python найден:
python --version
echo.

REM Установка зависимостей
echo Проверка и установка зависимостей...
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости
    echo Попробуйте запустить от имени администратора
    pause
    exit /b 1
)

echo.
echo ===========================================
echo Запуск программы...
echo ===========================================
echo.
echo Подключение:
echo   - COM порт: 4 (можно изменить в программе)
echo   - Baudrate: 19200
echo   - Формат: 8N1
echo.
echo Диагностика:
echo   - Проверьте что датчик включен
echo   - Проверьте подключение RS-485
echo   - Убедитесь что порт не занят другой программой
echo.
pause

python main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Программа завершилась с ошибкой
    pause
)
