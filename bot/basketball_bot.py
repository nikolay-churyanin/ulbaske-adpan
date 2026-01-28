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
        
        # Загружаем игры
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
        all_games = self.get_all_games_cached()
        for game_info in all_games:
            if self.github_manager.extract_game_number(game_info['file_name']) == game_number:
                return game_info
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