# Архитектура DYN-200 Monitor

## Общая архитектура

DYN-200 Monitor построен по принципу многоуровневой архитектуры (Layered Architecture) с разделением ответственности между компонентами.

### Высокоуровневая диаграмма

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Presentation Layer                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     ModernMainWindow                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │  │
│  │  │  ValueCard   │  │  PlotManager │  │    ModernDialogs        │  │  │
│  │  │  (UI Cards)  │  │  (Graphs)    │  │  (Settings/Connection)  │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                           Application Layer                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                          AppState                                  │  │
│  │   • Thread-safe shared state                                       │  │
│  │   • Data queues and deques                                         │  │
│  │   • Configuration variables                                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                            Core Layer                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Unit Conversion │  │  Modbus Client   │  │  Circuit Breaker     │  │
│  │  • raw_to_torque │  │  • Read/Write    │  │  • Failure tracking  │  │
│  │  • raw_to_speed  │  │  • Error handling│  │  • State management  │  │
│  │  • raw_to_power  │  │  • Retry logic   │  │  • Timeout control   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                           Infrastructure Layer                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Logger          │  │  Config          │  │  Validators          │  │
│  │  • File logging  │  │  • AppConfig     │  │  • Input validation  │  │
│  │  • GUI logging   │  │  • AppState      │  │  • Path validation   │  │
│  │  • Rotation      │  │  • Constants     │  │  • Type checking     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                         Hardware Abstraction                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    RS-485 / USB Converter                          │  │
│  │                         DYN-200 Sensor                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Описание слоёв

### 1. Presentation Layer (GUI)

**Расположение:** [`gui/`](gui/)

#### ModernMainWindow ([`gui/modern_main_window.py`](gui/modern_main_window.py))
Главное окно приложения, координирует все компоненты UI.

**Ключевые responsibilities:**
- Управление жизненным циклом приложения
- Координация между потоками (main thread + read thread)
- Обработка пользовательских действий
- Graceful shutdown

**Thread-safety:**
```python
# Потокобезопасное обновление UI через root.after()
self.root.after(0, lambda: self._update_cards(torque, speed, power))
```

#### ValueCard ([`gui/value_card.py`](gui/value_card.py))
Компонент для отображения значений с поддержкой:
- Текущих значений
- Максимальных значений (Peak Hold)
- Настраиваемых единиц измерения
- Десятичных знаков

#### PlotManager ([`gui/plot_manager.py`](gui/plot_manager.py))
Управление графиками matplotlib:
- Три оси Y (Torque, Speed, Power)
- Настраиваемые пределы осей
- Автомасштабирование
- Rolling window для данных

#### ModernDialogs ([`gui/modern_dialogs.py`](gui/modern_dialogs.py))
Диалоговые окна:
- `ModernConnectionDialog` — настройки подключения
- `ModernBasicSettingsDialog` — базовые настройки
- `ModernAxisDialog` — настройки осей графика

### 2. Application Layer

#### AppState ([`config.py`](config.py:55))
Централизованное состояние приложения с thread-safety.

```python
class AppState:
    def __init__(self):
        self._state_lock = threading.Lock()
        # ... переменные состояния ...
    
    def append_data(self, timestamp, torque, speed, power):
        """Thread-safe добавление данных"""
        with self._state_lock:
            self.timestamps.append(timestamp)
            # ...
```

**Паттерн:** [Singleton](https://refactoring.guru/design-patterns/singleton) (неявный, через один экземпляр)

### 3. Core Layer

#### Unit Conversion ([`core/unit_conversion.py`](core/unit_conversion.py))
Конвертация сырых Modbus-данных в физические единицы.

| Функция | Описание | Формула |
|---------|----------|---------|
| `raw_to_torque()` | Крутящий момент | `raw / 1000.0` → Н·м |
| `raw_to_speed()` | Скорость вращения | `raw / 10.0` → RPM |
| `raw_to_power()` | Мощность | `raw * correction` → Вт |
| `to_signed32()` | Знаковое 32-bit | Two's complement |

#### Circuit Breaker ([`gui/modern_main_window.py`](gui/modern_main_window.py:60))
Защита от каскадных ошибок при подключении.

```
┌─────────┐    ошибка     ┌─────────┐   timeout   ┌─────────┐
│  CLOSED │ ────────────→ │  OPEN   │ ──────────→ │ HALF_OPEN│
│ (норма) │  threshold    │(блокировка)│  10 sec   │(тест)   │
└─────────┘               └─────────┘            └─────────┘
     ↑                                              │
     └──────────────── success ────────────────────┘
```

#### Retry Logic ([`gui/modern_main_window.py`](gui/modern_main_window.py:114))
Exponential backoff для восстановления соединения.

```python
delay = min(base_delay * (2 ** attempt), max_delay)
# Attempt 1: 1.0s
# Attempt 2: 2.0s
# Attempt 3: 4.0s
```

### 4. Infrastructure Layer

#### Logger ([`utils/logger.py`](utils/logger.py))
Многоуровневое логирование:

**Handlers:**
1. `RotatingFileHandler` — файловое логирование с ротацией
2. `GUILogHandler` — вывод в GUI через очередь
3. `StreamHandler` — консольный вывод

**Уровни логирования:**
```
DEBUG    (10) — Подробная отладка
INFO     (20) — Информационные сообщения
WARNING  (30) — Предупреждения
ERROR    (40) — Ошибки
CRITICAL (50) — Критические ошибки
```

#### Validators ([`gui/modern_dialogs.py`](gui/modern_dialogs.py:23))
Валидация входных данных:
- `validate_com_port()` — COM-порт (Windows/Linux)
- `validate_baudrate()` — Baudrate
- `validate_log_path()` — Path traversal protection

## Потоки данных

### Диаграмма потока данных

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Flow                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DYN-200 Sensor                                                 │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────┐                                              │
│  │  Modbus RTU  │  ◄─── _modbus_read_loop() [background thread]│
│  │   Response   │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                              │
│  │   Parsing    │  ───► raw_to_torque(), raw_to_speed(), etc.  │
│  └──────┬───────┘                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                              │
│  │   AppState   │  ◄─── thread-safe append_data()             │
│  │   (shared)   │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│    ┌────┴────┐                                                  │
│    │         │                                                   │
│    ▼         ▼                                                   │
│ ┌──────┐  ┌────────┐                                            │
│ │ Plots│  │ Logger │                                            │
│ │  UI  │  │  File  │                                            │
│ └──────┘  └────────┘                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Жизненный цикл соединения

```
┌──────────┐
│  IDLE    │
└────┬─────┘
     │ Connect button
     ▼
┌──────────┐     Circuit Breaker      ┌──────────┐
│ CONNECTING│ ─────── blocks ────────► │ RETRYING │
└────┬─────┘   (threshold reached)     └────┬─────┘
     │                                      │
     │ Success                              │ Timeout
     ▼                                      ▼
┌──────────┐                          ┌──────────┐
│ CONNECTED │                          │  FAILED  │
└────┬─────┘                          └──────────┘
     │
     │ Toggle Reading
     ▼
┌──────────┐
│ READING  │
└────┬─────┘
     │ Disconnect / Error
     ▼
┌──────────┐
│   IDLE   │
└──────────┘
```

## Безопасность (Thread-Safety)

### Механизмы синхронизации

#### 1. Locks
```python
# AppState._state_lock для защиты данных
with self._state_lock:
    self.timestamps.append(timestamp)
```

#### 2. Threading Events
```python
# stop_thread — флаг остановки потока
while not self.stop_thread.is_set():
    # ... read data ...
    if self.stop_thread.wait(0.1):  # timeout с проверкой
        break
```

#### 3. Queue для GUI
```python
# GUILogHandler использует queue.Queue
self.log_queue.put(record)      # producer (any thread)
record = self.log_queue.get()   # consumer (main thread)
```

### Правила thread-safety

1. **Все обновления UI только из main thread**
   ```python
   self.root.after(0, callback)  # правильно
   # label.configure(...) в background thread — НЕПРАВИЛЬНО
   ```

2. **Все разделяемые данные под lock**
   ```python
   with self._state_lock:
       # доступ к shared data
   ```

3. **Graceful shutdown с таймаутом**
   ```python
   self.read_thread.join(timeout=3.0)
   ```

## Расширяемость

### Добавление нового типа датчика

1. **Создать класс конвертера:**
   ```python
   # core/sensor_xyz.py
   class SensorXYZConverter:
       @staticmethod
       def raw_to_torque(raw: int) -> float:
           return raw / 100.0  # другой коэффициент
   ```

2. **Добавить поддержку в UI:**
   ```python
   # gui/modern_main_window.py
   def _detect_sensor_type(self):
       # Пробуем разные протоколы
       if self._try_dyn200():
           return "DYN-200"
       elif self._try_xyz():
           return "XYZ"
   ```

### Добавление нового графика

1. **Расширить PlotManager:**
   ```python
   # gui/plot_manager.py
   def add_custom_axis(self, name: str, color: str):
       self.axis_custom = self.axis_torque.twinx()
       # ...
   ```

2. **Добавить карточку:**
   ```python
   # gui/modern_main_window.py
   self.custom_card = ValueCard(...)
   ```

### Плагиновая архитектура

```python
# plugins/base.py
class DataProcessorPlugin(ABC):
    @abstractmethod
    def process(self, torque, speed, power) -> tuple:
        pass

# Использование
for plugin in self.plugins:
    torque, speed, power = plugin.process(torque, speed, power)
```

## Производительность

### Оптимизации

| Компонент | Оптимизация | Результат |
|-----------|-------------|-----------|
| Графики | Rolling window (300 точек) | O(1) память |
| Логирование | RotatingFileHandler | 5 MB max |
| Данные | deque с maxlen | Автоочистка |
| UI Update | root.after(50ms) | ~20 FPS |
| Чтение | Thread + Event | Неблокирующий UI |

### Профилирование

```bash
# Профилирование памяти
python -m memory_profiler main.py

# Профилирование CPU
python -m cProfile -o profile.stats main.py
```

## Диаграмма классов

```
┌─────────────────────┐         ┌─────────────────────┐
│   ModernMainWindow  │────────►│      AppState       │
├─────────────────────┤  owns   ├─────────────────────┤
│ - root: CTk         │         │ - _state_lock: Lock │
│ - config: AppConfig │         │ - timestamps: deque │
│ - state: AppState   │         │ - torque_data: deque│
│ - logger: Logger    │         │ - speed_data: deque │
│ - circuit_breaker   │         │ - power_data: deque │
│ - retry_handler     │         │ - is_connected: bool│
├─────────────────────┤         │ - is_reading: bool  │
│ + __init__()        │         ├─────────────────────┤
│ + _connect()        │         │ + append_data()     │
│ + _disconnect()     │         │ + clear_data()      │
│ + _toggle_reading() │         │ + get_data_copy()   │
└─────────────────────┘         └─────────────────────┘
           │                              ▲
           │ uses                         │
           ▼                              │
┌─────────────────────┐                   │
│    CircuitBreaker   │                   │
├─────────────────────┤                   │
│ - state: CircuitState│                  │
│ - failure_count: int│                   │
│ - _lock: Lock       │                   │
├─────────────────────┤                   │
│ + can_execute()     │                   │
│ + record_success()  │                   │
│ + record_failure()  │                   │
└─────────────────────┘                   │
           │                              │
           │ uses                         │ updates
           ▼                              │
┌─────────────────────┐                   │
│      Logger         │───────────────────┘
├─────────────────────┤
│ - logger: logging.Logger
│ - log_queue: Queue  │
│ - _lock: Lock       │
├─────────────────────┤
│ + debug()           │
│ + info()            │
│ + error()           │
│ + process_queue()   │
└─────────────────────┘
```

## Дополнительные ресурсы

- [Modbus RTU Specification](https://modbus.org/docs/PI_MBUS_300.pdf)
- [Python Threading](https://docs.python.org/3/library/threading.html)
- [CustomTkinter Documentation](https://customtkinter.tomschimansky.com/)
