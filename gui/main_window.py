#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения DYN-200 Monitor
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
import queue
import time
import csv
from datetime import datetime
from PIL import Image, ImageTk

try:
    from pymodbus.client import ModbusSerialClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False

import serial

from config import AppConfig, AppState
from utils.logger import Logger

from gui.plot_manager import PlotManager
from gui.dialogs import ConnectionDialog, AxisSettingsDialog


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self, root):
        self.root = root
        self.config = AppConfig()
        self.state = AppState()
        self.logger = Logger()
        self.plot_manager = PlotManager(self.config, self.state)
        

        
        # Потоки и соединения
        self.read_thread = None
        self.stop_thread = threading.Event()
        self.serial_conn = None
        self.modbus_client = None
        
        # Файл логирования
        self.log_file = None
        self.csv_writer = None
        
        # Диалоги
        self.conn_dialog = None
        self.axis_dialog = None
        
        # Максимальные значения (Peak Hold)
        self.max_torque = 0.0
        self.max_speed = 0.0
        self.max_power = 0.0
        self.max_values_reset_time = time.time()
        
        # Коэффициент коррекции мощности
        self.power_correction = tk.DoubleVar(value=1.0)
        
        self._setup_window()
        self._create_ui()
        self._start_loops()
    
    def _setup_window(self):
        """Настройка окна"""
        self.root.title(self.config.WINDOW_TITLE)
        self.root.geometry(self.config.WINDOW_GEOMETRY)
        self.root.minsize(*self.config.WINDOW_MIN_SIZE)
    
    def _create_ui(self):
        """Создание интерфейса"""
        self._create_menu()
        self._create_header()
        self._create_control_panel()
        self._create_status_panel()
        self._create_values_panel()
        self._create_plot_panel()
        self._create_log_panel()
    
    def _create_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Connection Settings...", command=self._open_connection_dialog)
    
    def _create_header(self):
        """Верхняя панель с логотипом"""
        header_frame = ttk.Frame(self.root, padding=5)
        header_frame.pack(fill='x', padx=10, pady=5)
        
        # Логотип
        if os.path.exists('logo.png'):
            try:
                logo_img = Image.open('logo.png')
                max_height = 80
                ratio = max_height / logo_img.height
                new_width = int(logo_img.width * ratio)
                logo_img = logo_img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_img)
                ttk.Label(header_frame, image=self.logo_tk).pack(side='left', padx=(0, 20))
            except Exception as e:
                print(f"Ошибка загрузки логотипа: {e}")
        
        # Название
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side='left', fill='y')
        ttk.Label(title_frame, text="Система тестирования", 
                  font=('Arial', 14, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Папа Карло", 
                  font=('Arial', 18, 'bold'), foreground='#2E86AB').pack(anchor='w')
    
    def _create_control_panel(self):
        """Панель управления"""
        control_frame = ttk.LabelFrame(self.root, text="Управление", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Кнопка считывания с индикатором
        reading_frame = ttk.Frame(control_frame)
        reading_frame.pack(side='left', padx=5)
        
        self.reading_indicator = tk.Canvas(reading_frame, width=20, height=20, highlightthickness=0)
        self.reading_indicator.pack(side='left', padx=(0, 5))
        self.led_circle = self.reading_indicator.create_oval(2, 2, 18, 18, fill="red", outline="darkred", width=2)
        
        self.reading_btn = ttk.Button(reading_frame, text="▶ Запустить считывание", 
                                       command=self._toggle_reading, state='disabled', width=25)
        self.reading_btn.pack(side='left')
        
        # Логирование
        self.start_log_btn = ttk.Button(control_frame, text="Start Logging", 
                                         command=self._start_logging, state='disabled', width=15)
        self.start_log_btn.pack(side='left', padx=(30, 5))
        
        self.stop_log_btn = ttk.Button(control_frame, text="Stop Logging", 
                                        command=self._stop_logging, state='disabled', width=15)
        self.stop_log_btn.pack(side='left', padx=5)
        
        # Zero и настройки
        self.zero_btn = ttk.Button(control_frame, text="Zero Sensor", 
                                    command=self._zero_sensor, state='disabled', width=12)
        self.zero_btn.pack(side='left', padx=(30, 5))
        
        ttk.Button(control_frame, text="Настройки осей", 
                   command=self._open_axis_dialog, width=15).pack(side='left', padx=(30, 5))
        
        # Кнопка настроек коррекции мощности
        ttk.Button(control_frame, text="Коррекция мощности", 
                   command=self._open_power_correction_dialog, width=18).pack(side='left', padx=(10, 5))
    
    def _create_status_panel(self):
        """Панель статуса"""
        status_frame = ttk.LabelFrame(self.root, text="Статус системы", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(status_frame, text="Состояние:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w')
        self.status_label = ttk.Label(status_frame, textvariable=self.state.connection_status, 
                                       foreground="red", font=('Arial', 10))
        self.status_label.grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Label(status_frame, text="Режим датчика:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=(30,0))
        ttk.Label(status_frame, textvariable=self.state.sensor_mode, 
                  foreground="blue", font=('Arial', 10)).grid(row=0, column=3, sticky='w', padx=5)
        
        ttk.Label(status_frame, text="Получение данных:", font=('Arial', 10, 'bold')).grid(row=0, column=4, sticky='w', padx=(30,0))
        self.reading_status_label = ttk.Label(status_frame, textvariable=self.state.reading_status, 
                                               foreground="red", font=('Arial', 10))
        self.reading_status_label.grid(row=0, column=5, sticky='w', padx=5)
    
    def _create_values_panel(self):
        """Панель текущих значений с Peak Hold и индикаторами"""
        values_frame = ttk.LabelFrame(self.root, text="Текущие значения", padding=10)
        values_frame.pack(fill='x', padx=10, pady=5)
        
        # Левая колонка - Torque
        torque_frame = ttk.Frame(values_frame)
        torque_frame.grid(row=0, column=0, padx=20, sticky='n')
        
        torque_header = ttk.Frame(torque_frame)
        torque_header.pack(fill='x')
        self.torque_indicator = tk.Canvas(torque_header, width=16, height=16, highlightthickness=0)
        self.torque_indicator.pack(side='left', padx=(0, 5))
        self.torque_led = self.torque_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="darkgray", width=1)
        ttk.Label(torque_header, text="Torque(N.m)", font=('Arial', 10)).pack(side='left')
        
        self.torque_value_label = ttk.Label(torque_frame, text="0", font=('Arial', 24, 'bold'),
                                           foreground=self.config.COLOR_TORQUE, background='#f0f0f0', padding=(10, 5))
        self.torque_value_label.pack(fill='x', pady=2)
        
        self.max_torque_label = ttk.Label(torque_frame, text="Max: 0.00", font=('Arial', 10), foreground='gray')
        self.max_torque_label.pack()
        
        # Средняя колонка - Speed
        speed_frame = ttk.Frame(values_frame)
        speed_frame.grid(row=0, column=1, padx=20, sticky='n')
        
        speed_header = ttk.Frame(speed_frame)
        speed_header.pack(fill='x')
        self.speed_indicator = tk.Canvas(speed_header, width=16, height=16, highlightthickness=0)
        self.speed_indicator.pack(side='left', padx=(0, 5))
        self.speed_led = self.speed_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="darkgray", width=1)
        ttk.Label(speed_header, text="Speed(RPM)", font=('Arial', 10)).pack(side='left')
        
        self.speed_value_label = ttk.Label(speed_frame, text="0", font=('Arial', 24, 'bold'),
                                          foreground=self.config.COLOR_SPEED, background='#f0f0f0', padding=(10, 5))
        self.speed_value_label.pack(fill='x', pady=2)
        
        self.max_speed_label = ttk.Label(speed_frame, text="Max: 0", font=('Arial', 10), foreground='gray')
        self.max_speed_label.pack()
        
        # Правая колонка - Power
        power_frame = ttk.Frame(values_frame)
        power_frame.grid(row=0, column=2, padx=20, sticky='n')
        
        power_header = ttk.Frame(power_frame)
        power_header.pack(fill='x')
        self.power_indicator = tk.Canvas(power_header, width=16, height=16, highlightthickness=0)
        self.power_indicator.pack(side='left', padx=(0, 5))
        self.power_led = self.power_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="darkgray", width=1)
        ttk.Label(power_header, text="Power(kW)", font=('Arial', 10)).pack(side='left')
        
        self.power_value_label = ttk.Label(power_frame, text="0", font=('Arial', 24, 'bold'),
                                          foreground=self.config.COLOR_POWER, background='#f0f0f0', padding=(10, 5))
        self.power_value_label.pack(fill='x', pady=2)
        
        self.max_power_label = ttk.Label(power_frame, text="Max: 0.0000", font=('Arial', 10), foreground='gray')
        self.max_power_label.pack()
        
        # Кнопка сброса Peak Hold
        ttk.Button(values_frame, text="Сбросить Max", command=self._reset_max_values, width=12).grid(
            row=0, column=3, padx=20, sticky='n')
        
        # Сохраняем старые метки для совместимости
        self.torque_label = self.torque_value_label
        self.speed_label = self.speed_value_label
        self.power_label = self.power_value_label
    
    def _create_plot_panel(self):
        """Панель графика"""
        self.plot_frame = ttk.LabelFrame(self.root, text="График в реальном времени", padding=5)
        self.plot_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.plot_manager.create_plots(self.plot_frame)
    
    def _create_log_panel(self):
        """Панель логов"""
        log_frame = ttk.LabelFrame(self.root, text="Лог", padding=5)
        log_frame.pack(fill='x', padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=6, wrap='word')
        self.log_text.pack(fill='both', side='left', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Устанавливаем виджет для логгера
        self.logger.set_log_widget(self.log_text)
    
    def _start_loops(self):
        """Запуск циклов обновления"""
        self.logger.process_queue()
        self._update_plot_loop()
        
        if not PYMODBUS_AVAILABLE:
            self.logger.log("ВНИМАНИЕ: pymodbus не установлен!")
    
    def _open_connection_dialog(self):
        """Открыть диалог подключения"""
        if self.conn_dialog and self.conn_dialog.window.winfo_exists():
            self.conn_dialog.window.lift()
            return
        
        self.conn_dialog = ConnectionDialog(
            self.root, self.state,
            self._connect, self._disconnect
        )
    
    def _open_axis_dialog(self):
        """Открыть диалог настроек осей"""
        if self.axis_dialog and self.axis_dialog.window.winfo_exists():
            self.axis_dialog.window.lift()
            return
        
        self.axis_dialog = AxisSettingsDialog(
            self.root, self.state.axis_settings,
            self._apply_axis_settings
        )
    
    def _connect(self):
        """Подключение к датчику"""
        port = self.state.com_port.get()
        baud = self.state.baudrate.get()
        
        self.logger.log(f"Попытка подключения к {port} @ {baud} baud...")
        self.state.connection_status.set("подключение...")
        
        self.stop_thread.clear()
        self.read_thread = threading.Thread(target=self._detect_and_connect, args=(port, baud))
        self.read_thread.daemon = True
        self.read_thread.start()
    
    def _detect_and_connect(self, port, baud):
        """Определение режима и подключение"""
        try:
            # Пробуем только Modbus RTU
            self.logger.log("=== Проверка Modbus RTU mode ===")
            if PYMODBUS_AVAILABLE and self._try_modbus(port, baud):
                self.state.sensor_mode.set("получение данных (Modbus)")
                self.logger.log("✓ Датчик работает в Modbus RTU mode 1")
                self._start_modbus_reader(port, baud)
                return
            
            # Не удалось подключиться
            self.state.connection_status.set("не подключен")
            self.state.sensor_mode.set("-")
            self.logger.log("✗ Не удалось определить режим датчика")
            
        except Exception as e:
            self.state.connection_status.set("не подключен")
            self.logger.log(f"Критическая ошибка: {e}")
    
    def _try_modbus(self, port, baud):
        """Попытка подключения по Modbus"""
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
                    self.logger.log(f"[OK] Получено {len(response.registers)} регистров от slave {slave}")
                    return True
                else:
                    self.logger.log(f"[ERROR] Недостаточно регистров: {len(response.registers)}")
                    return False
            self.logger.log(f"[ERROR] Нет ответа или ошибка Modbus")
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
    

    def _start_modbus_reader(self, port, baud):
        """Запуск чтения Modbus"""
        try:
            self.modbus_client = ModbusSerialClient(
                port=port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=1
            )
            
            if self.modbus_client.connect():
                self.state.is_connected = True
                self.state.connection_status.set("подключен")
                self._update_ui_connected(True)
                self.logger.log("Подключено по Modbus RTU")
                
                self.read_thread = threading.Thread(target=self._modbus_read_loop)
                self.read_thread.daemon = True
                self.read_thread.start()
            else:
                self.state.connection_status.set("не подключен")
                
        except Exception as e:
            self.state.connection_status.set("не подключен")
            self.logger.log(f"Ошибка: {e}")
    
    def _modbus_read_loop(self):
        """Цикл чтения Modbus"""
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
                    torque = self._to_signed32(torque_raw)
                    speed_raw = (registers[2] << 16) | registers[3]
                    power_raw = (registers[4] << 16) | registers[5]
                    # Пересчет: torque / 1000 = Н·м, speed / 10 = RPM, power_raw = Вт (1:1)
                    from core.unit_conversion import raw_to_torque, raw_to_speed, raw_to_power

torque_nm = raw_to_torque(torque)
speed_rpm = raw_to_speed(speed_raw)
power_w = raw_to_power(power_raw, self.power_correction.get())
                    
                    self._add_data(torque_nm, speed_rpm, power_w, 'Modbus')
                else:
                    error_count += 1
                    if error_count > 10:
                        time.sleep(3)
                        error_count = 0
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.log(f"Ошибка чтения: {e}")
                time.sleep(1)
    
def _add_data(self, torque, speed, power, mode):
        """Добавление данных в очередь"""
        self.root.after(0, lambda: self._update_labels(torque, speed, power))
        
        self.state.timestamps.append(datetime.now())
        self.state.torque_data.append(torque)
        self.state.speed_data.append(speed)
        self.state.power_data.append(power)
        
        # Ограничиваем размер
        if len(self.state.timestamps) > self.config.MAX_POINTS:
            self.state.timestamps.pop(0)
            self.state.torque_data.pop(0)
            self.state.speed_data.pop(0)
            self.state.power_data.pop(0)
        
        # Логирование
        if self.state.is_logging and self.csv_writer:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.csv_writer.writerow([timestamp, torque, speed, power, mode])
            try:
                self.log_file.flush()
            except:
                pass
    
    def _update_labels(self, torque, speed, power_kw):
        """Обновление меток значений с Peak Hold"""
        # Обновляем текущие значения
        self.torque_value_label.config(text=f"{torque:.2f}")
        self.speed_value_label.config(text=f"{speed:.0f}")
        self.power_value_label.config(text=f"{power_kw:.4f}")
        
        # Обновляем максимальные значения
        if abs(torque) > abs(self.max_torque):
            self.max_torque = torque
            self.max_torque_label.config(text=f"Max: {self.max_torque:.2f}")
        
        if speed > self.max_speed:
            self.max_speed = speed
            self.max_speed_label.config(text=f"Max: {self.max_speed:.0f}")
        
        if power_kw > self.max_power:
            self.max_power = power_kw
            self.max_power_label.config(text=f"Max: {self.max_power:.4f}")
        
        # Обновляем индикаторы (зеленые при активном чтении)
        if self.state.is_reading:
            self.torque_indicator.itemconfig(self.torque_led, fill=self.config.COLOR_TORQUE, outline="darkgreen")
            self.speed_indicator.itemconfig(self.speed_led, fill=self.config.COLOR_SPEED, outline="darkgreen")
            self.power_indicator.itemconfig(self.power_led, fill=self.config.COLOR_POWER, outline="darkgreen")
        else:
            self.torque_indicator.itemconfig(self.torque_led, fill="gray", outline="darkgray")
            self.speed_indicator.itemconfig(self.speed_led, fill="gray", outline="darkgray")
            self.power_indicator.itemconfig(self.power_led, fill="gray", outline="darkgray")
    
    def _reset_max_values(self):
        """Сброс максимальных значений (Peak Hold)"""
        self.max_torque = 0.0
        self.max_speed = 0.0
        self.max_power = 0.0
        self.max_torque_label.config(text="Max: 0.00")
        self.max_speed_label.config(text="Max: 0")
        self.max_power_label.config(text="Max: 0.0000")
        self.logger.log("Максимальные значения сброшены")
    
    def _to_signed32(self, value):
        """Преобразование в знаковое 32-бит"""
        if value >= 0x80000000:
            return value - 0x100000000
        return value
    
    def _update_ui_connected(self, connected):
        """Обновление UI при подключении"""
        if connected:
            self.reading_btn.config(state='normal')
            self.zero_btn.config(state='normal')
            self._start_reading()
            if self.conn_dialog:
                self.conn_dialog.update_buttons(True)
        else:
            self.reading_btn.config(state='disabled')
            self.start_log_btn.config(state='disabled')
            self.stop_log_btn.config(state='disabled')
            self.zero_btn.config(state='disabled')
            self._stop_reading()
            if self.conn_dialog:
                self.conn_dialog.update_buttons(False)
    
    def _toggle_reading(self):
        """Переключение считывания"""
        if self.state.is_reading:
            self._stop_reading()
        else:
            self._start_reading()
    
    def _start_reading(self):
        """Начать считывание"""
        self.state.is_reading = True
        self.stop_thread.clear()
        
        self.reading_btn.config(text="⏹ Остановить считывание")
        self.reading_indicator.itemconfig(self.led_circle, fill="green", outline="darkgreen")
        self.state.reading_status.set("производится")
        self.reading_status_label.config(foreground="green")
        self.start_log_btn.config(state='normal')
        
        self.logger.log("Считывание данных начато")
    
    def _stop_reading(self):
        """Остановить считывание"""
        self.state.is_reading = False
        self.stop_thread.set()
        
        self.reading_btn.config(text="▶ Запустить считывание")
        self.reading_indicator.itemconfig(self.led_circle, fill="red", outline="darkred")
        self.state.reading_status.set("остановлено")
        self.reading_status_label.config(foreground="red")
        self.start_log_btn.config(state='disabled')
        
        self.logger.log("Считывание данных остановлено")
    
    def _disconnect(self):
        """Отключение"""
        self._stop_reading()
        self.state.is_connected = False
        
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except:
                pass
            self.modbus_client = None
        
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        
        self._stop_logging()
        self.state.connection_status.set("не подключен")
        self.state.sensor_mode.set("-")
        self._update_ui_connected(False)
        self.logger.log("Отключено от датчика")
    
    def _start_logging(self):
        """Начать логирование"""
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filename:
            try:
                self.log_file = open(filename, 'w', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.log_file)
                self.csv_writer.writerow(['Timestamp', 'Torque_Nm', 'Speed_RPM', 'Power_kW', 'Mode'])
                self.state.is_logging = True
                self.start_log_btn.config(state='disabled')
                self.stop_log_btn.config(state='normal')
                self.logger.log(f"Логирование начато: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")
    
    def _stop_logging(self):
        """Остановить логирование"""
        self.state.is_logging = False
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
            self.csv_writer = None
        self.start_log_btn.config(state='normal')
        self.stop_log_btn.config(state='disabled')
        self.logger.log("Логирование остановлено")
    
    def _zero_sensor(self):
        """Обнуление датчика"""
        if not self.state.is_connected:
            return
        
        try:
            zero_cmd = bytes([0x01, 0x05, 0x00, 0x00, 0xFF, 0x00, 0x8D, 0xFA])
            if self.serial_conn:
                self.serial_conn.write(zero_cmd)
                self.logger.log("[ZERO] Команда обнуления отправлена")
        except Exception as e:
            self.logger.log(f"[ZERO] Ошибка: {e}")
    
    def _apply_axis_settings(self):
        """Применить настройки осей"""
        self.logger.log("Применены настройки осей графика")
        self._update_plot_loop()
    
    def _update_plot_loop(self):
        """Цикл обновления графика"""
        if self.state.timestamps:
            # Преобразуем datetime в секунды от начала измерения
            start_time = self.state.timestamps[0]
            time_seconds = [(t - start_time).total_seconds() for t in self.state.timestamps]
            
            self.plot_manager.update_plots(
                time_seconds,
                self.state.torque_data,
                self.state.speed_data,
                self.state.power_data
            )
        self.root.after(50, self._update_plot_loop)
    
    def _update_parser_power_correction(self):
        """Обновить коэффициент коррекции мощности в парсере"""
        if hasattr(self.parser, 'set_power_correction'):
            self.parser.set_power_correction(self.power_correction.get())
    
    def _open_power_correction_dialog(self):
        """Открыть диалог настроек коррекции мощности"""
        if hasattr(self, 'power_corr_dialog') and self.power_corr_dialog and self.power_corr_dialog.winfo_exists():
            self.power_corr_dialog.lift()
            return
        
        self.power_corr_dialog = tk.Toplevel(self.root)
        self.power_corr_dialog.title("Коррекция мощности")
        self.power_corr_dialog.geometry("400x250")
        self.power_corr_dialog.resizable(False, False)
        self.power_corr_dialog.transient(self.root)
        
        frame = ttk.Frame(self.power_corr_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(frame, text="Настройка коррекции мощности", 
                  font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Описание
        desc_text = """Коэффициент коррекции позволяет скорректировать 
отображаемое значение мощности.

Пример: датчик=164 Вт, программа=227 Вт
Коэффициент = 164 / 227 = 0.722"""
        
        ttk.Label(frame, text=desc_text, wraplength=350, justify=tk.LEFT).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Поле ввода коэффициента
        ttk.Label(frame, text="Коэффициент:", font=('Arial', 10, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=10)
        
        coeff_spin = ttk.Spinbox(frame, from_=0.1, to=2.0, increment=0.001, 
                                  textvariable=self.power_correction, width=10, format="%.3f")
        coeff_spin.grid(row=2, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Слайдер для удобства
        ttk.Label(frame, text="Быстрая настройка:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        
        coeff_scale = tk.Scale(frame, from_=0.1, to=2.0, resolution=0.001, 
                               orient=tk.HORIZONTAL, variable=self.power_correction,
                               command=self._on_power_correction_changed,
                               length=300, showvalue=False)
        coeff_scale.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        # Метки масштаба
        scale_frame = ttk.Frame(frame)
        scale_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW)
        ttk.Label(scale_frame, text="0.1", foreground='gray').pack(side=tk.LEFT)
        ttk.Label(scale_frame, text="1.0", foreground='gray').pack(side=tk.LEFT, expand=True)
        ttk.Label(scale_frame, text="2.0", foreground='gray').pack(side=tk.RIGHT)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(btn_frame, text="Сбросить в 1.0", 
                   command=self._reset_power_correction, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", 
                   command=self._close_power_correction_dialog, width=15).pack(side=tk.LEFT, padx=5)
    
    def _on_power_correction_changed(self, value):
        """Обработчик изменения коэффициента через слайдер"""
        try:
            coeff = float(value)
            # Ограничиваем диапазон
            coeff = max(0.1, min(2.0, coeff))
            self.power_correction.set(coeff)
            self._update_parser_power_correction()
        except ValueError:
            pass
    
    def _reset_power_correction(self):
        """Сбросить коэффициент к значению по умолчанию"""
        self.power_correction.set(1.0)
        self._update_parser_power_correction()
        self.logger.log("[POWER] Коэффициент коррекции сброшен к 1.0")
    
    def _close_power_correction_dialog(self):
        """Закрыть диалог настроек коррекции мощности"""
        if hasattr(self, 'power_corr_dialog') and self.power_corr_dialog:
            self.power_corr_dialog.destroy()
            self.power_corr_dialog = None
