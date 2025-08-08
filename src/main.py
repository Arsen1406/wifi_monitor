import logging
from logging.handlers import RotatingFileHandler
import subprocess
import requests
from pywifi import PyWiFi
import time

from settings import Settings, settings

URL_SEND_MESSAGE = "https://api.telegram.org/bot{}/sendMessage"
MESSAGE_OK_LOG = 'Сообщение "{}" для {}'

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

    def get_wifi_list(self) -> set:
        """Получить все доступные сети WIFI."""

        while True:
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
                time.sleep(30)
                continue

    def send_message_telegram(self, message: str, chat_id: str):
        """Отправить сообщение в телеграм."""

        payload = {
            'chat_id': chat_id,
            'text': message
        }
        response = requests.post(
            URL_SEND_MESSAGE.format(self.telegram_token),
            json=payload
        )
        return response

    def sending_messages(self, message: str):
        """Рассылка сообщений в телеграм на все чаты."""

        for chat in self.chat_ids:
            response = self.send_message_telegram(
                message=message, chat_id=chat
            )
            if response.status_code < 400:
                logger.info(
                    MESSAGE_OK_LOG.format(message, chat)
                )
                continue

            logger.warning(
                f"Сбой отправки -> {response} -> {response.status_code}"
            )

    def drop_count(self):
        """Сбросить счётчик попыток."""
        self.count = 1

    def start(self):
        """Запуск таска."""

        self.sending_messages(message="Отслеживание wifi сети запущено")
        while True:
            wifi_info = self.get_wifi_list()
            logger.info(wifi_info)
            if self.wifi_name in wifi_info and self.is_check is False:
                time.sleep(self.check_interval)
                self.drop_count()
                continue

            if self.wifi_name not in wifi_info and self.count > 0:
                self.count -= 1
                continue

            if self.is_check is False:
                self.sending_messages(
                    message="Электропитание дома отключено❌"
                )
                self.is_check = True

            if self.wifi_name in wifi_info:
                self.sending_messages(
                    message="Электропитание дома возобновлено✅"
                )
                self.is_check = False
                self.drop_count()
            time.sleep(self.check_interval)


if __name__ == "__main__":
    checker = WiFiChecker(setting=settings)
    checker.start()

