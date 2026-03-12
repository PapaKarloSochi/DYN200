#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Профессиональный real-time график для динамометрического стенда DYN-200.
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
    """Компактный диалог настройки диапазонов - одно окно, 4 ползунка"""
    
    # Диапазоны для ползунков (min, max, step)
    RANGES = {
        'torque': (10, 500, 5),       # Н·м max
        'speed': (100, 25000, 100),   # об/мин max
        'power': (100, 25000, 100),   # Вт max
        'time': (5, 300, 5),          # секунды окно
    }
    
    def __init__(self, parent, plot_manager):
        self.parent = parent
        self.plot_manager = plot_manager
        self.result = None
        
        # Окно 420x480 - компактное, все влезает без прокрутки
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Настройка диапазонов")
        self.window.geometry("420x480")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрируем
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 210
        y = (self.window.winfo_screenheight() // 2) - 240
        self.window.geometry(f"+{x}+{y}")
        
        # Значения ползунков (только max для осей, окно для времени)
        self.torque_val = tk.DoubleVar(value=float(plot_manager.torque_range[1]))
        self.speed_val = tk.DoubleVar(value=float(plot_manager.speed_range[1]))
        self.power_val = tk.DoubleVar(value=float(plot_manager.power_range[1]))
        self.time_val = tk.DoubleVar(value=float(getattr(plot_manager, 'time_window_seconds', 60)))
        
        self._create_ui()
    
    def _create_ui(self):
        """Создание компактного интерфейса"""
        colors = self._get_theme_colors()
        
        # Главный контейнер
        main = ctk.CTkFrame(self.window, fg_color=colors['bg'])
        main.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Заголовок
        ctk.CTkLabel(main, text="📊 Настройка диапазонов", 
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=colors['text']).pack(anchor="w", padx=10, pady=(8, 2))
        
        ctk.CTkLabel(main, text="Установите максимальное значение для каждой оси", 
                    font=ctk.CTkFont(size=10),
                    text_color=colors['text_secondary']).pack(anchor="w", padx=10)
        
        ctk.CTkFrame(main, height=1, fg_color=colors['outline']).pack(fill="x", padx=10, pady=8)
        
        # === 1. TORQUE ===
        self._create_slider_row(main, "🔴", "Крутящий момент", "Н·м",
                               self.torque_val, 'torque', colors['torque'])
        
        # === 2. SPEED ===
        self._create_slider_row(main, "🔵", "Скорость", "об/мин",
                               self.speed_val, 'speed', colors['speed'])
        
        # === 3. POWER ===
        self._create_slider_row(main, "🟡", "Мощность", "Вт",
                               self.power_val, 'power', colors['power'])
        
        # Разделитель
        ctk.CTkFrame(main, height=1, fg_color=colors['outline']).pack(fill="x", padx=10, pady=5)
        
        # === 4. TIME ===
        self._create_slider_row(main, "⏱️", "Окно времени", "сек",
                               self.time_val, 'time', colors['primary'])
        
        # Разделитель
        ctk.CTkFrame(main, height=1, fg_color=colors['outline']).pack(fill="x", padx=10, pady=8)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkButton(btn_frame, text="✓ Применить", command=self._apply,
                     width=110, height=32, font=ctk.CTkFont(size=12, weight="bold"),
                     fg_color=colors['primary'], hover_color=self._adjust_brightness(colors['primary'], 1.1),
                     text_color="white").pack(side="left", padx=(0, 6))
        
        ctk.CTkButton(btn_frame, text="↺ Сброс", command=self._reset,
                     width=90, height=32, font=ctk.CTkFont(size=12),
                     fg_color=colors['secondary'], hover_color=self._adjust_brightness(colors['secondary'], 1.1),
                     text_color="white").pack(side="left", padx=(0, 6))
        
        ctk.CTkButton(btn_frame, text="✕", command=self.window.destroy,
                     width=50, height=32, font=ctk.CTkFont(size=12),
                     fg_color="transparent", border_width=1, border_color=colors['outline'],
                     hover_color=colors['surface_hover'], text_color=colors['text_secondary']).pack(side="right")
    
    def _create_slider_row(self, parent, icon, name, unit, var, key, color):
        """Одна строка с ползунком"""
        colors = self._get_theme_colors()
        rmin, rmax, rstep = self.RANGES[key]
        
        row = ctk.CTkFrame(parent, fg_color=colors['surface'], corner_radius=8)
        row.pack(fill="x", padx=10, pady=4)
        
        # Верхняя строка: иконка, название, значение
        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(6, 0))
        
        ctk.CTkLabel(top, text=f"{icon} {name}", font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=colors['text']).pack(side="left")
        
        val_label = ctk.CTkLabel(top, text=f"{var.get():.0f} {unit}",
                                font=ctk.CTkFont(size=12, weight="bold"),
                                text_color=color)
        val_label.pack(side="right")
        
        # Ползунок
        slider_frame = ctk.CTkFrame(row, fg_color="transparent")
        slider_frame.pack(fill="x", padx=10, pady=(2, 8))
        
        def on_change(val):
            val_label.configure(text=f"{float(val):.0f} {unit}")
        
        slider = ctk.CTkSlider(slider_frame, from_=rmin, to=rmax,
                               number_of_steps=int((rmax - rmin) / rstep),
                               variable=var, command=on_change,
                               fg_color=colors['outline'], progress_color=color,
                               button_color=color, height=14)
        slider.pack(side="left", fill="x", expand=True, padx=(0, 6))
        
        ctk.CTkLabel(slider_frame, text=str(rmin), font=ctk.CTkFont(size=9),
                    text_color=colors['text_secondary']).pack(side="left")
        ctk.CTkLabel(slider_frame, text=str(rmax), font=ctk.CTkFont(size=9),
                    text_color=colors['text_secondary']).pack(side="right")
    
    def _get_theme_colors(self):
        return {
            'bg': ModernTheme.BACKGROUND,
            'surface': ModernTheme.SURFACE_VARIANT,
            'primary': ModernTheme.PRIMARY,
            'secondary': ModernTheme.SECONDARY,
            'text': ModernTheme.ON_SURFACE,
            'text_secondary': ModernTheme.ON_SURFACE_VARIANT,
            'outline': ModernTheme.OUTLINE,
            'torque': '#e74c3c',
            'speed': '#00bcd4',
            'power': '#f1c40f',
        }
    
    def _adjust_brightness(self, hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _apply(self):
        """Применение настроек"""
        try:
            # Устанавливаем диапазоны (0 до выбранного max)
            self.plot_manager.torque_range = (0, self.torque_val.get())
            self.plot_manager.speed_range = (0, self.speed_val.get())
            self.plot_manager.power_range = (0, self.power_val.get())
            
            # Отключаем авто-масштабирование
            self.plot_manager.autoscale_torque = False
            self.plot_manager.autoscale_speed = False
            self.plot_manager.autoscale_power = False
            
            # Временное окно
            time_window = self.time_val.get()
            if time_window >= 5:
                self.plot_manager.time_window_seconds = time_window
                self.plot_manager.time_range = (0, time_window)
            
            self.plot_manager.apply_axis_ranges()
            self.result = True
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректное значение: {e}")
    
    def _reset(self):
        """Сброс к значениям по умолчанию"""
        self.plot_manager.autoscale_torque = True
        self.plot_manager.autoscale_speed = True
        self.plot_manager.autoscale_power = True
        self.plot_manager.time_window_seconds = 60
        self.plot_manager.time_range = (0, 60)
        self.plot_manager.apply_axis_ranges()
        self.result = True
        self.window.destroy()


class PlotManager:
    """Менеджер для создания и обновления real-time графика"""
    
    COLOR_TORQUE = '#e74c3c'
    COLOR_SPEED = '#00bcd4'
    COLOR_POWER = '#f1c40f'
    
    BG_COLOR = '#1a1a1a'
    FG_COLOR = '#2c2c2c'
    TEXT_COLOR = '#e4e6eb'
    GRID_COLOR = '#4b5563'
    
    LINE_WIDTH = 2.2
    MARKER_SIZE = 4
    MAX_TICKS_X = 6
    MAX_TICKS_Y = 8
    
    INITIAL_TORQUE_MIN = -10
    INITIAL_TORQUE_MAX = 100
    INITIAL_SPEED_MIN = 0
    INITIAL_SPEED_MAX = 10000
    INITIAL_POWER_MIN = 0
    INITIAL_POWER_MAX = 10000
    
    def __init__(self, config=None, state=None):
        self.config = config
        self.state = state
        
        self.fig = None
        self.canvas = None
        
        self.ax_speed = None
        self.ax_torque = None
        self.ax_power = None
        
        self.axes = {}
        self.lines = {}
        
        self.line_torque = None
        self.line_speed = None
        self.line_power = None
        
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
        """Создание графика с тремя осями Y слева"""
        # left=0.20 даёт достаточно места для трёх осей Y слева
        ax_torque = self.fig.add_axes([0.20, 0.18, 0.75, 0.72])
        ax_torque.set_facecolor(self.BG_COLOR)
        self.ax_torque = ax_torque
        
        # Ось X
        ax_torque.set_xlabel("Время (с)", color=self.TEXT_COLOR, fontsize=11, fontweight='bold')
        ax_torque.tick_params(axis='x', colors=self.TEXT_COLOR, labelsize=10)
        ax_torque.xaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_X, integer=False))
        ax_torque.xaxis.set_minor_locator(AutoMinorLocator(5))
        ax_torque.tick_params(axis='x', which='minor', length=3, color=self.TEXT_COLOR)
        
        # Ось Torque
        ax_torque.set_ylabel("Torque (Н·м)", color=self.COLOR_TORQUE, fontsize=11, fontweight='bold')
        ax_torque.tick_params(axis='y', colors=self.COLOR_TORQUE, labelsize=9)
        ax_torque.yaxis.label.set_color(self.COLOR_TORQUE)
        ax_torque.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_TICKS_Y, integer=True))
        ax_torque.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax_torque.tick_params(axis='y', which='minor', length=2, color=self.COLOR_TORQUE)
        
        ax_torque.spines['bottom'].set_color(self.GRID_COLOR)
        ax_torque.spines['top'].set_visible(False)
        ax_torque.spines['left'].set_color(self.COLOR_TORQUE)
        ax_torque.spines['left'].set_linewidth(1.5)
        ax_torque.spines['right'].set_visible(False)
        
        ax_torque.grid(True, alpha=0.4, color='#9e9e9e', linestyle='-', linewidth=0.8, which='major')
        ax_torque.grid(True, alpha=0.15, color='#e0e0e0', linestyle=':', linewidth=0.3, which='minor')
        
        self.line_torque, = ax_torque.plot(
            [], [], color=self.COLOR_TORQUE, linewidth=self.LINE_WIDTH,
            linestyle='-', alpha=0.9, label='Torque',
            marker='s', markersize=self.MARKER_SIZE, markevery=10
        )
        
        # Ось Speed
        ax_speed = ax_torque.twinx()
        ax_speed.spines['right'].set_visible(False)
        ax_speed.spines['left'].set_position(('outward', 80))
        ax_speed.spines['left'].set_visible(True)
        ax_speed.spines['left'].set_color(self.COLOR_SPEED)
        ax_speed.spines['left'].set_linewidth(1.5)
        ax_speed.spines['top'].set_visible(False)
        ax_speed.spines['bottom'].set_visible(False)
        ax_speed.set_facecolor('none')
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
        
        # Ось Power
        ax_power = ax_torque.twinx()
        ax_power.spines['right'].set_visible(False)
        ax_power.spines['left'].set_position(('outward', 160))
        ax_power.spines['left'].set_visible(True)
        ax_power.spines['left'].set_color(self.COLOR_POWER)
        ax_power.spines['left'].set_linewidth(1.5)
        ax_power.spines['top'].set_visible(False)
        ax_power.spines['bottom'].set_visible(False)
        ax_power.set_facecolor('none')
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
        
        self._set_initial_limits()
    
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
