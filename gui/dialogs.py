#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диалоговые окна для настроек
"""

import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports


class ConnectionDialog:
    """Диалог настроек подключения"""
    
    def __init__(self, parent, state, on_connect, on_disconnect):
        self.window = tk.Toplevel(parent)
        self.window.title("Connection Settings")
        self.window.geometry("450x300")
        self.window.resizable(False, False)
        self.window.transient(parent)
        
        self.state = state
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        self._create_ui()
    
    def _create_ui(self):
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Заголовок
        ttk.Label(frame, text="Настройки подключения", 
                  font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # COM порт
        ttk.Label(frame, text="COM порт:").grid(row=1, column=0, sticky='w', pady=5)
        self.port_combo = ttk.Combobox(frame, textvariable=self.state.com_port, width=15)
        self.port_combo['values'] = self._get_ports()
        self.port_combo.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(frame, text="Обновить", command=self._refresh_ports).grid(row=1, column=2, padx=5)
        
        # Скорость
        ttk.Label(frame, text="Baudrate:").grid(row=2, column=0, sticky='w', pady=5)
        ttk.Combobox(frame, textvariable=self.state.baudrate, 
                     values=[9600, 19200, 38400, 57600, 115200], 
                     width=15).grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # Slave address
        ttk.Label(frame, text="Slave Address:").grid(row=3, column=0, sticky='w', pady=5)
        ttk.Spinbox(frame, from_=1, to=247, textvariable=self.state.slave_addr, 
                    width=15).grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        # Разделитель
        ttk.Separator(frame, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky='ew', pady=15)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.connect_btn = ttk.Button(btn_frame, text="Подключить", 
                                       command=self._on_connect, width=15)
        self.connect_btn.pack(side='left', padx=5)
        
        self.disconnect_btn = ttk.Button(btn_frame, text="Отключить", 
                                          command=self._on_disconnect, 
                                          state='disabled', width=15)
        self.disconnect_btn.pack(side='left', padx=5)
        
        # Статус
        ttk.Label(frame, text="Статус:").grid(row=6, column=0, sticky='w', pady=5)
        ttk.Label(frame, textvariable=self.state.connection_status, 
                  foreground="red").grid(row=6, column=1, columnspan=2, sticky='w', padx=5)
        
        # Кнопка закрытия
        ttk.Button(frame, text="Закрыть", command=self.window.destroy, 
                   width=15).grid(row=7, column=0, columnspan=3, pady=15)
    
    def _get_ports(self):
        try:
            ports = serial.tools.list_ports.comports()
            return [p.device for p in ports] or ["COM4"]
        except:
            return ["COM4"]
    
    def _refresh_ports(self):
        self.port_combo['values'] = self._get_ports()
    
    def _on_connect(self):
        self.connect_btn.config(state='disabled')
        self.disconnect_btn.config(state='normal')
        self.on_connect()
    
    def _on_disconnect(self):
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.on_disconnect()
    
    def update_buttons(self, connected):
        if connected:
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
        else:
            self.connect_btn.config(state='normal')
            self.disconnect_btn.config(state='disabled')


class AxisSettingsDialog:
    """Диалог настроек осей графика"""
    
    def __init__(self, parent, axis_settings, on_apply):
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки осей графика")
        self.window.geometry("500x450")
        self.window.resizable(False, False)
        self.window.transient(parent)
        
        self.axis_settings = axis_settings
        self.on_apply = on_apply
        
        self._create_ui()
    
    def _create_ui(self):
        frame = ttk.Frame(self.window, padding=15)
        frame.pack(fill='both', expand=True)
        
        # Заголовок
        ttk.Label(frame, text="Настройки диапазонов осей", 
                  font=('Arial', 12, 'bold')).pack(pady=(0, 15))
        
        # Секции для каждой оси
        self._create_axis_section(frame, "Torque (N·m)", 'torque')
        self._create_axis_section(frame, "Speed (RPM)", 'speed')
        self._create_axis_section(frame, "Power (Вт)", 'power')
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="Применить", command=self._apply, 
                   width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=self.window.destroy, 
                   width=15).pack(side='left', padx=5)
    
    def _create_axis_section(self, parent, title, axis_key):
        section = ttk.LabelFrame(parent, text=title, padding=10)
        section.pack(fill='x', pady=5)
        
        # Autoscale
        ttk.Checkbutton(section, text="Autoscale", 
                       variable=self.axis_settings[axis_key]['autoscale']).pack(anchor='w')
        
        # Min/Max
        range_frame = ttk.Frame(section)
        range_frame.pack(fill='x', pady=5)
        
        ttk.Label(range_frame, text="Min:").pack(side='left', padx=(0, 5))
        ttk.Entry(range_frame, textvariable=self.axis_settings[axis_key]['min'], 
                  width=10).pack(side='left', padx=5)
        
        ttk.Label(range_frame, text="Max:").pack(side='left', padx=(20, 5))
        ttk.Entry(range_frame, textvariable=self.axis_settings[axis_key]['max'], 
                  width=10).pack(side='left', padx=5)
    
    def _apply(self):
        self.on_apply()
