#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit-тесты для модуля конвертации единиц DYN-200
"""

import pytest
import sys
import os

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.unit_conversion import (
    raw_to_torque,
    raw_to_speed,
    raw_to_power,
    to_signed32,
    raw_to_torque_nm,
    raw_to_speed_rpm,
    raw_to_power_w
)


class TestRawToTorque:
    """Тесты для функции raw_to_torque"""
    
    def test_raw_to_torque_positive(self):
        """Тест конвертации положительного значения (деление на 10)"""
        result = raw_to_torque(13)
        assert result == 1.3  # 13 / 10 = 1.3 Н·м (соответствует показаниям дисплея)
        assert isinstance(result, float)
    
    def test_raw_to_torque_zero(self):
        """Тест конвертации нуля"""
        result = raw_to_torque(0)
        assert result == 0.0
        assert isinstance(result, float)
    
    def test_raw_to_torque_negative(self):
        """Тест конвертации отрицательного значения"""
        result = raw_to_torque(-50)
        assert result == -5.0  # -50 / 10 = -5.0 Н·м
        assert isinstance(result, float)
    
    def test_raw_to_torque_large_positive(self):
        """Тест конвертации большого положительного значения"""
        result = raw_to_torque(500)
        assert result == 50.0  # 500 / 10 = 50.0 Н·м
    
    def test_raw_to_torque_large_negative(self):
        """Тест конвертации большого отрицательного значения"""
        result = raw_to_torque(-1000)
        assert result == -100.0  # -1000 / 10 = -100.0 Н·м
    
    def test_raw_to_torque_fractional(self):
        """Тест конвертации дробного результата"""
        result = raw_to_torque(123)
        assert result == 12.3  # 123 / 10 = 12.3 Н·м
    
    def test_raw_to_torque_with_coefficient(self):
        """Тест с коэффициентом коррекции"""
        # Если raw=12 (1.2 Н·м), а на дисплее показывает 1.2, то coefficient=1.0
        result = raw_to_torque(12, coefficient=1.0)
        assert pytest.approx(result, 0.0001) == 1.2  # (12 / 10) * 1.0 = 1.2

    def test_raw_to_torque_display_value_1_3_nm(self):
        """
        Тест для проверки соответствия показаниям дисплея датчика.
        
        На дисплее датчика: 1.3 Н·м
        Raw значение из Modbus: ~13 (в десятых долях)
        Ожидаемый результат: 1.3 Н·м
        """
        # При raw=13 должно получиться 1.3 Н·м (13 / 10 = 1.3)
        result = raw_to_torque(13, coefficient=1.0, t_ratio=1087)
        assert pytest.approx(result, 0.01) == 1.3, f"Expected 1.3 N·m, got {result}"
        
        # Проверка диапазона 1.1-1.3 Н·м
        result_11 = raw_to_torque(11, coefficient=1.0, t_ratio=1087)
        result_13 = raw_to_torque(13, coefficient=1.0, t_ratio=1087)
        assert pytest.approx(result_11, 0.01) == 1.1, f"Expected 1.1 N·m for raw=11, got {result_11}"
        assert pytest.approx(result_13, 0.01) == 1.3, f"Expected 1.3 N·m for raw=13, got {result_13}"

    def test_raw_to_torque_t_ratio_effect(self):
        """
        Тест влияния t_ratio на результат.
        
        При t_ratio=1087 множитель = 1.0
        При t_ratio=2174 множитель = 2.0 (удвоенное значение)
        """
        raw = 13
        result_default = raw_to_torque(raw, coefficient=1.0, t_ratio=1087)
        result_doubled = raw_to_torque(raw, coefficient=1.0, t_ratio=2174)
        
        assert pytest.approx(result_default, 0.01) == 1.3  # 13/10*1.0 = 1.3
        assert pytest.approx(result_doubled, 0.01) == 2.6  # 13/10*2.0 = 2.6 (должно удвоиться)
    
    def test_raw_to_torque_alias(self):
        """Тест алиаса raw_to_torque_nm"""
        result = raw_to_torque_nm(20)
        assert result == 2.0  # 20 / 10 = 2.0 Н·м
        assert raw_to_torque_nm(10) == raw_to_torque(10)


class TestRawToSpeed:
    """Тесты для функции raw_to_speed"""
    
    def test_raw_to_speed_zero(self):
        """Тест конвертации нуля"""
        result = raw_to_speed(0)
        assert result == 0.0
        assert isinstance(result, float)
    
    def test_raw_to_speed_positive(self):
        """Тест конвертации положительного значения (1:1)"""
        result = raw_to_speed(1000)
        assert result == 1000.0  # 1000 напрямую (без деления)
    
    def test_raw_to_speed_typical_rpm(self):
        """Тест типичных значений RPM"""
        # 3000 RPM
        result = raw_to_speed(3000)
        assert result == 3000.0
    
    def test_raw_to_speed_maximum(self):
        """Тест максимального значения"""
        # Максимум для 16-bit unsigned
        result = raw_to_speed(65535)
        assert result == 65535.0
    
    def test_raw_to_speed_alias(self):
        """Тест алиаса raw_to_speed_rpm"""
        result = raw_to_speed_rpm(5000)
        assert result == 5000.0
        assert raw_to_speed_rpm(1000) == raw_to_speed(1000)


class TestRawToPower:
    """Тесты для функции raw_to_power"""
    
    def test_raw_to_power_zero(self):
        """Тест конвертации нуля"""
        result = raw_to_power(0)
        assert result == 0.0
    
    def test_raw_to_power_positive(self):
        """Тест конвертации положительного значения (raw в Вт)"""
        result = raw_to_power(838)  # 838 Вт
        assert result == 838.0  # 838 * 1.0 = 838 Вт
    
    def test_raw_to_power_with_correction(self):
        """Тест с коэффициентом коррекции"""
        result = raw_to_power(500, correction=0.5)  # 500 * 0.5
        assert result == 250.0
    
    def test_raw_to_power_correction_greater_than_one(self):
        """Тест с коррекцией > 1"""
        result = raw_to_power(500, correction=1.5)  # 500 * 1.5
        assert result == 750.0
    
    def test_raw_to_power_default_correction(self):
        """Тест коррекции по умолчанию"""
        result = raw_to_power(1000)  # 1000 * 1.0 = 1000 Вт
        assert result == 1000.0  # correction=1.0 по умолчанию
    
    def test_raw_to_power_alias(self):
        """Тест алиаса raw_to_power_w"""
        result = raw_to_power_w(500, correction=0.8)  # 500 * 0.8
        assert result == 400.0
        assert raw_to_power_w(1000) == raw_to_power(1000)


class TestToSigned32:
    """Тесты для функции to_signed32"""
    
    def test_to_signed32_zero(self):
        """Тест нуля"""
        result = to_signed32(0)
        assert result == 0
    
    def test_to_signed32_positive(self):
        """Тест положительного значения"""
        result = to_signed32(1000)
        assert result == 1000
    
    def test_to_signed32_max_positive(self):
        """Тест максимального положительного значения (2^31 - 1)"""
        result = to_signed32(0x7FFFFFFF)
        assert result == 2147483647
    
    def test_to_signed32_min_negative(self):
        """Тест минимального отрицательного значения (-2^31)"""
        result = to_signed32(0x80000000)
        assert result == -2147483648
    
    def test_to_signed32_negative_one(self):
        """Тест -1 (0xFFFFFFFF)"""
        result = to_signed32(0xFFFFFFFF)
        assert result == -1
    
    def test_to_signed32_boundary(self):
        """Тест граничного значения"""
        # 0x80000000 = -2147483648
        result = to_signed32(0x80000000)
        assert result == -2147483648
    
    def test_to_signed32_mid_negative(self):
        """Тест среднего отрицательного значения"""
        # 0xFFFFFFFF = -1
        # 0xFFFFFFFE = -2
        result = to_signed32(0xFFFFFFFE)
        assert result == -2


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_raw_to_torque_boundary_32bit(self):
        """Тест максимального 32-bit значения"""
        result = raw_to_torque(2147483647)
        assert result == 214748364.7  # Делим на 10
    
    def test_raw_to_speed_zero_boundary(self):
        """Тест границы нуля (1:1 соответствие)"""
        result = raw_to_speed(1)
        assert result == 1.0  # 1:1, без деления
    
    def test_raw_to_power_with_zero_correction(self):
        """Тест с нулевой коррекцией"""
        result = raw_to_power(1000, correction=0.0)
        assert result == 0.0
    
    def test_chained_conversion(self):
        """Тест цепочки конверсий (типичный use case)"""
        # Симуляция чтения из Modbus
        # raw=12 → 1.2 Н·м (деление на 10)
        raw_high = 0x0000
        raw_low = 0x000C  # 12 в десятичном (12 / 10 = 1.2 Н·м)
        raw_32bit = (raw_high << 16) | raw_low
        
        signed = to_signed32(raw_32bit)
        torque = raw_to_torque(signed)
        
        assert signed == 12
        assert torque == 1.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
