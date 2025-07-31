import sys
import builtins
import telebot
from threading import Thread
from queue import Queue

from API import API_bot, my_chat_id


class SimpleTelegramLogger:
    def __init__(self, bot, chat_id, max_length=4000, stderr=False):
        self.max_length = max_length
        self.bot = bot
        self.chat_id = chat_id
        self.input_queue = Queue()
        self.active = True
        self.buffer = ""

        # Сохраняем оригинальные потоки
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_input = builtins.input

        # Перехватываем потоки
        sys.stdout = self
        if stderr:
            sys.stderr = self
        builtins.input = self._input_handler

        # Запускаем поток для консольного ввода
        Thread(target=self._read_console_input, daemon=True).start()

        # Простейший обработчик сообщений из Telegram
        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(msg):
            if msg.text:
                self.input_queue.put(msg.text)
                self.original_stdout.write(f"[Telegram Input] {msg.text}")

        # Запускаем бота в отдельном потоке
        Thread(target=self.bot.infinity_polling, daemon=True).start()

    def send_telegram_message(self, message):
        for i in range(0, len(message), self.max_length):
            chunk = message[i:i + self.max_length]
            self.bot.send_message(self.chat_id, chunk)
        self.buffer = ""

    def write(self, message, bool_buffer=True):
        if message.strip():
            # Выводим в оригинальный stdout
            def write_format(x: str) -> str:
                return x + "\n" if bool_buffer else x

            self.original_stdout.write(write_format(message))

            # Отправляем в Telegram (без буферизации)
            try:
                self.buffer += message
                if "\n" in self.buffer or not bool_buffer:
                    self.send_telegram_message(self.buffer)
            except Exception as e:
                self.original_stdout.write(f"\nОшибка Telegram: {e}\n")

    def flush(self):
        self.original_stdout.flush()

    def _input_handler(self, prompt=""):
        if prompt:
            self.write(prompt, bool_buffer=False)
        return self.input_queue.get()

    def _read_console_input(self):
        while self.active:
            try:
                user_input = self.original_input()
                if user_input.strip():
                    self.input_queue.put(user_input)
                    self.bot.send_message(self.chat_id, f"[Console Input] {user_input}")
            except (EOFError, KeyboardInterrupt):
                break

    def cleanup(self):
        self.active = False
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        builtins.input = self.original_input
        self.bot.stop_polling()

    def __enter__(self):
        """Поддержка менеджера контекста (with ...)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое восстановление потоков при выходе"""
        self.cleanup()
        if exc_type:
            error_msg = f"🚨 Ошибка: {exc_type.__name__}: {exc_val}"
            #self.bot.send_message(self.chat_id, error_msg)
            self.original_stdout.write(f"\n{error_msg}\n")
