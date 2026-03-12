#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для Modbus клиента с моками
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockModbusResponse:
    """Мок-объект ответа Modbus"""
    def __init__(self, registers=None, isError=False):
        self.registers = registers or []
        self.isError = isError


class MockModbusSerialClient:
    """Мок-класс для ModbusSerialClient"""
    
    def __init__(self, port="COM4", baudrate=19200, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self.timeout = kwargs.get('timeout', 2)
        self._should_fail_connect = False
        self._should_fail_read = False
        self._read_count = 0
        
    def connect(self):
        """Метод подключения"""
        if self._should_fail_connect:
            return False
        self.connected = True
        return True
    
    def close(self):
        """Метод закрытия соединения"""
        self.connected = False
        return True
    
    def read_holding_registers(self, address, count=1, device_id=1):
        """Метод чтения регистров"""
        if self._should_fail_read:
            return None
        
        self._read_count += 1
        
        # Генерируем тестовые данные
        registers = []
        for i in range(count):
            registers.append((address + i) * 100)
        
        return MockModbusResponse(registers=registers, isError=False)
    
    def set_fail_connect(self, fail=True):
        """Установка режима ошибки подключения"""
        self._should_fail_connect = fail
        
    def set_fail_read(self, fail=True):
        """Установка режима ошибки чтения"""
        self._should_fail_read = fail


class TestModbusClientMock:
    """Тесты мок-класса Modbus клиента"""
    
    def test_mock_client_creation(self):
        """Тест создания мок-клиента"""
        client = MockModbusSerialClient(port="COM3", baudrate=9600)
        assert client.port == "COM3"
        assert client.baudrate == 9600
        assert client.connected is False
    
    def test_mock_client_connect_success(self):
        """Тест успешного подключения"""
        client = MockModbusSerialClient()
        result = client.connect()
        assert result is True
        assert client.connected is True
    
    def test_mock_client_connect_failure(self):
        """Тест неудачного подключения"""
        client = MockModbusSerialClient()
        client.set_fail_connect(True)
        result = client.connect()
        assert result is False
        assert client.connected is False
    
    def test_mock_client_close(self):
        """Тест закрытия соединения"""
        client = MockModbusSerialClient()
        client.connect()
        assert client.connected is True
        client.close()
        assert client.connected is False
    
    def test_mock_client_read_success(self):
        """Тест успешного чтения регистров"""
        client = MockModbusSerialClient()
        client.connect()
        response = client.read_holding_registers(0, count=6, device_id=1)
        
        assert response is not None
        assert response.isError is False
        assert len(response.registers) == 6
        assert response.registers[0] == 0
        assert response.registers[5] == 500
    
    def test_mock_client_read_failure(self):
        """Тест неудачного чтения"""
        client = MockModbusSerialClient()
        client.connect()
        client.set_fail_read(True)
        response = client.read_holding_registers(0, count=6)
        
        assert response is None


class TestModbusWithPytestMock:
    """Тесты с использованием pytest-mock"""
    
    def test_modbus_connect_with_mock(self, mocker):
        """Тест подключения с моком pymodbus"""
        # Создаём мок для ModbusSerialClient
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        mock_instance.connect.return_value = True
        mock_client_class.return_value = mock_instance
        
        # Используем как в реальном коде
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM4", baudrate=19200)
        result = client.connect()
        
        assert result is True
        mock_instance.connect.assert_called_once()
    
    def test_modbus_read_registers_with_mock(self, mocker):
        """Тест чтения регистров с моком"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.registers = [1000, 2000, 3000, 4000, 5000, 6000]
        mock_response.isError = False
        mock_instance.read_holding_registers.return_value = mock_response
        mock_instance.connect.return_value = True
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM4", baudrate=19200)
        client.connect()
        
        response = client.read_holding_registers(0, count=6, device_id=1)
        
        assert response.registers[0] == 1000
        assert response.registers[5] == 6000
        mock_instance.read_holding_registers.assert_called_once_with(
            0, count=6, device_id=1
        )
    
    def test_modbus_connection_error_handling(self, mocker):
        """Тест обработки ошибок соединения"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        
        # Симулируем исключение при подключении
        from pymodbus.exceptions import ConnectionException
        mock_instance.connect.side_effect = ConnectionException("Port not found")
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM99", baudrate=19200)
        
        with pytest.raises(ConnectionException):
            client.connect()
    
    def test_modbus_io_error_handling(self, mocker):
        """Тест обработки IO ошибок"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        
        from pymodbus.exceptions import ModbusIOException
        mock_instance.read_holding_registers.side_effect = ModbusIOException("Timeout")
        mock_instance.connect.return_value = True
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM4", baudrate=19200)
        client.connect()
        
        with pytest.raises(ModbusIOException):
            client.read_holding_registers(0, count=6)
    
    def test_modbus_slave_address_validation(self, mocker):
        """Тест валидации slave адреса"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.registers = [1, 2, 3]
        mock_response.isError = False
        mock_instance.read_holding_registers.return_value = mock_response
        mock_instance.connect.return_value = True
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM4", baudrate=19200)
        client.connect()
        
        # Тест с разными slave адресами
        for slave_id in [1, 10, 127, 247]:
            client.read_holding_registers(0, count=3, device_id=slave_id)
            mock_instance.read_holding_registers.assert_called_with(
                0, count=3, device_id=slave_id
            )


class TestModbusDataProcessing:
    """Тесты обработки данных Modbus"""
    
    def test_decode_32bit_signed(self):
        """Тест декодирования 32-bit знакового значения"""
        # Данные из Modbus (2 регистра = 32 бита)
        high_word = 0x0000
        low_word = 0x03E8  # 1000
        
        # Объединение в 32-bit
        raw_32bit = (high_word << 16) | low_word
        
        # Конвертация в знаковое
        if raw_32bit >= 0x80000000:
            value = raw_32bit - 0x100000000
        else:
            value = raw_32bit
        
        assert value == 1000
    
    def test_decode_32bit_negative(self):
        """Тест декодирования отрицательного 32-bit"""
        # -500 в дополнительном коде = 0xFFFFFE0C
        registers = [0xFFFF, 0xFE0C]
        raw_32bit = (registers[0] << 16) | registers[1]
        
        if raw_32bit >= 0x80000000:
            value = raw_32bit - 0x100000000
        else:
            value = raw_32bit
        
        assert value == -500
    
    def test_decode_multiple_values(self):
        """Тест декодирования нескольких 32-bit значений"""
        # 6 регистров = 3 значения по 32 бита
        registers = [0x0000, 0x03E8,  # 1000
                     0x0000, 0x1388,  # 5000
                     0x0000, 0x2710]  # 10000
        
        values = []
        for i in range(0, 6, 2):
            raw_32bit = (registers[i] << 16) | registers[i+1]
            if raw_32bit >= 0x80000000:
                value = raw_32bit - 0x100000000
            else:
                value = raw_32bit
            values.append(value)
        
        assert values == [1000, 5000, 10000]
    
    def test_consecutive_read_simulation(self, mocker):
        """Тест последовательного чтения с имитацией реальных данных"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        
        # Имитация изменяющихся данных
        responses = [
            Mock(registers=[0, 1000, 0, 500, 0, 200], isError=False),
            Mock(registers=[0, 1200, 0, 550, 0, 250], isError=False),
            Mock(registers=[0, 1100, 0, 525, 0, 225], isError=False),
        ]
        mock_instance.read_holding_registers.side_effect = responses
        mock_instance.connect.return_value = True
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        client = ModbusSerialClient(port="COM4", baudrate=19200)
        client.connect()
        
        readings = []
        for _ in range(3):
            response = client.read_holding_registers(0, count=6)
            if response and not response.isError:
                # Декодируем (каждое значение = 2 регистра)
                torque_raw = (response.registers[0] << 16) | response.registers[1]
                readings.append(torque_raw)
        
        assert len(readings) == 3
        assert readings == [1000, 1200, 1100]


class TestModbusConnectionLifecycle:
    """Тесты жизненного цикла соединения"""
    
    def test_full_connection_lifecycle(self, mocker):
        """Тест полного цикла: подключение -> чтение -> отключение"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.registers = [0, 1000, 0, 500, 0, 200]
        mock_response.isError = False
        mock_instance.read_holding_registers.return_value = mock_response
        mock_instance.connect.return_value = True
        mock_instance.close.return_value = True
        mock_client_class.return_value = mock_instance
        
        from pymodbus.client import ModbusSerialClient
        
        # Подключение
        client = ModbusSerialClient(port="COM4", baudrate=19200, timeout=1)
        assert client.connect() is True
        
        # Чтение данных
        response = client.read_holding_registers(0, count=6, device_id=1)
        assert response is not None
        assert len(response.registers) == 6
        
        # Отключение
        client.close()
        
        # Проверка вызовов
        mock_instance.connect.assert_called_once()
        mock_instance.read_holding_registers.assert_called_once_with(0, count=6, device_id=1)
        mock_instance.close.assert_called_once()
    
    def test_reconnection_scenario(self, mocker):
        """Тест сценария переподключения"""
        mock_client_class = mocker.patch('pymodbus.client.ModbusSerialClient')
        
        # Первый клиент падает, второй работает
        mock_instance1 = Mock()
        mock_instance1.connect.return_value = False
        
        mock_instance2 = Mock()
        mock_instance2.connect.return_value = True
        mock_instance2.read_holding_registers.return_value = Mock(
            registers=[0, 1000, 0, 500, 0, 200], isError=False
        )
        
        mock_client_class.side_effect = [mock_instance1, mock_instance2]
        
        from pymodbus.client import ModbusSerialClient
        
        # Первая попытка
        client1 = ModbusSerialClient(port="COM4", baudrate=19200)
        if not client1.connect():
            client1.close()
            
            # Вторая попытка
            client2 = ModbusSerialClient(port="COM3", baudrate=19200)
            assert client2.connect() is True
            response = client2.read_holding_registers(0, count=6)
            assert response is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
