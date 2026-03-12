# Исправление ошибки Tcl/Tk

## Проблема
Виртуальное окружение (.venv) использует Python 3.13 без Tcl/Tk.

## Быстрое решение - запуск без виртуального окружения

### Для PowerShell:
```powershell
# Деактивируйте venv
.venv\Scripts\deactivate.bat

# Запустите через системный Python
python dyn200_monitor.py
```

### Для Command Prompt (cmd):
```cmd
.venv\Scripts\deactivate.bat
python dyn200_monitor.py
```

### Для Git Bash:
```bash
source .venv/Scripts/deactivate
python dyn200_monitor.py
```

## Альтернативные решения

### Вариант 1: Пересоздать venv с правильным Python
```bash
# Удалить старое venv
rmdir /s /q .venv

# Создать новое с системным Python
python -m venv .venv

# Активировать
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### Вариант 2: Использовать Python без venv
Системный Python уже имеет tkinter (проверено: Tcl 8.6.13).

## Проверка tkinter
```bash
python -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
```

## Запуск программы
```bash
# Через системный Python (рекомендуется)
python dyn200_monitor.py

# Или после исправления venv
.venv\Scripts\activate
python dyn200_monitor.py
```
