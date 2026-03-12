#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Профессиональный real-time график для динамометрического стенда DYN-200.
Три Y-оси: Speed (левая), Torque (средняя), Power (правая).
"""

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator, AutoMinorLocator
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from gui.modern_theme import ModernTheme


class AxisRangeDialog:
    """Диалог настройки диапазонов осей графика"""
    
    def __init__(self, parent, plot_manager):
        self.parent = parent
        self.plot_manager = plot_manager
        self.result = None
        
        # Создаем окно
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Настройка диапазонов осей")
        self.window.geometry("450x600")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрируем
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Текущие значения
        self.autoscale_torque = tk.BooleanVar(value=plot_manager.autoscale_torque)
        self.autoscale_speed = tk.BooleanVar(value=plot_manager.autoscale_speed)
        self.autoscale_power = tk.BooleanVar(value=plot_manager.autoscale_power)
        self.autoscale_time = tk.BooleanVar(value=plot_manager.autoscale_time)
        
        # Значения диапазонов (StringVar для предотвращения TclError при пустом вводе)
        self.torque_min = tk.StringVar(value=str(plot_manager.torque_range[0]))
        self.torque_max = tk.StringVar(value=str(plot_manager.torque_range[1]))
        self.speed_min = tk.StringVar(value=str(plot_manager.speed_range[0]))
        self.speed_max = tk.StringVar(value=str(plot_manager.speed_range[1]))
        self.power_min = tk.StringVar(value=str(plot_manager.power_range[0]))
        self.power_max = tk.StringVar(value=str(plot_manager.power_range[1]))
        self.time_min = tk.StringVar(value=str(plot_manager.time_range[0]))
        self.time_max = tk.StringVar(value=str(plot_manager.time_range[1]))

        # Настройка шкалы времени (количество точек/секунд на оси X)
        self.time_window = tk.StringVar(value=str(getattr(plot_manager, 'time_window_seconds', 60)))

        # Регистрируем функцию валидации
        self.vcmd = (self.window.register(self._validate_numeric), '%P')
        
        self._create_ui()

    def _validate_numeric(self, value):
        """Проверяет что значение является числом или пустой строкой"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _create_ui(self):
        """Создание интерфейса диалога"""
        colors = self._get_theme_colors()
        
        # Главный контейнер
        main_frame = ctk.CTkFrame(
            self.window,
            fg_color=colors['bg'],
            corner_radius=12
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок (вне прокрутки)
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header,
            text="📊 Настройка диапазонов осей",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors['text']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header,
            text="Задайте фиксированные пределы или включите авто-масштабирование",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary']
        ).pack(anchor="w", pady=(4, 0))
        
        # Разделитель
        separator = ctk.CTkFrame(main_frame, height=1, fg_color=colors['outline'])
        separator.pack(fill="x", padx=20, pady=10)
        
        # Контейнер с прокруткой для секций осей
        scroll_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent",
            height=300,
            scrollbar_button_color=colors['primary'],
            scrollbar_button_hover_color=self._adjust_brightness(colors['primary'], 1.1)
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Секция Speed (основная ось - первая в списке)
        self._create_axis_section(
            scroll_frame, "Speed (об/мин)",
            self.autoscale_speed,
            self.speed_min, self.speed_max,
            self.plot_manager.COLOR_SPEED
        )

        # Секция Torque
        self._create_axis_section(
            scroll_frame, "Torque (Н·м)",
            self.autoscale_torque,
            self.torque_min, self.torque_max,
            self.plot_manager.COLOR_TORQUE
        )

        # Секция Power
        self._create_axis_section(
            scroll_frame, "Power (Вт)",
            self.autoscale_power,
            self.power_min, self.power_max,
            self.plot_manager.COLOR_POWER
        )
        
        # Секция настройки шкалы времени
        self._create_time_section(scroll_frame)
        
        # Разделитель перед кнопками (вне прокрутки)
        separator2 = ctk.CTkFrame(main_frame, height=1, fg_color=colors['outline'])
        separator2.pack(fill="x", padx=20, pady=15)
        
        # Кнопки (вне прокрутки)
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            btn_frame,
            text="Применить",
            command=self._apply,
            width=140,
            height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=colors['primary'],
            hover_color=self._adjust_brightness(colors['primary'], 1.1),
            text_color="white"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="Сбросить (Auto)",
            command=self._reset_to_auto,
            width=140,
            height=36,
            font=ctk.CTkFont(size=14),
            fg_color=colors['secondary'],
            hover_color=self._adjust_brightness(colors['secondary'], 1.1),
            text_color="white"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="Отмена",
            command=self.window.destroy,
            width=100,
            height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=colors['surface_hover'],
            text_color=colors['text_secondary']
        ).pack(side="right")
        
    def _create_axis_section(self, parent, title, autoscale_var, min_var, max_var, color):
        """Создание секции для оси"""
        colors = self._get_theme_colors()
        
        section = ctk.CTkFrame(parent, fg_color=colors['surface'], corner_radius=8)
        section.pack(fill="x", padx=20, pady=8)
        
        # Заголовок с индикатором цвета
        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        # Цветной индикатор
        indicator = ctk.CTkFrame(header, width=4, height=20, fg_color=color, corner_radius=2)
        indicator.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=colors['text']
        ).pack(side="left")
        
        # Чекбокс автомасштабирования
        ctk.CTkCheckBox(
            section,
            text="Авто-масштабирование",
            variable=autoscale_var,
            font=ctk.CTkFont(size=12),
            text_color=colors['text'],
            fg_color=colors['primary'],
            border_color=colors['outline'],
            hover_color=self._adjust_brightness(colors['primary'], 1.1),
            corner_radius=6
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Поля Min/Max
        range_frame = ctk.CTkFrame(section, fg_color="transparent")
        range_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # Min
        min_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
        min_frame.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(
            min_frame,
            text="Min:",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary'],
            width=40
        ).pack(side="left")
        
        ctk.CTkEntry(
            min_frame,
            textvariable=min_var,
            width=80,
            font=ctk.CTkFont(size=12),
            fg_color=colors['input_bg'],
            border_color=colors['outline'],
            validate="key",
            validatecommand=self.vcmd
        ).pack(side="left", padx=(5, 0))
        
        # Max
        max_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
        max_frame.pack(side="left")
        
        ctk.CTkLabel(
            max_frame,
            text="Max:",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary'],
            width=40
        ).pack(side="left")
        
        ctk.CTkEntry(
            max_frame,
            textvariable=max_var,
            width=80,
            font=ctk.CTkFont(size=12),
            fg_color=colors['input_bg'],
            border_color=colors['outline'],
            validate="key",
            validatecommand=self.vcmd
        ).pack(side="left", padx=(5, 0))
        
    def _create_time_section(self, parent):
        """Создание секции для настройки шкалы времени"""
        colors = self._get_theme_colors()
        
        section = ctk.CTkFrame(parent, fg_color=colors['surface'], corner_radius=8)
        section.pack(fill="x", padx=20, pady=8)
        
        # Заголовок с индикатором цвета
        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        # Цветной индикатор (синий для времени)
        indicator = ctk.CTkFrame(header, width=4, height=20, fg_color=self.plot_manager.COLOR_SPEED, corner_radius=2)
        indicator.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            header,
            text="Шкала времени",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=colors['text']
        ).pack(side="left")
        
        # Описание
        ctk.CTkLabel(
            section,
            text="Количество секунд для отображения на оси X",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary']
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Поле ввода времени
        time_frame = ctk.CTkFrame(section, fg_color="transparent")
        time_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(
            time_frame,
            text="Окно времени:",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary'],
            width=100
        ).pack(side="left")
        
        ctk.CTkEntry(
            time_frame,
            textvariable=self.time_window,
            width=80,
            font=ctk.CTkFont(size=12),
            fg_color=colors['input_bg'],
            border_color=colors['outline'],
            validate="key",
            validatecommand=self.vcmd
        ).pack(side="left", padx=(5, 0))
        
        ctk.CTkLabel(
            time_frame,
            text="сек",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary']
        ).pack(side="left", padx=(10, 0))
        
    def _get_theme_colors(self):
        """Получение цветов текущей темы (только темная тема)"""
        return {
            'bg': ModernTheme.BACKGROUND,
            'surface': ModernTheme.SURFACE_VARIANT,
            'primary': ModernTheme.PRIMARY,
            'secondary': ModernTheme.SECONDARY,
            'text': ModernTheme.ON_SURFACE,
            'text_secondary': ModernTheme.ON_SURFACE_VARIANT,
            'outline': ModernTheme.OUTLINE,
            'input_bg': ModernTheme.SURFACE_CONTAINER,
            'surface_hover': ModernTheme.SURFACE_CONTAINER_HIGH
        }
    
    def _adjust_brightness(self, hex_color: str, factor: float) -> str:
        """Изменение яркости цвета"""
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def _apply(self):
        """Применение настроек"""
        try:
            # Валидация и применение диапазонов
            self.plot_manager.autoscale_torque = self.autoscale_torque.get()
            self.plot_manager.autoscale_speed = self.autoscale_speed.get()
            self.plot_manager.autoscale_power = self.autoscale_power.get()

            # Обработка диапазонов с защитой от пустых значений
            try:
                torque_min = float(self.torque_min.get()) if self.torque_min.get() else self.plot_manager.INITIAL_TORQUE_MIN
            except ValueError:
                torque_min = self.plot_manager.INITIAL_TORQUE_MIN

            try:
                torque_max = float(self.torque_max.get()) if self.torque_max.get() else self.plot_manager.INITIAL_TORQUE_MAX
            except ValueError:
                torque_max = self.plot_manager.INITIAL_TORQUE_MAX

            try:
                speed_min = float(self.speed_min.get()) if self.speed_min.get() else self.plot_manager.INITIAL_SPEED_MIN
            except ValueError:
                speed_min = self.plot_manager.INITIAL_SPEED_MIN

            try:
                speed_max = float(self.speed_max.get()) if self.speed_max.get() else self.plot_manager.INITIAL_SPEED_MAX
            except ValueError:
                speed_max = self.plot_manager.INITIAL_SPEED_MAX

            try:
                power_min = float(self.power_min.get()) if self.power_min.get() else self.plot_manager.INITIAL_POWER_MIN
            except ValueError:
                power_min = self.plot_manager.INITIAL_POWER_MIN

            try:
                power_max = float(self.power_max.get()) if self.power_max.get() else self.plot_manager.INITIAL_POWER_MAX
            except ValueError:
                power_max = self.plot_manager.INITIAL_POWER_MAX

            self.plot_manager.torque_range = (torque_min, torque_max)
            self.plot_manager.speed_range = (speed_min, speed_max)
            self.plot_manager.power_range = (power_min, power_max)

            # Применяем настройку временного окна
            try:
                time_window = float(self.time_window.get()) if self.time_window.get() else 60
            except ValueError:
                time_window = 60

            if time_window >= 5:  # Минимум 5 секунд
                self.plot_manager.time_window_seconds = time_window
                # Обновляем time_range для оси X
                self.plot_manager.time_range = (0, time_window)

            # Применяем диапазоны к осям
            self.plot_manager.apply_axis_ranges()

            self.result = True
            self.window.destroy()
        except Exception as e:
            # Показать ошибку валидации
            messagebox.showerror("Ошибка", f"Некорректное значение: {e}")
    
    def _reset_to_auto(self):
        """Сброс к авто-масштабированию"""
        self.autoscale_torque.set(True)
        self.autoscale_speed.set(True)
        self.autoscale_power.set(True)
        
        self.plot_manager.autoscale_torque = True
        self.plot_manager.autoscale_speed = True
        self.plot_manager.autoscale_power = True
        
        # Применяем
        self.plot_manager.apply_axis_ranges()
        self.result = True
        self.window.destroy()


# Встроить диалог в конец файла или рядом с PlotManager


class PlotManager:
    """
    Менеджер для создания и обновления real-time графика
    с тремя осями Y для системы мониторинга динамометрического стенда.
    """
    
    # Цвета по требованиям задачи
    COLOR_TORQUE = '#e74c3c'      # Красный - крутящий момент
    COLOR_SPEED = '#3498db'       # Синий - скорость
    COLOR_POWER = '#f1c40f'       # Жёлтый - мощность
    
    # Тёмная тема
    BG_COLOR = '#1a1a1a'
    FG_COLOR = '#2c2c2c'
    TEXT_COLOR = '#e4e6eb'
    GRID_COLOR = '#4b5563'
    GRID_ALPHA = 0.25
    
    # Параметры линий
    LINE_WIDTH = 2.2
    MARKER_SIZE = 4
    
    # Размер rolling buffer (уменьшен для оптимизации производительности)
    MAX_POINTS = 200
    
    # Максимальное количество меток на осях (для динамического расчета)
    MAX_TICKS_X = 6               # Меток на оси X
    MAX_TICKS_Y = 8               # Меток на оси Y
    
    # Начальные пределы при мало данных (< 20 точек)
    INITIAL_TORQUE_MIN = -10
    INITIAL_TORQUE_MAX = 50
    INITIAL_SPEED_MIN = 0
    INITIAL_SPEED_MAX = 500
    INITIAL_POWER_MIN = 0
    INITIAL_POWER_MAX = 5000      # 5000 Вт = 5 кВт (увеличено для больших значений)
    
    def __init__(self, config=None, state=None):
        self.config = config
        self.state = state
        
        self.fig = None
        self.canvas = None
        
        # Три оси Y
        self.ax_speed = None        # Левая ось (основная) - Speed (шаг 50 об/мин)
        self.ax_torque = None       # Средняя ось - Torque (шаг 1 Н·м)
        self.ax_power = None        # Правая ось - Power (шаг 50 Вт)
        
        # Линии графиков
        self.line_torque = None
        self.line_speed = None
        self.line_power = None
        
        # Видимость линий
        self.line_visibility = {
            'torque': True,
            'speed': True,
            'power': True
        }
        
        # Текстовые метки для текущих значений
        self.value_texts = {}

        # Аннотации для ключевых точек
        self.annotations = {}
        
        # Данные для rolling buffer
        self.timestamps = []
        self.torque_data = []
        self.speed_data = []
        self.power_data = []
        
        # Настройки диапазонов осей (по умолчанию ВКЛЮЧЕН автоскейл)
        self.autoscale_torque = True
        self.autoscale_speed = True
        self.autoscale_power = True
        self.autoscale_time = False
        self.torque_range = (self.INITIAL_TORQUE_MIN, self.INITIAL_TORQUE_MAX)
        self.speed_range = (self.INITIAL_SPEED_MIN, self.INITIAL_SPEED_MAX)
        self.power_range = (self.INITIAL_POWER_MIN, self.INITIAL_POWER_MAX)
        self.time_range = (0, 10)  # Начальный диапазон времени (с)
        self.time_window_seconds = 60  # Окно времени на графике (секунд)
        
        # Родительский фрейм для кнопки
        self.parent_frame = None
        self.range_button = None
    
    def create_plots(self, parent_frame):
        """Создание графика с тремя осями Y"""
        # Очищаем старые графики
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # Создаём фигуру с тёмным фоном
        self.fig = Figure(
            figsize=(10, 6),
            dpi=100,
            facecolor=self.BG_COLOR,
            edgecolor=self.BG_COLOR
        )
        
        self._create_triple_axis_plot()
        
        # Создаем контейнер для графика и кнопки
        self.parent_frame = parent_frame
        main_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        main_container.pack(fill='both', expand=True)
        
        # Canvas с графиком
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Кнопка настройки диапазонов
        self._create_range_button(main_container)
        
        return self.canvas
    
    def _create_range_button(self, parent):
        """Создание кнопки настройки диапазонов"""
        colors = self._get_theme_colors()
        
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        btn_frame.pack(fill='x', padx=10, pady=(5, 10))
        btn_frame.pack_propagate(False)
        
        self.range_button = ctk.CTkButton(
            btn_frame,
            text="⚙️ Настройка диапазонов",
            command=self._open_range_dialog,
            width=200,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=colors['primary'],
            hover_color=self._adjust_color_brightness(colors['primary'], 1.1),
            text_color="white",
            corner_radius=8
        )
        self.range_button.pack(side="right")
    
    def _get_theme_colors(self):
        """Получение цветов текущей темы"""
        return {
            'primary': ModernTheme.PRIMARY,
            'secondary': ModernTheme.SECONDARY,
            'bg': ModernTheme.BACKGROUND,
            'surface': ModernTheme.SURFACE,
            'text': ModernTheme.ON_SURFACE,
            'text_secondary': ModernTheme.ON_SURFACE_VARIANT,
            'outline': ModernTheme.OUTLINE
        }
    
    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """Изменение яркости цвета"""
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _open_range_dialog(self):
        """Открытие диалога настройки диапазонов"""
        if self.parent_frame:
            dialog = AxisRangeDialog(self.parent_frame, self)
    
    def apply_axis_ranges(self):
        """Применение сохраненных диапазонов к осям"""
        if self.ax_speed:
            if self.autoscale_speed:
                self.ax_speed.autoscale(True)
            else:
                self.ax_speed.set_ylim(self.speed_range[0], self.speed_range[1])
                self.ax_speed.autoscale(False)

        if self.ax_torque:
            if self.autoscale_torque:
                self.ax_torque.autoscale(True)
            else:
                self.ax_torque.set_ylim(self.torque_range[0], self.torque_range[1])
                self.ax_torque.autoscale(False)

        if self.ax_power:
            if self.autoscale_power:
                self.ax_power.autoscale(True)
            else:
                self.ax_power.set_ylim(self.power_range[0], self.power_range[1])
                self.ax_power.autoscale(False)

        # Применяем диапазон времени к оси X
        if self.ax_speed and hasattr(self, 'time_range'):
            self.ax_speed.set_xlim(self.time_range[0], self.time_range[1])

        # Принудительно перерисовываем график
        if self.canvas:
            self.canvas.draw()
    
    def _create_triple_axis_plot(self):
        """Создание графика с тремя осями Y"""
        # Основная ось - Speed (самая левая)
        # Область графика увеличена для размещения легенды снизу
        self.ax_speed = self.fig.add_axes([0.10, 0.18, 0.88, 0.75])
        self.ax_speed.set_facecolor(self.BG_COLOR)

        # Заголовок графика
        self.ax_speed.set_title(
            "Мониторинг параметров DYN-200",
            fontsize=14, fontweight='bold',
            color=self.TEXT_COLOR, pad=15
        )

        # Настройка оси X с подписью с единицами измерения
        self.ax_speed.set_xlabel("Время (с)", color=self.TEXT_COLOR, fontsize=11, fontweight='bold')
        self.ax_speed.tick_params(axis='x', colors=self.TEXT_COLOR, labelsize=10)
        self.ax_speed.xaxis.label.set_color(self.TEXT_COLOR)
        # Динамические метки на оси X (максимум 6 меток)
        self.ax_speed.xaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_X, integer=False))
        self.ax_speed.xaxis.set_minor_locator(AutoMinorLocator(5))
        # Включаем отображение minor ticks
        self.ax_speed.tick_params(axis='x', which='minor', length=3, color=self.TEXT_COLOR)

        # Левая ось Y - Speed (синяя)
        self.ax_speed.set_ylabel(
            "Speed (об/мин)",
            color=self.COLOR_SPEED,
            fontsize=11,
            fontweight='bold'
        )
        self.ax_speed.tick_params(axis='y', colors=self.COLOR_SPEED, labelsize=9)
        self.ax_speed.yaxis.label.set_color(self.COLOR_SPEED)
        # Динамические метки на оси Speed (максимум 8 меток)
        self.ax_speed.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        self.ax_speed.yaxis.set_minor_locator(AutoMinorLocator(4))
        # Включаем отображение minor ticks
        self.ax_speed.tick_params(axis='y', which='minor', length=2, color=self.COLOR_SPEED)

        # Сетка - улучшенная видимость на тёмном фоне
        # Основная сетка
        self.ax_speed.grid(True, alpha=0.4, color='#9e9e9e',
                           linestyle='-', linewidth=0.8, which='major')
        # Вспомогательная сетка
        self.ax_speed.grid(True, alpha=0.15, color='#e0e0e0',
                           linestyle=':', linewidth=0.3, which='minor')

        # Линия Speed (сплошная линия)
        self.line_speed, = self.ax_speed.plot(
            [], [],
            color=self.COLOR_SPEED,
            linewidth=self.LINE_WIDTH,
            linestyle='-',
            alpha=0.9,
            label='Speed',
            marker='o',
            markersize=self.MARKER_SIZE,
            markevery=10
        )

        # Вторая ось Y - Torque (смещённая внутрь, offset=50)
        self.ax_torque = self.ax_speed.twinx()
        self.ax_torque.spines['right'].set_position(('outward', 50))
        self.ax_torque.set_facecolor('none')

        self.ax_torque.set_ylabel(
            "Torque (Н·м)",
            color=self.COLOR_TORQUE,
            fontsize=11,
            fontweight='bold'
        )
        self.ax_torque.tick_params(axis='y', colors=self.COLOR_TORQUE, labelsize=9)
        self.ax_torque.yaxis.label.set_color(self.COLOR_TORQUE)
        # Динамические метки на оси Torque (максимум 8 меток)
        self.ax_torque.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        self.ax_torque.yaxis.set_minor_locator(AutoMinorLocator(4))
        # Включаем отображение minor ticks на оси Y
        self.ax_torque.tick_params(axis='y', which='minor', length=2, color=self.COLOR_TORQUE)

        # Линия Torque (пунктирная линия)
        self.line_torque, = self.ax_torque.plot(
            [], [],
            color=self.COLOR_TORQUE,
            linewidth=self.LINE_WIDTH,
            linestyle='--',
            alpha=0.9,
            label='Torque',
            marker='s',
            markersize=self.MARKER_SIZE,
            markevery=10
        )

        # Третья ось Y - Power (самая правая, offset=100)
        self.ax_power = self.ax_speed.twinx()
        self.ax_power.spines['right'].set_position(('outward', 100))
        self.ax_power.set_facecolor('none')

        self.ax_power.set_ylabel(
            "Power (Вт)",
            color=self.COLOR_POWER,
            fontsize=11,
            fontweight='bold'
        )
        self.ax_power.tick_params(axis='y', colors=self.COLOR_POWER, labelsize=9)
        self.ax_power.yaxis.label.set_color(self.COLOR_POWER)
        # Динамические метки на оси Power (максимум 8 меток)
        self.ax_power.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        self.ax_power.yaxis.set_minor_locator(AutoMinorLocator(4))
        # Включаем отображение minor ticks
        self.ax_power.tick_params(axis='y', which='minor', length=2, color=self.COLOR_POWER)

        # Линия Power (точка-тире)
        self.line_power, = self.ax_power.plot(
            [], [],
            color=self.COLOR_POWER,
            linewidth=self.LINE_WIDTH,
            linestyle='-.',
            alpha=0.9,
            label='Power',
            marker='^',
            markersize=self.MARKER_SIZE,
            markevery=10
        )

        # Настройка цвета осей - КРИТИЧЕСКИ ВАЖНО
        # Настраиваем цвета spine для каждой оси
        self.ax_speed.spines['bottom'].set_color(self.GRID_COLOR)
        self.ax_speed.spines['top'].set_visible(False)
        self.ax_speed.spines['left'].set_color(self.COLOR_SPEED)   # Левая ось = Speed = синий
        self.ax_speed.spines['right'].set_visible(False)  # Скрываем правую spine основной оси

        self.ax_torque.spines['right'].set_color(self.COLOR_TORQUE)  # Правая ось Torque = красный
        self.ax_torque.spines['top'].set_visible(False)
        self.ax_torque.spines['left'].set_visible(False)  # Скрываем левую spine Torque

        self.ax_power.spines['right'].set_color(self.COLOR_POWER)   # Правая ось Power = жёлтый
        self.ax_power.spines['top'].set_visible(False)
        self.ax_power.spines['left'].set_visible(False)  # Скрываем левую spine Power

        # Создаём легенду
        self._create_legend()

        # Устанавливаем начальные пределы
        self._set_initial_limits()
    
    def _create_legend(self):
        """Создание легенды под графиком с рамкой и тенью"""
        from matplotlib.lines import Line2D

        # Легенда с соответствующими стилями линий
        # Порядок: Speed (синий), Torque (красный), Power (жёлтый)
        legend_elements = [
            Line2D([0], [0], color=self.COLOR_SPEED, lw=self.LINE_WIDTH, linestyle='-', label='Speed (об/мин)'),
            Line2D([0], [0], color=self.COLOR_TORQUE, lw=self.LINE_WIDTH, linestyle='--', label='Torque (Н·м)'),
            Line2D([0], [0], color=self.COLOR_POWER, lw=self.LINE_WIDTH, linestyle='-.', label='Power (Вт)')
        ]

        self.fig.legend(
            handles=legend_elements,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.02),
            ncol=3,
            facecolor=self.FG_COLOR,
            edgecolor=self.GRID_COLOR,
            labelcolor=self.TEXT_COLOR,
            fontsize=10,
            framealpha=0.95,
            fancybox=True,
            shadow=True
        )
    
    def _set_initial_limits(self):
        """Установка начальных пределов осей с учетом сохраненных диапазонов"""
        # Всегда используем сохраненные диапазоны (фиксированные значения)
        # Автоскейл отключен по умолчанию
        self.ax_speed.set_ylim(self.speed_range[0], self.speed_range[1])
        self.ax_torque.set_ylim(self.torque_range[0], self.torque_range[1])
        self.ax_power.set_ylim(self.power_range[0], self.power_range[1])
        self.ax_speed.set_xlim(0, 10)

        # Отключаем autoscale если заданы фиксированные диапазоны (по умолчанию выключен)
        self.ax_speed.autoscale(self.autoscale_speed)
        self.ax_torque.autoscale(self.autoscale_torque)
        self.ax_power.autoscale(self.autoscale_power)
    
    def update_plots(self, timestamps, torque_data, speed_data, power_data):
        """
        Обновление графика с новыми данными.
        
        Args:
            timestamps: список временных меток (в секундах)
            torque_data: список значений крутящего момента (Н·м)
            speed_data: список значений скорости (об/мин)
            power_data: список значений мощности (кВт)
        """
        if not timestamps or len(timestamps) == 0:
            return
        
        # Сохраняем данные
        self.timestamps = list(timestamps)
        self.torque_data = list(torque_data) if torque_data else []
        self.speed_data = list(speed_data) if speed_data else []
        self.power_data = list(power_data) if power_data else []
        
        # Обновляем данные линий
        if self.line_torque and len(self.torque_data) == len(self.timestamps):
            self.line_torque.set_data(self.timestamps, self.torque_data)
        
        if self.line_speed and len(self.speed_data) == len(self.timestamps):
            self.line_speed.set_data(self.timestamps, self.speed_data)
        
        if self.line_power and len(self.power_data) == len(self.timestamps):
            self.line_power.set_data(self.timestamps, self.power_data)
        
        # Обновляем масштаб осей
        self._update_axis_limits()

        # Перерисовываем
        self.canvas.draw_idle()
    
    def _update_annotations(self):
        """Обновление аннотаций с текущими значениями у последней точки каждой линии"""
        if not self.timestamps or len(self.timestamps) == 0:
            return

        # Удаляем старые аннотации
        for ann in self.annotations.values():
            if ann in self.ax_speed.texts:
                ann.remove()
        self.annotations.clear()

        # Получаем последнюю точку
        x = self.timestamps[-1]
        offset_x = 0.5  # смещение по X в секундах

        # Получаем пределы осей для правильного позиционирования аннотаций
        speed_ymin, speed_ymax = self.ax_speed.get_ylim()
        torque_ymin, torque_ymax = self.ax_torque.get_ylim()
        power_ymin, power_ymax = self.ax_power.get_ylim()

        # Аннотация для Speed (основная ось - ax_speed)
        if self.speed_data and len(self.speed_data) > 0:
            y_speed = self.speed_data[-1]
            # Проверяем, что значение в пределах оси
            if speed_ymin <= y_speed <= speed_ymax:
                self.annotations['speed'] = self.ax_speed.annotate(
                    f'{y_speed:.0f}',
                    xy=(x, y_speed),
                    xytext=(x + offset_x, y_speed),
                    fontsize=9,
                    color=self.COLOR_SPEED,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor=self.BG_COLOR, edgecolor=self.COLOR_SPEED, alpha=0.8)
                )

        # Аннотация для Torque (ось ax_torque - используем transform для правильного позиционирования)
        if self.torque_data and len(self.torque_data) > 0:
            y_torque = self.torque_data[-1]
            # Проверяем, что значение в пределах оси
            if torque_ymin <= y_torque <= torque_ymax:
                # Аннотация создаётся на ax_torque с правильной системой координат
                self.annotations['torque'] = self.ax_torque.annotate(
                    f'{y_torque:.1f}',
                    xy=(x, y_torque),
                    xytext=(x + offset_x, y_torque),
                    fontsize=9,
                    color=self.COLOR_TORQUE,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor=self.BG_COLOR, edgecolor=self.COLOR_TORQUE, alpha=0.8)
                )

        # Аннотация для Power (ось ax_power)
        if self.power_data and len(self.power_data) > 0:
            y_power = self.power_data[-1]
            # Проверяем, что значение в пределах оси
            if power_ymin <= y_power <= power_ymax:
                self.annotations['power'] = self.ax_power.annotate(
                    f'{y_power:.0f}',
                    xy=(x, y_power),
                    xytext=(x + offset_x, y_power),
                    fontsize=9,
                    color=self.COLOR_POWER,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor=self.BG_COLOR, edgecolor=self.COLOR_POWER, alpha=0.8)
                )

    def _update_axis_limits(self):
        """Обновление пределов осей с учетом настроек автоскейла"""
        if not self.timestamps:
            return

        n_points = len(self.timestamps)

        # Ось X - время (скользящее окно)
        if n_points > 1:
            x_max = self.timestamps[-1]
            x_min = max(0, x_max - self.time_window_seconds)
            self.ax_speed.set_xlim(x_min, x_max)

        # Если мало данных (< 20 точек) - используем начальные пределы
        if n_points < 20:
            self._set_initial_limits()
            return

        # Ось Speed (левая, основная) - автоскейл только если включен
        if self.autoscale_speed and self.speed_data:
            speed_min = min(self.speed_data)
            speed_max = max(self.speed_data)
            
            # Добавляем отступ 5% сверху и снизу
            speed_range = speed_max - speed_min if speed_max != speed_min else 100
            s_min = max(0, speed_min - speed_range * 0.05)
            s_max = speed_max + speed_range * 0.05
            
            # Округляем для красоты
            s_min = int(s_min / 100) * 100 if s_min > 100 else int(s_min / 10) * 10
            s_max = int(s_max / 100 + 1) * 100 if s_max > 100 else int(s_max / 10 + 1) * 10

            cur_min, cur_max = self.ax_speed.get_ylim()
            # Обновляем только если изменение значительное (>5%)
            if abs(s_min - cur_min) > speed_range * 0.05 or abs(s_max - cur_max) > speed_range * 0.05:
                self.ax_speed.set_ylim(s_min, s_max)
        elif not self.autoscale_speed:
            # Используем фиксированные значения
            self.ax_speed.set_ylim(self.speed_range[0], self.speed_range[1])

        # Ось Torque (средняя) - автоскейл только если включен
        if self.autoscale_torque and self.torque_data:
            torque_min = min(self.torque_data)
            torque_max = max(self.torque_data)
            
            # Добавляем отступ 5% сверху и снизу
            torque_range = torque_max - torque_min if torque_max != torque_min else 10
            t_min = torque_min - torque_range * 0.05
            t_max = torque_max + torque_range * 0.05
            
            # Округляем для красоты
            t_min = int(t_min / 10) * 10 if abs(t_min) > 10 else int(t_min)
            t_max = int(t_max / 10 + 1) * 10 if abs(t_max) > 10 else int(t_max + 1)

            cur_min, cur_max = self.ax_torque.get_ylim()
            # Обновляем только если изменение значительное (>5%)
            if abs(t_min - cur_min) > torque_range * 0.05 or abs(t_max - cur_max) > torque_range * 0.05:
                self.ax_torque.set_ylim(t_min, t_max)
        elif not self.autoscale_torque:
            # Используем фиксированные значения
            self.ax_torque.set_ylim(self.torque_range[0], self.torque_range[1])

        # Ось Power (правая) - автоскейл только если включен
        if self.autoscale_power and self.power_data:
            power_min = min(self.power_data)
            power_max = max(self.power_data)
            
            # Добавляем отступ 5% сверху и снизу
            power_range = power_max - power_min if power_max != power_min else 100
            p_min = max(0, power_min - power_range * 0.05)
            p_max = power_max + power_range * 0.05
            
            # Округляем для красоты
            p_min = int(p_min / 100) * 100 if p_min > 100 else int(p_min / 10) * 10
            p_max = int(p_max / 100 + 1) * 100 if p_max > 100 else int(p_max / 10 + 1) * 10

            cur_min, cur_max = self.ax_power.get_ylim()
            # Обновляем только если изменение значительное (>5%)
            if abs(p_min - cur_min) > power_range * 0.05 or abs(p_max - cur_max) > power_range * 0.05:
                self.ax_power.set_ylim(p_min, p_max)
        elif not self.autoscale_power:
            # Используем фиксированные значения
            self.ax_power.set_ylim(self.power_range[0], self.power_range[1])
    
    def toggle_line(self, line_name, visible):
        """Переключение видимости линии"""
        if line_name in self.line_visibility:
            self.line_visibility[line_name] = visible
        
        if line_name == 'torque' and self.line_torque:
            self.line_torque.set_visible(visible)
        elif line_name == 'speed' and self.line_speed:
            self.line_speed.set_visible(visible)
        elif line_name == 'power' and self.line_power:
            self.line_power.set_visible(visible)
        
        self.canvas.draw_idle()
    
    def clear_plots(self):
        """Очистка всех графиков"""
        if self.line_torque:
            self.line_torque.set_data([], [])
        if self.line_speed:
            self.line_speed.set_data([], [])
        if self.line_power:
            self.line_power.set_data([], [])
        
        self.timestamps = []
        self.torque_data = []
        self.speed_data = []
        self.power_data = []
        
        self._set_initial_limits()
        self.canvas.draw()
    
    def get_visibility(self, line_name):
        """Получить текущую видимость линии"""
        return self.line_visibility.get(line_name, True)
    
    def set_all_visible(self, visible=True):
        """Установить видимость всех линий"""
        for name in self.line_visibility:
            self.line_visibility[name] = visible
        
        if self.line_torque:
            self.line_torque.set_visible(visible)
        if self.line_speed:
            self.line_speed.set_visible(visible)
        if self.line_power:
            self.line_power.set_visible(visible)
        
        self.canvas.draw_idle()
    
    # Удален метод set_theme - только темная тема
