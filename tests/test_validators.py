#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для валидаторов из gui/modern_dialogs.py
"""

import pytest
import sys
import os

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.modern_dialogs import validate_com_port, validate_baudrate, validate_log_path


class TestValidateComPort:
    """Тесты для функции validate_com_port"""
    
    def test_valid_windows_port_low(self):
        """Тест валидного Windows COM-порта (COM1)"""
        is_valid, error_msg = validate_com_port("COM1")
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_windows_port_mid(self):
        """Тест валидного Windows COM-порта (COM10)"""
        is_valid, error_msg = validate_com_port("COM10")
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_windows_port_high(self):
        """Тест валидного Windows COM-порта (COM256)"""
        is_valid, error_msg = validate_com_port("COM256")
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_windows_port_case_insensitive(self):
        """Тест регистронезависимости (com1, Com1)"""
        for port in ["com1", "Com1", "COM1", "cOm1"]:
            is_valid, _ = validate_com_port(port)
            assert is_valid is True, f"Failed for {port}"
    
    def test_valid_linux_port_ttyusb(self):
        """Тест валидного Linux порта (/dev/ttyUSB0)"""
        is_valid, error_msg = validate_com_port("/dev/ttyUSB0")
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_linux_port_ttyacm(self):
        """Тест валидного Linux порта (/dev/ttyACM0)"""
        is_valid, error_msg = validate_com_port("/dev/ttyACM0")
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_linux_port_ttys(self):
        """Тест валидного Linux порта (/dev/ttyS0)"""
        is_valid, error_msg = validate_com_port("/dev/ttyS0")
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_empty_port(self):
        """Тест пустого порта"""
        is_valid, error_msg = validate_com_port("")
        assert is_valid is False
        assert "пустым" in error_msg.lower()
    
    def test_invalid_windows_port_zero(self):
        """Тест невалидного порта COM0"""
        is_valid, error_msg = validate_com_port("COM0")
        assert is_valid is False
        assert "Неверный формат" in error_msg
    
    def test_invalid_windows_port_too_high(self):
        """Тест невалидного порта COM257"""
        is_valid, error_msg = validate_com_port("COM257")
        assert is_valid is False
        assert "Неверный формат" in error_msg
    
    def test_invalid_port_format(self):
        """Тест невалидного формата порта"""
        invalid_ports = ["PORT1", "COM", "123", "COM1a", "ABC"]
        for port in invalid_ports:
            is_valid, error_msg = validate_com_port(port)
            assert is_valid is False, f"Should fail for {port}"
            assert "Неверный формат" in error_msg


class TestValidateBaudrate:
    """Тесты для функции validate_baudrate"""
    
    @pytest.mark.parametrize("baud", [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400])
    def test_valid_baudrates(self, baud):
        """Тест всех валидных baudrate"""
        is_valid, error_msg = validate_baudrate(baud)
        assert is_valid is True, f"Should accept {baud}"
        assert error_msg == ""
    
    def test_invalid_baudrate_low(self):
        """Тест слишком низкого baudrate"""
        is_valid, error_msg = validate_baudrate(600)
        assert is_valid is False
        assert "Неверный baudrate" in error_msg
    
    def test_invalid_baudrate_high(self):
        """Тест слишком высокого baudrate"""
        is_valid, error_msg = validate_baudrate(500000)
        assert is_valid is False
        assert "Неверный baudrate" in error_msg
    
    def test_invalid_baudrate_nonstandard(self):
        """Тест нестандартного baudrate"""
        is_valid, error_msg = validate_baudrate(12345)
        assert is_valid is False
        assert "Допустимые значения" in error_msg
    
    def test_invalid_baudrate_zero(self):
        """Тест нулевого baudrate"""
        is_valid, error_msg = validate_baudrate(0)
        assert is_valid is False
    
    def test_invalid_baudrate_negative(self):
        """Тест отрицательного baudrate"""
        is_valid, error_msg = validate_baudrate(-9600)
        assert is_valid is False


class TestValidateLogPath:
    """Тесты для функции validate_log_path"""
    
    def test_valid_simple_filename(self, tmp_path):
        """Тест валидного простого имени файла"""
        filepath = str(tmp_path / "test_log.txt")
        is_valid, error_msg = validate_log_path(filepath)
        assert is_valid is True
        assert error_msg == ""
    
    def test_valid_relative_path(self, tmp_path):
        """Тест валидного относительного пути"""
        # Создаём временную директорию
        subdir = tmp_path / "logs"
        subdir.mkdir()
        filepath = str(subdir / "log.txt")
        is_valid, error_msg = validate_log_path(filepath)
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_empty_path(self):
        """Тест пустого пути"""
        is_valid, error_msg = validate_log_path("")
        assert is_valid is False
        assert "пустым" in error_msg.lower()
    
    def test_invalid_path_traversal(self, tmp_path):
        """Тест path traversal атаки (..)"""
        is_valid, error_msg = validate_log_path("../etc/passwd")
        assert is_valid is False
        assert ".." in error_msg
    
    def test_invalid_path_traversal_nested(self, tmp_path):
        """Тест вложенного path traversal"""
        is_valid, error_msg = validate_log_path("logs/../../etc/passwd")
        assert is_valid is False
        assert ".." in error_msg
    
    def test_invalid_nonexistent_directory(self, tmp_path):
        """Тест несуществующей директории"""
        filepath = str(tmp_path / "nonexistent" / "log.txt")
        is_valid, error_msg = validate_log_path(filepath)
        assert is_valid is False
        assert "не существует" in error_msg
    
    def test_invalid_path_is_not_directory(self, tmp_path):
        """Тест когда путь не является директорией"""
        # Создаём файл вместо директории
        filepath = str(tmp_path / "not_a_dir")
        with open(filepath, 'w') as f:
            f.write("test")
        
        log_path = str(tmp_path / "not_a_dir" / "log.txt")
        is_valid, error_msg = validate_log_path(log_path)
        assert is_valid is False
        assert "не является директорией" in error_msg


class TestValidatorsIntegration:
    """Интеграционные тесты валидаторов"""
    
    def test_connection_params_validation(self):
        """Тест валидации параметров подключения"""
        # Типичные правильные параметры
        port = "COM4"
        baud = 19200
        
        port_valid, port_error = validate_com_port(port)
        baud_valid, baud_error = validate_baudrate(baud)
        
        assert port_valid is True
        assert baud_valid is True
        assert port_error == ""
        assert baud_error == ""
    
    def test_invalid_connection_params(self):
        """Тест валидации неправильных параметров подключения"""
        # Неправильные параметры
        port = "COM999"
        baud = 99999
        
        port_valid, port_error = validate_com_port(port)
        baud_valid, baud_error = validate_baudrate(baud)
        
        assert port_valid is False
        assert baud_valid is False
        assert "Неверный формат" in port_error
        assert "Неверный baudrate" in baud_error
    
    def test_complete_validation_workflow(self, tmp_path):
        """Тест полного workflow валидации"""
        # Шаг 1: Валидация порта
        port = "/dev/ttyUSB0"
        port_valid, _ = validate_com_port(port)
        assert port_valid is True
        
        # Шаг 2: Валидация baudrate
        baud = 115200
        baud_valid, _ = validate_baudrate(baud)
        assert baud_valid is True
        
        # Шаг 3: Валидация пути
        log_file = str(tmp_path / "dyn200_log.txt")
        path_valid, _ = validate_log_path(log_file)
        assert path_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
