@echo off
chcp 65001 >nul
echo ==========================================
echo Сборка DYN-200 Monitor в EXE
echo ==========================================
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

echo [1/5] Проверка Python... OK

:: Проверка виртуального окружения
if not exist ".venv\Scripts\python.exe" (
    echo [2/5] Создание виртуального окружения...
    python -m venv .venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
) else (
    echo [2/5] Виртуальное окружение найдено... OK
)

:: Активация виртуального окружения
echo [3/5] Активация окружения...
call .venv\Scripts\activate.bat

:: Установка зависимостей
echo [4/5] Установка зависимостей...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1

:: Установка PyInstaller если нет
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo         Установка PyInstaller...
    pip install pyinstaller >nul 2>&1
)

echo [5/5] Сборка EXE...
echo.

:: Очистка старых сборок
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul

:: Сборка EXE с помощью PyInstaller
pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "DYN200_Monitor" ^
    --icon "logo.png" ^
    --add-data "logo.png;." ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "utils;utils" ^
    --hidden-import "pymodbus" ^
    --hidden-import "pymodbus.client" ^
    --hidden-import "serial" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._imagingtk" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "customtkinter" ^
    --hidden-import "matplotlib" ^
    --hidden-import "matplotlib.backends.backend_tkagg" ^
    --hidden-import "numpy" ^
    main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка завершилась с ошибкой!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo [УСПЕХ] Сборка завершена!
echo ==========================================
echo.
echo EXE файл находится в папке: dist\DYN200_Monitor.exe
echo.
echo Для запуска на другом ПК:
echo 1. Скопируйте файл dist\DYN200_Monitor.exe
echo 2. Убедитесь, что на целевом ПК установлен драйвер COM-порта
echo 3. Запустите DYN200_Monitor.exe
echo.
pause
