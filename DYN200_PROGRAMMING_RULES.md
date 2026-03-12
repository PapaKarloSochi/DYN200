# DYN200 Programming Rules

## 1. Общие положения

### 1.1. Описание датчика
DYN-200 (и аналоги ATO/CALT/DAYSENSOR DYN-серии) — датчик крутящего момента со встроенным дисплеем и RS-485 интерфейсом.

### 1.2. Архитектура проекта (ЭТАП 5-6)

Проект следует многоуровневой архитектуре с разделением ответственности:

```
dyn200-monitor/
├── core/                   # Ядро: бизнес-логика, конвертация
│   ├── __init__.py
│   └── unit_conversion.py
├── gui/                    # UI: окна, диалоги, графики
│   ├── __init__.py
│   ├── modern_main_window.py
│   ├── modern_dialogs.py
│   ├── modern_theme.py
│   ├── plot_manager.py
│   └── value_card.py
├── utils/                  # Утилиты: логирование, валидация
│   ├── __init__.py
│   └── logger.py
├── tests/                  # Тесты: pytest
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_unit_conversion.py
│   ├── test_modbus_client.py
│   └── test_validators.py
├── config.py              # Конфигурация и состояние
└── main.py                # Точка входа
```

---

## 2. Аппаратное подключение

### 2.1. Распиновка (стандартный кабель)
```
Pin 1 (красный):   PWR (+24V)
Pin 2 (черный):    PWR (0V/GND)
Pin 3 (зеленый):   SIG OUT (±5V/0-10V/4-20mA)
Pin 4 (белый):     SIG GND
Pin 5 (желтый):    RS485 A
Pin 6 (синий):     RS485 B
Pin 7 (оранжевый): RPM+
Pin 8 (серый):     RPM-
```

### 2.2. Требования к питанию
- Напряжение: DC 24V (±10%), 0.2A
- Максимальное: 27.5V
- Минимальное запуска: 21V

### 2.3. RS-485 → USB конвертер
- Использовать стабильный конвертер с гальванической развязкой
- Скорость: до 115200 baud
- Подключение: A→A, B→B

---

## 3. Настройки связи

### 3.1. Параметры по умолчанию
```
Baud rate: 19200 (или 38400 — проверять на дисплее!)
Data bits: 8
Parity:    None
Stop bits: 1 (или 2 — проверять!)
Format:    8N1 (или 8N2)
Timeout:   500-1000 мс (минимум 300 мс)
```

### 3.2. Настройка на датчике
- Baud rate настраивается через меню датчика
- Slave address (для Modbus): 0x01 (по умолчанию)

---

## 4. Протокол Modbus RTU

### 4.1. Основные правила
- ТОЛЬКО pymodbus — не использовать minimalmodbus
- Функция: 0x03 (Read Holding Registers)
- Slave address: 0x01 (1 в десятичной)

### 4.2. Регистры (critical!)
```
Адрес 0x0000: Torque (2 регистра)  → 32-bit signed integer
Адрес 0x0002: Speed  (2 регистра)  → 32-bit unsigned integer
Адрес 0x0004: Power  (2 регистра)  → 32-bit integer
```
⚠️ **Важно:** Читать ВСЕГДА 6 регистров (count=6) одним запросом!

### 4.3. Формат запроса (Modbus RTU)
```python
# Правильный способ для pymodbus 3.x
response = client.read_holding_registers(0, 6, slave=0x01)

# Для старых версий (fallback):
response = client.read_holding_registers(address=0, count=6, slave=0x01)
response = client.read_holding_registers(address=0, count=6, unit=0x01)
```

### 4.4. Парсинг ответа
```python
registers = response.registers

# Big-endian: старший регистр первый
torque_raw = (registers[0] << 16) | registers[1]
torque = to_signed32(torque_raw)

speed = (registers[2] << 16) | registers[3]  # unsigned

power_raw = (registers[4] << 16) | registers[5]
```

### 4.5. Команды управления

#### Обнуление (Zero)
- Функция: 0x05 (Write Single Coil)
- Адрес: 0x0000
- Значение: 0xFF00

```python
zero_cmd = bytes([0x01, 0x05, 0x00, 0x00, 0xFF, 0x00, crc_lo, crc_hi])
```

#### Сброс к заводским настройкам
- Через Modbus function 0x05 или 0x10
- Адрес: 0x0002
- Значение: 0x0001

---

## 5. Пересчёт единиц измерения (critical!)

### 5.1. Формулы
```python
# Torque (крутящий момент)
# Диапазон: -99999 ~ 99999 (в единицах 0.001 N·m)
torque_nm = raw_torque / 1000.0

# Speed (обороты)
# Диапазон: 0 ~ 99999 (1:1, в RPM)
speed_rpm = raw_speed  # без деления!

# Power (мощность)
# Диапазон: регистр содержит кВт × 10
# raw_power = кВт × 10 → кВт = raw_power / 10 → Вт = raw_power × 100
power_w = raw_power * 100
```

### 5.2. Проверка
- Torque делится на 1000
- Speed не делится
- Power умножается на 100

---

## 6. Архитектура программы

### 6.1. Структура модулей

```python
# core/ - ядро бизнес-логики
from core.unit_conversion import raw_to_torque, raw_to_speed, raw_to_power

# gui/ - пользовательский интерфейс
from gui.modern_main_window import ModernMainWindow
from gui.modern_dialogs import ModernConnectionDialog

# utils/ - вспомогательные функции
from utils.logger import Logger
```

### 6.2. Thread-Safety механизмы (ЭТАП 5)

#### Обязательные правила:
1. **Все разделяемые данные под Lock**
   ```python
   class AppState:
       def __init__(self):
           self._state_lock = threading.Lock()
       
       def append_data(self, timestamp, torque, speed, power):
           """Thread-safe добавление данных"""
           with self._state_lock:
               self.timestamps.append(timestamp)
               self.torque_data.append(torque)
               # ...
   ```

2. **Обновление UI только из main thread**
   ```python
   # Правильно:
   self.root.after(0, lambda: self._update_cards(torque, speed, power))
   
   # НЕПРАВИЛЬНО:
   # self.torque_card.update_value(torque)  # в background thread!
   ```

3. **Использование threading.Event для остановки**
   ```python
   while not self.stop_thread.is_set():
       # ... чтение данных ...
       if self.stop_thread.wait(0.1):  # timeout с проверкой флага
           break
   ```

### 6.3. Валидация входных данных (ЭТАП 5)

#### Валидаторы в gui/modern_dialogs.py:
```python
def validate_com_port(port: str) -> Tuple[bool, str]:
    """Валидация COM-порта.
    
    Returns:
        (is_valid, error_message)
    """
    if not port:
        return False, "COM-порт не может быть пустым"
    
    windows_pattern = r'^COM([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-6])$'
    linux_pattern = r'^/dev/tty[A-Za-z0-9]+$'
    
    if not (re.match(windows_pattern, port, re.IGNORECASE) or 
            re.match(linux_pattern, port)):
        return False, f"Неверный формат COM-порта: {port}"
    
    return True, ""


def validate_baudrate(baud: int) -> Tuple[bool, str]:
    """Валидация baudrate."""
    valid_baudrates = [1200, 2400, 4800, 9600, 19200, 
                       38400, 57600, 115200, 230400]
    
    if baud not in valid_baudrates:
        return False, f"Неверный baudrate: {baud}"
    
    return True, ""


def validate_log_path(filepath: str) -> Tuple[bool, str]:
    """Валидация пути (защита от path traversal)."""
    if not filepath:
        return False, "Путь к файлу не может быть пустым"
    
    normalized_path = os.path.normpath(filepath)
    
    if '..' in normalized_path:
        return False, "Путь содержит недопустимые символы (..)"
    
    # Проверка доступности директории...
    return True, ""
```

### 6.4. Circuit Breaker (ЭТАП 5)

Защита от бесконечных попыток подключения:

```python
class CircuitState(Enum):
    CLOSED = auto()      # Нормальная работа
    OPEN = auto()        # Ошибки, нет соединения
    HALF_OPEN = auto()   # Пробуем восстановить

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Проверить, можно ли выполнять операцию"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            
            return True  # HALF_OPEN
    
    def record_failure(self) -> bool:
        """Записать ошибку. Возвращает True если state -> OPEN."""
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                return True
            return False
    
    def record_success(self) -> None:
        """Записать успешную операцию"""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
```

### 6.5. Retry Logic с Exponential Backoff (ЭТАП 5)

```python
class RetryWithBackoff:
    def __init__(self, max_retries: int = 3, 
                 base_delay: float = 1.0, 
                 max_delay: float = 10.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, operation: Callable, logger: Logger, 
                operation_name: str = "operation"):
        """Выполнить операцию с повторными попытками"""
        for attempt in range(1, self.max_retries + 1):
            try:
                return operation()
            except Exception as e:
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** (attempt - 1)), 
                               self.max_delay)
                    logger.log(f"[RETRY] {operation_name} failed, "
                               f"waiting {delay}s...")
                    time.sleep(delay)
                else:
                    raise
```

### 6.6. Graceful Shutdown (ЭТАП 5)

```python
def _graceful_shutdown(self) -> None:
    """Graceful shutdown с сохранением данных"""
    try:
        # 1. Устанавливаем флаг остановки
        self.stop_thread.set()
        self.state.is_connected = False
        self.state.is_reading = False
        
        # 2. Останавливаем логирование
        self._stop_logging()
        
        # 3. Ожидаем завершения потока с таймаутом
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=3.0)
        
        # 4. Закрываем соединения
        if self.modbus_client:
            self.modbus_client.close()
        if self.serial_conn:
            self.serial_conn.close()
        
        # 5. Закрываем логгер
        self.logger.close()
        
    except Exception as e:
        self.logger.log(f"[SHUTDOWN CRITICAL] {e}")
```

### 6.7. Требования к GUI
- 3 отдельных графика для Torque, Speed, Power
- Индивидуальное масштабирование каждого графика
- Большие цифры для текущих значений
- Кнопки: Connect, Disconnect, Start/Stop Logging, Zero
- Статус: Connected/Disconnected/Error

### 6.8. Логирование
```
Timestamp,Torque_Nm,Speed_RPM,Power_W
2026-03-10 09:24:48.062,0.00,0,0.0
```

---

## 7. Обработка ошибок

### 7.1. Типы ошибок
- `ModbusException` — ошибки Modbus протокола
- `serial.SerialException` — проблемы с COM-портом
- `Timeout` — нет ответа от датчика

### 7.2. Стратегия
- НЕ крашить программу при ошибке чтения
- Переподключение каждые 3-5 сек при потере связи
- Логирование всех ошибок

### 7.3. Поведение при ошибке
```python
try:
    response = client.read_holding_registers(...)
except ModbusIOException as e:
    self.logger.log(f"[ERROR] Modbus IO: {e}")
    consecutive_errors += 1
    if consecutive_errors >= 5:
        self.root.after(0, lambda: self.status_badge.set_status("DISCONNECTED", False))
except ConnectionException as e:
    self.logger.log(f"[ERROR] Connection lost: {e}")
    self.circuit_breaker.record_failure()
    break
except Exception as e:
    self.logger.log_exception("[CRITICAL] Unexpected error", e)
```

---

## 8. Производительность

### 8.1. Частота опроса
- Рекомендуемая: 50-200 мс (5-20 Hz)
- Максимальная для Modbus: ~30 раз/сек

### 8.2. Размер буфера графика
- Хранить 100-300 точек
- Автоматическая прокрутка (rolling window)
- Использовать `collections.deque` с `maxlen`

### 8.3. Оптимизация
- Чтение в отдельном потоке
- GUI не блокируется
- Queue для передачи данных между потоками

---

## 9. Тестирование

### 9.1. Запуск тестов
```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный файл
pytest tests/test_unit_conversion.py
```

### 9.2. Структура тестов
```
tests/
├── test_config.py           # Тесты конфигурации и состояния
├── test_modbus_client.py    # Тесты Modbus клиента
├── test_unit_conversion.py  # Тесты конвертации единиц
└── test_validators.py       # Тесты валидации
```

### 9.3. Пример теста
```python
def test_circuit_breaker_transitions():
    """Тест переходов состояний Circuit Breaker."""
    cb = CircuitBreaker(failure_threshold=3, timeout=1.0)
    
    # Начальное состояние
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True
    
    # После 2 ошибок - всё ещё CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    
    # После 3-й ошибки - OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False
```

---

## 10. PyInstaller (production)

### 10.1. Команда сборки
```bash
pyinstaller --onefile --windowed --name DYN200Monitor main.py
```

### 10.2. Требования
- Не использовать относительные пути к иконкам
- Проверять наличие файлов перед использованием
- try-except вокруг mainloop()

---

## 11. Проверка работоспособности

### 11.1. Алгоритм отладки
1. Проверить COM-порт в диспетчере устройств
2. Убедиться что датчик включен (дисплей светится)
3. Проверить baud rate на дисплее датчика
4. Запустить программу и проверить логи
5. Покрутить вал — данные должны меняться

### 11.2. Ожидаемые значения
- Без нагрузки: torque ≈ 0, speed = 0 или RPM вала
- С нагрузкой: torque ≠ 0, power ≠ 0

---

## 12. Запрещено

❌ Использовать minimalmodbus
❌ Читать регистры по одному (всегда count=6)
❌ Игнорировать знак torque (signed 32-bit)
❌ Использовать магические числа без комментариев
❌ Обновлять UI из background thread
❌ Пропускать валидацию пользовательского ввода

---

## 13. Полезные ссылки

- Документация pymodbus: https://pymodbus.readthedocs.io/
- Modbus RTU specification: https://modbus.org/docs/PI_MBUS_300.pdf
- PySerial documentation: https://pyserial.readthedocs.io/
- CustomTkinter: https://customtkinter.tomschimansky.com/
