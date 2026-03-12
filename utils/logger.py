#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль логирования для DYN-200 Monitor
Улучшенная версия с уровнями логирования, ротацией и цветовым кодированием

ЭТАП 4: Система логирования с ротацией
- Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Ротация логов (RotatingFileHandler)
- Форматирование с timestamp, модулем, номером строки
- Цветовое кодирование в GUI
"""

import logging
import logging.handlers
import queue
import sys
import threading
import traceback
from datetime import datetime
from enum import IntEnum
from typing import Optional

# Импортируем настройки
from config import LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_FORMAT, LOG_FILE_PATH

# Уровни логирования
LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARNING = 30
LOG_LEVEL_ERROR = 40
LOG_LEVEL_CRITICAL = 50


class LogLevel(IntEnum):
    """Уровни логирования"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Цвета для GUI (теги tkinter)
class LogColor:
    """Цветовое кодирование уровней логирования"""
    DEBUG = "gray"
    INFO = "white"
    WARNING = "yellow"
    ERROR = "red"
    CRITICAL = "red_bold"


class ColoredLogRecord:
    """Запись лога с информацией о цвете"""
    def __init__(self, message: str, level: LogLevel, timestamp: str, 
                 module: str = "", line_no: int = 0, color: str = LogColor.INFO):
        self.message = message
        self.level = level
        self.timestamp = timestamp
        self.module = module
        self.line_no = line_no
        self.color = color


class GUILogHandler(logging.Handler):
    """Обработчик для вывода логов в GUI"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.setLevel(LOG_LEVEL)
        
    def emit(self, record: logging.LogRecord) -> None:
        """Отправка записи в очередь для GUI"""
        try:
            # Определяем цвет по уровню
            color = self._get_color(record.levelno)
            
            # Создаём запись для GUI
            log_record = ColoredLogRecord(
                message=record.getMessage(),
                level=int(record.levelno),
                timestamp=datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                module=record.module,
                line_no=record.lineno,
                color=color
            )
            self.log_queue.put(log_record)
        except Exception:
            self.handleError(record)
    
    def _get_color(self, level: int) -> str:
        """Получить цвет по уровню логирования"""
        if level >= LOG_LEVEL_CRITICAL:
            return LogColor.CRITICAL
        elif level >= LOG_LEVEL_ERROR:
            return LogColor.ERROR
        elif level >= LOG_LEVEL_WARNING:
            return LogColor.WARNING
        elif level >= LOG_LEVEL_DEBUG:
            return LogColor.DEBUG
        return LogColor.INFO


class Logger:
    """
    Потокобезопасный логгер с ротацией и GUI-выводом
    
    Использует стандартный модуль logging с:
    - RotatingFileHandler для ротации файлов
    - Очередью для thread-safe вывода в GUI
    - Цветовым кодированием уровней
    """
    
    def __init__(self):
        # Очередь для GUI (thread-safe)
        self.log_queue = queue.Queue()
        self.log_text_widget = None
        self._lock = threading.Lock()
        
        # Флаги для graceful degradation
        self._file_error_shown = False
        self._is_closing = False
        
        # Настраиваем стандартный логгер
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Настройка стандартного логгера Python"""
        # Создаём логгер
        self.logger = logging.getLogger("DYN200")
        self.logger.setLevel(LOG_LEVEL)
        
        # Очищаем старые обработчики
        self.logger.handlers.clear()
        
        # Форматтер
        formatter = logging.Formatter(LOG_FORMAT)
        
        # 1. Обработчик для ротации файлов
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=LOG_FILE_PATH,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)  # В файл пишем всё
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"[LOGGER ERROR] Failed to create file handler: {e}", file=sys.stderr)
        
        # 2. Обработчик для GUI
        gui_handler = GUILogHandler(self.log_queue)
        gui_handler.setFormatter(formatter)
        self.logger.addHandler(gui_handler)
        
        # 3. Обработчик для консоли (stderr)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(LOG_LEVEL)
        self.logger.addHandler(console_handler)
    
    def set_log_widget(self, text_widget: Optional[object]) -> None:
        """Установить виджет Text для отображения логов"""
        self.log_text_widget = text_widget
        self._configure_text_widget_tags()
    
    def _configure_text_widget_tags(self) -> None:
        """Настройка тегов цветов для Text виджета"""
        if not self.log_text_widget:
            return
            
        try:
            # Определяем цвета для темной темы
            colors = {
                LogColor.DEBUG: "#808080",      # Серый
                LogColor.INFO: "#FFFFFF",       # Белый
                LogColor.WARNING: "#FFD700",    # Жёлтый (золотой)
                LogColor.ERROR: "#FF4444",      # Красный
                LogColor.CRITICAL: "#FF0000"    # Ярко-красный
            }
            
            # Создаём теги
            for tag, color in colors.items():
                self.log_text_widget.tag_configure(tag, foreground=color)
                if tag == LogColor.CRITICAL:
                    # Для CRITICAL добавляем жирный шрифт
                    self.log_text_widget.tag_configure(tag, foreground=color, font=("Consolas", 11, "bold"))
        except Exception as e:
            print(f"[LOGGER ERROR] Failed to configure tags: {e}", file=sys.stderr)
    
    # ===== Методы логирования по уровням =====
    
    def debug(self, message: str) -> None:
        """Логирование отладочной информации"""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Логирование информационного сообщения"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Логирование предупреждения"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Логирование ошибки"""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Логирование критической ошибки"""
        self.logger.critical(message)
    
    # ===== Обратная совместимость =====
    
    def log(self, message: str, level: int = LOG_LEVEL_INFO) -> None:
        """
        Универсальный метод логирования (для обратной совместимости)
        
        Args:
            message: Сообщение для логирования
            level: Уровень логирования (по умолчанию INFO)
        """
        if level <= LOG_LEVEL_DEBUG:
            self.debug(message)
        elif level <= LOG_LEVEL_INFO:
            self.info(message)
        elif level <= LOG_LEVEL_WARNING:
            self.warning(message)
        elif level <= LOG_LEVEL_ERROR:
            self.error(message)
        else:
            self.critical(message)
    
    def log_exception(self, message: str, exception: Exception) -> None:
        """Логирование исключения с полным traceback"""
        tb_str = traceback.format_exc()
        full_message = f"{message}: {type(exception).__name__}: {exception}\n{tb_str}"
        self.error(full_message)
    
    # ===== Обработка очереди GUI =====
    
    def process_queue(self) -> None:
        """Обработка очереди логов для GUI (вызывать из главного потока)"""
        if self._is_closing:
            return
            
        try:
            # Обрабатываем все сообщения в очереди
            while True:
                try:
                    record = self.log_queue.get_nowait()
                    self._update_gui(record)
                except queue.Empty:
                    break
                    
        except Exception as e:
            print(f"[LOGGER ERROR] Error processing queue: {e}", file=sys.stderr)
        
        # Планируем следующий вызов
        self._schedule_next_process()
    
    def _update_gui(self, record: ColoredLogRecord) -> None:
        """Обновление GUI с записью лога"""
        if not self.log_text_widget:
            return
            
        try:
            # Формируем строку для отображения
            log_line = f"{record.timestamp} [{self._level_name(record.level)}] [{record.module}:{record.line_no}] {record.message}\n"
            
            # Вставляем с цветом
            self.log_text_widget.insert('end', log_line, record.color)
            self.log_text_widget.see('end')
            
            # Ограничиваем размер лога в виджете (макс 1000 строк)
            line_count = int(self.log_text_widget.index('end-1c').split('.')[0])
            if line_count > 1000:
                self.log_text_widget.delete('1.0', '100.0')
                
        except RuntimeError:
            # Виджет уничтожен
            pass
        except Exception as e:
            print(f"[LOGGER UI ERROR] {e}", file=sys.stderr)
    
    def _level_name(self, level: int) -> str:
        """Получить имя уровня"""
        names = {
            LOG_LEVEL_DEBUG: "DEBUG",
            LOG_LEVEL_INFO: "INFO",
            LOG_LEVEL_WARNING: "WARNING",
            LOG_LEVEL_ERROR: "ERROR",
            LOG_LEVEL_CRITICAL: "CRITICAL"
        }
        return names.get(level, "UNKNOWN")
    
    def _schedule_next_process(self) -> None:
        """Планирование следующей обработки очереди"""
        try:
            if self.log_text_widget and not self._is_closing:
                self.log_text_widget.after(100, self.process_queue)
        except RuntimeError:
            # Приложение закрывается
            pass
        except Exception:
            pass
    
    # ===== Управление =====
    
    def close(self) -> None:
        """Закрытие логгера"""
        self._is_closing = True
        
        with self._lock:
            # Закрываем обработчики
            for handler in self.logger.handlers:
                try:
                    handler.flush()
                    handler.close()
                except Exception as e:
                    print(f"[LOGGER CLOSE ERROR] {e}", file=sys.stderr)
            
            self.logger.handlers.clear()
    
    def set_level(self, level: int) -> None:
        """Изменить уровень логирования"""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
    
    def get_level(self) -> int:
        """Получить текущий уровень логирования"""
        return self.logger.level


# ===== Утилиты для работы с уровнями =====

def level_from_string(level_str: str) -> int:
    """Преобразовать строку уровня в числовое значение"""
    levels = {
        "DEBUG": LOG_LEVEL_DEBUG,
        "INFO": LOG_LEVEL_INFO,
        "WARNING": LOG_LEVEL_WARNING,
        "ERROR": LOG_LEVEL_ERROR,
        "CRITICAL": LOG_LEVEL_CRITICAL
    }
    return levels.get(level_str.upper(), LOG_LEVEL_INFO)


def level_to_string(level: int) -> str:
    """Преобразовать числовое значение уровня в строку"""
    levels = {
        LOG_LEVEL_DEBUG: "DEBUG",
        LOG_LEVEL_INFO: "INFO",
        LOG_LEVEL_WARNING: "WARNING",
        LOG_LEVEL_ERROR: "ERROR",
        LOG_LEVEL_CRITICAL: "CRITICAL"
    }
    return levels.get(level, "UNKNOWN")
