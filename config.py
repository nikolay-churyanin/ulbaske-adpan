import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

SEASONS_CATALOG_PATH = "data/seasons.json"
DEFAULT_SEASON_ID = os.getenv("CURRENT_SEASON", "").strip() or None

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'


def season_dir(season_id):
    return f"data/seasons/{season_id}"


def season_file(season_id, filename):
    return f"{season_dir(season_id)}/{filename}"
