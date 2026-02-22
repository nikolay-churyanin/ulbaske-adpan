import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from config import *
from github_manager import GitHubManager
from utils.helpers import convert_to_timestamp, parse_user_info

logger = logging.getLogger(__name__)

class BasketballChampionshipBot:
    def __init__(self, token, github_manager):
        self.token = token
        self.github_manager = github_manager
        self.leagues = {}
        self.venues = []
        self.schedule_data = {"season": "2025-2026", "stages": []}
        self.leagues_config = {}
        self.pending_matches = []
        self.pending_results = []
        self.temp_files = []

        # Кэш для оптимизации поиска игр
        self._games_cache = None
        self._games_cache_timestamp = 0
        self._games_without_stats_cache = {}
        self._games_without_stats_cache_timestamp = {}
        
        # Кэш для номеров игр со статистикой
        self._games_with_stats_cache = None
        self._games_with_stats_cache_timestamp = 0
    
    def load_data_from_github(self):
        """Загрузка всех данных из GitHub"""
        try:
            teams_data = self.github_manager.get_teams_data()
            self.leagues = self.organize_teams_by_league(teams_data)
            
            self.venues = self.github_manager.get_venues_data()
            self.schedule_data = self.github_manager.get_schedule_data()
            
            # Загружаем конфигурацию лиг
            self.leagues_config = self.github_manager.get_leagues_config()
            
            logger.info("Данные успешно загружены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            return False
    
    def organize_teams_by_league(self, teams_data):
        """Организовать команды по лигам"""
        leagues = {}
        for team in teams_data:
            league_name = team.get('league', 'Без лиги')
            if league_name not in leagues:
                leagues[league_name] = {
                    "teams": [],
                    "full_data": []
                }
            leagues[league_name]["teams"].append(team['name'])
            leagues[league_name]["full_data"].append(team)
        return leagues
    
    def determine_game_type(self, league, team_home, team_away, date):
        """
        Определить тип игры (regular/playoff) на основе количества сыгранных матчей
        в регулярном сезоне для данной лиги
        """
        try:
            # Загружаем конфигурацию лиг
            leagues_config = self.github_manager.get_leagues_config()
            
            # Находим ID лиги по её названию
            league_id = None
            for lid, config in leagues_config.items():
                if lid == league:
                    league_id = lid
                    break
            
            if not league_id:
                logger.warning(f"Лига '{league}' не найдена в конфигурации, используется regular")
                return "regular"
            
            # Получаем количество кругов регулярного сезона
            regular_rounds = leagues_config[league_id].get('regularSeasonRounds', 1)
            
            # Получаем все команды лиги
            teams_in_league = self.leagues.get(league, {}).get('teams', [])
            num_teams = len(teams_in_league)
            
            if num_teams < 2:
                return "regular"
            
            # Количество матчей в регулярном сезоне для каждой команды
            # В двухкруговом турнире каждая команда играет с каждой дважды
            matches_per_team_in_regular = (num_teams - 1) * regular_rounds
            
            # Получаем ВСЕ сыгранные матчи (по наличию файлов в games/)
            all_played_games = self.get_all_games_cached()
            
            # Словарь для подсчета сыгранных матчей каждой команды
            team_played_matches = {team: 0 for team in teams_in_league}
            
            for game_info in all_played_games:
                game_data = game_info.get('data', {})
                match_info = game_data.get('match_info', {})
                
                # Получаем лигу из данных игры
                game_league = match_info.get('league') or match_info.get('competition', '')
                
                # Проверяем, относится ли игра к нужной лиге
                if game_league == league:
                    team_a = match_info.get('team_a', '')
                    team_b = match_info.get('team_b', '')
                    
                    if team_a in team_played_matches:
                        team_played_matches[team_a] += 1
                    if team_b in team_played_matches:
                        team_played_matches[team_b] += 1
            
            # Логируем статистику для отладки
            logger.info(f"Статистика сыгранных матчей для лиги '{league}' (определено по файлам в games/):")
            for team, played in team_played_matches.items():
                logger.info(f"  {team}: {played}/{matches_per_team_in_regular}")
            
            # Проверяем, завершен ли регулярный сезон для КАЖДОЙ команды
            regular_season_finished = True
            teams_not_finished = []
            
            for team, played in team_played_matches.items():
                if played < matches_per_team_in_regular:
                    regular_season_finished = False
                    teams_not_finished.append(f"{team} ({played}/{matches_per_team_in_regular})")
            
            if regular_season_finished:
                logger.info(f"✅ Регулярный сезон для лиги '{league}' завершен. Матч определяется как playoff")
                return "playoff"
            else:
                logger.info(f"❌ Регулярный сезон для лиги '{league}' не завершен. Не сыграли: {', '.join(teams_not_finished)}")
                return "regular"
                
        except Exception as e:
            logger.error(f"Ошибка при определении gameType для лиги '{league}': {e}")
            return "regular"

    def get_all_matches(self):
        """Получить все матчи из расписания в плоском формате"""
        all_matches = []
        for stage in self.schedule_data.get("stages", []):
            for game in stage.get("games", []):
                league = self.find_league_for_teams(game.get("teamHome"), game.get("teamAway"))
                match_info = {
                    'stage': stage.get('name', 'Неизвестный этап'),
                    'league': league,
                    'teamHome': game.get('teamHome'),
                    'teamAway': game.get('teamAway'),
                    'date': game.get('date'),
                    'time': game.get('time'),
                    'location': game.get('location'),
                    'datetime': f"{game.get('date')} {game.get('time')}",
                    'timestamp': convert_to_timestamp(game.get('date'), game.get('time'))
                }
                all_matches.append(match_info)
        return sorted(all_matches, key=lambda x: x['timestamp'])
    
    def find_league_for_teams(self, team1, team2):
        """Найти лигу для команд"""
        for league_name, league_data in self.leagues.items():
            if team1 in league_data["teams"] or team2 in league_data["teams"]:
                return league_name
        return "Неизвестная лига"

    def get_games_without_stats(self, league=None):
        """Получить игры без статистики с кэшированием"""
        cache_key = league or 'all'
        
        # Проверяем кэш (актуален в течение 30 секунд)
        current_time = time.time()
        if (cache_key in self._games_without_stats_cache and 
            current_time - self._games_without_stats_cache_timestamp.get(cache_key, 0) < 30):
            return self._games_without_stats_cache[cache_key]
        
        # Получаем игры со статистикой из кэша
        games_with_stats = self.get_games_with_statistics()
        
        # Получаем все игры из кэша
        all_games = self.get_all_games_cached()
        games_without_stats = []
        
        for game in all_games:
            game_number = self.github_manager.extract_game_number(game['file_name'])
            if game_number not in games_with_stats:
                # Проверяем лигу если указана
                if league:
                    game_league = self.github_manager.get_game_league(game.get('data', {}))
                    if game_league != league:
                        continue
                
                # Добавляем номер игры в объект для быстрого доступа
                game['game_number'] = game_number
                games_without_stats.append(game)
        
        # Сортируем по номеру игры (по убыванию - самые новые первые)
        games_without_stats.sort(key=lambda x: x['game_number'], reverse=True)
        
        # Сохраняем в кэш
        self._games_without_stats_cache[cache_key] = games_without_stats
        self._games_without_stats_cache_timestamp[cache_key] = current_time
        
        return games_without_stats[:5]  # Возвращаем только 5 последних игр
    
    def get_all_games_cached(self):
        """Получить все игры с кэшированием"""
        current_time = time.time()
        
        # Проверяем кэш (актуален в течение 60 секунд)
        if (self._games_cache is not None and 
            current_time - self._games_cache_timestamp < 60):
            return self._games_cache
        
        games = self.github_manager.get_all_games()
        
        # Сохраняем в кэш
        self._games_cache = games
        self._games_cache_timestamp = current_time
        
        return games
    
    def get_games_with_statistics(self):
        """Получить игры со статистикой с кэшированием"""
        current_time = time.time()
        
        # Проверяем кэш (актуален в течение 60 секунд)
        if (self._games_with_stats_cache is not None and 
            current_time - self._games_with_stats_cache_timestamp < 60):
            return self._games_with_stats_cache
        
        # Загружаем игры со статистикой
        games_with_stats = self.github_manager.get_games_with_statistics()
        
        # Сохраняем в кэш
        self._games_with_stats_cache = games_with_stats
        self._games_with_stats_cache_timestamp = current_time
        
        return games_with_stats
    
    def get_game_by_number_cached(self, game_number):
        """Получить игру по номеру с использованием кэша"""
        # Проверяем в кэше игр без статистики
        for cache_key in self._games_without_stats_cache:
            if cache_key in self._games_without_stats_cache:
                for game_info in self._games_without_stats_cache[cache_key]:
                    if game_info.get('game_number') == game_number:
                        return game_info
        
        # Если не нашли в кэше, ищем во всех играх
        all_games = self.get_all_games_cached()
        for game_info in all_games:
            if self.github_manager.extract_game_number(game_info['file_name']) == game_number:
                # Добавляем номер игры для быстрого доступа
                game_info['game_number'] = game_number
                return game_info
        
        # Если не нашли, загружаем напрямую
        filename = f"game_{game_number:03d}.json"
        game_data = self.github_manager._load_game_data(filename)
        if game_data:
            return {
                'file_name': filename,
                'data': game_data,
                'game_number': game_number,
                'path': f"{GAMES_DIR_PATH}/{filename}"
            }
        return None
    
    def update_games_cache_after_stats_added(self, game_number):
        """Обновить кэш после добавления статистики"""
        # Обновляем кэш игр со статистикой
        if self._games_with_stats_cache is not None:
            self._games_with_stats_cache.add(game_number)
        
        # Обновляем кэш игр без статистики
        for key in list(self._games_without_stats_cache.keys()):
            if key in self._games_without_stats_cache:
                self._games_without_stats_cache[key] = [
                    game for game in self._games_without_stats_cache[key] 
                    if game.get('game_number') != game_number
                ]

    def get_games_without_stats_optimized(self, league=None):
        """Оптимизированное получение игр без статистики"""
        cache_key = league or 'all'
        current_time = time.time()
        
        # Проверяем кэш (актуален в течение 30 секунд)
        if (cache_key in self._games_without_stats_cache and 
            current_time - self._games_without_stats_cache_timestamp.get(cache_key, 0) < 30):
            cached_games = self._games_without_stats_cache[cache_key]
            # Убедимся, что у всех игр есть данные
            for game_info in cached_games:
                if 'data' not in game_info:
                    game_data = self.github_manager._load_game_data(game_info['file_name'])
                    if game_data:
                        game_info['data'] = game_data
            return cached_games
        
        # Используем оптимизированный метод
        games_without_stats = self.github_manager.get_games_without_statistics_optimized(league)
        
        # Дозагружаем данные для отображения
        for game_info in games_without_stats:
            if 'data' not in game_info:
                game_data = self.github_manager._load_game_data(game_info['file_name'])
                if game_data:
                    game_info['data'] = game_data
        
        # Сохраняем в кэш
        self._games_without_stats_cache[cache_key] = games_without_stats
        self._games_without_stats_cache_timestamp[cache_key] = current_time
        
        return games_without_stats

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
        except:
            return None

    def has_games_without_stats(self, league=None):
        """Быстрая проверка наличия игр без статистики"""
        try:
            # Получаем игры со статистикой из кэша
            games_with_stats = self.get_games_with_statistics()
            
            # Получаем все номера игр из папки games
            all_game_numbers = set()
            for filename in os.listdir(GAMES_DIR_PATH) if os.path.exists(GAMES_DIR_PATH) else []:
                if filename.startswith("game_") and filename.endswith(".json"):
                    game_number = self.github_manager.extract_game_number(filename)
                    if game_number:
                        all_game_numbers.add(game_number)
            
            # Быстро проверяем, есть ли игры без статистики
            for game_number in all_game_numbers:
                if game_number not in games_with_stats:
                    return True
            return False
        except:
            return False

    def get_all_games_without_stats(self):
        """Получить все игры без статистики (без фильтрации по лигам)"""
        cache_key = 'all_games_no_stats'
        
        # Проверяем кэш (актуален в течение 30 секунд)
        current_time = time.time()
        if (cache_key in self._games_without_stats_cache and 
            current_time - self._games_without_stats_cache_timestamp.get(cache_key, 0) < 30):
            return self._games_without_stats_cache[cache_key]
        
        # Получаем игры со статистикой из кэша
        games_with_stats = self.get_games_with_statistics()
        
        # Получаем все игры из кэша
        all_games = self.get_all_games_cached()
        games_without_stats = []
        
        for game in all_games:
            game_number = self.github_manager.extract_game_number(game['file_name'])
            if game_number not in games_with_stats:
                # Добавляем номер игры в объект для быстрого доступа
                game['game_number'] = game_number
                games_without_stats.append(game)
        
        # Сортируем по номеру игры (по убыванию - самые новые первые)
        games_without_stats.sort(key=lambda x: x['game_number'], reverse=True)
        
        # Сохраняем в кэш
        self._games_without_stats_cache[cache_key] = games_without_stats
        self._games_without_stats_cache_timestamp[cache_key] = current_time
        
        return games_without_stats[:10]  # Возвращаем только 10 последних игр