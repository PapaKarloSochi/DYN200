# Руководство по внесению изменений (Contributing Guide)

Спасибо за интерес к развитию DYN-200 Monitor! Этот документ поможет вам начать участие в проекте.

## 🚀 Быстрый старт

### 1. Подготовка окружения

```bash
# 1. Форкните репозиторий на GitHub
# 2. Клонируйте свой форк
git clone https://github.com/YOUR_USERNAME/dyn200-monitor.git
cd dyn200-monitor

# 3. Создайте виртуальное окружение
python -m venv .venv

# 4. Активируйте окружение
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 5. Установите зависимости для разработки
pip install -r requirements.txt
pip install -r requirements-dev.txt  # дополнительные зависимости
```

### 2. Запуск тестов

```bash
# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск с покрытием кода
pytest --cov=. --cov-report=html --cov-report=term

# Проверка конкретного модуля
pytest tests/test_unit_conversion.py -v
```

### 3. Создание ветки

```bash
# Создайте ветку для ваших изменений
git checkout -b feature/your-feature-name

# Или для исправления ошибки
git checkout -b fix/issue-description
```

## 📝 Стиль кода

### Общие правила

Мы следуем стандарту **PEP 8** с несколькими дополнениями:

#### Отступы и форматирование
- **4 пробела** для отступов (без табуляций)
- **Максимальная длина строки:** 100 символов
- **UTF-8** кодировка файлов

#### Импорты
```python
# Группировка импортов:
# 1. Стандартная библиотека
import os
import sys
import threading
from datetime import datetime

# 2. Сторонние библиотеки
import customtkinter as ctk
import tkinter as tk
from PIL import Image

# 3. Локальные модули
from config import AppConfig
from utils.logger import Logger
```

#### Docstrings
Используем стиль **Google/NumPy**:

```python
def process_data(raw_value: int, coefficient: float = 1.0) -> float:
    """Краткое описание функции.
    
    Подробное описание того, что делает функция,
    когда и зачем её использовать.
    
    Args:
        raw_value: Сырое значение из регистров Modbus.
            Описание может занимать несколько строк.
        coefficient: Коэффициент коррекции.
            Должен быть положительным числом.
            По умолчанию 1.0 (без коррекции).
    
    Returns:
        Преобразованное значение в физических единицах.
    
    Raises:
        ValueError: Если coefficient <= 0.
    
    Examples:
        >>> process_data(50000, 1.0)
        50.0
        >>> process_data(50000, 2.0)
        100.0
    """
    if coefficient <= 0:
        raise ValueError("Coefficient must be positive")
    return raw_value / 1000.0 * coefficient
```

#### Именование

| Тип | Стиль | Пример |
|-----|-------|--------|
| Классы | PascalCase | `ModernMainWindow`, `AppConfig` |
| Функции/методы | snake_case | `process_data()`, `get_value()` |
| Переменные | snake_case | `max_torque`, `is_connected` |
| Константы | UPPER_SNAKE_CASE | `MAX_POINTS`, `DEFAULT_BAUDRATE` |
| Приватные атрибуты | _leading_underscore | `_state_lock`, `_is_closing` |

### Type Hints

Все публичные функции должны иметь аннотации типов:

```python
from typing import Optional, Tuple, List, Dict

def connect(port: str, baudrate: int = 19200) -> Tuple[bool, str]:
    """Подключение к датчику.
    
    Returns:
        Кортеж (успех, сообщение_об_ошибке).
    """
    pass

def get_data() -> Optional[Dict[str, float]]:
    """Получение данных.
    
    Returns:
        Словарь с данными или None если нет соединения.
    """
    pass
```

### Обработка ошибок

```python
# Правильно: конкретные исключения
from pymodbus.exceptions import ModbusIOException, ConnectionException

try:
    response = client.read_holding_registers(...)
except ConnectionException as e:
    logger.error(f"Connection lost: {e}")
    self._handle_connection_error()
except ModbusIOException as e:
    logger.error(f"Modbus IO error: {e}")
except Exception as e:
    logger.exception("Unexpected error")
    raise  # или обработать корректно

# Неправильно:
try:
    response = client.read_holding_registers(...)
except:  # голый except - плохая практика
    pass
```

## 🧪 Тестирование

### Структура тестов

```
tests/
├── __init__.py
├── conftest.py           # Фикстуры pytest
├── test_config.py        # Тесты конфигурации
├── test_unit_conversion.py
├── test_modbus_client.py
└── test_validators.py
```

### Написание тестов

```python
import pytest
from core.unit_conversion import raw_to_torque

class TestUnitConversion:
    """Тесты конвертации единиц измерения."""
    
    def test_raw_to_torque_positive(self):
        """Проверка конвертации положительных значений."""
        assert raw_to_torque(50000) == 50.0
        assert raw_to_torque(1000) == 1.0
    
    def test_raw_to_torque_negative(self):
        """Проверка конвертации отрицательных значений."""
        assert raw_to_torque(-50000) == -50.0
    
    def test_raw_to_torque_zero(self):
        """Проверка конвертации нуля."""
        assert raw_to_torque(0) == 0.0
    
    @pytest.mark.parametrize("raw,expected", [
        (1000, 1.0),
        (5000, 5.0),
        (10000, 10.0),
    ])
    def test_raw_to_torque_parametrized(self, raw, expected):
        """Параметризованный тест."""
        assert raw_to_torque(raw) == expected
```

### Моки и фикстуры

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_modbus_client():
    """Фикстура для мока Modbus клиента."""
    client = Mock()
    client.connect.return_value = True
    client.read_holding_registers.return_value = Mock(
        isError.return_value=False,
        registers=[0, 50000, 0, 1000, 0, 25000]
    )
    return client

def test_connection_with_mock(mock_modbus_client):
    """Тест подключения с моком."""
    with patch('gui.modern_main_window.ModbusSerialClient', 
               return_value=mock_modbus_client):
        # ... тест ...
        pass
```

## 🔄 Создание Pull Request

### Процесс

1. **Перед созданием PR:**
   ```bash
   # Обновите main ветку
   git checkout main
   git pull upstream main
   
   # Переключитесь на вашу ветку и сделайте rebase
   git checkout feature/your-feature
   git rebase main
   
   # Запустите тесты
   pytest
   
   # Проверьте стиль кода
   flake8 .
   black --check .
   ```

2. **Создание коммитов:**
   ```bash
   # Формат коммита:
   # <тип>: <краткое описание>
   #
   # Подробное описание при необходимости
   
   git commit -m "feat: добавлена поддержка нового датчика XYZ"
   git commit -m "fix: исправлена ошибка подключения при потере связи"
   git commit -m "docs: обновлено описание API"
   ```

   **Типы коммитов:**
   - `feat:` — новая функциональность
   - `fix:` — исправление ошибки
   - `docs:` — изменения документации
   - `test:` — добавление/обновление тестов
   - `refactor:` — рефакторинг кода
   - `style:` — форматирование, исправление опечаток
   - `perf:` — улучшение производительности

3. **Заполнение PR:**
   - **Заголовок:** краткое описание изменений
   - **Описание:** 
     - Что изменено и зачем
     - Как протестировать
     - Ссылки на связанные issues
   - **Чеклист:**
     - [ ] Тесты пройдены
     - [ ] Документация обновлена
     - [ ] Код соответствует стилю проекта

### Ревью кода

После создания PR:
1. Ожидайте ревью от мейнтейнеров
2. Отвечайте на комментарии
3. Вносите необходимые изменения
4. После approval PR будет merged

## 📂 Структура проекта

```
dyn200-monitor/
├── core/                    # Ядро приложения
│   ├── __init__.py
│   └── *.py                # Бизнес-логика
├── gui/                     # Графический интерфейс
│   ├── __init__.py
│   └── *.py                # Компоненты UI
├── utils/                   # Утилиты
│   ├── __init__.py
│   └── *.py                # Вспомогательные функции
├── tests/                   # Тесты
│   ├── __init__.py
│   └── test_*.py           # Файлы тестов
├── docs/                    # Документация
├── config.py               # Конфигурация
├── main.py                 # Точка входа
├── requirements.txt        # Производственные зависимости
├── requirements-dev.txt    # Зависимости разработки
└── pytest.ini             # Настройки тестирования
```

## 🐛 Сообщение об ошибках

При обнаружении ошибки создайте Issue с описанием:

```markdown
**Описание ошибки**
Чёткое описание что произошло.

**Как воспроизвести**
1. Перейдите в '...'
2. Нажмите на '...'
3. Увидите ошибку

**Ожидаемое поведение**
Что должно было произойти.

**Скриншоты**
Если применимо.

**Окружение**
- OS: Windows 10 / Ubuntu 22.04 / macOS 13
- Python: 3.10.5
- Версия приложения: 1.2.3

**Логи**
```
Содержимое debug_log.txt
```
```

## 💡 Предложение улучшений

Для предложения новой функциональности:

1. Создайте Issue с меткой `enhancement`
2. Опишите проблему которую решает улучшение
3. Предложите возможное решение
4. Обсудите с сообществом

## 📚 Дополнительные ресурсы

- [PEP 8 — Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)

## ❓ Вопросы

Если у вас есть вопросы:
- Создайте Issue с меткой `question`
- Или напишите в Discussions

---

Спасибо за участие в развитии DYN-200 Monitor! 🎉
