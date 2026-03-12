#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация приложения DYN-200 Monitor
"""

import tkinter as tk
import threading
from collections import deque
import logging


# ===== НАСТРОЙКИ ЛОГИРОВАНИЯ (ЭТАП 4) =====
# Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = logging.INFO

# Путь к файлу логов
LOG_FILE_PATH = 'debug_log.txt'

# Максимальный размер файла лога (5 MB)
LOG_MAX_BYTES = 5 * 1024 * 1024

# Количество резервных копий
LOG_BACKUP_COUNT = 5

# Формат логов: timestamp [LEVEL] [module:line] message
LOG_FORMAT = '%(asctime)s.%(msecs)03d [%(levelname)s] [%(module)s:%(lineno)d] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class AppConfig:
    """Конфигурация приложения"""
    
    # Окно
    WINDOW_TITLE = "Система тестирования - DYN-200 Monitor"
    WINDOW_GEOMETRY = "1300x950"
    WINDOW_MIN_SIZE = (1200, 800)
    
    # График
    MAX_POINTS = 300
    FIGURE_SIZE = (12, 7)
    DPI = 100
    
    # Цвета графиков
    COLOR_TORQUE = 'blue'
    COLOR_SPEED = 'green'
    COLOR_POWER = 'red'
    
    # Параметры по умолчанию
    DEFAULT_COM_PORT = "COM4"
    DEFAULT_BAUDRATE = 19200
    DEFAULT_SLAVE_ADDR = 1


class AppState:
    """Состояние приложения (shared state) с thread-safety"""
    
    def __init__(self):
        # Параметры подключения
        self.com_port = tk.StringVar(value=AppConfig.DEFAULT_COM_PORT)
        self.baudrate = tk.IntVar(value=AppConfig.DEFAULT_BAUDRATE)
        self.slave_addr = tk.IntVar(value=AppConfig.DEFAULT_SLAVE_ADDR)
        
        # Статус
        self.connection_status = tk.StringVar(value="не подключен")
        self.sensor_mode = tk.StringVar(value="-")
        self.reading_status = tk.StringVar(value="остановлено")
        
        # Флаги состояния
        self.is_connected = False
        self.is_logging = False
        self.is_reading = False
        
        # Thread-safety lock для разделяемых данных
        self._state_lock = threading.Lock()
        
        # ===== НАСТРОЙКИ ОТОБРАЖЕНИЯ =====
        # Тема (True = темная, False = светлая)
        self.dark_theme = tk.BooleanVar(value=True)
        
        # Десятичные знаки для отображения (0-4)
        self.torque_decimal = tk.IntVar(value=2)      # Знаки после запятой для момента
        self.speed_decimal = tk.IntVar(value=0)       # Знаки после запятой для оборотов
        
        # Коэффициенты пересчета
        self.torque_coefficient = tk.DoubleVar(value=1.0)  # Множитель для момента
        self.speed_coefficient = tk.DoubleVar(value=1.0)   # Множитель для оборотов (1:1 для DYN-200)
        self.power_correction = tk.DoubleVar(value=1.0)    # Коэффициент коррекции мощности (0.1 - 2.0)
        
        # ===== ПАРАМЕТРЫ ДАТЧИКА DYN-200 (редактируемые) =====
        # Rdecimal: количество десятичных знаков для скорости (влияет на деление/умножение speed)
        self.r_decimal = tk.IntVar(value=1)  # 0-4, по умолчанию 1 (деление на 10^1 = 10)
        # T_ratio: передаточное отношение для крутящего момента (коэффициент для torque)
        self.t_ratio = tk.IntVar(value=1087)  # 1-9999, по умолчанию 1087
        # P_units: единицы измерения мощности W/kW
        self.p_units = tk.StringVar(value="W")  # "W" или "kW", по умолчанию "W"
        
        # Настройки осей
        self.axis_settings = {
            'torque': {
                'min': tk.DoubleVar(value=-10),
                'max': tk.DoubleVar(value=50),
                'autoscale': tk.BooleanVar(value=False)
            },
            'speed': {
                'min': tk.DoubleVar(value=0),
                'max': tk.DoubleVar(value=500),
                'autoscale': tk.BooleanVar(value=False)
            },
            'power': {
                'min': tk.DoubleVar(value=0),
                'max': tk.DoubleVar(value=1.0),
                'autoscale': tk.BooleanVar(value=False)
            }
        }
        
        # Данные для графиков - используем deque для ограничения размера
        self.timestamps = deque(maxlen=AppConfig.MAX_POINTS)
        self.torque_data = deque(maxlen=AppConfig.MAX_POINTS)
        self.speed_data = deque(maxlen=AppConfig.MAX_POINTS)
        self.power_data = deque(maxlen=AppConfig.MAX_POINTS)
    
    # Thread-safe методы для работы с данными
    def append_data(self, timestamp, torque, speed, power):
        """Thread-safe добавление данных"""
        with self._state_lock:
            self.timestamps.append(timestamp)
            self.torque_data.append(torque)
            self.speed_data.append(speed)
            self.power_data.append(power)
    
    def clear_data(self):
        """Thread-safe очистка данных"""
        with self._state_lock:
            self.timestamps.clear()
            self.torque_data.clear()
            self.speed_data.clear()
            self.power_data.clear()
    
    def get_data_copy(self):
        """Thread-safe получение копии данных"""
        with self._state_lock:
            return (
                list(self.timestamps),
                list(self.torque_data),
                list(self.speed_data),
                list(self.power_data)
            )
