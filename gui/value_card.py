#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Карточка параметра с современным дизайном (Material Design 3)
Поддерживает Torque, Speed, Power с индикаторами, анимациями и шкалами с делениями
"""

import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable, List, Tuple
import threading
import time
import math

from gui.modern_theme import ModernTheme, theme


class ValueCard(ctk.CTkFrame):
    """
    Карточка для отображения параметра (Torque/Speed/Power).
    Стиль: Material Design 3 + Glassmorphism + шкала с равномерными делениями.
    """
    
    # Параметры шкалы по умолчанию для каждого типа параметра
    SCALE_PARAMS = {
        'Torque': {
            'min': -9,
            'max': 10,
            'major_step': 1,
            'minor_ticks': 4,
            'zero_highlight': True,
            'negative_color': '#e74c3c',  # Красный для отрицательных
            'positive_color': '#27ae60',  # Зелёный для положительных
        },
        'Speed': {
            'min': 50,
            'max': 1000,
            'major_step': 50,
            'minor_ticks': 4,
            'zero_highlight': False,
            'negative_color': None,
            'positive_color': None,
        },
        'Power': {
            'min': 50,      # 50 Вт мин
            'max': 950,     # 950 Вт макс
            'major_step': 50,  # Шаг 50 Вт
            'minor_ticks': 4,
            'zero_highlight': False,
            'negative_color': None,
            'positive_color': None,
        }
    }
    
    def __init__(self, parent, title: str, unit: str, color: str,
                 max_unit: str = "",
                 width: int = 240, height: int = 220,
                 decimal_places: int = 2, **kwargs):
        """
        Инициализация карточки параметра.
        
        Args:
            parent: Родительский виджет
            title: Название параметра (Torque/Speed/Power)
            unit: Единица измерения (N·m, RPM, kW)
            color: Акцентный цвет для индикатора и значения
            width: Ширина карточки
            height: Высота карточки
            decimal_places: Количество десятичных знаков для отображения
        """
        super().__init__(parent, **kwargs)
        
        self.title_text = title
        self.unit = unit
        self.max_unit = max_unit
        self.accent_color = color
        self.decimal_places = decimal_places
        self.max_value: float = 0.0
        self.current_value: float = 0.0
        self.pulsing = False
        self.previous_value: float = 0.0
        
        # Параметры шкалы для этого параметра
        self.scale_params = self.SCALE_PARAMS.get(title, self.SCALE_PARAMS['Torque'])
        
        # Настройка стиля карточки (Glassmorphism effect)
        self.configure(
            width=width,
            height=height,
            fg_color=ModernTheme.SURFACE_VARIANT,
            corner_radius=ModernTheme.RADIUS_LG,
            border_width=1,
            border_color=ModernTheme.OUTLINE_VARIANT
        )
        
        # Запрещаем изменение размера
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        # Создаем внутреннюю структуру
        self._create_header()
        self._create_value_display()
        self._create_scale_display()
        self._create_footer()
        
    def _create_scale_display(self):
        """Создание отображения максимального значения вместо шкалы."""
        # Контейнер для max значения
        self.max_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.max_frame.pack(fill="x", padx=12, pady=(4, 4))
        self.max_frame.pack_propagate(False)
        
        # Метка "MAX"
        self.max_title_label = ctk.CTkLabel(
            self.max_frame,
            text="MAX",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_XS, "bold"),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        )
        self.max_title_label.pack(pady=(2, 0))
        
        # Значение максимума крупным шрифтом (уменьшен для помещения в карточку)
        self.max_value_label = ctk.CTkLabel(
            self.max_frame,
            text="—",
            font=ModernTheme.get_font(ModernTheme.FONT_SIZE_LG, "bold"),
            text_color=self.accent_color
        )
        self.max_value_label.pack(pady=(0, 2))
        
    def _draw_scale(self):
        """Отрисовка шкалы с делениями и цветовыми зонами."""
        self.scale_canvas.delete("all")
        
        width = self.scale_canvas.winfo_width()
        height = self.scale_canvas.winfo_height()
        
        if width < 50:
            # Canvas ещё не готов, отложим отрисовку
            self.after(100, self._draw_scale)
            return
        
        params = self.scale_params
        min_val = params['min']
        max_val = params['max']
        major_step = params['major_step']
        minor_ticks = params['minor_ticks']
        
        # Отступы
        left_pad = 25
        right_pad = 25
        scale_width = width - left_pad - right_pad
        
        # Высоты рисок
        major_height = 16
        minor_height = 8
        zero_height = 20  # Ноль выделен длиннее
        
        # Позиция по Y для рисок (внизу)
        base_y = height - 6
        
        # Цвета
        tick_color = ModernTheme.ON_SURFACE_VARIANT
        text_color = ModernTheme.ON_SURFACE_VARIANT
        negative_color = '#c0392b'  # Тёмно-красный для отрицательных значений
        zero_color = '#f39c12'  # Оранжевый для нуля
        
        # Расчёт шага между основными делениями в пикселях
        total_range = max_val - min_val
        major_count = int(total_range / major_step)
        major_pixel_step = scale_width / major_count
        minor_pixel_step = major_pixel_step / (minor_ticks + 1)
        
        # Рисуем цветовые зоны для Torque (отрицательная область)
        if self.title_text == 'Torque' and min_val < 0:
            # Позиция нуля
            zero_ratio = (0 - min_val) / total_range
            zero_x = left_pad + zero_ratio * scale_width
            
            # Отрицательная область (красный полупрозрачный фон)
            self.scale_canvas.create_rectangle(
                left_pad, base_y - 4,
                zero_x, base_y,
                fill='#c0392b',
                outline='',
                stipple='gray50'
            )
        
        # Рисуем все промежуточные риски (minor ticks)
        for i in range(major_count * (minor_ticks + 1) + 1):
            x = left_pad + i * minor_pixel_step
            is_major = (i % (minor_ticks + 1)) == 0
            tick_value = min_val + i * (major_step / (minor_ticks + 1))
            
            # Определяем цвет риски
            if self.title_text == 'Torque' and tick_value < 0:
                current_tick_color = negative_color
            else:
                current_tick_color = tick_color
            
            # Определяем высоту риски
            if is_major:
                # Основное деление
                if params.get('zero_highlight') and abs(tick_value) < (major_step / (minor_ticks + 1) / 2):
                    # Ноль - выделяем
                    tick_h = zero_height
                    tick_color_major = zero_color
                else:
                    tick_h = major_height
                    tick_color_major = current_tick_color
                
                # Рисуем основную риску (толще)
                self.scale_canvas.create_line(
                    x, base_y - tick_h, x, base_y,
                    fill=tick_color_major, width=2
                )
                
                # Подпись для основного деления
                if tick_value == int(tick_value):
                    label = str(int(tick_value))
                else:
                    label = f"{tick_value:.1f}"
                
                self.scale_canvas.create_text(
                    x, base_y - tick_h - 6,
                    text=label,
                    fill=text_color,
                    font=("Arial", 7),
                    anchor="s"
                )
            else:
                # Промежуточная риска (тоньше)
                self.scale_canvas.create_line(
                    x, base_y - minor_height, x, base_y,
                    fill=current_tick_color, width=1
                )
        
        # Индикатор текущего значения (треугольник)
        self.scale_indicator = self.scale_canvas.create_polygon(
            0, 0, 0, 0, 0, 0,
            fill=self.accent_color,
            outline=""
        )
        
        # Обновляем позицию индикатора
        self._update_scale_indicator()
        
    def _update_scale_indicator(self):
        """Обновление положения индикатора на шкале."""
        if not hasattr(self, 'scale_canvas') or not self.scale_canvas.winfo_exists():
            return
            
        width = self.scale_canvas.winfo_width()
        height = self.scale_canvas.winfo_height()
        
        if width < 50:
            return
        
        params = self.scale_params
        min_val = params['min']
        max_val = params['max']
        
        # Отступы
        left_pad = 25
        right_pad = 25
        scale_width = width - left_pad - right_pad
        
        # Ограничиваем значение диапазоном шкалы
        value = max(min_val, min(max_val, self.current_value))
        
        # Позиция индикатора
        ratio = (value - min_val) / (max_val - min_val)
        x = left_pad + ratio * scale_width
        
        # Рисуем треугольник-указатель
        indicator_y = 6
        size = 6
        self.scale_canvas.coords(
            self.scale_indicator,
            x, indicator_y,
            x - size, indicator_y - size,
            x + size, indicator_y - size
        )
        
    def _create_header(self):
        """Создание заголовка с индикатором."""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=16, pady=(16, 4))
        
        # Индикатор-точка (Canvas для анимации)
        self.indicator_canvas = tk.Canvas(
            self.header, 
            width=12, 
            height=12,
            bg=ModernTheme.SURFACE_VARIANT,
            highlightthickness=0
        )
        self.indicator_canvas.pack(side="left", padx=(0, 8))
        
        # Круг индикатора
        self.indicator_circle = self.indicator_canvas.create_oval(
            2, 2, 10, 10,
            fill=self.accent_color,
            outline=""
        )
        
        # Название параметра
        self.title_label = ctk.CTkLabel(
            self.header,
            text=self.title_text,
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_MD, 
                "bold"
            ),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        )
        self.title_label.pack(side="left")
        
    def _create_value_display(self):
        """Создание области отображения значения."""
        self.value_container = ctk.CTkFrame(self, fg_color="transparent")
        self.value_container.pack(expand=True, fill="both", padx=16, pady=4)
        
        # Главное значение (большое)
        self.value_label = ctk.CTkLabel(
            self.value_container,
            text="0.00",
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_4XL,
                "bold"
            ),
            text_color=self.accent_color
        )
        self.value_label.pack(expand=True)
        
        # Единица измерения
        self.unit_label = ctk.CTkLabel(
            self.value_container,
            text=self.unit,
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_MD
            ),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        )
        self.unit_label.pack()
        
    def _create_footer(self):
        """Создание подвала с максимумом."""
        # Разделительная линия
        self.separator = ctk.CTkFrame(
            self,
            height=1,
            fg_color=ModernTheme.OUTLINE_VARIANT
        )
        self.separator.pack(fill="x", padx=16, pady=(4, 8))
        
        # Подвал
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=16, pady=(0, 16))
        
        # Метка максимума
        self.max_label = ctk.CTkLabel(
            self.footer,
            text="Max: —",
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_SM
            ),
            text_color=ModernTheme.ON_SURFACE_VARIANT
        )
        self.max_label.pack(side="left")
        
        # Индикатор тренда (вверх/вниз/—)
        self.trend_label = ctk.CTkLabel(
            self.footer,
            text="",
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_SM,
                "bold"
            ),
            text_color=self.accent_color
        )
        self.trend_label.pack(side="right")
        
    def update_value(self, value: float, animate: bool = True):
        """
        Обновление текущего значения с анимацией.
        
        Args:
            value: Новое значение
            animate: Включить анимацию изменения
        """
        self.previous_value = self.current_value
        self.current_value = value

        # Форматирование значения с учетом decimal_places
        formatted = self._format_value(value)

        # Обновление значения
        self.value_label.configure(text=formatted)

        # Обновление тренда
        self._update_trend()
    
    def update_max_value(self, max_value: float):
        """
        Требование 3: Обновление максимального значения в карточке.
        
        Максимальные значения отображаются в квадратах слева
        и сбрасываются только при нажатии кнопки "Сброс".
        
        Args:
            max_value: Максимальное значение для отображения
        """
        self.max_value = max_value
        max_formatted = self._format_value(max_value)
        
        # Обновляем метку максимума в подвале
        self.max_label.configure(text=f"Max: {max_formatted}")
        
        # Обновляем крупное отображение максимума
        if self.max_unit:
            max_formatted += f" {self.max_unit}"
        self.max_value_label.configure(text=max_formatted)

    def _format_value(self, value: float) -> str:
        """
        Форматирование значения с учетом decimal_places.
        
        Args:
            value: Значение для форматирования
            
        Returns:
            Отформатированная строка
        """
        # Используем указанное количество десятичных знаков
        return f"{value:.{self.decimal_places}f}"

    def show_max_value(self):
        """Показать максимальное значение в основном поле (после остановки)."""
        formatted = self._format_value(self.max_value)
        self.value_label.configure(text=formatted)

    def show_current_value(self):
        """Вернуть отображение текущего значения."""
        formatted = self._format_value(self.current_value)
        self.value_label.configure(text=formatted)
            
    def _animate_value_change(self):
        """Анимация изменения значения (увеличение и возврат)."""
        # Увеличиваем шрифт
        self.value_label.configure(
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_4XL + 4,
                "bold"
            )
        )
        
        # Возвращаем через 100мс
        self.after(100, lambda: self.value_label.configure(
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_4XL,
                "bold"
            )
        ))
        
    def _update_trend(self):
        """Обновление индикатора тренда."""
        diff = self.current_value - self.previous_value
        
        if abs(diff) < 0.001:
            trend = "—"
        elif diff > 0:
            trend = "▲"
        else:
            trend = "▼"
            
        self.trend_label.configure(text=trend)
        
    def _pulse_indicator(self):
        """Анимация пульсации индикатора."""
        self.pulsing = True
        
        def animate():
            # Увеличение
            for i in range(5):
                size = 10 + i * 2
                offset = 6 - size // 2
                self.indicator_canvas.coords(
                    self.indicator_circle,
                    offset, offset,
                    offset + size, offset + size
                )
                time.sleep(0.02)
                
            # Уменьшение
            for i in range(5):
                size = 16 - i * 2
                offset = 6 - size // 2
                self.indicator_canvas.coords(
                    self.indicator_circle,
                    offset, offset,
                    offset + size, offset + size
                )
                time.sleep(0.02)
                
            self.pulsing = False
            
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=animate, daemon=True)
        thread.start()
        
    def reset_max(self):
        """
        Требование 3: Сброс максимального значения.
        
        Вызывается только при нажатии кнопки "Сброс".
        Очищает отображение максимальных значений в карточке.
        """
        self.max_value = 0.0
        self.max_label.configure(text="Max: —")
        self.max_value_label.configure(text="—")
        
    def update_theme_colors(self, colors: dict):
        """Обновление цветов карточки при смене темы.
        
        Args:
            colors: Словарь цветов темы
        """
        # Обновляем фон карточки
        self.configure(
            fg_color=colors['SURFACE_VARIANT'],
            border_color=colors['OUTLINE_VARIANT']
        )
        
        # Обновляем цвета заголовка и значения
        self.title_label.configure(text_color=colors['ON_SURFACE_VARIANT'])
        self.value_label.configure(text_color=self.accent_color)
        self.unit_label.configure(text_color=colors['ON_SURFACE_VARIANT'])
        self.max_label.configure(text_color=colors['ON_SURFACE_VARIANT'])
        self.trend_label.configure(text_color=self.accent_color)
        
        # Обновляем цвета для max отображения
        self.max_title_label.configure(text_color=colors['ON_SURFACE_VARIANT'])
        self.max_value_label.configure(text_color=self.accent_color)
        
        # Обновляем цвет разделителя
        self.separator.configure(fg_color=colors['OUTLINE_VARIANT'])
        
        # Обновляем цвет индикатора
        self.indicator_canvas.configure(bg=colors['SURFACE_VARIANT'])
        
    def highlight(self, active: bool = True):
        """
        Подсветка карточки (например, при hover или активности).
        
        Args:
            active: Включить или выключить подсветку
        """
        if active:
            self.configure(
                border_color=self.accent_color,
                border_width=2
            )
        else:
            self.configure(
                border_color=ModernTheme.OUTLINE_VARIANT,
                border_width=1
            )


class StatusBadge(ctk.CTkFrame):
    """
    Значок статуса с индикатором.
    Используется в хедере для показа состояния подключения.
    """
    
    def __init__(self, parent, status_text: str = "DISCONNECTED",
                 is_active: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.status_text = status_text
        self.is_active = is_active
        
        # Настройка стиля
        self.configure(
            fg_color=ModernTheme.SURFACE_CONTAINER,
            corner_radius=ModernTheme.RADIUS_FULL,
            height=32
        )
        self.pack_propagate(False)
        
        # Индикатор
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ModernTheme.get_font(10),
            text_color=ModernTheme.SECONDARY if is_active else ModernTheme.ERROR
        )
        self.dot.pack(side="left", padx=(12, 4))
        
        # Текст статуса
        self.text_label = ctk.CTkLabel(
            self,
            text=status_text,
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_XS,
                "bold"
            ),
            text_color=ModernTheme.ON_SURFACE
        )
        self.text_label.pack(side="left", padx=(0, 12))
        
    def set_status(self, text: str, is_active: bool):
        """
        Обновление статуса.
        
        Args:
            text: Новый текст статуса
            is_active: Активен ли статус (зеленый/красный)
        """
        self.status_text = text
        self.is_active = is_active
        
        self.text_label.configure(text=text.upper())
        self.dot.configure(
            text_color=ModernTheme.SECONDARY if is_active else ModernTheme.ERROR
        )


class ActionButton(ctk.CTkButton):
    """
    Кнопка действия с Material Design 3 стилем.
    Поддерживает варианты: primary, secondary, tertiary.
    """
    
    def __init__(self, parent, text: str, variant: str = "primary",
                 icon: str = "", command: Optional[Callable] = None, **kwargs):
        """
        Создание кнопки.
        
        Args:
            parent: Родительский виджет
            text: Текст кнопки
            variant: Стиль кнопки ("primary", "secondary", "tertiary")
            icon: Иконка (эмодзи или символ)
            command: Функция при нажатии
        """
        self.variant = variant
        self.icon = icon
        
        # Текст с иконкой
        full_text = f"{icon}  {text}" if icon else text
        
        # Настройки в зависимости от варианта
        if variant == "primary":
            fg_color = ModernTheme.PRIMARY
            hover_color = ModernTheme.adjust_brightness(ModernTheme.PRIMARY, 1.1)
            border_width = 0
            text_color = ModernTheme.ON_PRIMARY
            height = 44
            
        elif variant == "secondary":
            fg_color = ModernTheme.SURFACE
            hover_color = ModernTheme.SURFACE_CONTAINER
            border_width = 1
            text_color = ModernTheme.ON_SURFACE
            height = 44
            
        else:  # tertiary
            fg_color = ModernTheme.SURFACE
            hover_color = ModernTheme.SURFACE_CONTAINER
            border_width = 0
            text_color = ModernTheme.ON_SURFACE_VARIANT
            height = 36
            
        super().__init__(
            parent,
            text=full_text,
            command=command,
            font=ModernTheme.get_font(
                ModernTheme.FONT_SIZE_MD,
                "bold" if variant == "primary" else "normal"
            ),
            fg_color=fg_color,
            hover_color=hover_color,
            border_width=border_width,
            border_color=ModernTheme.OUTLINE if variant == "secondary" else ModernTheme.SURFACE,
            text_color=text_color,
            corner_radius=ModernTheme.RADIUS_FULL,
            height=height,
            **kwargs
        )
