#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Современные диалоговые окна с Material Design 3.

Предоставляет диалоги для настройки подключения, осей графика
и базовых параметров с валидацией входных данных.

ЭТАП 5-6: Валидация входных данных, защита от path traversal,
модульная архитектура gui/.

Examples:
    >>> import customtkinter as ctk
    >>> from gui.modern_dialogs import ModernConnectionDialog
    >>> 
    >>> root = ctk.CTk()
    >>> dialog = ModernConnectionDialog(root, state, on_connect, on_disconnect)

Attributes:
    validate_com_port: Функция валидации COM-порта.
    validate_baudrate: Функция валидации baudrate.
    validate_log_path: Функция валидации пути к файлу логов.
    ModernDialogBase: Базовый класс для всех диалогов.
    ModernConnectionDialog: Диалог настроек подключения.
    ModernAxisDialog: Диалог настроек осей графика.
    ModernBasicSettingsDialog: Диалог базовых настроек.
"""

# ===== СТАНДАРТНЫЕ БИБЛИОТЕКИ =====
import os
import re
from typing import Callable, Optional, Tuple

# ===== СТОРОННИЕ БИБЛИОТЕКИ =====
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import serial.tools.list_ports

# ===== ЛОКАЛЬНЫЕ МОДУЛИ =====
from gui.modern_theme import ModernTheme
from gui.value_card import ActionButton


def validate_com_port(port: str) -> Tuple[bool, str]:
    """
    Валидация COM-порта.
    
    Проверяет формат COM-порта для Windows (COM1-COM256)
    или Linux (/dev/ttyUSB0, /dev/ttyACM0 и т.д.).
    
    Args:
        port: Строка с именем COM-порта.
    
    Returns:
        Кортеж (is_valid, error_message).
        is_valid: True если порт корректен, False если нет.
        error_message: Описание ошибки (пустая строка если is_valid=True).
    
    Examples:
        >>> validate_com_port("COM4")
        (True, '')
        >>> validate_com_port("/dev/ttyUSB0")
        (True, '')
        >>> validate_com_port("COM0")
        (False, 'Неверный формат COM-порта: COM0')
        >>> validate_com_port("")
        (False, 'COM-порт не может быть пустым')
    """
    if not port:
        return False, "COM-порт не может быть пустым"
    
    # Windows: COM1-COM256, Linux: /dev/ttyUSB0, /dev/ttyACM0, etc.
    windows_pattern = r'^COM([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-6])$'
    linux_pattern = r'^/dev/tty[A-Za-z0-9]+$'
    
    if not (re.match(windows_pattern, port, re.IGNORECASE) or re.match(linux_pattern, port)):
        return False, f"Неверный формат COM-порта: {port}"
    
    return True, ""


def validate_baudrate(baud: int) -> Tuple[bool, str]:
    """
    Валидация baudrate.
    
    Проверяет, что baudrate является одним из стандартных значений.
    
    Args:
        baud: Целое число - скорость передачи данных.
    
    Returns:
        Кортеж (is_valid, error_message).
        is_valid: True если baudrate корректен, False если нет.
        error_message: Описание ошибки (пустая строка если is_valid=True).
    
    Examples:
        >>> validate_baudrate(19200)
        (True, '')
        >>> validate_baudrate(115200)
        (True, '')
        >>> validate_baudrate(99999)
        (False, 'Неверный baudrate: 99999...')
    """
    valid_baudrates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]
    
    if baud not in valid_baudrates:
        return False, f"Неверный baudrate: {baud}. Допустимые значения: {valid_baudrates}"
    
    return True, ""


def validate_log_path(filepath: str) -> Tuple[bool, str]:
    """
    Валидация пути для сохранения лога (защита от path traversal).
    
    Проверяет:
    - Путь не пустой
    - Нет символов .. (path traversal)
    - Директория существует и доступна для записи
    - Файл доступен для записи (если существует)
    
    Args:
        filepath: Путь к файлу логов.
    
    Returns:
        Кортеж (is_valid, error_message).
        is_valid: True если путь корректен, False если нет.
        error_message: Описание ошибки (пустая строка если is_valid=True).
    
    Examples:
        >>> validate_log_path("data/log.csv")
        (True, '')
        >>> validate_log_path("../etc/passwd")
        (False, 'Путь содержит недопустимые символы (..)')
        >>> validate_log_path("/nonexistent/file.csv")
        (False, 'Директория не существует...')
    """
    if not filepath:
        return False, "Путь к файлу не может быть пустым"
    
    # Проверка на path traversal
    normalized_path = os.path.normpath(filepath)
    
    # Запрещаем пути с .. или абсолютные пути вне текущей директории
    if '..' in normalized_path:
        return False, "Путь содержит недопустимые символы (..)"
    
    # Проверяем, что путь к файлу доступен для записи
    try:
        directory = os.path.dirname(normalized_path) or '.'
        if not os.path.exists(directory):
            return False, f"Директория не существует: {directory}"
        if not os.path.isdir(directory):
            return False, f"Указанный путь не является директорией: {directory}"
        # Проверка доступности на запись
        if os.path.exists(normalized_path) and not os.access(normalized_path, os.W_OK):
            return False, f"Файл недоступен для записи: {normalized_path}"
        if not os.access(directory, os.W_OK):
            return False, f"Директория недоступна для записи: {directory}"
    except Exception as e:
        return False, f"Ошибка проверки пути: {e}"
    
    return True, ""


class ModernDialogBase:
    """
    Базовый класс для современных диалогов.
    
    Предоставляет общую функциональность для всех диалогов:
    - Центрирование окна на экране
    - Управление modal mode (grab_set)
    - Стандартное закрытие с освобождением ресурсов
    - Callback при закрытии
    
    Attributes:
        parent: Родительское окно.
        window: Окно диалога (CTkToplevel).
        on_close_callback: Callback при закрытии диалога.
    
    Example:
        >>> class MyDialog(ModernDialogBase):
        ...     def __init__(self, parent):
        ...         super().__init__(parent, "Мой диалог", 400, 300)
        ...         self._create_ui()
        ...
        >>> dialog = MyDialog(root)
    """
    
    def __init__(self, parent: ctk.CTk, title: str, width: int, height: int) -> None:
        """
        Инициализация базового диалога.
        
        Args:
            parent: Родительское окно.
            title: Заголовок диалога.
            width: Ширина окна в пикселях.
            height: Высота окна в пикселях.
        """
        self.parent = parent
        self.window = ctk.CTkToplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрируем окно
        self._center_window(width, height)
        
        # Callback для закрытия
        self.on_close_callback: Optional[Callable[[], None]] = None
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _center_window(self, width: int, height: int) -> None:
        """
        Центрирование окна на экране.
        
        Args:
            width: Ширина окна.
            height: Высота окна.
        """
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        
    def _on_close(self) -> None:
        """
        Закрытие окна с освобождением grab.
        
        Вызывается при закрытии диалога (X, Esc, или программно).
        Освобождает modal mode и вызывает on_close_callback если установлен.
        """
        try:
            self.window.grab_release()
        except (tk.TclError, RuntimeError):
            # Окно уже освобождено или уничтожено
            pass
        except Exception as e:
            print(f"[DIALOG] Error releasing grab: {e}")
        finally:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception as e:
                print(f"[DIALOG] Error in close callback: {e}")
            
    def _create_main_frame(self) -> ctk.CTkFrame:
        """
        Создание главного контейнера диалога.
        
        Returns:
            Фрейм с настройками по умолчанию для содержимого диалога.
        """
        main_frame = ctk.CTkFrame(
            self.window,
            fg_color=ModernTheme.SURFACE,
            corner_radius=ModernTheme.RADIUS_MD
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        return main_frame
        
    def _create_header(self, parent: ctk.CTkFrame, title: str, subtitle: str = "") -> None:
        """
        Создание заголовка диалога.
        
        Args:
            parent: Родительский фрейм.
            title: Заголовок.
            subtitle: Подзаголовок (опционально).
        """
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header,
            text=title,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XL, "bold"),
            text_color=ModernTheme.ON_SURFACE
        ).pack(anchor="w")
        
        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM),
                text_color=ModernTheme.ON_SURFACE_VARIANT
            ).pack(anchor="w", pady=(4, 0))
            
    def _create_separator(self, parent: ctk.CTkFrame) -> None:
        """
        Создание горизонтального разделителя.
        
        Args:
            parent: Родительский фрейм.
        """
        separator = ctk.CTkFrame(
            parent, height=1, fg_color=ModernTheme.OUTLINE_VARIANT
        )
        separator.pack(fill="x", padx=20, pady=10)


class ModernConnectionDialog(ModernDialogBase):
    """
    Современный диалог настроек подключения.
    
    Позволяет настроить:
    - COM-порт (с валидацией)
    - Baudrate (с валидацией)
    - Slave Address
    
    Выполняет валидацию перед подключением и отображает статус.
    
    Attributes:
        state: Состояние приложения (AppState).
        on_connect: Callback для подключения.
        on_disconnect: Callback для отключения.
    
    Example:
        >>> dialog = ModernConnectionDialog(root, state, connect_fn, disconnect_fn)
    """
    
    def __init__(self, parent: ctk.CTk, state, on_connect: Callable[[], None], on_disconnect: Callable[[], None]) -> None:
        """
        Инициализация диалога подключения.
        
        Args:
            parent: Родительское окно.
            state: Состояние приложения.
            on_connect: Функция для вызова при подключении.
            on_disconnect: Функция для вызова при отключении.
        """
        super().__init__(parent, "Настройки подключения", 500, 500)
        self.state = state
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        self._create_ui()
        
    def _create_ui(self) -> None:
        """Создание интерфейса диалога."""
        main_frame = self._create_main_frame()
        
        # Заголовок
        self._create_header(main_frame, "🔌 Настройки подключения", "Выберите порт и параметры связи")
        
        # Разделитель
        self._create_separator(main_frame)
        
        # Форма настроек
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=10)
        
        # COM порт
        self._create_form_row(form_frame, "COM порт:", 0, self._create_port_combo)
        
        # Baudrate
        self._create_form_row(form_frame, "Baudrate:", 1, self._create_baud_combo)
        
        # Slave Address
        self._create_form_row(form_frame, "Slave Address:", 2, self._create_slave_spinbox)
        
        # Статус и режим
        self._create_status_section(main_frame)
        
        # Кнопки управления
        self._create_button_section(main_frame)
        
        # Устанавливаем правильное состояние кнопок при открытии диалога
        self.update_buttons(self.state.is_connected)

    def _create_form_row(self, parent: ctk.CTkFrame, label_text: str, row: int, create_widget_func: Callable[[ctk.CTkFrame], None]) -> None:
        """
        Создание строки формы.
        
        Args:
            parent: Родительский фрейм.
            label_text: Текст метки.
            row: Номер строки (для совместимости).
            create_widget_func: Функция создания виджета.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Метка
        ctk.CTkLabel(
            frame,
            text=label_text,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=120
        ).pack(side="left")
        
        # Виджет создается через функцию
        create_widget_func(frame)
        
    def _create_port_combo(self, parent: ctk.CTkFrame) -> None:
        """
        Создание комбобокса для портов.
        
        Args:
            parent: Родительский фрейм.
        """
        self.port_combo = ctk.CTkComboBox(
            parent,
            values=self._get_ports(),
            variable=self.state.com_port,
            width=200,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            dropdown_font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            button_color=ModernTheme.PRIMARY,
            button_hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1)
        )
        self.port_combo.pack(side="left", padx=(10, 0))
        
        # Кнопка обновления
        refresh_btn = ctk.CTkButton(
            parent,
            text="🔄",
            width=36,
            height=36,
            corner_radius=8,
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=self._refresh_ports
        )
        refresh_btn.pack(side="left", padx=(8, 0))
        
    def _create_baud_combo(self, parent: ctk.CTkFrame) -> None:
        """
        Создание комбобокса для baudrate.
        
        Args:
            parent: Родительский фрейм.
        """
        baud_values = ["9600", "19200", "38400", "57600", "115200"]
        
        self.baud_combo = ctk.CTkComboBox(
            parent,
            values=baud_values,
            variable=tk.StringVar(value=str(self.state.baudrate.get())),
            width=200,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            dropdown_font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            button_color=ModernTheme.PRIMARY,
            button_hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1),
            command=self._on_baud_changed
        )
        self.baud_combo.pack(side="left", padx=(10, 0))
        
    def _on_baud_changed(self, value: str) -> None:
        """
        Обработка изменения baudrate.
        
        Args:
            value: Новое значение baudrate.
        """
        try:
            self.state.baudrate.set(int(value))
        except ValueError:
            # Некорректное значение baudrate
            pass
        except tk.TclError:
            # Переменная не инициализирована или уничтожена
            pass
            
    def _create_slave_spinbox(self, parent: ctk.CTkFrame) -> None:
        """
        Создание спинбокса для slave address.
        
        Args:
            parent: Родительский фрейм.
        """
        # CTk не имеет спинбокса, используем entry + кнопки
        slave_frame = ctk.CTkFrame(parent, fg_color="transparent")
        slave_frame.pack(side="left", padx=(10, 0))
        
        self.slave_entry = ctk.CTkEntry(
            slave_frame,
            textvariable=self.state.slave_addr,
            width=80,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            justify="center"
        )
        self.slave_entry.pack(side="left")
        
        # Кнопки +/-
        btn_frame = ctk.CTkFrame(slave_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="▲",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=self._increment_slave
        ).pack()
        
        ctk.CTkButton(
            btn_frame,
            text="▼",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=self._decrement_slave
        ).pack(pady=(2, 0))
        
    def _create_status_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции статуса.
        
        Args:
            parent: Родительский фрейм.
        """
        # Статус
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(
            status_frame,
            text="Статус:",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.state.connection_status,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD, "bold"),
            text_color=ModernTheme.ERROR
        )
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Режим датчика
        mode_frame = ctk.CTkFrame(parent, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=(5, 0))
        
        ctk.CTkLabel(
            mode_frame,
            text="Режим:",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left")
        
        ctk.CTkLabel(
            mode_frame,
            textvariable=self.state.sensor_mode,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.PRIMARY
        ).pack(side="left", padx=(10, 0))
        
    def _create_button_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции кнопок.
        
        Args:
            parent: Родительский фрейм.
        """
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(20, 20))
        
        # Используем стандартные CTkButton вместо ActionButton для надёжности
        self.connect_btn = ctk.CTkButton(
            btn_frame,
            text="🔌 Подключить",
            command=self._on_connect,
            width=150,
            height=36,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD, "bold"),
            fg_color=ModernTheme.PRIMARY,
            hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1),
            text_color="white"
        )
        self.connect_btn.pack(side="left", padx=(0, 10))
        
        self.disconnect_btn = ctk.CTkButton(
            btn_frame,
            text="⏏ Отключить",
            command=self._on_disconnect,
            width=150,
            height=36,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            hover_color=ModernTheme.adjust_brightness(ModernTheme.SURFACE_CONTAINER_HIGH, 1.1),
            text_color=ModernTheme.ON_SURFACE,
            state="disabled"
        )
        self.disconnect_btn.pack(side="left", padx=(0, 10))
        
        self.close_btn = ctk.CTkButton(
            btn_frame,
            text="Закрыть",
            command=self._on_close,
            width=100,
            height=36,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color="transparent",
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            text_color=ModernTheme.ON_SURFACE_VARIANT
        )
        self.close_btn.pack(side="right")
        
    def _increment_slave(self) -> None:
        """Увеличение slave address."""
        current = self.state.slave_addr.get()
        if current < 247:
            self.state.slave_addr.set(current + 1)
            
    def _decrement_slave(self) -> None:
        """Уменьшение slave address."""
        current = self.state.slave_addr.get()
        if current > 1:
            self.state.slave_addr.set(current - 1)
        
    def _get_ports(self) -> list:
        """
        Получение списка COM портов.
        
        Returns:
            Список доступных портов или ['COM4'] по умолчанию.
        """
        try:
            ports = serial.tools.list_ports.comports()
            return [p.device for p in ports] or ["COM4"]
        except (ImportError, OSError, IOError) as e:
            # Ошибка доступа к системным портам
            print(f"[PORTS] Error listing ports: {e}")
            return ["COM4"]
        except Exception as e:
            # Прочие ошибки
            print(f"[PORTS] Unexpected error: {e}")
            return ["COM4"]
            
    def _refresh_ports(self) -> None:
        """Обновление списка портов."""
        self.port_combo.configure(values=self._get_ports())
        
    def _on_connect(self) -> None:
        """
        Обработка подключения с валидацией.
        
        Проверяет COM-порт и baudrate перед вызовом on_connect.
        При ошибке показывает сообщение.
        """
        # Валидация COM-порта
        port = self.state.com_port.get()
        is_valid, error_msg = validate_com_port(port)
        if not is_valid:
            tk.messagebox.showerror("Ошибка", f"Некорректный COM-порт:\n{error_msg}")
            return
        
        # Валидация baudrate
        baud = self.state.baudrate.get()
        is_valid, error_msg = validate_baudrate(baud)
        if not is_valid:
            tk.messagebox.showerror("Ошибка", f"Некорректный baudrate:\n{error_msg}")
            return
        
        # Разблокируем GUI перед потенциально блокирующей операцией
        try:
            self.window.grab_release()
        except (tk.TclError, RuntimeError):
            # Grab уже освобождён или окно уничтожено
            pass
        self.connect_btn.configure(state="disabled")
        self.disconnect_btn.configure(state="normal")
        self.on_connect()

    def _on_disconnect(self) -> None:
        """Обработка отключения."""
        # Разблокируем GUI перед потенциально блокирующей операцией
        try:
            self.window.grab_release()
        except (tk.TclError, RuntimeError):
            # Grab уже освобождён или окно уничтожено
            pass
        self.connect_btn.configure(state="normal")
        self.disconnect_btn.configure(state="disabled")
        self.on_disconnect()
        
    def update_buttons(self, connected: bool) -> None:
        """
        Обновление состояния кнопок.
        
        Args:
            connected: True если подключено, False если нет.
        """
        if connected:
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.configure(state="normal")
        else:
            self.connect_btn.configure(state="normal")
            self.disconnect_btn.configure(state="disabled")


class ModernBasicSettingsDialog(ModernDialogBase):
    """
    Современный диалог базовых настроек отображения.
    
    Позволяет настроить:
    - Десятичные знаки для Torque и Speed
    - Коэффициенты пересчёта (torque, speed, power)
    
    Выполняет валидацию значений при применении.
    
    Attributes:
        state: Состояние приложения (AppState).
        on_apply: Callback при применении настроек.
    
    Example:
        >>> dialog = ModernBasicSettingsDialog(root, state, apply_callback)
    """
    
    def __init__(self, parent: ctk.CTk, state, on_apply: Optional[Callable[[], None]] = None) -> None:
        """
        Инициализация диалога базовых настроек.
        
        Args:
            parent: Родительское окно.
            state: Состояние приложения.
            on_apply: Callback при применении настроек.
        """
        super().__init__(parent, "Базовые настройки", 450, 400)
        self.state = state
        self.on_apply = on_apply
        
        self._create_ui()
        
    def _create_ui(self) -> None:
        """Создание интерфейса."""
        main_frame = self._create_main_frame()
        
        # Заголовок
        self._create_header(main_frame, "⚙️ Базовые настройки", "Настройте отображение значений и коэффициенты")
        
        # Разделитель
        self._create_separator(main_frame)
        
        # Секция: Десятичные знаки
        self._create_decimal_section(main_frame)
        
        # Секция: Коэффициенты
        self._create_coefficient_section(main_frame)
        
        # Разделитель перед кнопками
        self._create_separator(main_frame)
        
        # Кнопки
        self._create_button_section(main_frame)
        
    def _create_decimal_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции настройки десятичных знаков.
        
        Args:
            parent: Родительский фрейм.
        """
        decimal_frame = ctk.CTkFrame(parent, fg_color="transparent")
        decimal_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            decimal_frame,
            text="Десятичные знаки",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_LG, "bold"),
            text_color=ModernTheme.ON_SURFACE
        ).pack(anchor="w")
        
        # Torque decimal
        self._create_decimal_row(
            decimal_frame, 
            "Крутящий момент (Torque):",
            self.state.torque_decimal,
            "0-4 знака",
            0
        )
        
        # Speed decimal
        self._create_decimal_row(
            decimal_frame,
            "Обороты (Speed):",
            self.state.speed_decimal,
            "0-4 знака",
            1
        )
        
    def _create_coefficient_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции коэффициентов.
        
        Args:
            parent: Родительский фрейм.
        """
        coeff_frame = ctk.CTkFrame(parent, fg_color="transparent")
        coeff_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(
            coeff_frame,
            text="Коэффициенты пересчета",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_LG, "bold"),
            text_color=ModernTheme.ON_SURFACE
        ).pack(anchor="w")
        
        # Torque coefficient
        self._create_coefficient_row(coeff_frame, "Коэффициент момента:", self.state.torque_coefficient, "множитель для крутящего момента")
        
        # Speed coefficient
        self._create_coefficient_row(coeff_frame, "Коэффициент оборотов:", self.state.speed_coefficient, "множитель для оборотов (1.0 = без изменений)")
        
        # Power correction coefficient
        self._create_coefficient_row(coeff_frame, "Коррекция мощности:", self.state.power_correction, "коэффициент коррекции мощности (0.1-2.0)")
        
    def _create_button_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание кнопок диалога.
        
        Args:
            parent: Родительский фрейм.
        """
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            btn_frame,
            text="Применить",
            command=self._apply,
            width=140,
            height=36,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD, "bold"),
            fg_color=ModernTheme.PRIMARY,
            hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1),
            text_color=ModernTheme.ON_PRIMARY
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="Закрыть",
            command=self.window.destroy,
            width=100,
            height=36,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color="transparent",
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="right")
        
    def _create_decimal_row(self, parent: ctk.CTkFrame, label_text: str, variable, hint: str, row: int) -> None:
        """
        Создание строки для настройки десятичных знаков.
        
        Args:
            parent: Родительский фрейм.
            label_text: Текст метки.
            variable: Переменная tkinter для связи.
            hint: Подсказка.
            row: Номер строки (для совместимости).
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=6)
        
        # Метка
        ctk.CTkLabel(
            frame,
            text=label_text,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=200
        ).pack(side="left")
        
        # Контейнер для спинбокса
        spin_frame = ctk.CTkFrame(frame, fg_color="transparent")
        spin_frame.pack(side="left", padx=(10, 0))
        
        # Поле ввода
        entry = ctk.CTkEntry(
            spin_frame,
            textvariable=variable,
            width=60,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            justify="center"
        )
        entry.pack(side="left")
        
        # Кнопки +/-
        btn_frame = ctk.CTkFrame(spin_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="▲",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=lambda: self._increment_var(variable, 0, 4)
        ).pack()
        
        ctk.CTkButton(
            btn_frame,
            text="▼",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=lambda: self._decrement_var(variable, 0, 4)
        ).pack(pady=(2, 0))
        
        # Подсказка
        ctk.CTkLabel(
            frame,
            text=hint,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _create_coefficient_row(self, parent: ctk.CTkFrame, label: str, variable, hint: str) -> None:
        """
        Создание строки для коэффициента.
        
        Args:
            parent: Родительский фрейм.
            label: Текст метки.
            variable: Переменная tkinter для связи.
            hint: Подсказка.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Метка
        ctk.CTkLabel(
            frame,
            text=label,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=200
        ).pack(side="left")
        
        # Поле ввода
        entry = ctk.CTkEntry(
            frame,
            textvariable=variable,
            width=100,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            justify="center"
        )
        entry.pack(side="left", padx=(10, 0))
        
        # Подсказка
        ctk.CTkLabel(
            frame,
            text=hint,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _increment_var(self, variable, min_val: int, max_val: int) -> None:
        """
        Увеличение значения переменной с ограничением.
        
        Args:
            variable: Переменная tkinter.
            min_val: Минимальное значение.
            max_val: Максимальное значение.
        """
        try:
            current = variable.get()
            if current < max_val:
                variable.set(current + 1)
        except (ValueError, tk.TclError):
            # Некорректное значение или переменная уничтожена
            pass
        except Exception as e:
            print(f"[DIALOG] Error incrementing var: {e}")
            
    def _decrement_var(self, variable, min_val: int, max_val: int) -> None:
        """
        Уменьшение значения переменной с ограничением.
        
        Args:
            variable: Переменная tkinter.
            min_val: Минимальное значение.
            max_val: Максимальное значение.
        """
        try:
            current = variable.get()
            if current > min_val:
                variable.set(current - 1)
        except (ValueError, tk.TclError):
            # Некорректное значение или переменная уничтожена
            pass
        except Exception as e:
            print(f"[DIALOG] Error decrementing var: {e}")

    def _apply(self) -> None:
        """
        Применение настроек и закрытие диалога.
        
        Выполняет валидацию значений перед применением:
        - Десятичные знаки ограничиваются диапазоном 0-4
        - Коэффициенты должны быть положительными
        - Коррекция мощности ограничена 0.1-2.0
        
        Вызывает on_apply callback если установлен.
        """
        # Валидация значений
        try:
            # Ограничиваем десятичные знаки 0-4
            torque_dec = max(0, min(4, self.state.torque_decimal.get()))
            self.state.torque_decimal.set(torque_dec)

            speed_dec = max(0, min(4, self.state.speed_decimal.get()))
            self.state.speed_decimal.set(speed_dec)

            # Коэффициент должен быть положительным
            coeff = self.state.torque_coefficient.get()
            if coeff <= 0:
                self.state.torque_coefficient.set(1.0)
            
            # Коэффициент коррекции мощности должен быть в диапазоне 0.1-2.0
            power_coeff = self.state.power_correction.get()
            if power_coeff < 0.1 or power_coeff > 2.0:
                self.state.power_correction.set(1.0)

        except (ValueError, tk.TclError) as e:
            # Ошибка валидации значения
            print(f"[DIALOG] Validation error: {e}")

        # Вызываем callback если есть
        if self.on_apply:
            self.on_apply()

        self._on_close()


class ModernSensorInfoDialog(ModernDialogBase):
    """
    Диалог редактирования параметров датчика DYN-200.
    
    Позволяет редактировать ключевые параметры датчика, влияющие на расчёт значений:
    - Rdecimal: количество десятичных знаков для скорости
    - T_ratio: передаточное отношение для крутящего момента
    - P_units: единицы измерения мощности (W/kW)
    
    Параметры автоматически применяются при нажатии кнопки "Применить"
    и сохраняются в состоянии приложения (AppState).
    
    Attributes:
        state: Состояние приложения (AppState).
        on_apply: Callback при применении настроек.
    
    Example:
        >>> dialog = ModernSensorInfoDialog(root, state, on_apply_callback)
    """
    
    def __init__(self, parent: ctk.CTk, state, on_apply: Optional[Callable[[], None]] = None) -> None:
        """
        Инициализация диалога параметров датчика.
        
        Args:
            parent: Родительское окно.
            state: Состояние приложения (AppState).
            on_apply: Callback при применении настроек (опционально).
        """
        super().__init__(parent, "Параметры датчика DYN-200", 500, 550)
        self.state = state
        self.on_apply = on_apply
        self._param_widgets = {}  # Словарь для хранения виджетов параметров
        self._create_ui()
        
    def _create_ui(self) -> None:
        """Создание интерфейса диалога."""
        main_frame = self._create_main_frame()
        
        # Заголовок с иконкой
        self._create_header(
            main_frame,
            "⚙️ Параметры датчика DYN-200",
            "Настройте параметры, влияющие на расчёт значений"
        )
        
        # Информационная панель с иконкой
        self._create_info_banner(main_frame)
        
        # Разделитель
        self._create_separator(main_frame)
        
        # Секция с редактируемыми параметрами
        self._create_editable_params_section(main_frame)
        
        # Секция read-only параметров
        self._create_readonly_params_section(main_frame)
        
        # Разделитель перед кнопками
        self._create_separator(main_frame)
        
        # Кнопки
        self._create_button_section(main_frame)
        
    def _create_info_banner(self, parent: ctk.CTkFrame) -> None:
        """
        Создание информационного баннера с подсказкой.
        
        Args:
            parent: Родительский фрейм.
        """
        banner = ctk.CTkFrame(
            parent,
            fg_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            corner_radius=ModernTheme.RADIUS_MD
        )
        banner.pack(fill="x", padx=20, pady=(10, 5))
        
        # Иконка информации
        icon_label = ctk.CTkLabel(
            banner,
            text="ℹ️",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XL),
            width=40
        )
        icon_label.pack(side="left", padx=(15, 10), pady=15)
        
        # Текст подсказки
        info_text = ctk.CTkLabel(
            banner,
            text="Изменение этих параметров повлияет на расчёт отображаемых значений.\\n" +
                 "Rdecimal - десятичные знаки скорости, T_ratio - передаточное отношение, P_units - единицы мощности.",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM),
            text_color=ModernTheme.ON_SURFACE_VARIANT,
            justify="left"
        )
        info_text.pack(side="left", padx=(0, 15), pady=15)
        
    def _create_editable_params_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции с редактируемыми параметрами.
        
        Args:
            parent: Родительский фрейм.
        """
        # Заголовок секции
        section_header = ctk.CTkFrame(parent, fg_color="transparent")
        section_header.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(
            section_header,
            text="🔧 Редактируемые параметры",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_LG, "bold"),
            text_color=ModernTheme.PRIMARY
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            section_header,
            text="Эти параметры влияют на формулы пересчёта значений",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(anchor="w", pady=(2, 0))
        
        # Контейнер для параметров
        params_container = ctk.CTkFrame(parent, fg_color="transparent")
        params_container.pack(fill="x", padx=20, pady=10)
        
        # Rdecimal - SpinBox (0-4)
        self._create_spinbox_param(
            params_container,
            "Rdecimal:",
            self.state.r_decimal,
            "Десятичные знаки скорости (0-4)",
            0, 4
        )
        
        # T_ratio - Entry для ввода числа
        self._create_entry_param(
            params_container,
            "T_ratio:",
            self.state.t_ratio,
            "Передаточное отношение (1-9999)"
        )
        
        # P_units - ComboBox (W/kW)
        self._create_combobox_param(
            params_container,
            "P_units:",
            self.state.p_units,
            ["W", "kW"],
            "Единицы измерения мощности"
        )
        
    def _create_readonly_params_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции с read-only параметрами.
        
        Args:
            parent: Родительский фрейм.
        """
        # Заголовок секции
        section_header = ctk.CTkFrame(parent, fg_color="transparent")
        section_header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            section_header,
            text="📋 Информационные параметры",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD, "bold"),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            section_header,
            text="Текущие настройки датчика (только для просмотра)",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(anchor="w", pady=(2, 0))
        
        # Контейнер для параметров
        params_container = ctk.CTkFrame(parent, fg_color="transparent")
        params_container.pack(fill="x", padx=20, pady=10)
        
        # Read-only параметры
        readonly_params = [
            ("Baud rate:", str(self.state.baudrate.get()), "Скорость передачи данных"),
            ("Modbus ID:", f"{self.state.slave_addr.get():03d}", "Адрес устройства в сети Modbus"),
            ("Transmit:", "Auto", "Режим передачи данных"),
            ("Parity:", "None", "Четность"),
        ]
        
        for name, value, desc in readonly_params:
            self._create_readonly_param_row(params_container, name, value, desc)
        
    def _create_spinbox_param(self, parent: ctk.CTkFrame, label: str, variable, hint: str, min_val: int, max_val: int) -> None:
        """
        Создание строки с spinbox для числового параметра.
        
        Args:
            parent: Родительский фрейм.
            label: Текст метки.
            variable: Переменная tkinter для связи.
            hint: Подсказка.
            min_val: Минимальное значение.
            max_val: Максимальное значение.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Метка параметра
        ctk.CTkLabel(
            frame,
            text=label,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=100
        ).pack(side="left")
        
        # Контейнер для поля ввода и кнопок
        spin_frame = ctk.CTkFrame(frame, fg_color="transparent")
        spin_frame.pack(side="left", padx=(10, 0))
        
        # Поле ввода
        entry = ctk.CTkEntry(
            spin_frame,
            textvariable=variable,
            width=80,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            justify="center"
        )
        entry.pack(side="left")
        
        # Кнопки +/-
        btn_frame = ctk.CTkFrame(spin_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="▲",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=lambda: self._increment_var(variable, min_val, max_val)
        ).pack()
        
        ctk.CTkButton(
            btn_frame,
            text="▼",
            width=24,
            height=18,
            corner_radius=4,
            font=ModernTheme.get_font(8),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            hover_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            command=lambda: self._decrement_var(variable, min_val, max_val)
        ).pack(pady=(2, 0))
        
        # Подсказка
        ctk.CTkLabel(
            frame,
            text=hint,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _create_entry_param(self, parent: ctk.CTkFrame, label: str, variable, hint: str) -> None:
        """
        Создание строки с полем ввода для числового параметра.
        
        Args:
            parent: Родительский фрейм.
            label: Текст метки.
            variable: Переменная tkinter для связи.
            hint: Подсказка.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Метка параметра
        ctk.CTkLabel(
            frame,
            text=label,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=100
        ).pack(side="left")
        
        # Поле ввода
        entry = ctk.CTkEntry(
            frame,
            textvariable=variable,
            width=100,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            justify="center"
        )
        entry.pack(side="left", padx=(10, 0))
        
        # Подсказка
        ctk.CTkLabel(
            frame,
            text=hint,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _create_combobox_param(self, parent: ctk.CTkFrame, label: str, variable, values: list, hint: str) -> None:
        """
        Создание строки с выпадающим списком для выбора значения.
        
        Args:
            parent: Родительский фрейм.
            label: Текст метки.
            variable: Переменная tkinter для связи.
            values: Список допустимых значений.
            hint: Подсказка.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)
        
        # Метка параметра
        ctk.CTkLabel(
            frame,
            text=label,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            text_color=ModernTheme.ON_SURFACE,
            width=100
        ).pack(side="left")
        
        # Выпадающий список
        combo = ctk.CTkComboBox(
            frame,
            values=values,
            variable=variable,
            width=100,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            dropdown_font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER,
            border_color=ModernTheme.OUTLINE,
            button_color=ModernTheme.PRIMARY,
            button_hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1)
        )
        combo.pack(side="left", padx=(10, 0))
        
        # Подсказка
        ctk.CTkLabel(
            frame,
            text=hint,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _create_readonly_param_row(self, parent: ctk.CTkFrame, name: str, value: str, description: str) -> None:
        """
        Создание строки с read-only параметром.
        
        Args:
            parent: Родительский фрейм.
            name: Название параметра.
            value: Значение параметра.
            description: Описание параметра.
        """
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=3)
        
        # Название параметра
        ctk.CTkLabel(
            row_frame,
            text=name,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM),
            text_color=ModernTheme.ON_SURFACE,
            width=100
        ).pack(side="left")
        
        # Значение (read-only поле)
        value_frame = ctk.CTkFrame(
            row_frame,
            fg_color=ModernTheme.SURFACE_CONTAINER_LOW,
            corner_radius=ModernTheme.RADIUS_SM,
            width=80,
            height=28
        )
        value_frame.pack(side="left", padx=(10, 0))
        value_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            value_frame,
            text=value,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_SM, "bold"),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Описание
        ctk.CTkLabel(
            row_frame,
            text=description,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        ).pack(side="left", padx=(15, 0))
        
    def _increment_var(self, variable, min_val: int, max_val: int) -> None:
        """
        Увеличение значения переменной с ограничением.
        
        Args:
            variable: Переменная tkinter.
            min_val: Минимальное значение.
            max_val: Максимальное значение.
        """
        try:
            current = variable.get()
            if current < max_val:
                variable.set(current + 1)
        except (ValueError, tk.TclError):
            pass
            
    def _decrement_var(self, variable, min_val: int, max_val: int) -> None:
        """
        Уменьшение значения переменной с ограничением.
        
        Args:
            variable: Переменная tkinter.
            min_val: Минимальное значение.
            max_val: Максимальное значение.
        """
        try:
            current = variable.get()
            if current > min_val:
                variable.set(current - 1)
        except (ValueError, tk.TclError):
            pass
        
    def _create_button_section(self, parent: ctk.CTkFrame) -> None:
        """
        Создание секции кнопок.
        
        Args:
            parent: Родительский фрейм.
        """
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Кнопка Применить
        ctk.CTkButton(
            btn_frame,
            text="Применить",
            command=self._apply_settings,
            width=140,
            height=40,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD, "bold"),
            fg_color=ModernTheme.PRIMARY,
            hover_color=ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1),
            text_color=ModernTheme.ON_PRIMARY
        ).pack(side="left", padx=(0, 10))
        
        # Кнопка Закрыть
        ctk.CTkButton(
            btn_frame,
            text="Закрыть",
            command=self._on_close,
            width=120,
            height=40,
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_MD),
            fg_color=ModernTheme.SURFACE_CONTAINER_HIGH,
            hover_color=ModernTheme.adjust_brightness(ModernTheme.SURFACE_CONTAINER_HIGH, 1.1),
            text_color=ModernTheme.ON_SURFACE
        ).pack(side="left")
        
    def _apply_settings(self) -> None:
        """
        Применение настроек с валидацией.
        
        Валидирует значения параметров:
        - Rdecimal: 0-4
        - T_ratio: 1-9999
        - P_units: "W" или "kW"
        
        Вызывает on_apply callback если установлен.
        """
        try:
            # Валидация Rdecimal (0-4)
            r_decimal = self.state.r_decimal.get()
            if not (0 <= r_decimal <= 4):
                messagebox.showerror(
                    "Ошибка валидации",
                    f"Rdecimal должен быть в диапазоне 0-4.\\nТекущее значение: {r_decimal}"
                )
                return
            
            # Валидация T_ratio (1-9999)
            t_ratio = self.state.t_ratio.get()
            if not (1 <= t_ratio <= 9999):
                messagebox.showerror(
                    "Ошибка валидации",
                    f"T_ratio должен быть в диапазоне 1-9999.\\nТекущее значение: {t_ratio}"
                )
                return
            
            # Валидация P_units
            p_units = self.state.p_units.get()
            if p_units not in ["W", "kW"]:
                messagebox.showerror(
                    "Ошибка валидации",
                    f"P_units должен быть 'W' или 'kW'.\\nТекущее значение: {p_units}"
                )
                return
            
            # Вызываем callback если есть
            if self.on_apply:
                self.on_apply()
            
            # Показываем подтверждение
            messagebox.showinfo(
                "Настройки применены",
                f"Параметры датчика обновлены:\\n"
                f"• Rdecimal: {r_decimal}\\n"
                f"• T_ratio: {t_ratio}\\n"
                f"• P_units: {p_units}"
            )
            
        except (ValueError, tk.TclError) as e:
            messagebox.showerror(
                "Ошибка",
                f"Ошибка при применении настроек:\\n{e}"
            )
