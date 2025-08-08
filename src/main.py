import logging
from logging.handlers import RotatingFileHandler
import subprocess
import requests
import time
import threading
from typing import Dict, Optional

from settings import Settings, settings

URL_SEND_MESSAGE = "https://api.telegram.org/bot{}/sendMessage"
URL_GET_UPDATES = "https://api.telegram.org/bot{}/getUpdates"
MESSAGE_OK_LOG = 'Сообщение "{}" для {}'
START_COMMAND = "Запустить мониторинг сети"
STOP_COMMAND = "Остановить мониторинг сети"

START_BUTTON = {
    'keyboard': [
        [{'text': START_COMMAND}]
    ],
    'resize_keyboard': True,
    'one_time_keyboard': True
}
STOP_BUTTON = {
    'keyboard': [
        [{'text': STOP_COMMAND}]
    ],
    'resize_keyboard': True,
    'one_time_keyboard': True
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    "wifi_monitor.log", maxBytes=1000000, backupCount=3
)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())


class WiFiChecker:
    def __init__(self, setting: Settings):
        self.settings = setting
        self.chat_ids = setting.CHAT_IDS
        self.check_interval = setting.CHECK_INTERVAL
        self.wifi_name = setting.WIFI_NAME
        self.telegram_token = setting.TELEGRAM_TOKEN
        self.is_check = False
        self.count = 1
        self.monitoring_active = False
        self.last_update_id = 0
        self.active_chats: Dict[str, bool] = {}

    def get_wifi_list(self) -> set:
        """Получить все доступные сети WIFI."""
        try:
            result = subprocess.check_output(
                ["iwlist", "wlx6c60ebd46348", "scan"],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            return {
                line.split('"')[1]
                for line in result.split('\n') if "ESSID" in line
            }
        except Exception as e:
            logger.warning(f"Ошибка сканирования: {e}")
            return set()

    def send_message_telegram(
        self, message: str, chat_id: str, buttons: Optional[dict] = None
    ):
        """Отправить сообщение в телеграм."""
        payload = {"chat_id": chat_id, "text": message}
        if buttons:
            payload["reply_markup"] = buttons
        response = requests.post(
            URL_SEND_MESSAGE.format(self.telegram_token),
            json=payload
        )
        return response

    def sending_messages(self, message: str, buttons: Optional[dict] = None):
        """Рассылка сообщений в телеграм на все чаты."""
        for chat in self.chat_ids:
            response = self.send_message_telegram(
                message=message, chat_id=chat, buttons=buttons
            )
            if response.status_code < 400:
                logger.info(MESSAGE_OK_LOG.format(message, chat))
            else:
                logger.warning(
                    f"Сбой отправки -> {response} -> {response.status_code}"
                )

    def check_telegram_commands(self):
        """Проверка входящих команд от пользователей."""
        while True:
            try:
                response = requests.get(
                    URL_GET_UPDATES.format(self.telegram_token),
                    params={"offset": self.last_update_id + 1, "timeout": 30}
                )
                if response.status_code != 200:
                    continue

                data = response.json()
                if data.get("ok") is None or data.get("result") is None:
                    continue

                for update in data["result"]:
                    text, chat_id = self.get_text_chat_id(update=update)
                    if chat_id not in self.chat_ids:
                        self.send_message_telegram(
                            message="Вы не добавлены в группу допуска. "
                                    "Пожалуйста, обратитесь к администратору.",
                            chat_id=chat_id,
                            buttons=START_BUTTON
                        )
                        continue

                    if text == START_COMMAND:
                        self.start_handler(chat_id=chat_id)

                    elif text == STOP_COMMAND:
                        self.stop_handler(chat_id=chat_id)

            except Exception as e:
                logger.error(f"Ошибка при проверке команд: {e}")
                time.sleep(10)

    def get_text_chat_id(self, update: dict) -> tuple[str, str]:
        self.last_update_id = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "").strip()
        chat_id = str(message.get("chat", {}).get("id"))
        return text, chat_id

    def start_handler(self, chat_id):
        logger.info(START_COMMAND)
        if chat_id in self.active_chats:
            return

        self.active_chats[chat_id] = True
        self.send_message_telegram(
            message="Мониторинг WiFi запущен. Ожидание сети...",
            chat_id=chat_id,
            buttons=STOP_BUTTON
        )
        if not self.monitoring_active:
            self.monitoring_active = True
            threading.Thread(
                target=self.monitor_wifi,
                daemon=True
            ).start()

    def stop_handler(self, chat_id):
        logger.info(STOP_COMMAND)
        if chat_id not in self.active_chats:
            return

        del self.active_chats[chat_id]
        self.send_message_telegram(
            message="Мониторинг WiFi остановлен.",
            chat_id=chat_id,
            buttons=START_BUTTON
        )

        if not self.active_chats:
            self.monitoring_active = False

    def monitor_wifi(self):
        """Мониторинг WiFi сети."""
        logger.info("Запуск мониторинга WiFi")

        while self.monitoring_active:
            wifi_info = self.get_wifi_list()
            logger.info(f"Найдены сети: {wifi_info}")

            if self.wifi_name in wifi_info:
                message = "Электропитание дома возобновлено✅"
                logger.info(message)

                for chat_id in list(self.active_chats.keys()):
                    self.send_message_telegram(message, chat_id)
                    del self.active_chats[chat_id]

                if not self.active_chats:
                    self.monitoring_active = False
                    break

            time.sleep(60)

    def start(self):
        """Запуск бота."""
        logger.info("Бот запущен")
        self.sending_messages(
            message="Бот мониторинга WiFi запущен. "
                    f"Отправьте {START_COMMAND} для начала мониторинга.",
            buttons=START_BUTTON
        )
        threading.Thread(
            target=self.check_telegram_commands,
            daemon=True
        ).start()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    checker = WiFiChecker(setting=settings)
    checker.start()
