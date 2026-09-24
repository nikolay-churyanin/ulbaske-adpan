import logging
import json
import os
import base64
import re
import requests
from config import (
    SEASONS_CATALOG_PATH,
    DEFAULT_SEASON_ID,
    season_file,
)

logger = logging.getLogger(__name__)


class GitHubManager:
    def __init__(self, token, owner, repo_name):
        self.season_id = None
        self.catalog = {"version": "1.0", "current": None, "seasons": []}
        self.token = token
        self.owner = owner
        self.repo_name = repo_name
        try:
            from github import Github
            self.g = Github(token)
            self.repo = self.g.get_repo(f"{owner}/{repo_name}")
            self.github_available = True
        except ImportError:
            logger.error("PyGithub не установлен. Используется локальное хранение.")
            self.github_available = False
            self.repo = None
        except Exception as e:
            logger.error(f"Ошибка при инициализации GitHub: {e}")
            self.github_available = False
            self.repo = None

    def load_catalog(self):
        self.catalog = self._load_json(SEASONS_CATALOG_PATH, {
            "version": "1.0",
            "current": None,
            "seasons": []
        })
        return self.catalog

    def resolve_season_id(self, requested=None):
        seasons = self.catalog.get("seasons") or []
        ids = [item.get("id") for item in seasons if item.get("id")]
        if requested and requested in ids:
            return requested
        if DEFAULT_SEASON_ID and DEFAULT_SEASON_ID in ids:
            return DEFAULT_SEASON_ID
        unfinished = next((item["id"] for item in seasons if not item.get("archived")), None)
        if unfinished:
            return unfinished
        current = self.catalog.get("current")
        if current in ids:
            return current
        return ids[0] if ids else None

    def set_season(self, season_id):
        self.season_id = season_id

    def season_meta(self):
        for item in self.catalog.get("seasons") or []:
            if item.get("id") == self.season_id:
                return item
        return {"id": self.season_id, "label": self.season_id}

    def _path(self, filename):
        if not self.season_id:
            raise ValueError("Сезон не выбран")
        return season_file(self.season_id, filename)

    def get_leagues_config(self):
        return self._load_json(self._path("leagues-config.json"), {})

    def get_teams_data(self):
        return self._load_json(self._path("teams.json"), [])

    def get_venues_data(self):
        return self._load_json(self._path("venues.json"), [])

    def save_venues_data(self, venues_data, commit_message):
        return self._save_json(self._path("venues.json"), venues_data, commit_message, bump_version=True)

    def get_games(self):
        games = self._load_json(self._path("games.json"), [])
        return games if isinstance(games, list) else []

    def save_games(self, games, commit_message):
        return self._save_json(self._path("games.json"), games, commit_message, bump_version=True)

    def next_game_id(self, games=None):
        games = games if games is not None else self.get_games()
        numbers = []
        for game in games:
            number = self.extract_game_number(game.get("id") or "")
            if number:
                numbers.append(number)
        next_number = (max(numbers) + 1) if numbers else 1
        return f"game_{next_number:03d}", next_number

    def get_all_games(self):
        wrapped = []
        for game in self.get_games():
            game_id = game.get("id") or ""
            wrapped.append({
                "file_name": f"{game_id}.json" if game_id else "game.json",
                "game_number": self.extract_game_number(game_id),
                "id": game_id,
                "data": game,
                "path": self._path("games.json")
            })
        return wrapped

    def get_games_with_statistics(self):
        games_with_stats = set()
        result_dir = self._path("result")
        try:
            if not self.github_available:
                if not os.path.exists(result_dir):
                    return games_with_stats
                for filename in os.listdir(result_dir):
                    number = self.extract_game_number(filename)
                    if number:
                        games_with_stats.add(number)
                return games_with_stats

            contents = self.repo.get_contents(result_dir)
            items = contents if isinstance(contents, list) else [contents]
            for item in items:
                number = self.extract_game_number(item.name)
                if number:
                    games_with_stats.add(number)
        except Exception as e:
            logger.info(f"Папка result недоступна: {e}")
        return games_with_stats

    def save_statistics_image(self, image_data, game_number, commit_message):
        filename = f"game_{game_number:03d}.jpg"
        file_path = f"{self._path('result')}/{filename}"

        if not self.github_available:
            return self._save_local_image(file_path, image_data)

        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/contents/{file_path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(api_url, headers=headers)
            payload = {
                "message": commit_message,
                "content": base64.b64encode(image_data).decode("utf-8")
            }
            if response.status_code == 200:
                payload["sha"] = response.json()["sha"]
            elif response.status_code == 404:
                self._ensure_directory_exists(self._path("result"))
            else:
                logger.error(f"Ошибка проверки файла: {response.status_code}, {response.text}")
                return self._save_local_image(file_path, image_data)

            save_response = requests.put(api_url, headers=headers, json=payload)
            if save_response.status_code in [200, 201]:
                self.bump_catalog_version(f"cache-bust after {filename}")
                return True
            logger.error(f"Ошибка сохранения изображения: {save_response.status_code}, {save_response.text}")
            return self._save_local_image(file_path, image_data)
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения статистики: {e}")
            return self._save_local_image(file_path, image_data)

    def bump_catalog_version(self, commit_message="Bump data version"):
        catalog = self.load_catalog()
        version = str(catalog.get("version") or "1.0")
        parts = version.split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            catalog["version"] = ".".join(parts)
        except ValueError:
            catalog["version"] = f"{version}.1"
        self.catalog = catalog
        return self._save_json(SEASONS_CATALOG_PATH, catalog, commit_message, bump_version=False)

    def extract_game_number(self, value):
        if not value:
            return None
        match = re.search(r"game_(\d+)", str(value))
        return int(match.group(1)) if match else None

    def get_game_league(self, game_data):
        if not isinstance(game_data, dict):
            return None
        info = game_data.get("match_info") or game_data
        return info.get("league") or game_data.get("league")

    def _ensure_directory_exists(self, directory_path):
        try:
            self.repo.get_contents(directory_path)
            return True
        except Exception:
            try:
                self.repo.create_file(f"{directory_path}/.gitkeep", "Create directory", "")
                return True
            except Exception as e:
                logger.error(f"Ошибка при создании директории {directory_path}: {e}")
                return False

    def _load_json(self, path, default):
        try:
            if not self.github_available:
                return self._load_local_data(path, default)
            file_content = self.repo.get_contents(path)
            content = base64.b64decode(file_content.content).decode("utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке {path}: {e}")
            return self._load_local_data(path, default)

    def _save_json(self, path, data, commit_message, bump_version=False):
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            if not self.github_available:
                saved = self._save_local_data(path, data)
                return saved
            try:
                file_content = self.repo.get_contents(path)
                self.repo.update_file(path, commit_message, payload, file_content.sha)
            except Exception:
                self.repo.create_file(path, commit_message, payload)
            if bump_version:
                self.bump_catalog_version(f"cache-bust after {path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении {path}: {e}")
            return self._save_local_data(path, data)

    def _load_local_data(self, filename, default):
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            return default
        except Exception as e:
            logger.error(f"Ошибка при загрузке локального файла {filename}: {e}")
            return default

    def _save_local_data(self, filename, data):
        try:
            directory = os.path.dirname(filename)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении локального файла {filename}: {e}")
            return False

    def _save_local_image(self, file_path, image_data):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(image_data)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении локального изображения: {e}")
            return False
