#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Профессиональный real-time график для динамометрического стенда DYN-200.
Три Y-оси слева в фиксированном порядке (от графика влево):
- Torque (Н·м) - красная, ближе к графику
- Speed (об/мин) - голубая/бирюзовая, средняя
- Power (Вт) - жёлтая, самая левая
Каждая ось имеет индивидуальное авто-масштабирование или ручные пределы.
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
        self.window.geometry("450x700")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрируем
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.window.winfo_screenheight() // 2) - (700 // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Текущие значения
        self.autoscale_torque = tk.BooleanVar(value=plot_manager.autoscale_torque)
        self.autoscale_speed = tk.BooleanVar(value=plot_manager.autoscale_speed)
        self.autoscale_power = tk.BooleanVar(value=plot_manager.autoscale_power)
        self.autoscale_time = tk.BooleanVar(value=plot_manager.autoscale_time)
        
        # Значения диапазонов
        self.torque_min = tk.StringVar(value=str(plot_manager.torque_range[0]))
        self.torque_max = tk.StringVar(value=str(plot_manager.torque_range[1]))
        self.speed_min = tk.StringVar(value=str(plot_manager.speed_range[0]))
        self.speed_max = tk.StringVar(value=str(plot_manager.speed_range[1]))
        self.power_min = tk.StringVar(value=str(plot_manager.power_range[0]))
        self.power_max = tk.StringVar(value=str(plot_manager.power_range[1]))
        self.time_min = tk.StringVar(value=str(plot_manager.time_range[0]))
        self.time_max = tk.StringVar(value=str(plot_manager.time_range[1]))

        # Настройка шкалы времени
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
        
        # Заголовок
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
        
        # Контейнер с прокруткой
        scroll_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent",
            height=350,
            scrollbar_button_color=colors['primary'],
            scrollbar_button_hover_color=self._adjust_brightness(colors['primary'], 1.1)
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Примечание о порядке осей
        note_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        note_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            note_frame,
            text="ℹ️ Порядок осей (слева направо): Power → Speed → Torque (ближе к графику)",
            font=ctk.CTkFont(size=11),
            text_color=colors['text_secondary']
        ).pack(anchor="w")
        
        # Секции осей (в порядке от ближней к дальней от графика)
        self._create_axis_section(
            scroll_frame, "Torque (Н·м) - ближе к графику",
            self.autoscale_torque,
            self.torque_min, self.torque_max,
            self.plot_manager.COLOR_TORQUE
        )

        self._create_axis_section(
            scroll_frame, "Speed (об/мин) - средняя",
            self.autoscale_speed,
            self.speed_min, self.speed_max,
            self.plot_manager.COLOR_SPEED
        )

        self._create_axis_section(
            scroll_frame, "Power (Вт) - самая левая",
            self.autoscale_power,
            self.power_min, self.power_max,
            self.plot_manager.COLOR_POWER
        )
        
        # Секция времени
        self._create_time_section(scroll_frame)
        
        # Разделитель перед кнопками
        separator2 = ctk.CTkFrame(main_frame, height=1, fg_color=colors['outline'])
        separator2.pack(fill="x", padx=20, pady=15)
        
        # Кнопки
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
        
        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        indicator = ctk.CTkFrame(header, width=4, height=20, fg_color=color, corner_radius=2)
        indicator.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=colors['text']
        ).pack(side="left")
        
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
        
        range_frame = ctk.CTkFrame(section, fg_color="transparent")
        range_frame.pack(fill="x", padx=15, pady=(0, 15))
        
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
        
        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        indicator = ctk.CTkFrame(header, width=4, height=20, fg_color=self.plot_manager.COLOR_SPEED, corner_radius=2)
        indicator.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            header,
            text="Шкала времени",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=colors['text']
        ).pack(side="left")
        
        ctk.CTkLabel(
            section,
            text="Количество секунд для отображения на оси X",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_secondary']
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
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
        """Получение цветов текущей темы"""
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
            # Автомасштабирование
            self.plot_manager.autoscale_torque = self.autoscale_torque.get()
            self.plot_manager.autoscale_speed = self.autoscale_speed.get()
            self.plot_manager.autoscale_power = self.autoscale_power.get()

            # Диапазоны
            for attr, var, default in [
                ('torque_range', (self.torque_min, self.torque_max), 
                 (self.plot_manager.INITIAL_TORQUE_MIN, self.plot_manager.INITIAL_TORQUE_MAX)),
                ('speed_range', (self.speed_min, self.speed_max),
                 (self.plot_manager.INITIAL_SPEED_MIN, self.plot_manager.INITIAL_SPEED_MAX)),
                ('power_range', (self.power_min, self.power_max),
                 (self.plot_manager.INITIAL_POWER_MIN, self.plot_manager.INITIAL_POWER_MAX)),
            ]:
                try:
                    min_val = float(var[0].get()) if var[0].get() else default[0]
                except ValueError:
                    min_val = default[0]
                try:
                    max_val = float(var[1].get()) if var[1].get() else default[1]
                except ValueError:
                    max_val = default[1]
                setattr(self.plot_manager, attr, (min_val, max_val))

            # Временное окно
            try:
                time_window = float(self.time_window.get()) if self.time_window.get() else 60
            except ValueError:
                time_window = 60

            if time_window >= 5:
                self.plot_manager.time_window_seconds = time_window
                self.plot_manager.time_range = (0, time_window)

            # Применяем настройки
            self.plot_manager.apply_axis_ranges()

            self.result = True
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректное значение: {e}")
    
    def _reset_to_auto(self):
        """Сброс к авто-масштабированию"""
        self.autoscale_torque.set(True)
        self.autoscale_speed.set(True)
        self.autoscale_power.set(True)
        
        self.plot_manager.autoscale_torque = True
        self.plot_manager.autoscale_speed = True
        self.plot_manager.autoscale_power = True
        
        self.plot_manager.apply_axis_ranges()
        self.result = True
        self.window.destroy()


class PlotManager:
    """
    Менеджер для создания и обновления real-time графика
    с тремя осями Y слева для системы мониторинга DYN-200.
    """
    
    COLOR_TORQUE = '#e74c3c'  # Красный
    COLOR_SPEED = '#00bcd4'   # Голубой/бирюзовый
    COLOR_POWER = '#f1c40f'   # Жёлтый
    
    BG_COLOR = '#1a1a1a'
    FG_COLOR = '#2c2c2c'
    TEXT_COLOR = '#e4e6eb'
    GRID_COLOR = '#4b5563'
    GRID_ALPHA = 0.25
    
    LINE_WIDTH = 2.2
    MARKER_SIZE = 4
    MAX_POINTS = 200
    MAX_TICKS_X = 6
    MAX_TICKS_Y = 8
    
    # Требование 1: Базовые настройки графика (начальные max значения осей)
    INITIAL_TORQUE_MIN = -10
    INITIAL_TORQUE_MAX = 100    # Н·м
    INITIAL_SPEED_MIN = 0
    INITIAL_SPEED_MAX = 10000   # об/мин
    INITIAL_POWER_MIN = 0
    INITIAL_POWER_MAX = 10000   # Вт
    
    def __init__(self, config=None, state=None):
        self.config = config
        self.state = state
        
        self.fig = None
        self.canvas = None
        
        # Три оси Y - все слева
        self.ax_speed = None
        self.ax_torque = None
        self.ax_power = None
        
        # Словари для доступа по имени
        self.axes = {}
        self.lines = {}
        
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
        
        self.value_texts = {}
        self.annotations = {}
        
        self.timestamps = []
        self.torque_data = []
        self.speed_data = []
        self.power_data = []
        
        self.autoscale_torque = True
        self.autoscale_speed = True
        self.autoscale_power = True
        self.autoscale_time = False
        self.torque_range = (self.INITIAL_TORQUE_MIN, self.INITIAL_TORQUE_MAX)
        self.speed_range = (self.INITIAL_SPEED_MIN, self.INITIAL_SPEED_MAX)
        self.power_range = (self.INITIAL_POWER_MIN, self.INITIAL_POWER_MAX)
        self.time_range = (0, 10)
        self.time_window_seconds = 60
        
        # Основная ось - всегда Torque (основная сетка и ось X)
        self.primary_axis = 'torque'
        
        self.parent_frame = None
        self.range_button = None
    
    def create_plots(self, parent_frame):
        """Создание графика с тремя осями Y слева"""
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        self.fig = Figure(
            figsize=(10, 6),
            dpi=100,
            facecolor=self.BG_COLOR,
            edgecolor=self.BG_COLOR
        )
        
        self._create_triple_axis_plot()
        
        self.parent_frame = parent_frame
        main_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        main_container.pack(fill='both', expand=True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
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
    
    def _create_triple_axis_plot(self):
        """Создание графика с тремя осями Y слева в фиксированном порядке:
        - Torque (Н·м) - красная, ближе к графику (offset=0)
        - Speed (об/мин) - голубая, средняя (offset=80)
        - Power (Вт) - жёлтая, самая левая (offset=160)

        Все три оси строго слева от области построения, никаких осей справа.
        """
        # Увеличенный отступ слева для размещения трёх осей: [left, bottom, width, height]
        # left=0.32 даёт достаточно места для трёх осей Y слева
        ax_torque = self.fig.add_axes([0.32, 0.18, 0.63, 0.72])
        ax_torque.set_facecolor(self.BG_COLOR)
        self.ax_torque = ax_torque

        # Заголовок убран по требованию
        # ax_torque.set_title(
        #     "Мониторинг параметров DYN-200",
        #     fontsize=14, fontweight='bold',
        #     color=self.TEXT_COLOR, pad=15
        # )

        # Ось X (общая для всех) - снизу
        ax_torque.set_xlabel("Время (с)", color=self.TEXT_COLOR, fontsize=11, fontweight='bold')
        ax_torque.tick_params(axis='x', colors=self.TEXT_COLOR, labelsize=10)
        ax_torque.xaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_X, integer=False))
        ax_torque.xaxis.set_minor_locator(AutoMinorLocator(5))
        ax_torque.tick_params(axis='x', which='minor', length=3, color=self.TEXT_COLOR)

        # --- Ось Torque (основная, ближе к графику, offset=0) ---
        # Правая из левых осей - самая близкая к графику
        ax_torque.set_ylabel("Torque (Н·м)", color=self.COLOR_TORQUE, fontsize=11, fontweight='bold')
        ax_torque.tick_params(axis='y', colors=self.COLOR_TORQUE, labelsize=9)
        ax_torque.yaxis.label.set_color(self.COLOR_TORQUE)
        ax_torque.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        ax_torque.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax_torque.tick_params(axis='y', which='minor', length=2, color=self.COLOR_TORQUE)

        # Настройка spine для Torque - левая ось на своём месте
        ax_torque.spines['bottom'].set_color(self.GRID_COLOR)
        ax_torque.spines['top'].set_visible(False)
        ax_torque.spines['left'].set_color(self.COLOR_TORQUE)
        ax_torque.spines['left'].set_linewidth(1.5)
        ax_torque.spines['right'].set_visible(False)

        # Сетка привязана к основной оси (Torque)
        ax_torque.grid(True, alpha=0.4, color='#9e9e9e', linestyle='-', linewidth=0.8, which='major')
        ax_torque.grid(True, alpha=0.15, color='#e0e0e0', linestyle=':', linewidth=0.3, which='minor')

        # Линия Torque
        self.line_torque, = ax_torque.plot(
            [], [], color=self.COLOR_TORQUE, linewidth=self.LINE_WIDTH,
            linestyle='-', alpha=0.9, label='Torque',
            marker='s', markersize=self.MARKER_SIZE, markevery=10
        )

        # --- Ось Speed (средняя, offset=80) ---
        # Создаём через twinx(), но принудительно настраиваем всё слева
        ax_speed = ax_torque.twinx()

        # Отключаем правую ось полностью
        ax_speed.spines['right'].set_visible(False)

        # Настраиваем левую ось с отступом (средняя позиция)
        ax_speed.spines['left'].set_position(('outward', 80))
        ax_speed.spines['left'].set_visible(True)
        ax_speed.spines['left'].set_color(self.COLOR_SPEED)
        ax_speed.spines['left'].set_linewidth(1.5)
        ax_speed.spines['top'].set_visible(False)
        ax_speed.spines['bottom'].set_visible(False)
        ax_speed.set_facecolor('none')

        # Явно указываем, что деления и метки должны быть слева
        ax_speed.yaxis.set_ticks_position('left')
        ax_speed.yaxis.set_label_position('left')

        ax_speed.set_ylabel("Speed (об/мин)", color=self.COLOR_SPEED, fontsize=11, fontweight='bold')
        ax_speed.tick_params(axis='y', colors=self.COLOR_SPEED, labelsize=9)
        ax_speed.yaxis.label.set_color(self.COLOR_SPEED)
        ax_speed.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        ax_speed.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax_speed.tick_params(axis='y', which='minor', length=2, color=self.COLOR_SPEED)

        self.line_speed, = ax_speed.plot(
            [], [], color=self.COLOR_SPEED, linewidth=self.LINE_WIDTH,
            linestyle='-', alpha=0.9, label='Speed',
            marker='o', markersize=self.MARKER_SIZE, markevery=10
        )
        self.ax_speed = ax_speed

        # --- Ось Power (самая левая, offset=160) ---
        # Создаём через twinx(), но принудительно настраиваем всё слева
        ax_power = ax_torque.twinx()

        # Отключаем правую ось полностью
        ax_power.spines['right'].set_visible(False)

        # Настраиваем левую ось с отступом (самая левая позиция)
        ax_power.spines['left'].set_position(('outward', 160))
        ax_power.spines['left'].set_visible(True)
        ax_power.spines['left'].set_color(self.COLOR_POWER)
        ax_power.spines['left'].set_linewidth(1.5)
        ax_power.spines['top'].set_visible(False)
        ax_power.spines['bottom'].set_visible(False)
        ax_power.set_facecolor('none')

        # Явно указываем, что деления и метки должны быть слева
        ax_power.yaxis.set_ticks_position('left')
        ax_power.yaxis.set_label_position('left')

        ax_power.set_ylabel("Power (Вт)", color=self.COLOR_POWER, fontsize=11, fontweight='bold')
        ax_power.tick_params(axis='y', colors=self.COLOR_POWER, labelsize=9)
        ax_power.yaxis.label.set_color(self.COLOR_POWER)
        ax_power.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        ax_power.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax_power.tick_params(axis='y', which='minor', length=2, color=self.COLOR_POWER)

        self.line_power, = ax_power.plot(
            [], [], color=self.COLOR_POWER, linewidth=self.LINE_WIDTH,
            linestyle='-', alpha=0.9, label='Power',
            marker='^', markersize=self.MARKER_SIZE, markevery=10
        )
        self.ax_power = ax_power

        # Обновляем словари
        self.axes = {
            'speed': self.ax_speed,
            'torque': self.ax_torque,
            'power': self.ax_power
        }
        self.lines = {
            'speed': self.line_speed,
            'torque': self.line_torque,
            'power': self.line_power
        }

        # Легенда отключена (удалён вызов _create_legend)
        # self._create_legend()
        self._set_initial_limits()
    
    def _create_legend(self):
        """Создание горизонтальной легенды сверху"""
        from matplotlib.lines import Line2D
        
        legend_elements = [
            Line2D([0], [0], color=self.COLOR_TORQUE, lw=self.LINE_WIDTH, linestyle='-', 
                   marker='s', markersize=6, label='Torque (Н·м)'),
            Line2D([0], [0], color=self.COLOR_SPEED, lw=self.LINE_WIDTH, linestyle='-', 
                   marker='o', markersize=6, label='Speed (об/мин)'),
            Line2D([0], [0], color=self.COLOR_POWER, lw=self.LINE_WIDTH, linestyle='-', 
                   marker='^', markersize=6, label='Power (Вт)')
        ]
        
        self.fig.legend(
            handles=legend_elements,
            loc='upper center',
            bbox_to_anchor=(0.5, 0.98),
            ncol=3,
            facecolor=self.FG_COLOR,
            edgecolor=self.GRID_COLOR,
            labelcolor=self.TEXT_COLOR,
            fontsize=10,
            framealpha=0.95,
            fancybox=True,
            shadow=True
        )
    
    def _get_primary_ax(self):
        """Получение основной оси"""
        return self.axes.get(self.primary_axis, self.ax_speed)
    
    def apply_axis_ranges(self):
        """Применение диапазонов к осям"""
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

        if hasattr(self, 'time_range'):
            primary = self._get_primary_ax()
            if primary:
                primary.set_xlim(self.time_range[0], self.time_range[1])

        if self.canvas:
            self.canvas.draw()
    
    def _set_initial_limits(self):
        """Установка начальных пределов"""
        if self.ax_speed:
            self.ax_speed.set_ylim(self.speed_range[0], self.speed_range[1])
        if self.ax_torque:
            self.ax_torque.set_ylim(self.torque_range[0], self.torque_range[1])
        if self.ax_power:
            self.ax_power.set_ylim(self.power_range[0], self.power_range[1])
        
        primary = self._get_primary_ax()
        if primary:
            primary.set_xlim(0, 10)

        if self.ax_speed:
            self.ax_speed.autoscale(self.autoscale_speed)
        if self.ax_torque:
            self.ax_torque.autoscale(self.autoscale_torque)
        if self.ax_power:
            self.ax_power.autoscale(self.autoscale_power)
    
    def update_plots(self, timestamps, torque_data, speed_data, power_data):
        """Обновление графика"""
        if not timestamps or len(timestamps) == 0:
            return
        
        self.timestamps = list(timestamps)
        self.torque_data = list(torque_data) if torque_data else []
        self.speed_data = list(speed_data) if speed_data else []
        self.power_data = list(power_data) if power_data else []
        
        if self.line_torque and len(self.torque_data) == len(self.timestamps):
            self.line_torque.set_data(self.timestamps, self.torque_data)
        
        if self.line_speed and len(self.speed_data) == len(self.timestamps):
            self.line_speed.set_data(self.timestamps, self.speed_data)
        
        if self.line_power and len(self.power_data) == len(self.timestamps):
            self.line_power.set_data(self.timestamps, self.power_data)
        
        self._update_axis_limits()
        self.canvas.draw_idle()
    
    def _update_axis_limits(self):
        """Обновление пределов осей"""
        if not self.timestamps:
            return

        n_points = len(self.timestamps)
        primary = self._get_primary_ax()

        # Ось X
        if n_points > 1 and primary:
            x_max = self.timestamps[-1]
            x_min = max(0, x_max - self.time_window_seconds)
            primary.set_xlim(x_min, x_max)

        if n_points < 20:
            self._set_initial_limits()
            return

        # Speed
        if self.autoscale_speed and self.speed_data and self.ax_speed:
            speed_min = min(self.speed_data)
            speed_max = max(self.speed_data)
            speed_range = speed_max - speed_min if speed_max != speed_min else 100
            s_min = max(0, speed_min - speed_range * 0.05)
            s_max = speed_max + speed_range * 0.05
            s_min = int(s_min / 100) * 100 if s_min > 100 else int(s_min / 10) * 10
            s_max = int(s_max / 100 + 1) * 100 if s_max > 100 else int(s_max / 10 + 1) * 10
            cur_min, cur_max = self.ax_speed.get_ylim()
            if abs(s_min - cur_min) > speed_range * 0.05 or abs(s_max - cur_max) > speed_range * 0.05:
                self.ax_speed.set_ylim(s_min, s_max)
        elif not self.autoscale_speed and self.ax_speed:
            self.ax_speed.set_ylim(self.speed_range[0], self.speed_range[1])

        # Torque
        if self.autoscale_torque and self.torque_data and self.ax_torque:
            torque_min = min(self.torque_data)
            torque_max = max(self.torque_data)
            torque_range = torque_max - torque_min if torque_max != torque_min else 10
            t_min = torque_min - torque_range * 0.05
            t_max = torque_max + torque_range * 0.05
            t_min = int(t_min / 10) * 10 if abs(t_min) > 10 else int(t_min)
            t_max = int(t_max / 10 + 1) * 10 if abs(t_max) > 10 else int(t_max + 1)
            cur_min, cur_max = self.ax_torque.get_ylim()
            if abs(t_min - cur_min) > torque_range * 0.05 or abs(t_max - cur_max) > torque_range * 0.05:
                self.ax_torque.set_ylim(t_min, t_max)
        elif not self.autoscale_torque and self.ax_torque:
            self.ax_torque.set_ylim(self.torque_range[0], self.torque_range[1])

        # Power
        if self.autoscale_power and self.power_data and self.ax_power:
            power_min = min(self.power_data)
            power_max = max(self.power_data)
            power_range = power_max - power_min if power_max != power_min else 100
            p_min = max(0, power_min - power_range * 0.05)
            p_max = power_max + power_range * 0.05
            p_min = int(p_min / 100) * 100 if p_min > 100 else int(p_min / 10) * 10
            p_max = int(p_max / 100 + 1) * 100 if p_max > 100 else int(p_max / 10 + 1) * 10
            cur_min, cur_max = self.ax_power.get_ylim()
            if abs(p_min - cur_min) > power_range * 0.05 or abs(p_max - cur_max) > power_range * 0.05:
                self.ax_power.set_ylim(p_min, p_max)
        elif not self.autoscale_power and self.ax_power:
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
        """Очистка графиков"""
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
        """Получить видимость линии"""
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
