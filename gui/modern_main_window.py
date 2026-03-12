#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно с современным Material Design 3 интерфейсом.

Использует CustomTkinter для темной темы и современных компонентов.

ЭТАП 3: Обработка исключений и graceful degradation
- Circuit Breaker pattern для Modbus
- Retry logic с exponential backoff
- Graceful shutdown
- Комплексная обработка ошибок

ЭТАП 5-6: Архитектура core/, gui/, utils/, tests/
- Модульная структура
- Thread-safety
- Валидация входных данных

Examples:
    >>> import customtkinter as ctk
    >>> from gui.modern_main_window import ModernMainWindow
    >>> 
    >>> root = ctk.CTk()
    >>> app = ModernMainWindow(root)
    >>> root.mainloop()

Attributes:
    CircuitState: Enum для состояний Circuit Breaker
    CircuitBreaker: Класс защиты от каскадных ошибок
    RetryWithBackoff: Класс retry logic с экспоненциальной задержкой
    ModernMainWindow: Главное окно приложения
"""

# ===== СТАНДАРТНЫЕ БИБЛИОТЕКИ =====
import os
import sys
import threading
import time
import csv
import signal
import traceback
from datetime import datetime
from typing import Optional, Callable
from enum import Enum, auto

# ===== СТОРОННИЕ БИБЛИОТЕКИ =====
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk

# Проверка наличия pymodbus
try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusIOException, ConnectionException
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    ModbusIOException = Exception
    ConnectionException = Exception

# ===== ЛОКАЛЬНЫЕ МОДУЛИ =====
from config import AppConfig, AppState
from utils.logger import Logger
from core.unit_conversion import raw_to_torque, raw_to_speed, raw_to_power, to_signed32
from gui.modern_theme import ModernTheme
from gui.value_card import ValueCard, StatusBadge, ActionButton
from gui.plot_manager import PlotManager
from gui.modern_dialogs import ModernConnectionDialog, ModernBasicSettingsDialog, validate_log_path


# ===== CIRCUIT BREAKER STATES =====
class CircuitState(Enum):
    """
    Состояния Circuit Breaker для управления повторными попытками.
    
    Circuit Breaker предотвращает бесконечные попытки подключения
    при постоянных ошибках, защищая систему от перегрузки.
    
    Attributes:
        CLOSED: Нормальная работа, попытки разрешены.
        OPEN: Слишком много ошибок, попытки блокированы.
        HALF_OPEN: Таймаут прошёл, пробуем восстановить соединение.
    
    Example:
        >>> state = CircuitState.CLOSED
        >>> print(state.name)
        'CLOSED'
    """
    CLOSED = auto()      #: Нормальная работа
    OPEN = auto()        #: Ошибки, нет соединения
    HALF_OPEN = auto()   #: Пробуем восстановить


class CircuitBreaker:
    """
    Circuit Breaker для предотвращения бесконечных попыток подключения.
    
    Реализует паттерн Circuit Breaker для защиты от каскадных ошибок
    при подключении к датчику. После достижения порога ошибок
    блокирует новые попытки на заданное время.
    
    Attributes:
        failure_threshold: Количество ошибок до открытия цепи.
        timeout: Время блокировки в секундах.
        failure_count: Текущий счётчик ошибок.
        state: Текущее состояние (CircuitState).
    
    Example:
        >>> cb = CircuitBreaker(failure_threshold=5, timeout=10.0)
        >>> cb.can_execute()
        True
        >>> cb.record_failure()
        False
        >>> # После 5 ошибок
        >>> cb.record_failure()
        True  # Цепь открыта
        >>> cb.can_execute()
        False
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 10.0):
        """
        Инициализация Circuit Breaker.
        
        Args:
            failure_threshold: Количество ошибок до перехода в OPEN.
            timeout: Время ожидания перед пробой восстановления (сек).
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()
    
    def record_success(self) -> None:
        """
        Записать успешную операцию и сбросить счётчик ошибок.
        
        При успешной операции счётчик ошибок сбрасывается в 0,
        а состояние возвращается в CLOSED.
        
        Example:
            >>> cb = CircuitBreaker()
            >>> cb.record_failure()
            >>> cb.failure_count
            1
            >>> cb.record_success()
            >>> cb.failure_count
            0
        """
        with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                print("[CIRCUIT] Connection restored, state: CLOSED")
    
    def record_failure(self) -> bool:
        """
        Записать ошибку операции.
        
        Returns:
            True если достигнут порог и цепь перешла в OPEN.
            False если цепь остаётся в CLOSED или HALF_OPEN.
        
        Example:
            >>> cb = CircuitBreaker(failure_threshold=3)
            >>> cb.record_failure()  # 1/3
            False
            >>> cb.record_failure()  # 2/3
            False
            >>> cb.record_failure()  # 3/3 - OPEN
            True
        """
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    self.state = CircuitState.OPEN
                    print(f"[CIRCUIT] Too many failures ({self.failure_count}), state: OPEN")
                return True
            return False
    
    def can_execute(self) -> bool:
        """
        Проверить, можно ли выполнять операцию.
        
        В состоянии OPEN проверяется таймаут. Если таймаут прошёл,
        состояние переходит в HALF_OPEN и выполнение разрешается.
        
        Returns:
            True если операция разрешена, False если заблокирована.
        
        Example:
            >>> cb = CircuitBreaker()
            >>> cb.can_execute()
            True
            >>> # После OPEN и ожидания timeout
            >>> cb.can_execute()  # Переход в HALF_OPEN
            True
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Проверяем, прошло ли время таймаута
                if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    print("[CIRCUIT] Timeout passed, trying HALF_OPEN")
                    return True
                return False
            
            # HALF_OPEN - пробуем одну операцию
            return True
    
    def get_state_name(self) -> str:
        """
        Получить имя текущего состояния.
        
        Returns:
            Строковое представление состояния (CLOSED, OPEN, HALF_OPEN).
        
        Example:
            >>> cb = CircuitBreaker()
            >>> cb.get_state_name()
            'CLOSED'
        """
        return self.state.name


class RetryWithBackoff:
    """
    Retry logic с exponential backoff.
    
    Автоматически повторяет операцию при неудаче с увеличивающейся
    задержкой между попытками (экспоненциальный backoff).
    
    Attributes:
        max_retries: Максимальное количество попыток.
        base_delay: Начальная задержка в секундах.
        max_delay: Максимальная задержка в секундах.
    
    Example:
        >>> retry = RetryWithBackoff(max_retries=3, base_delay=1.0)
        >>> def operation():
        ...     # Может выбросить исключение
        ...     return result
        >>> result = retry.execute(operation, logger, "my_operation")
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
        """
        Инициализация retry handler.
        
        Args:
            max_retries: Максимальное число попыток (включая первую).
            base_delay: Начальная задержка между попытками (сек).
            max_delay: Максимальная задержка между попытками (сек).
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, operation: Callable, logger: Logger, operation_name: str = "operation"):
        """
        Выполнить операцию с повторными попытками.
        
        При неудаче ожидает время, рассчитанное по формуле:
        delay = min(base_delay * 2^(attempt-1), max_delay)
        
        Args:
            operation: Функция для выполнения (без аргументов).
            logger: Экземпляр логгера для записи попыток.
            operation_name: Имя операции для логов.
        
        Returns:
            Результат выполнения operation().
        
        Raises:
            Exception: Если все попытки неудачны.
        
        Example:
            >>> def connect():
            ...     return modbus_client.connect()
            >>> retry = RetryWithBackoff()
            >>> result = retry.execute(connect, logger, "Modbus connect")
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = operation()
                if attempt > 1:
                    logger.log(f"[RETRY] {operation_name} succeeded on attempt {attempt}")
                return result
            except Exception as e:
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                    logger.log(f"[RETRY] {operation_name} failed (attempt {attempt}/{self.max_retries}): {e}")
                    logger.log(f"[RETRY] Waiting {delay}s before next attempt...")
                    time.sleep(delay)
                else:
                    logger.log(f"[RETRY] {operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
        
        return None


class ModernMainWindow:
    """
    Главное окно приложения DYN-200 Monitor с современным UI.
    
    Material Design 3 + Industrial Dark Theme.
    
    ЭТАП 3: Улучшенная обработка ошибок и graceful degradation
    ЭТАП 5-6: Модульная архитектура с core/, gui/, utils/, tests/
    
    Attributes:
        root: Корневой виджет CustomTkinter.
        config: Конфигурация приложения (AppConfig).
        state: Состояние приложения (AppState).
        logger: Логгер (Logger).
        circuit_breaker: Защита от каскадных ошибок (CircuitBreaker).
        retry_handler: Повторные попытки (RetryWithBackoff).
    
    Example:
        >>> import customtkinter as ctk
        >>> from gui.modern_main_window import ModernMainWindow
        >>> 
        >>> ctk.set_appearance_mode("dark")
        >>> root = ctk.CTk()
        >>> app = ModernMainWindow(root)
        >>> root.mainloop()
    """
    
    def __init__(self, root: ctk.CTk) -> None:
        """
        Инициализация главного окна.
        
        Args:
            root: Корневой виджет CustomTkinter.
        
        Note:
            Создаёт все UI-компоненты, настраивает обработчики сигналов
            и запускает циклы обновления.
        """
        self.root = root
        self.config = AppConfig()
        self.state = AppState()
        self.logger = Logger()
        self.plot_manager = PlotManager(self.config, self.state)
        
        # Потоки и соединения
        self.read_thread: Optional[threading.Thread] = None
        self.stop_thread = threading.Event()
        self.serial_conn: Optional[object] = None
        self.modbus_client: Optional[ModbusSerialClient] = None
        
        # Circuit Breaker для защиты от бесконечных попыток подключения
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=10.0)
        
        # Retry logic с exponential backoff
        self.retry_handler = RetryWithBackoff(max_retries=3, base_delay=1.0)
        
        # Файл логирования
        self.log_file: Optional[object] = None
        self.csv_writer: Optional[csv.writer] = None
        
        # Диалоги
        self.conn_dialog: Optional[ModernConnectionDialog] = None
        self.settings_dialog: Optional[ModernBasicSettingsDialog] = None
        
        # Максимальные значения (Peak Hold)
        self.max_torque = 0.0
        self.max_speed = 0.0
        self.max_power = 0.0
        
        # Флаг graceful shutdown
        self._is_shutting_down = False
        self._shutdown_complete = threading.Event()
        
        # Применяем тему
        ModernTheme.apply()
        
        # Настройка окна
        self._setup_window()
        self._create_ui()
        self._setup_signal_handlers()
        self._start_loops()
        
    def _setup_window(self) -> None:
        """Настройка главного окна."""
        self.root.title("Система тестирования")
        self.root.geometry("1400x950")
        self.root.minsize(1200, 800)
        self.root.configure(fg_color=ModernTheme.BACKGROUND)
        
        # Создаем меню
        self._create_menu()
        
    def _create_menu(self) -> None:
        """Создание меню приложения."""
        # Используем стандартное tkinter меню, т.к. customtkinter не имеет меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Меню Settings
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Connection Settings...", command=self._open_connection_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="Basic Settings...", command=self._open_basic_settings_dialog)
        
    def _create_ui(self) -> None:
        """Создание пользовательского интерфейса."""
        # Главный контейнер с отступами
        self.main_container = ctk.CTkFrame(
            self.root,
            fg_color=ModernTheme.BACKGROUND
        )
        self.main_container.pack(fill="both", expand=True, padx=24, pady=24)
        
        self._create_header()
        self._create_content()
        self._create_bottom_bar()
        
    def _create_header(self) -> None:
        """Создание компактного хедера с логотипом."""
        self.header = ctk.CTkFrame(
            self.main_container,
            fg_color=ModernTheme.SURFACE,
            corner_radius=ModernTheme.RADIUS_MD,
            height=80
        )
        self.header.pack(fill="x", pady=(0, 16))
        self.header.pack_propagate(False)
        
        # Левая часть - логотип и название
        left_section = ctk.CTkFrame(self.header, fg_color="transparent")
        left_section.pack(side="left", padx=20, fill="y")
        
        # Логотип из файла
        self._create_logo(left_section)
        
        # Название системы
        title_frame = ctk.CTkFrame(left_section, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        
        ctk.CTkLabel(
            title_frame,
            text="Система тестирования",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_2XL, "bold"),
            text_color=ModernTheme.ON_SURFACE
        ).pack(anchor="w")
        
        # Правая часть - статус
        self.status_badge = StatusBadge(
            self.header,
            status_text="DISCONNECTED",
            is_active=False
        )
        self.status_badge.pack(side="right", padx=20)
        
    def _create_logo(self, parent: ctk.CTkFrame) -> None:
        """
        Создание логотипа или fallback-иконки.
        
        Args:
            parent: Родительский фрейм для размещения логотипа.
        
        Note:
            Пытается загрузить logo.png, при ошибке использует текстовую иконку.
        """
        if os.path.exists('logo.png'):
            try:
                logo_img = Image.open('logo.png')
                # Масштабируем до высоты 60px
                max_height = 60
                ratio = max_height / logo_img.height
                new_width = int(logo_img.width * ratio)
                logo_img = logo_img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                self.logo_tk = ctk.CTkImage(logo_img, size=(new_width, max_height))
                logo_label = ctk.CTkLabel(parent, image=self.logo_tk, text="")
                logo_label.pack(side="left", padx=(0, 16))
                return
            except Exception as e:
                self.logger.log(f"Ошибка загрузки логотипа: {e}")
        
        # Fallback на иконку
        icon_label = ctk.CTkLabel(
            parent,
            text="◈",
            font=ModernTheme.get_font(28, "bold"),
            text_color=ModernTheme.PRIMARY
        )
        icon_label.pack(side="left", padx=(0, 12))
        
    def _create_content(self) -> None:
        """Создание основного контента."""
        content = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Левая панель с карточками значений
        self._create_left_panel(content)
        
        # Правая панель с графиком
        self._create_plot_panel(content)
        
    def _create_left_panel(self, parent: ctk.CTkFrame) -> None:
        """
        Создание левой панели с карточками значений.
        
        Args:
            parent: Родительский фрейм.
        
        Note:
            Создаёт три ValueCard для Torque, Speed и Power.
        """
        left_panel = ctk.CTkFrame(parent, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 16))

        # Карточки параметров
        self.torque_card = ValueCard(
            left_panel,
            title="Torque",
            unit="N·m",
            max_unit="Н·м",
            color=ModernTheme.TORQUE_COLOR,
            width=280,
            height=220,
            decimal_places=self.state.torque_decimal.get()
        )
        self.torque_card.pack(pady=(0, 12))

        self.speed_card = ValueCard(
            left_panel,
            title="Speed",
            unit="RPM",
            max_unit="об/мин",
            color=ModernTheme.SPEED_COLOR,
            width=280,
            height=220,
            decimal_places=self.state.speed_decimal.get()
        )
        self.speed_card.pack(pady=(0, 12))

        self.power_card = ValueCard(
            left_panel,
            title="Power",
            unit="W",
            max_unit="Вт",
            color=ModernTheme.POWER_COLOR,
            width=280,
            height=220
        )
        self.power_card.pack()
        
    def _create_plot_panel(self, parent: ctk.CTkFrame) -> None:
        """
        Создание панели с графиком.
        
        Args:
            parent: Родительский фрейм.
        
        Note:
            Создаёт matplotlib canvas с тремя осями Y и
            привязывает контекстное меню для настройки осей.
        """
        self.plot_panel = ctk.CTkFrame(
            parent,
            fg_color=ModernTheme.SURFACE,
            corner_radius=ModernTheme.RADIUS_LG
        )
        self.plot_panel.grid(row=0, column=1, sticky="nsew")
        
        # Создаем график
        self.plot_manager.create_plots(self.plot_panel)
        
        # Привязываем контекстное меню к графику (ПКМ для настройки осей)
        if self.plot_manager.canvas:
            self.plot_manager.canvas.get_tk_widget().bind("<Button-3>", self._show_axis_context_menu)
            # Для macOS (Button-2)
            self.plot_manager.canvas.get_tk_widget().bind("<Button-2>", self._show_axis_context_menu)
        
    def _create_bottom_bar(self) -> None:
        """Создание нижней панели с кнопками управления."""
        self.bottom_bar = ctk.CTkFrame(
            self.main_container,
            fg_color=ModernTheme.SURFACE,
            corner_radius=ModernTheme.RADIUS_MD
        )
        self.bottom_bar.pack(fill="x", pady=(16, 0))
        
        # Контейнер кнопок
        button_container = ctk.CTkFrame(
            self.bottom_bar,
            fg_color="transparent"
        )
        button_container.pack(padx=16, pady=12)
        
        # Разделитель
        separator = ctk.CTkFrame(
            button_container,
            width=1,
            height=36,
            fg_color=ModernTheme.OUTLINE
        )
        separator.pack(side="left", padx=12)
        
        # Требование 2 & 3: Кнопка Старт (начать/продолжить считывание)
        self.start_btn = ActionButton(
            button_container,
            text="СТАРТ",
            variant="primary",
            icon="▶",
            command=self._start_reading,
            state="disabled"
        )
        self.start_btn.pack(side="left", padx=4)
        
        # Кнопка Стоп (пауза)
        self.stop_btn = ActionButton(
            button_container,
            text="СТОП",
            variant="secondary",
            icon="⏹",
            command=self._stop_reading,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=4)
        
        # Кнопка Сброс (полностью очищает график и данные)
        self.reset_btn = ActionButton(
            button_container,
            text="СБРОС",
            variant="secondary",
            icon="↺",
            command=self._reset_all,
            state="disabled"
        )
        self.reset_btn.pack(side="left", padx=4)
        
        # Кнопка логирования
        self.log_btn = ActionButton(
            button_container,
            text="Логирование",
            variant="secondary",
            icon="⬇",
            command=self._start_logging,
            state="disabled"
        )
        self.log_btn.pack(side="left", padx=4)
        
        # Создаем скрытый виджет для логов
        self._create_hidden_log_widget()
        
    def _create_hidden_log_widget(self) -> None:
        """Создание скрытого виджета для логов."""
        # Создаем невидимый виджет для логгера
        self.log_text = tk.Text(
            self.root,
            height=1,
            width=1,
            wrap="word",
            bg=ModernTheme.BACKGROUND,
            fg=ModernTheme.ON_SURFACE,
            font=(ModernTheme.FONT_FAMILY_MONO, 11),
            relief="flat",
            highlightthickness=0
        )
        # Не показываем, но используем для логирования
        self.logger.set_log_widget(self.log_text)
        
    def _start_loops(self) -> None:
        """Запуск циклов обновления."""
        self.logger.process_queue()
        self._update_plot_loop()
        
        if not PYMODBUS_AVAILABLE:
            self.logger.log("ВНИМАНИЕ: pymodbus не установлен!")
        
        # Устанавливаем обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
            
    def _setup_signal_handlers(self) -> None:
        """
        Настройка обработчиков системных сигналов.
        
        Обрабатывает SIGINT (Ctrl+C) и SIGTERM для graceful shutdown.
        """
        try:
            # Обработка Ctrl+C (SIGINT)
            signal.signal(signal.SIGINT, self._signal_handler)
            # Обработка SIGTERM
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, OSError):
            # Windows может не поддерживать некоторые сигналы
            pass
    
    def _signal_handler(self, signum, frame) -> None:
        """
        Обработчик системных сигналов.
        
        Args:
            signum: Номер сигнала.
            frame: Текущий stack frame.
        """
        self.logger.log(f"[SIGNAL] Received signal {signum}, initiating shutdown...")
        self._on_window_close()
    
    def _on_window_close(self) -> None:
        """
        Обработчик закрытия окна - graceful shutdown.
        
        Гарантирует корректное закрытие всех соединений и ресурсов.
        """
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self.logger.log("[SHUTDOWN] Initiating graceful shutdown...")
        
        # Останавливаем все операции
        self._graceful_shutdown()
        
        # Закрываем окно
        self.root.quit()
        self.root.destroy()
    
    def _graceful_shutdown(self) -> None:
        """
        Graceful shutdown с сохранением данных и закрытием ресурсов.
        
        Выполняет:
        1. Остановку чтения данных
        2. Закрытие COM-порта
        3. Сохранение файлов логов
        4. Завершение потоков с таймаутом
        """
        try:
            # Устанавливаем флаг остановки
            self.stop_thread.set()
            self.state.is_connected = False
            self.state.is_reading = False
            
            # Останавливаем логирование
            self._stop_logging()
            
            # Ожидаем завершения потока чтения
            if self.read_thread and self.read_thread.is_alive():
                self.logger.log("[SHUTDOWN] Waiting for read thread...")
                try:
                    if self.read_thread != threading.current_thread():
                        self.read_thread.join(timeout=3.0)
                except Exception as e:
                    self.logger.log(f"[SHUTDOWN] Error waiting for thread: {e}")
            
            # Закрываем Modbus соединение
            if self.modbus_client:
                try:
                    self.modbus_client.close()
                    self.logger.log("[SHUTDOWN] Modbus client closed")
                except Exception as e:
                    self.logger.log(f"[SHUTDOWN] Error closing Modbus: {e}")
                finally:
                    self.modbus_client = None
            
            # Закрываем Serial соединение
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                    self.logger.log("[SHUTDOWN] Serial connection closed")
                except Exception as e:
                    self.logger.log(f"[SHUTDOWN] Error closing serial: {e}")
                finally:
                    self.serial_conn = None
            
            # Закрываем файл логов
            self.logger.close()
            
            self._shutdown_complete.set()
            self.logger.log("[SHUTDOWN] Graceful shutdown completed")
            
        except Exception as e:
            self.logger.log(f"[SHUTDOWN CRITICAL] Error during shutdown: {e}")
    
    def _open_connection_dialog(self) -> None:
        """
        Открыть диалог настроек подключения.
        
        Создаёт модальное окно для настройки параметров подключения
        к датчику DYN-200 через Modbus RTU.
        """
        if self.conn_dialog and self.conn_dialog.window.winfo_exists():
            self.conn_dialog.window.lift()
            return
        
        self.conn_dialog = ModernConnectionDialog(
            self.root, self.state,
            self._connect, self._disconnect
        )
    
    def _open_basic_settings_dialog(self) -> None:
        """
        Открыть диалог базовых настроек.
        
        Позволяет настроить отображение значений и коэффициенты пересчета.
        """
        if self.settings_dialog and self.settings_dialog.window.winfo_exists():
            self.settings_dialog.window.lift()
            return
        
        self.settings_dialog = ModernBasicSettingsDialog(
            self.root, self.state,
            self._apply_basic_settings
        )
    
    def _apply_basic_settings(self) -> None:
        """Применение базовых настроек"""
        # Обновляем отображение карточек
        self.torque_card.decimal_places = self.state.torque_decimal.get()
        self.speed_card.decimal_places = self.state.speed_decimal.get()
        self.logger.log("Базовые настройки применены")
    
    def _show_axis_context_menu(self, event) -> None:
        """
        Показать контекстное меню для настройки осей графика.
        
        Args:
            event: Событие мыши (Button-3 или Button-2)
        """
        # Создаем меню
        menu = tk.Menu(self.root, tearoff=0)
        
        menu.add_command(label="Настройка диапазонов осей",
                        command=self._open_axis_dialog)
        menu.add_separator()
        
        # Подменю для переключения видимости линий
        visibility_menu = tk.Menu(menu, tearoff=0)
        visibility_menu.add_checkbutton(label="Torque",
                                       command=lambda: self._toggle_line('torque'))
        visibility_menu.add_checkbutton(label="Speed",
                                       command=lambda: self._toggle_line('speed'))
        visibility_menu.add_checkbutton(label="Power",
                                       command=lambda: self._toggle_line('power'))
        menu.add_cascade(label="Видимость линий", menu=visibility_menu)
        
        # Показываем меню
        menu.post(event.x_root, event.y_root)
    
    def _open_axis_dialog(self) -> None:
        """Открыть диалог настроек осей графика"""
        # Используем PlotManager для открытия диалога
        if hasattr(self.plot_manager, '_open_range_dialog'):
            self.plot_manager._open_range_dialog()
    
    def _toggle_line(self, line_name: str) -> None:
        """
        Переключить видимость линии на графике.
        
        Args:
            line_name: Название линии ('torque', 'speed', 'power')
        """
        if hasattr(self.plot_manager, 'toggle_line'):
            current_visibility = self.plot_manager.get_visibility(line_name)
            self.plot_manager.toggle_line(line_name, not current_visibility)
    
    def _connect(self) -> None:
        """
        Подключение к датчику DYN-200.
        
        Выполняет подключение по Modbus RTU с использованием настроек из состояния.
        Проверяет Circuit Breaker перед попыткой подключения.
        """
        if not self.circuit_breaker.can_execute():
            self.logger.log("[CIRCUIT] Connection blocked by circuit breaker")
            return
        
        port = self.state.com_port.get()
        baud = self.state.baudrate.get()
        
        self.logger.log(f"Попытка подключения к {port} @ {baud} baud...")
        self.state.connection_status.set("подключение...")
        
        self.stop_thread.clear()
        self.read_thread = threading.Thread(target=self._detect_and_connect,
                                           args=(port, baud))
        self.read_thread.daemon = True
        self.read_thread.start()
    
    def _detect_and_connect(self, port: str, baud: int) -> None:
        """
        Определение режима и подключение в отдельном потоке.
        
        Args:
            port: COM порт
            baud: Скорость передачи данных
        """
        try:
            if PYMODBUS_AVAILABLE and self._try_modbus(port, baud):
                self.state.sensor_mode.set("Modbus RTU")
                self.logger.log("✓ Датчик работает в Modbus RTU mode")
                self._start_modbus_reader(port, baud)
                return
            
            # Не удалось подключиться
            self.state.connection_status.set("не подключен")
            self.state.sensor_mode.set("-")
            self.logger.log("✗ Не удалось определить режим датчика")
            self.circuit_breaker.record_failure()
            
        except Exception as e:
            self.state.connection_status.set("не подключен")
            self.logger.log(f"Критическая ошибка: {e}")
            self.circuit_breaker.record_failure()
    
    def _try_modbus(self, port: str, baud: int) -> bool:
        """
        Попытка подключения по Modbus.
        
        Args:
            port: COM порт
            baud: Скорость передачи данных
            
        Returns:
            True если подключение успешно, False в противном случае
        """
        client = None
        try:
            client = ModbusSerialClient(
                port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=2
            )
            
            if not client.connect():
                self.logger.log(f"[ERROR] Не удалось открыть порт {port}")
                return False
            
            slave = self.state.slave_addr.get()
            response = client.read_holding_registers(0, count=6, device_id=slave)
            
            if response and not response.isError() and hasattr(response, 'registers'):
                if len(response.registers) >= 6:
                    self.logger.log(f"[OK] Получено {len(response.registers)} регистров от device_id {slave}")
                    return True
                else:
                    self.logger.log(f"[ERROR] Недостаточно регистров: {len(response.registers)}")
                    return False
            self.logger.log("[ERROR] Нет ответа или ошибка Modbus")
            return False
            
        except Exception as e:
            self.logger.log(f"[CRITICAL] Исключение: {e}")
            return False
        finally:
            if client:
                try:
                    client.close()
                except Exception as e:
                    self.logger.log(f"[WARN] Ошибка закрытия клиента: {e}")
    
    def _start_modbus_reader(self, port: str, baud: int) -> None:
        """
        Запуск чтения данных по Modbus.
        
        Args:
            port: COM порт
            baud: Скорость передачи данных
        """
        try:
            self.modbus_client = ModbusSerialClient(
                port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=1
            )
            
            if self.modbus_client.connect():
                self.state.is_connected = True
                self.state.connection_status.set("подключен")
                self._update_ui_connected(True)
                self.circuit_breaker.record_success()
                self.logger.log("Подключено по Modbus RTU")
                
                # Запускаем поток чтения
                self.read_thread = threading.Thread(target=self._modbus_read_loop)
                self.read_thread.daemon = True
                self.read_thread.start()
            else:
                self.state.connection_status.set("не подключен")
                self.circuit_breaker.record_failure()
                
        except Exception as e:
            self.state.connection_status.set("не подключен")
            self.logger.log(f"Ошибка: {e}")
            self.circuit_breaker.record_failure()
    
    def _modbus_read_loop(self) -> None:
        """Цикл чтения данных по Modbus"""
        error_count = 0
        self.logger.log("Запущен цикл чтения Modbus")
        
        while not self.stop_thread.is_set() and self.state.is_connected:
            if not self.state.is_reading:
                time.sleep(0.1)
                continue
            
            try:
                response = self.modbus_client.read_holding_registers(
                        0, count=6, device_id=self.state.slave_addr.get()
                    )
                
                if response and not response.isError() and hasattr(response, 'registers'):
                    error_count = 0
                    registers = response.registers
                    
                    torque_raw = (registers[0] << 16) | registers[1]
                    torque = to_signed32(torque_raw)
                    speed_raw = (registers[2] << 16) | registers[3]
                    power_raw = (registers[4] << 16) | registers[5]
                    
                    torque_nm = raw_to_torque(torque)
                    speed_rpm = raw_to_speed(speed_raw)
                    power_w = raw_to_power(power_raw, self.state.power_correction.get())
                    
                    self._add_data(torque_nm, speed_rpm, power_w)
                else:
                    error_count += 1
                    if error_count > 10:
                        self.logger.log("[WARN] Слишком много ошибок чтения")
                        time.sleep(3)
                        error_count = 0
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.log(f"Ошибка чтения: {e}")
                error_count += 1
                if error_count > 5:
                    self.logger.log("[CRITICAL] Критическое количество ошибок, переподключение...")
                    self._disconnect()
                    return
                time.sleep(1)
    
    def _add_data(self, torque: float, speed: float, power: float) -> None:
        """
        Добавление данных в очередь.
        
        Args:
            torque: Крутящий момент в Н·м
            speed: Скорость в RPM
            power: Мощность в Вт
        """
        timestamp = datetime.now()
        self.state.append_data(timestamp, torque, speed, power)
        
        # Обновляем UI
        self.root.after(0, lambda: self._update_labels(torque, speed, power))
        
        # Логирование в CSV
        if self.state.is_logging and self.csv_writer:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.csv_writer.writerow([timestamp_str, torque, speed, power, 'Modbus'])
            try:
                self.log_file.flush()
            except:
                pass
    
    def _update_labels(self, torque: float, speed: float, power: float) -> None:
        """
        Обновление меток значений.
        
        Требование 3: Максимальные значения фиксируются во время замера
        и отображаются в квадратах слева.
        
        Args:
            torque: Крутящий момент в Н·м
            speed: Скорость в RPM
            power: Мощность в Вт
        """
        # Обновляем текущие значения в карточках
        self.torque_card.update_value(torque)
        self.speed_card.update_value(speed)
        self.power_card.update_value(power)
        
        # Требование 3: Обновляем максимальные значения ТОЛЬКО если идёт считывание
        if self.state.is_reading:
            max_updated = False
            
            if abs(torque) > abs(self.max_torque):
                self.max_torque = torque
                max_updated = True
            if speed > self.max_speed:
                self.max_speed = speed
                max_updated = True
            if power > self.max_power:
                self.max_power = power
                max_updated = True
            
            # Обновляем отображение максимумов в карточках
            if max_updated:
                self.torque_card.update_max_value(self.max_torque)
                self.speed_card.update_max_value(self.max_speed)
                self.power_card.update_max_value(self.max_power)
    
    def _update_ui_connected(self, connected: bool) -> None:
        """
        Обновление UI при изменении состояния подключения.
        
        Требование 2: При подключении считывание НЕ начинается автоматически.
        Пользователь должен явно нажать кнопку "Старт".
        
        Args:
            connected: True если подключено
        """
        if connected:
            # Требование 2: Не запускаем считывание автоматически
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.reset_btn.configure(state="normal")
            self.log_btn.configure(state="normal")
            self.status_badge.set_status("CONNECTED", True)
            # НЕ вызываем self._start_reading() - ждём нажатия кнопки Старт
        else:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            self.reset_btn.configure(state="disabled")
            self.log_btn.configure(state="disabled")
            self.status_badge.set_status("DISCONNECTED", False)
            self._stop_reading()
    
    def _start_reading(self) -> None:
        """
        Требование 2 & 3: Начать/продолжить считывание данных.
        
        При повторном нажатии после остановки - данные продолжают накапливаться
        (график продолжается, а не начинается заново).
        """
        if not self.state.is_connected:
            self.logger.log("Нет подключения к датчику")
            return
            
        self.state.is_reading = True
        self.stop_thread.clear()
        
        # Обновляем кнопки
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.state.reading_status.set("производится")
        
        self.logger.log("Считывание данных начато (продолжено)")
    
    def _stop_reading(self) -> None:
        """
        Требование 3: Остановить (приостановить) считывание данных.
        
        Данные сохраняются, при повторном старте график продолжится.
        """
        self.state.is_reading = False
        self.stop_thread.set()
        
        # Обновляем кнопки
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.state.reading_status.set("остановлено")
        
        self.logger.log("Считывание данных остановлено (пауза)")
    
    def _disconnect(self) -> None:
        """Отключение от датчика"""
        self._stop_reading()
        self.state.is_connected = False
        
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except:
                pass
            self.modbus_client = None
        
        self._stop_logging()
        self.state.connection_status.set("не подключен")
        self.state.sensor_mode.set("-")
        self._update_ui_connected(False)
        self.logger.log("Отключено от датчика")
    
    def _start_logging(self) -> None:
        """Начать логирование в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.log_file = open(filename, 'w', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.log_file)
                self.csv_writer.writerow(['Timestamp', 'Torque_Nm', 'Speed_RPM', 'Power_W', 'Mode'])
                self.state.is_logging = True
                self.log_btn.configure(text="⏹ Стоп лог", variant="secondary")
                self.logger.log(f"Логирование начато: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")
    
    def _stop_logging(self) -> None:
        """Остановить логирование"""
        self.state.is_logging = False
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
            self.csv_writer = None
        self.log_btn.configure(text="Логирование")
        self.logger.log("Логирование остановлено")
    
    def _reset_all(self) -> None:
        """
        Требование 2 & 3: Полный сброс - очищает график, все данные и максимумы.
        
        Эта кнопка полностью сбрасывает состояние:
        - Очищает все накопленные данные
        - Очищает график
        - Сбрасывает максимальные значения
        - Останавливает считывание если было активно
        """
        # Останавливаем считывание если активно
        was_reading = self.state.is_reading
        if was_reading:
            self._stop_reading()
        
        # Очищаем данные
        self.state.clear_data()
        self.plot_manager.clear_plots()
        
        # Требование 3: Сбрасываем максимальные значения
        self._reset_max_values_internal()
        
        self.logger.log("Полный сброс выполнен (данные, график, максимумы)")
    
    def _reset_max_values_internal(self) -> None:
        """Внутренний метод сброса максимальных значений (без лога)"""
        self.max_torque = 0.0
        self.max_speed = 0.0
        self.max_power = 0.0
        self.torque_card.reset_max()
        self.speed_card.reset_max()
        self.power_card.reset_max()
    
    def _update_plot_loop(self) -> None:
        """
        Цикл обновления графика.
        
        Вызывается периодически для обновления отображения данных на графике.
        Использует tkinter.after для планирования следующего обновления.
        """
        try:
            # Получаем данные из состояния
            timestamps, torque_data, speed_data, power_data = self.state.get_data_copy()
            
            if timestamps:
                # Преобразуем datetime в секунды от начала измерения
                start_time = timestamps[0]
                time_seconds = [(t - start_time).total_seconds() for t in timestamps]
                
                # Обновляем график
                self.plot_manager.update_plots(
                    time_seconds,
                    torque_data,
                    speed_data,
                    power_data
                )
        except Exception as e:
            self.logger.log(f"[PLOT] Error updating plot: {e}")
        
        # Планируем следующее обновление (каждые 50 мс = 20 FPS)
        self.root.after(50, self._update_plot_loop)
