#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Material Design 3 тема для современного интерфейса DYN-200 Monitor
Только темная тема (удалена поддержка светлой темы)
"""

import customtkinter as ctk
from typing import Tuple


class ModernTheme:
    """
    Material Design 3 цветовая палитра.
    ТОЛЬКО ТЕМНАЯ ТЕМА (светлая тема удалена).
    Контрасты соответствуют WCAG AA стандартам.
    """
    
    # ========== Dark Theme Colors (единственная тема) ==========
    PRIMARY: str = "#4A90D9"
    ON_PRIMARY: str = "#FFFFFF"
    PRIMARY_CONTAINER: str = "#00477C"
    ON_PRIMARY_CONTAINER: str = "#D1E4FF"
    SECONDARY: str = "#5CBC7C"
    ON_SECONDARY: str = "#00391C"
    SECONDARY_CONTAINER: str = "#1A5C3A"
    TERTIARY: str = "#FFB74D"
    ON_TERTIARY: str = "#4A2C00"
    ERROR: str = "#EF5350"
    ON_ERROR: str = "#FFFFFF"
    ERROR_CONTAINER: str = "#8B1A1A"
    SURFACE: str = "#1A1C23"
    SURFACE_VARIANT: str = "#252830"
    SURFACE_CONTAINER: str = "#2D313A"
    SURFACE_CONTAINER_HIGH: str = "#363A45"
    BACKGROUND: str = "#12141A"
    ON_SURFACE: str = "#E4E6EB"
    ON_SURFACE_VARIANT: str = "#9CA3AF"
    ON_SURFACE_DISABLED: str = "#6B7280"
    OUTLINE: str = "#4B5563"
    OUTLINE_VARIANT: str = "#374151"
    
    # ========== Parameter Colors (для графиков и индикаторов) ==========
    TORQUE_COLOR: str = "#E53935"
    TORQUE_COLOR_GLOW: str = "#EF5350"
    SPEED_COLOR: str = "#00897B"
    SPEED_COLOR_GLOW: str = "#26A69A"
    POWER_COLOR: str = "#FDD835"
    POWER_COLOR_GLOW: str = "#FFEE58"
    
    # ========== Animation Settings ==========
    TRANSITION_DURATION: int = 200
    TRANSITION_EASING: str = "cubic-bezier(0.4, 0, 0.2, 1)"
    
    # ========== Spacing Scale ==========
    SPACING_XS: int = 4
    SPACING_SM: int = 8
    SPACING_MD: int = 16
    SPACING_LG: int = 24
    SPACING_XL: int = 32
    SPACING_2XL: int = 48
    
    # ========== Corner Radius ==========
    RADIUS_SM: int = 8
    RADIUS_MD: int = 12
    RADIUS_LG: int = 16
    RADIUS_XL: int = 24
    RADIUS_FULL: int = 1000
    
    # ========== Typography ==========
    FONT_FAMILY: str = "Segoe UI"
    FONT_FAMILY_MONO: str = "Consolas"
    
    FONT_SIZE_XS: int = 10
    FONT_SIZE_SM: int = 12
    FONT_SIZE_MD: int = 14
    FONT_SIZE_LG: int = 16
    FONT_SIZE_XL: int = 18
    FONT_SIZE_2XL: int = 24
    FONT_SIZE_3XL: int = 32
    FONT_SIZE_4XL: int = 48
    
    @classmethod
    def apply(cls) -> None:
        """
        Применение темной темы к CustomTkinter.
        """
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    @classmethod
    def get_font(cls, size: int = FONT_SIZE_MD, weight: str = "normal", 
                 family: str = None):
        """
        Получить шрифт с указанными параметрами.
        
        Args:
            size: Размер шрифта
            weight: "normal" или "bold"
            family: Семейство шрифтов (по умолчанию FONT_FAMILY)
            
        Returns:
            CTkFont объект
        """
        return ctk.CTkFont(
            family=family or cls.FONT_FAMILY,
            size=size,
            weight=weight
        )
    
    @classmethod
    def hex_to_rgb(cls, hex_color: str) -> Tuple[int, int, int]:
        """Конвертация HEX в RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @classmethod
    def rgb_to_hex(cls, r: int, g: int, b: int) -> str:
        """Конвертация RGB в HEX строку."""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @classmethod
    def adjust_brightness(cls, hex_color: str, factor: float) -> str:
        """
        Изменить яркость цвета.
        
        Args:
            hex_color: Исходный цвет в HEX
            factor: Множитель (>1 - светлее, <1 - темнее)
            
        Returns:
            Новый цвет в HEX
        """
        r, g, b = cls.hex_to_rgb(hex_color)
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return cls.rgb_to_hex(r, g, b)
    
    @classmethod
    def with_alpha(cls, hex_color: str, alpha: float) -> str:
        """
        Добавить альфа-канал к цвету для CSS-like rgba.
        Возвращает строку в формате rgba(r,g,b,a)
        """
        r, g, b = cls.hex_to_rgb(hex_color)
        return f"rgba({r}, {g}, {b}, {alpha})"
    
    @classmethod
    def get_all_colors(cls) -> dict:
        """Получить все цвета темы в виде словаря."""
        return {
            'PRIMARY': cls.PRIMARY,
            'ON_PRIMARY': cls.ON_PRIMARY,
            'PRIMARY_CONTAINER': cls.PRIMARY_CONTAINER,
            'ON_PRIMARY_CONTAINER': cls.ON_PRIMARY_CONTAINER,
            'SECONDARY': cls.SECONDARY,
            'ON_SECONDARY': cls.ON_SECONDARY,
            'SECONDARY_CONTAINER': cls.SECONDARY_CONTAINER,
            'TERTIARY': cls.TERTIARY,
            'ON_TERTIARY': cls.ON_TERTIARY,
            'ERROR': cls.ERROR,
            'ON_ERROR': cls.ON_ERROR,
            'ERROR_CONTAINER': cls.ERROR_CONTAINER,
            'SURFACE': cls.SURFACE,
            'SURFACE_VARIANT': cls.SURFACE_VARIANT,
            'SURFACE_CONTAINER': cls.SURFACE_CONTAINER,
            'SURFACE_CONTAINER_HIGH': cls.SURFACE_CONTAINER_HIGH,
            'BACKGROUND': cls.BACKGROUND,
            'ON_SURFACE': cls.ON_SURFACE,
            'ON_SURFACE_VARIANT': cls.ON_SURFACE_VARIANT,
            'ON_SURFACE_DISABLED': cls.ON_SURFACE_DISABLED,
            'OUTLINE': cls.OUTLINE,
            'OUTLINE_VARIANT': cls.OUTLINE_VARIANT,
            'TORQUE_COLOR': cls.TORQUE_COLOR,
            'SPEED_COLOR': cls.SPEED_COLOR,
            'POWER_COLOR': cls.POWER_COLOR,
        }


class AnimationHelper:
    """Вспомогательный класс для анимаций UI элементов."""
    
    @staticmethod
    def pulse_widget(widget, scale: float = 1.05, duration: int = 150):
        """
        Пульсация виджета (увеличение и возврат).
        
        Args:
            widget: CTk виджет для анимации
            scale: Масштаб увеличения
            duration: Длительность в мс
        """
        original_width = widget.winfo_width()
        original_height = widget.winfo_height()
        
        # Увеличиваем
        widget.configure(
            width=int(original_width * scale),
            height=int(original_height * scale)
        )
        
        # Возвращаем через duration
        widget.after(duration, lambda: widget.configure(
            width=original_width,
            height=original_height
        ))
    
    @staticmethod
    def fade_color(widget, property_name: str, 
                   from_color: str, to_color: str,
                   steps: int = 10, delay: int = 20):
        """
        Плавный переход цвета.
        
        Args:
            widget: Виджет
            property_name: Имя свойства для изменения (например, 'fg_color')
            from_color: Начальный цвет
            to_color: Конечный цвет
            steps: Количество шагов анимации
            delay: Задержка между шагами (мс)
        """
        from_rgb = ModernTheme.hex_to_rgb(from_color)
        to_rgb = ModernTheme.hex_to_rgb(to_color)
        
        step_r = (to_rgb[0] - from_rgb[0]) / steps
        step_g = (to_rgb[1] - from_rgb[1]) / steps
        step_b = (to_rgb[2] - from_rgb[2]) / steps
        
        def animate_step(current_step):
            if current_step > steps:
                return
            
            r = int(from_rgb[0] + step_r * current_step)
            g = int(from_rgb[1] + step_g * current_step)
            b = int(from_rgb[2] + step_b * current_step)
            
            color = ModernTheme.rgb_to_hex(r, g, b)
            widget.configure(**{property_name: color})
            
            widget.after(delay, lambda: animate_step(current_step + 1))
        
        animate_step(0)


# Глобальный экземпляр для удобного импорта
theme = ModernTheme
