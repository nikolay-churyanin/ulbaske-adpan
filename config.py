import os
from dotenv import load_dotenv

load_dotenv()

# Настройки Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Настройки GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# Пути к файлам
TEAMS_FILE_PATH = "data/teams.json"
VENUES_FILE_PATH = "data/venues.json"
SCHEDULE_FILE_PATH = "data/schedule.json"
GAMES_DIR_PATH = "data/games"
RESULT_IMAGES_DIR = "data/result"

# Настройки логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'