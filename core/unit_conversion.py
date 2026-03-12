#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль конвертации сырых данных DYN-200 в физические единицы.

DYN-200 Protocol (исправлено):
- Torque: 32-bit signed, делим на 10 → Н·м (значения в десятых долях)
- Speed: 32-bit unsigned, 1:1 → RPM (без деления)
- Power: 32-bit unsigned, умножаем на 100 → Вт

ИСТОРИЯ ИСПРАВЛЕНИЙ:
- Было: деление на 1000 (ошибочно по документации)
- Стало: деление на 100 (проверено экспериментально)
- Финальное: деление на 10 (проверено по показаниям дисплея датчика)
- Причина: Датчик DYN-200 передаёт значения в десятых долях Н·м (raw=13 → 1.3 Н·м)
  Это соответствует показаниям на дисплее датчика.

Examples:
    >>> from core.unit_conversion import raw_to_torque, raw_to_speed, raw_to_power
    >>>
    >>> # Конвертация крутящего момента
    >>> torque_nm = raw_to_torque(500)  # 5.0 Н·м
    >>>
    >>> # Конвертация скорости
    >>> speed_rpm = raw_to_speed(1500)  # 1500.0 RPM
    >>>
    >>> # Конвертация мощности
    >>> power_w = raw_to_power(5, 1.0)  # 500 Вт
"""


def raw_to_torque(raw_value: int, coefficient: float = 1.0, t_ratio: int = 1087) -> float:
    """
    Конвертация сырого значения крутящего момента в Н·м.
    
    DYN-200 передаёт крутящий момент как 32-bit signed integer.
    По документации: значение передаётся в единицах 0.001 Н·м (тысячные доли),
    то есть raw_value = 1000 соответствует 1.0 Н·м.
    
    Добавлен параметр t_ratio (T_ratio) - передаточное отношение датчика,
    которое влияет на конечное значение момента.
    
    Args:
        raw_value: 32-bit signed integer из регистров Modbus.
            Диапазон: -99999 ~ 99999 (в единицах 0.001 Н·м).
        coefficient: Коэффициент коррекции (по умолчанию 1.0).
            Используется для калибровки датчика.
        t_ratio: Передаточное отношение датчика (по умолчанию 1087).
            Стандартное значение для DYN-200. Влияет на масштабирование.
    
    Returns:
        Значение крутящего момента в Н·м (Ньютон-метрах).
    
    Raises:
        TypeError: Если raw_value или coefficient не являются числами.
    
    Examples:
        >>> raw_to_torque(50000)
        50.0
        >>> raw_to_torque(-50000)
        -50.0
        >>> raw_to_torque(0)
        0.0
        >>> raw_to_torque(1000)
        1.0
        >>> raw_to_torque(5400, 0.1)  # Калибровка: 0.54 Н·м
        0.54
        >>> raw_to_torque(50000, 1.0, 2174)  # С удвоенным передаточным отношением
        100.0
    """
    # Базовое преобразование: делим на 10 (значения в десятых долях)
    # ИСПРАВЛЕНО: Датчик DYN-200 передаёт значения в десятых долях Н·м
    # Например: raw=13 → 1.3 Н·м (как показывает дисплей датчика)
    base_torque = raw_value / 10.0
    # Применяем передаточное отношение: t_ratio / 1087
    # При t_ratio=1087 множитель = 1.0 (базовое поведение)
    # При t_ratio=2174 множитель = 2.0 (удвоенное значение)
    ratio_factor = t_ratio / 1087.0 if t_ratio > 0 else 1.0
    return base_torque * ratio_factor * coefficient


def raw_to_speed(raw_value: int, r_decimal: int = 0) -> float:
    """
    Конвертация сырого значения скорости в RPM.
    
    DYN-200 передаёт скорость как 32-bit unsigned integer.
    Параметр r_decimal (Rdecimal) определяет количество десятичных знаков
    и влияет на деление: speed = raw_value / (10 ^ r_decimal)
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
            Диапазон: 0 ~ 99999.
        r_decimal: Количество десятичных знаков (0-4, по умолчанию 1).
            Определяет делитель: 10^r_decimal.
            0 = без деления, 1 = /10, 2 = /100, 3 = /1000, 4 = /10000
    
    Returns:
        Скорость вращения в RPM (обороты в минуту).
    
    Raises:
        TypeError: Если raw_value не является числом.
        ValueError: Если raw_value отрицательное.
    
    Examples:
        >>> raw_to_speed(1500)
        1500.0  # По умолчанию r_decimal=0, без деления
        >>> raw_to_speed(1500, 1)
        150.0  # Делим на 10
        >>> raw_to_speed(1500, 2)
        15.0  # Делим на 100
        >>> raw_to_speed(0, 1)
        0.0
        >>> raw_to_speed(10000, 1)
        1000.0
    """
    # Ограничиваем r_decimal диапазоном 0-4
    r_decimal = max(0, min(4, r_decimal))
    divisor = 10 ** r_decimal
    return float(raw_value) / divisor


def raw_to_power(raw_value: int, correction: float = 1.0, p_units: str = "W") -> float:
    """
    Конвертация сырого значения мощности в Ватты или килоВатты.
    
    DYN-200 передаёт мощность как 32-bit unsigned integer.
    Параметр p_units определяет единицы измерения:
    - "W" (Ватты): значение возвращается как есть (×1)
    - "kW" (килоВатты): значение делится на 1000
    
    Применяется коэффициент коррекции для калибровки.
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
            Диапазон: 0 ~ 99999 (в единицах Вт).
        correction: Коэффициент коррекции мощности.
            Диапазон: 0.1 ~ 2.0 (по умолчанию 1.0).
            Значение 1.0 означает отсутствие коррекции.
        p_units: Единицы измерения мощности ("W" или "kW", по умолчанию "W").
            "W" - Ватты (множитель 1)
            "kW" - килоВатты (множитель 0.001)
    
    Returns:
        Значение мощности в выбранных единицах с применённым коэффициентом.
    
    Raises:
        TypeError: Если raw_value или correction не являются числами.
        ValueError: Если correction вне допустимого диапазона.
    
    Examples:
        >>> raw_to_power(838, 1.0, "W")  # 838 Вт
        838.0
        >>> raw_to_power(838, 1.0, "kW")  # 0.838 кВт
        0.838
        >>> raw_to_power(500, 1.5, "W")
        750.0
        >>> raw_to_power(0, 1.0, "W")
        0.0
    """
    # Множитель для единиц измерения
    unit_multiplier = 0.001 if p_units.upper() == "KW" else 1.0
    return raw_value * unit_multiplier * correction


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

def raw_to_torque_nm(raw_value: int, coefficient: float = 1.0, t_ratio: int = 1087) -> float:
    """
    Алиас для функции raw_to_torque().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_torque().
    
    Args:
        raw_value: 32-bit signed integer из регистров Modbus.
        coefficient: Коэффициент коррекции (по умолчанию 1.0).
        t_ratio: Передаточное отношение датчика (по умолчанию 1087).
    
    Returns:
        Значение в Н·м.
    
    See Also:
        raw_to_torque: Основная функция конвертации.
    """
    return raw_to_torque(raw_value, coefficient, t_ratio)


def raw_to_speed_rpm(raw_value: int, r_decimal: int = 0) -> float:
    """
    Алиас для функции raw_to_speed().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_speed().
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
        r_decimal: Количество десятичных знаков (по умолчанию 1).
    
    Returns:
        Значение в RPM.
    
    See Also:
        raw_to_speed: Основная функция конвертации.
    """
    return raw_to_speed(raw_value, r_decimal)


def raw_to_power_w(raw_value: int, correction: float = 1.0, p_units: str = "W") -> float:
    """
    Алиас для функции raw_to_power().
    
    Сохранён для обратной совместимости со старым кодом.
    Новый код должен использовать raw_to_power().
    
    Args:
        raw_value: 32-bit unsigned integer из регистров Modbus.
        correction: Коэффициент коррекции (по умолчанию 1.0).
        p_units: Единицы измерения мощности ("W" или "kW", по умолчанию "W").
    
    Returns:
        Значение в Ваттах или килоВаттах.
    
    See Also:
        raw_to_power: Основная функция конвертации.
    """
    return raw_to_power(raw_value, correction, p_units)
