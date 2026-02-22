import logging
import json
import os
import base64
from config import *
import mimetypes
import requests

logger = logging.getLogger(__name__)

class GitHubManager:
    def __init__(self, token, owner, repo_name):
        try:
            from github import Github
            self.g = Github(token)
            self.repo = self.g.get_repo(f"{owner}/{repo_name}")
            self.github_available = True
            self.token = token
            self.owner = owner
            self.repo_name = repo_name
        except ImportError:
            logger.error("PyGithub не установлен. Используется локальное хранение.")
            self.github_available = False
        except Exception as e:
            logger.error(f"Ошибка при инициализации GitHub: {e}")
            self.github_available = False
    
    def get_leagues_config(self):
        """Получить конфигурацию лиг"""
        try:
            if not self.github_available:
                return self._load_local_data(CONFIG_FILE_PATH, {})
            
            file_content = self.repo.get_contents(CONFIG_FILE_PATH)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации лиг: {e}")
            return self._load_local_data(CONFIG_FILE_PATH, {})

    def get_teams_data(self):
        """Получить данные о командах из GitHub или локально"""
        try:
            if not self.github_available:
                return self._load_local_data(TEAMS_FILE_PATH, [])
            
            file_content = self.repo.get_contents(TEAMS_FILE_PATH)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке команд: {e}")
            return self._load_local_data(TEAMS_FILE_PATH, [])
    
    def get_venues_data(self):
        """Получить данные о залах из GitHub или локально"""
        try:
            if not self.github_available:
                return self._load_local_data(VENUES_FILE_PATH, [])
            
            file_content = self.repo.get_contents(VENUES_FILE_PATH)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке залов: {e}")
            return self._load_local_data(VENUES_FILE_PATH, [])
    
    def save_venues_data(self, venues_data, commit_message):
        """Сохранить данные о залах в GitHub или локально"""
        try:
            if not self.github_available:
                return self._save_local_data(VENUES_FILE_PATH, venues_data)
            
            try:
                file_content = self.repo.get_contents(VENUES_FILE_PATH)
                self.repo.update_file(
                    VENUES_FILE_PATH,
                    commit_message,
                    json.dumps(venues_data, ensure_ascii=False, indent=2),
                    file_content.sha
                )
            except:
                self.repo.create_file(
                    VENUES_FILE_PATH,
                    commit_message,
                    json.dumps(venues_data, ensure_ascii=False, indent=2)
                )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении залов: {e}")
            return self._save_local_data(VENUES_FILE_PATH, venues_data)
    
    def get_schedule_data(self):
        """Получить расписание из GitHub или локально"""
        try:
            if not self.github_available:
                return self._load_local_data(SCHEDULE_FILE_PATH, {"season": "2025-2026", "stages": []})
            
            file_content = self.repo.get_contents(SCHEDULE_FILE_PATH)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке расписания: {e}")
            return self._load_local_data(SCHEDULE_FILE_PATH, {"season": "2025-2026", "stages": []})
    
    def save_schedule_to_github(self, schedule_data, commit_message):
        """Сохранить расписание в GitHub или локально"""
        try:
            if not self.github_available:
                return self._save_local_data(SCHEDULE_FILE_PATH, schedule_data)
            
            try:
                file_content = self.repo.get_contents(SCHEDULE_FILE_PATH)
                self.repo.update_file(
                    SCHEDULE_FILE_PATH,
                    commit_message,
                    json.dumps(schedule_data, ensure_ascii=False, indent=2),
                    file_content.sha
                )
            except:
                self.repo.create_file(
                    SCHEDULE_FILE_PATH,
                    commit_message,
                    json.dumps(schedule_data, ensure_ascii=False, indent=2)
                )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении в GitHub: {e}")
            return self._save_local_data(SCHEDULE_FILE_PATH, schedule_data)
    
    def save_game_result(self, game_data, game_number, commit_message):
        """Сохранить результат игры в отдельный файл"""
        try:
            filename = f"game_{game_number:03d}.json"
            file_path = f"{GAMES_DIR_PATH}/{filename}"
            
            if not self.github_available:
                return self._save_local_data(f"games/{filename}", game_data)
            
            try:
                self.repo.get_contents(GAMES_DIR_PATH)
            except:
                self.repo.create_file(
                    f"{GAMES_DIR_PATH}/.gitkeep",
                    "Create games directory",
                    ""
                )
            
            try:
                file_content = self.repo.get_contents(file_path)
                self.repo.update_file(
                    file_path,
                    commit_message,
                    json.dumps(game_data, ensure_ascii=False, indent=2),
                    file_content.sha
                )
            except:
                self.repo.create_file(
                    file_path,
                    commit_message,
                    json.dumps(game_data, ensure_ascii=False, indent=2)
                )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата игры: {e}")
            return self._save_local_data(f"games/{filename}", game_data)
    
    def get_next_game_number(self):
        """Получить следующий номер для файла игры"""
        try:
            if not self.github_available:
                games_dir = "games"
                if not os.path.exists(games_dir):
                    return 1
                existing_files = [f for f in os.listdir(games_dir) if f.startswith("game_") and f.endswith(".json")]
                if not existing_files:
                    return 1
                numbers = [int(f.split("_")[1].split(".")[0]) for f in existing_files]
                return max(numbers) + 1
            
            contents = self.repo.get_contents(GAMES_DIR_PATH)
            game_files = [item for item in contents if item.name.startswith("game_") and item.name.endswith(".json")]
            
            if not game_files:
                return 1
            
            numbers = []
            for file in game_files:
                try:
                    number = int(file.name.split("_")[1].split(".")[0])
                    numbers.append(number)
                except:
                    continue
            
            return max(numbers) + 1 if numbers else 1
            
        except Exception as e:
            logger.error(f"Ошибка при получении номера игры: {e}")
            return 1
    
    def get_games_without_statistics(self, league=None):
        """Получить список игр без статистики"""
        try:
            games_with_stats = self.get_games_with_statistics()
            
            all_games = self.get_all_games()
            games_without_stats = []
            
            for game in all_games:
                game_number = self.extract_game_number(game['file_name'])
                if game_number not in games_with_stats:
                    # Проверяем лигу если указана
                    if league and self.get_game_league(game.get('data', {})) != league:
                        continue
                    games_without_stats.append(game)
            
            # Сортируем по номеру игры (по убыванию - самые новые первые)
            games_without_stats.sort(key=lambda x: self.extract_game_number(x['file_name']), reverse=True)
            
            # Ограничиваем 5 последними играми
            return games_without_stats[:5]
            
        except Exception as e:
            logger.error(f"Ошибка при получении игр без статистики: {e}")
            return []
    
    def get_all_games(self):
        """Получить все игры из папки games/"""
        try:
            if not self.github_available:
                return self._get_local_games()
            
            games = []
            try:
                contents = self.repo.get_contents(GAMES_DIR_PATH)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith(".json"):
                        try:
                            # Загружаем данные игры
                            file_content = base64.b64decode(item.content).decode('utf-8')
                            game_data = json.loads(file_content)
                            games.append({
                                'file_name': item.name,
                                'data': game_data,
                                'path': item.path
                            })
                        except Exception as e:
                            logger.error(f"Ошибка при загрузке игры {item.name}: {e}")
                            # Добавляем игру даже без данных (для подсчета)
                            games.append({
                                'file_name': item.name,
                                'path': item.path
                            })
            except:
                pass  # Папка games может не существовать
            
            return games
            
        except Exception as e:
            logger.error(f"Ошибка при получении всех игр: {e}")
            return []
    
    def get_games_with_statistics(self):
        """Получить номера игр, для которых есть статистика"""
        try:
            if not self.github_available:
                return self._get_local_games_with_stats()
            
            games_with_stats = set()
            try:
                contents = self.repo.get_contents(RESULT_IMAGES_DIR)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith((".jpg", ".jpeg", ".png")):
                        try:
                            # Извлекаем номер игры из названия файла
                            game_number = self.extract_game_number(item.name)
                            if game_number:
                                games_with_stats.add(game_number)
                        except:
                            continue
            except:
                pass  # Папка result может не существовать
            
            return games_with_stats
            
        except Exception as e:
            logger.error(f"Ошибка при получении игр со статистикой: {e}")
            return set()
    
    def save_statistics_image(self, image_data, game_number, commit_message):
        """Сохранить изображение со статистикой через GitHub REST API"""
        try:
            filename = f"game_{game_number:03d}.jpg"
            file_path = f"{RESULT_IMAGES_DIR}/{filename}"
            
            if not self.github_available:
                return self._save_local_image(filename, image_data)
            
            # Используем GitHub REST API напрямую для загрузки изображений
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/contents/{file_path}"
            
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Проверяем, существует ли файл
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                # Файл существует, получаем sha для обновления
                file_info = response.json()
                sha = file_info["sha"]
                
                # Обновляем файл
                data = {
                    "message": commit_message,
                    "content": base64.b64encode(image_data).decode('utf-8'),
                    "sha": sha
                }
                
                update_response = requests.put(api_url, headers=headers, json=data)
                
                if update_response.status_code in [200, 201]:
                    logger.info(f"Изображение {filename} обновлено через REST API")
                    return True
                else:
                    logger.error(f"Ошибка обновления: {update_response.status_code}, {update_response.text}")
                    return self._save_local_image(filename, image_data)
                    
            elif response.status_code == 404:
                # Файл не существует, создаем новый
                # Сначала проверяем/создаем папку
                self._ensure_directory_exists(RESULT_IMAGES_DIR)
                
                # Создаем файл
                data = {
                    "message": commit_message,
                    "content": base64.b64encode(image_data).decode('utf-8')
                }
                
                create_response = requests.put(api_url, headers=headers, json=data)
                
                if create_response.status_code in [200, 201]:
                    logger.info(f"Изображение {filename} создано через REST API")
                    return True
                else:
                    logger.error(f"Ошибка создания: {create_response.status_code}, {create_response.text}")
                    return self._save_local_image(filename, image_data)
            else:
                logger.error(f"Ошибка проверки файла: {response.status_code}, {response.text}")
                return self._save_local_image(filename, image_data)
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения статистики: {e}")
            return self._save_local_image(filename, image_data)
    
    def _ensure_directory_exists(self, directory_path):
        """Убедиться, что директория существует в репозитории"""
        try:
            # Проверяем существование директории
            try:
                self.repo.get_contents(directory_path)
                return True
            except:
                # Директория не существует, создаем .gitkeep файл
                self.repo.create_file(
                    f"{directory_path}/.gitkeep",
                    "Create directory",
                    ""
                )
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании директории {directory_path}: {e}")
            return False
    
    def extract_game_number(self, filename):
        """Извлечь номер игры из названия файла"""
        try:
            # Ожидаемые форматы: game_001.json, game_001.jpg, game_123.jpeg и т.д.
            if filename.startswith("game_") and (filename.endswith(".json") or 
                                               filename.endswith(".jpg") or 
                                               filename.endswith(".jpeg") or 
                                               filename.endswith(".png")):
                number_str = filename.split("_")[1].split(".")[0]
                return int(number_str)
            return None
        except:
            return None
    
    def get_game_league(self, game_data):
        """Получить лигу из данных игры"""
        try:
            # Ищем лигу в разных возможных местах
            if isinstance(game_data, dict):
                # Проверяем разные возможные ключи
                if 'match_info' in game_data and 'competition' in game_data['match_info']:
                    competition = game_data['match_info']['competition']
                    # Извлекаем лигу из названия соревнования
                    if "Муж. Чемп. Ульян. области" in competition:
                        return competition.replace("Муж. Чемп. Ульян. области", "").strip()
                
                # Пробуем другие возможные ключи
                for key in ['league', 'competition', 'Лига']:
                    if key in game_data:
                        return game_data[key]
            
            return "Неизвестная лига"
        except:
            return "Неизвестная лига"
    
    def _load_local_data(self, filename, default):
        """Загрузить данные из локального файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logger.error(f"Ошибка при загрузке локального файла {filename}: {e}")
            return default
    
    def _save_local_data(self, filename, data):
        """Сохранить данные в локальный файл"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении локального файла {filename}: {e}")
            return False
    
    def _get_local_games(self):
        """Получить все игры локально"""
        try:
            games_dir = GAMES_DIR_PATH
            if not os.path.exists(games_dir):
                return []
            
            games = []
            for filename in os.listdir(games_dir):
                if filename.startswith("game_") and filename.endswith(".json"):
                    try:
                        file_path = os.path.join(games_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            game_data = json.load(f)
                        games.append({
                            'file_name': filename,
                            'data': game_data,
                            'path': file_path
                        })
                    except Exception as e:
                        logger.error(f"Ошибка при загрузке локальной игры {filename}: {e}")
                        # Добавляем игру даже без данных
                        games.append({
                            'file_name': filename,
                            'path': os.path.join(games_dir, filename)
                        })
            
            return games
        except Exception as e:
            logger.error(f"Ошибка при получении локальных игр: {e}")
            return []
    
    def _get_local_games_with_stats(self):
        """Получить игры со статистикой локально"""
        try:
            stats_dir = RESULT_IMAGES_DIR
            if not os.path.exists(stats_dir):
                return set()
            
            games_with_stats = set()
            for filename in os.listdir(stats_dir):
                if filename.startswith("game_") and filename.endswith((".jpg", ".jpeg", ".png")):
                    game_number = self.extract_game_number(filename)
                    if game_number:
                        games_with_stats.add(game_number)
            
            return games_with_stats
        except Exception as e:
            logger.error(f"Ошибка при получении локальных игр со статистикой: {e}")
            return set()
    
    def _save_local_image(self, filename, image_data):
        """Сохранить изображение локально"""
        try:
            os.makedirs(RESULT_IMAGES_DIR, exist_ok=True)
            file_path = os.path.join(RESULT_IMAGES_DIR, filename)
            
            with open(file_path, 'wb') as f:
                f.write(image_data)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении локального изображения: {e}")
            return False

    def _load_game_data(self, filename):
        """Загрузить данные конкретной игры"""
        try:
            if not self.github_available:
                file_path = os.path.join(GAMES_DIR_PATH, filename)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                return None
            
            file_path = f"{GAMES_DIR_PATH}/{filename}"
            file_content = self.repo.get_contents(file_path)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных игры {filename}: {e}")
            return None

    def _load_game_data_by_number(self, game_number):
        """Загрузить данные игры по номеру"""
        filename = f"game_{game_number:03d}.json"
        return self._load_game_data(filename)

    def get_games_without_statistics_optimized(self, league=None):
        """Оптимизированное получение игр без статистики"""
        try:
            if not self.github_available:
                return self._get_local_games_without_stats_optimized(league)
            
            # Получаем файлы статистики одним запросом
            stats_files = set()
            try:
                contents = self.repo.get_contents(RESULT_IMAGES_DIR)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith((".jpg", ".jpeg", ".png")):
                        game_number = self.extract_game_number(item.name)
                        if game_number:
                            stats_files.add(game_number)
            except:
                pass  # Папка может не существовать
            
            # Получаем все игры
            all_games = []
            try:
                contents = self.repo.get_contents(GAMES_DIR_PATH)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith(".json"):
                        try:
                            # Проверяем, есть ли статистика
                            game_number = self.extract_game_number(item.name)
                            if game_number and game_number not in stats_files:
                                # Проверяем лигу если указана
                                if league:
                                    # Загружаем данные для проверки лиги
                                    file_content = base64.b64decode(item.content).decode('utf-8')
                                    game_data = json.loads(file_content)
                                    game_league = self.get_game_league(game_data)
                                    if game_league != league:
                                        continue
                                
                                all_games.append({
                                    'file_name': item.name,
                                    'game_number': game_number,
                                    'path': item.path
                                })
                        except:
                            continue
            except:
                pass
            
            # Сортируем по номеру игры (по убыванию)
            all_games.sort(key=lambda x: x['game_number'], reverse=True)
            return all_games[:5]  # Возвращаем только 5 последних
                
        except Exception as e:
            logger.error(f"Ошибка при получении игр без статистики (оптимизированно): {e}")
            return []

    def get_all_games_without_statistics(self):
        """Получить все игры без статистики (без фильтрации)"""
        try:
            # Получаем файлы статистики
            stats_files = set()
            try:
                contents = self.repo.get_contents(RESULT_IMAGES_DIR)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith((".jpg", ".jpeg", ".png")):
                        game_number = self.extract_game_number(item.name)
                        if game_number:
                            stats_files.add(game_number)
            except:
                pass  # Папка может не существовать
            
            # Получаем все игры
            all_games = []
            try:
                contents = self.repo.get_contents(GAMES_DIR_PATH)
                for item in contents:
                    if item.name.startswith("game_") and item.name.endswith(".json"):
                        game_number = self.extract_game_number(item.name)
                        if game_number and game_number not in stats_files:
                            # Загружаем данные для отображения
                            try:
                                file_content = base64.b64decode(item.content).decode('utf-8')
                                game_data = json.loads(file_content)
                                all_games.append({
                                    'file_name': item.name,
                                    'game_number': game_number,
                                    'data': game_data,
                                    'path': item.path
                                })
                            except:
                                # Если не удалось загрузить данные, добавляем без них
                                all_games.append({
                                    'file_name': item.name,
                                    'game_number': game_number,
                                    'path': item.path
                                })
            except:
                pass
            
            # Сортируем по номеру игры (по убыванию)
            all_games.sort(key=lambda x: x['game_number'], reverse=True)
            return all_games[:10]  # Возвращаем только 10 последних
            
        except Exception as e:
            logger.error(f"Ошибка при получении всех игр без статистики: {e}")
            return []

    def _get_local_games_without_stats_optimized(self, league=None):
        """Локальная оптимизированная версия"""
        try:
            stats_dir = RESULT_IMAGES_DIR
            games_dir = GAMES_DIR_PATH
            
            # Получаем файлы статистики
            stats_files = set()
            if os.path.exists(stats_dir):
                for filename in os.listdir(stats_dir):
                    if filename.startswith("game_") and filename.endswith((".jpg", ".jpeg", ".png")):
                        game_number = self.extract_game_number(filename)
                        if game_number:
                            stats_files.add(game_number)
            
            # Получаем игры без статистики
            games_without_stats = []
            if os.path.exists(games_dir):
                for filename in os.listdir(games_dir):
                    if filename.startswith("game_") and filename.endswith(".json"):
                        game_number = self.extract_game_number(filename)
                        if game_number and game_number not in stats_files:
                            if league:
                                # Проверяем лигу
                                file_path = os.path.join(games_dir, filename)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    game_data = json.load(f)
                                game_league = self.get_game_league(game_data)
                                if game_league != league:
                                    continue
                            
                            games_without_stats.append({
                                'file_name': filename,
                                'game_number': game_number,
                                'path': os.path.join(games_dir, filename)
                            })
            
            games_without_stats.sort(key=lambda x: x['game_number'], reverse=True)
            return games_without_stats[:5]
        except Exception as e:
            logger.error(f"Ошибка локального получения игр без статистики: {e}")
            return []