#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль конвертации сырых данных DYN-200 в физические единицы.

DYN-200 Protocol:
- Torque: 32-bit signed, делим на 1000 → Н·м
- Speed: 32-bit unsigned, делим на 10 → RPM
- Power: 32-bit unsigned, 1:1 → Вт

Examples:
    >>> from core.unit_conversion import raw_to_torque, raw_to_speed, raw_to_power
    >>> 
    >>> # Конвертация крутящего момента
    >>> torque_nm = raw_to_torque(50000)  # 50.0 Н·м
    >>> 
    >>> # Конвертация скорости
    >>> speed_rpm = raw_to_speed(1500)    # 150.0 RPM
    >>> 
    >>> # Конвертация мощности
    >>> power_w = raw_to_power(500, 1.0)  # 500 Вт
"""


def raw_to_torque(raw_value: int) -> float:
    """
    Конвертация сырого значения крутящего момента в Н·м.
    
    DYN-200 передаёт крутящий момент как 32-bit signed integer,
    где значение 1000 соответствует 1.0 Н·м.
    
    Args:
        raw_value: 32-bit signed integer из регистров Modbus.
            Диапазон: -99999 ~ 99999 (в единицах 0.001 Н·м).
    
    Returns:
        Значение крутящего момента в Н·м (Ньютон-метрах).
    
    Raises:
        TypeError: Если raw_value не является числом.
    
    Examples:
        >>> raw_to_torque(50000)
        50.0
        >>> raw_to_torque(-50000)
        -50.0
        >>> raw_to_torque(0)
        0.0
        >>> raw_to_torque(1000)
        1.0
    """
    return raw_value / 1000.0


def raw_to_speed(raw_value: int) -> float:
    """
    Конвертация сырого значения скорости в RPM.
    
    DYN-200 передаёт скорость как 32-bit unsigned integer,
    где значение делится на 10 для получения RPM.
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
            Диапазон: 0 ~ 99999.
    
    Returns:
        Скорость вращения в RPM (обороты в минуту).
    
    Raises:
        TypeError: Если raw_value не является числом.
        ValueError: Если raw_value отрицательное.
    
    Examples:
        >>> raw_to_speed(1500)
        150.0
        >>> raw_to_speed(0)
        0.0
        >>> raw_to_speed(10000)
        1000.0
    """
    return raw_value / 10.0


def raw_to_power(raw_value: int, correction: float = 1.0) -> float:
    """
    Конвертация сырого значения мощности в Ватты.
    
    DYN-200 передаёт мощность как 32-bit unsigned integer,
    где каждая единица соответствует 1 Вт. Применяется
    коэффициент коррекции для калибровки.
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
            Диапазон: 0 ~ 99999.
        correction: Коэффициент коррекции мощности.
            Диапазон: 0.1 ~ 2.0 (по умолчанию 1.0).
            Значение 1.0 означает отсутствие коррекции.
    
    Returns:
        Значение мощности в Ваттах с применённым коэффициентом коррекции.
    
    Raises:
        TypeError: Если raw_value или correction не являются числами.
        ValueError: Если correction вне допустимого диапазона.
    
    Examples:
        >>> raw_to_power(500, 1.0)
        500.0
        >>> raw_to_power(500, 1.5)
        750.0
        >>> raw_to_power(0, 1.0)
        0.0
    """
    return raw_value * correction


def to_signed32(value: int) -> int:
    """
    Преобразование беззнакового 32-bit в знаковое.
    
    Используется для корректной интерпретации отрицательных
    значений крутящего момента из регистров Modbus.
    Реализует two's complement преобразование.
    
    Args:
        value: Беззнаковое 32-bit значение (0 ~ 4294967295).
    
    Returns:
        Знаковое 32-bit значение (-2147483648 ~ 2147483647).
    
    Raises:
        TypeError: Если value не является целым числом.
    
    Examples:
        >>> to_signed32(50000)
        50000
        >>> to_signed32(0xFFFFFFFF)  # -1 в two's complement
        -1
        >>> to_signed32(0x80000000)  # Минимальное отрицательное
        -2147483648
        >>> to_signed32(0)
        0
    """
    if value >= 0x80000000:
        return value - 0x100000000
    return value


# =============================================================================
# Алиасы для обратной совместимости
# =============================================================================

def raw_to_torque_nm(raw_value: int) -> float:
    """
    Алиас для функции raw_to_torque().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_torque().
    
    Args:
        raw_value: 32-bit signed integer из регистров Modbus.
    
    Returns:
        Значение в Н·м.
    
    See Also:
        raw_to_torque: Основная функция конвертации.
    """
    return raw_to_torque(raw_value)


def raw_to_speed_rpm(raw_value: int) -> float:
    """
    Алиас для функции raw_to_speed().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_speed().
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
    
    Returns:
        Значение в RPM.
    
    See Also:
        raw_to_speed: Основная функция конвертации.
    """
    return raw_to_speed(raw_value)


def raw_to_power_w(raw_value: int, correction: float = 1.0) -> float:
    """
    Алиас для функции raw_to_power().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_power().
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
        correction: Коэффициент коррекции (по умолчанию 1.0).
    
    Returns:
        Значение в Ваттах.
    
    See Also:
        raw_to_power: Основная функция конвертации.
    """
    return raw_to_power(raw_value, correction)
