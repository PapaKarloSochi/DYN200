@echo off
chcp 65001 >nul
echo ==========================================
echo Сборка DYN-200 Monitor в EXE
echo ==========================================
echo.
echo [!] ВАЖНО: Для работы tkinter рекомендуется сборка через системный Python
echo     без виртуального окружения, так как venv может не содержать Tcl/Tk.
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

echo [1/4] Проверка Python... OK

:: Проверка наличия tkinter в системном Python
python -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))" >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] В системном Python отсутствует tkinter!
    echo         Установите Python с поддержкой Tcl/Tk.
    pause
    exit /b 1
)
echo     tkinter найден... OK

:: Используем системный Python для сборки (tkinter может отсутствовать в venv)
echo [2/4] Настройка окружения...
echo     Используется системный Python (tkinter может отсутствовать в venv)

:: Установка зависимостей
echo [3/4] Установка зависимостей...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1

:: Установка PyInstaller если нет
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo         Установка PyInstaller...
    pip install pyinstaller >nul 2>&1
)

echo [4/4] Сборка EXE...
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
    --collect-all "tkinter" ^
    --collect-all "tcl8" ^
    --collect-all "tk8" ^
    --hidden-import "tkinter" ^
    --hidden-import "_tkinter" ^
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
echo 2. Запустите DYN200_Monitor.exe
echo.
echo [ВАЖНО] EXE включает все необходимые библиотеки (tkinter, tcl, tk)
echo         Дополнительная установка Python на целевом ПК не требуется.
echo.
pause
