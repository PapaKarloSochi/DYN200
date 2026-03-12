#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для config.py - AppConfig и AppState
"""

import pytest
import sys
import os
import threading
import time
import tkinter as tk
from unittest.mock import Mock, patch

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AppConfig, AppState, LOG_LEVEL, LOG_FILE_PATH, LOG_MAX_BYTES


class TestAppConfig:
    """Тесты для класса AppConfig"""
    
    def test_window_config(self):
        """Тест конфигурации окна"""
        assert AppConfig.WINDOW_TITLE == "Система тестирования - DYN-200 Monitor"
        assert AppConfig.WINDOW_GEOMETRY == "1300x950"
        assert AppConfig.WINDOW_MIN_SIZE == (1200, 800)
    
    def test_plot_config(self):
        """Тест конфигурации графика"""
        assert AppConfig.MAX_POINTS == 300
        assert AppConfig.FIGURE_SIZE == (12, 7)
        assert AppConfig.DPI == 100
    
    def test_colors_config(self):
        """Тест цветов графиков"""
        assert AppConfig.COLOR_TORQUE == 'blue'
        assert AppConfig.COLOR_SPEED == 'green'
        assert AppConfig.COLOR_POWER == 'red'
    
    def test_defaults_config(self):
        """Тест значений по умолчанию"""
        assert AppConfig.DEFAULT_COM_PORT == "COM4"
        assert AppConfig.DEFAULT_BAUDRATE == 19200
        assert AppConfig.DEFAULT_SLAVE_ADDR == 1
    
    def test_config_immutable(self):
        """Тест что конфигурация является константой"""
        # Проверяем что значения существуют и не пустые
        assert len(AppConfig.WINDOW_TITLE) > 0
        assert AppConfig.MAX_POINTS > 0


class TestLoggingConfig:
    """Тесты для конфигурации логирования"""
    
    def test_log_level(self):
        """Тест уровня логирования"""
        import logging
        assert LOG_LEVEL == logging.INFO
    
    def test_log_file_path(self):
        """Тест пути к файлу логов"""
        assert LOG_FILE_PATH == 'debug_log.txt'
    
    def test_log_max_bytes(self):
        """Тест максимального размера файла"""
        assert LOG_MAX_BYTES == 5 * 1024 * 1024  # 5 MB
    
    def test_log_format(self):
        """Тест формата логов"""
        from config import LOG_FORMAT, LOG_DATE_FORMAT
        assert '%(asctime)s' in LOG_FORMAT
        assert '%(levelname)s' in LOG_FORMAT
        assert LOG_DATE_FORMAT == '%Y-%m-%d %H:%M:%S'


@pytest.fixture
def app_state():
    """Фикстура для создания AppState с инициализированным Tkinter"""
    # Создаем root окно для Tkinter
    root = tk.Tk()
    root.withdraw()  # Скрываем окно
    
    state = AppState()
    yield state
    
    # Очистка после теста
    root.destroy()


class TestAppStateInitialization:
    """Тесты инициализации AppState"""
    
    def test_initial_connection_params(self, app_state):
        """Тест начальных параметров подключения"""
        assert app_state.com_port.get() == AppConfig.DEFAULT_COM_PORT
        assert app_state.baudrate.get() == AppConfig.DEFAULT_BAUDRATE
        assert app_state.slave_addr.get() == AppConfig.DEFAULT_SLAVE_ADDR
    
    def test_initial_status(self, app_state):
        """Тест начального статуса"""
        assert app_state.connection_status.get() == "не подключен"
        assert app_state.sensor_mode.get() == "-"
        assert app_state.reading_status.get() == "остановлено"
    
    def test_initial_flags(self, app_state):
        """Тест начальных флагов"""
        assert app_state.is_connected is False
        assert app_state.is_logging is False
        assert app_state.is_reading is False
    
    def test_initial_display_settings(self, app_state):
        """Тест начальных настроек отображения"""
        assert app_state.dark_theme.get() is True
        assert app_state.torque_decimal.get() == 2
        assert app_state.speed_decimal.get() == 0
    
    def test_initial_coefficients(self, app_state):
        """Тест начальных коэффициентов"""
        assert app_state.torque_coefficient.get() == 1.0
        assert app_state.speed_coefficient.get() == 1.0
        assert app_state.power_correction.get() == 1.0
    
    def test_initial_axis_settings(self, app_state):
        """Тест начальных настроек осей"""
        assert 'torque' in app_state.axis_settings
        assert 'speed' in app_state.axis_settings
        assert 'power' in app_state.axis_settings
        
        # Проверка torque axis
        assert app_state.axis_settings['torque']['min'].get() == -10
        assert app_state.axis_settings['torque']['max'].get() == 50
        assert app_state.axis_settings['torque']['autoscale'].get() is False


class TestAppStateDataOperations:
    """Тесты операций с данными AppState"""
    
    def test_append_data(self, app_state):
        """Тест добавления данных"""
        app_state.append_data("12:00:01", 10.5, 100, 150.5)
        
        assert len(app_state.timestamps) == 1
        assert len(app_state.torque_data) == 1
        assert app_state.torque_data[0] == 10.5
    
    def test_append_multiple_data(self, app_state):
        """Тест добавления нескольких данных"""
        for i in range(5):
            app_state.append_data(f"12:00:0{i}", float(i), i * 100, i * 10)
        
        assert len(app_state.timestamps) == 5
        assert list(app_state.torque_data) == [0.0, 1.0, 2.0, 3.0, 4.0]
    
    def test_clear_data(self, app_state):
        """Тест очистки данных"""
        # Добавляем данные
        app_state.append_data("12:00:01", 10.5, 100, 150.5)
        app_state.append_data("12:00:02", 11.0, 110, 160.0)
        
        # Очищаем
        app_state.clear_data()
        
        assert len(app_state.timestamps) == 0
        assert len(app_state.torque_data) == 0
        assert len(app_state.speed_data) == 0
        assert len(app_state.power_data) == 0
    
    def test_get_data_copy(self, app_state):
        """Тест получения копии данных"""
        app_state.append_data("12:00:01", 10.5, 100, 150.5)
        
        timestamps, torque, speed, power = app_state.get_data_copy()
        
        assert isinstance(timestamps, list)
        assert timestamps == ["12:00:01"]
        assert torque == [10.5]
        assert speed == [100]
        assert power == [150.5]
    
    def test_get_data_copy_isolation(self, app_state):
        """Тест что копия изолирована от оригинала"""
        app_state.append_data("12:00:01", 10.5, 100, 150.5)
        
        timestamps, torque, speed, power = app_state.get_data_copy()
        
        # Модифицируем копию
        timestamps.append("12:00:02")
        torque.append(20.0)
        
        # Оригинал не должен измениться
        assert len(app_state.timestamps) == 1
        assert len(app_state.torque_data) == 1


class TestAppStateThreadSafety:
    """Тесты thread-safety AppState"""
    
    def test_thread_safe_append(self, app_state):
        """Тест thread-safe добавления данных"""
        errors = []
        
        def append_worker(worker_id):
            try:
                for i in range(50):
                    app_state.append_data(f"worker{worker_id}_{i}", float(i), i, i)
                    time.sleep(0.001)  # Небольшая задержка
            except Exception as e:
                errors.append(e)
        
        # Запускаем несколько потоков (меньше, чтобы не превысить MAX_POINTS)
        threads = []
        for i in range(3):
            t = threading.Thread(target=append_worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Ждём завершения
        for t in threads:
            t.join()
        
        # Проверяем что не было ошибок
        assert len(errors) == 0, f"Thread errors: {errors}"
        
        # Проверяем что все данные добавлены (3 * 50 = 150)
        assert len(app_state.timestamps) == 150
    
    def test_thread_safe_clear(self, app_state):
        """Тест thread-safe очистки данных"""
        # Добавляем данные
        for i in range(100):
            app_state.append_data(f"12:00:{i:02d}", float(i), i, i)
        
        errors = []
        
        def clear_worker():
            try:
                app_state.clear_data()
            except Exception as e:
                errors.append(e)
        
        def append_worker():
            try:
                for i in range(50):
                    app_state.append_data(f"new_{i}", float(i), i, i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Запускаем потоки
        threads = [
            threading.Thread(target=clear_worker),
            threading.Thread(target=append_worker),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Проверяем что не было ошибок
        assert len(errors) == 0
    
    def test_thread_safe_get_copy(self, app_state):
        """Тест thread-safe получения копии"""
        # Добавляем данные
        for i in range(100):
            app_state.append_data(f"12:00:{i:02d}", float(i), i, i)
        
        results = []
        errors = []
        
        def get_worker():
            try:
                for _ in range(50):
                    data = app_state.get_data_copy()
                    results.append(len(data[0]))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def append_worker():
            try:
                for i in range(50):
                    app_state.append_data(f"new_{i}", float(i), i, i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=get_worker),
            threading.Thread(target=append_worker),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        # Проверяем что все операции завершились без ошибок
        assert len(results) == 50


class TestAppStateMaxPoints:
    """Тесты ограничения размера данных"""
    
    def test_max_points_limit(self, app_state):
        """Тест ограничения максимального количества точек"""
        # Добавляем больше чем MAX_POINTS
        for i in range(AppConfig.MAX_POINTS + 50):
            app_state.append_data(f"12:00:{i%60:02d}", float(i), i, i)
        
        # Проверяем что размер не превышает MAX_POINTS
        assert len(app_state.timestamps) == AppConfig.MAX_POINTS
        assert len(app_state.torque_data) == AppConfig.MAX_POINTS
    
    def test_fifo_behavior(self, app_state):
        """Тест FIFO поведения при переполнении"""
        # Добавляем данные
        for i in range(AppConfig.MAX_POINTS + 10):
            app_state.append_data(f"time_{i}", float(i), i, i)
        
        # Первые 10 значений должны быть удалены
        timestamps = list(app_state.timestamps)
        assert "time_0" not in timestamps
        assert "time_1" not in timestamps
        # Последние значения должны быть на месте
        assert "time_{}".format(AppConfig.MAX_POINTS + 9) in timestamps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
