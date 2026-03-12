#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа для DYN-200 Monitor
Система тестирования - современный интерфейс
"""

import customtkinter as ctk
from gui.modern_main_window import ModernMainWindow


def main():
    """Главная функция запуска приложения"""
    try:
        # Устанавливаем темную тему
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        root = ctk.CTk()
        app = ModernMainWindow(root)
        root.mainloop()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
