import logging
import time
from utils.helpers import convert_to_timestamp, game_has_score

logger = logging.getLogger(__name__)


class BasketballChampionshipBot:
    def __init__(self, token, github_manager):
        self.token = token
        self.github_manager = github_manager
        self.leagues = {}
        self.venues = []
        self.games = []
        self.leagues_config = {}
        self.pending_matches = []
        self.pending_results = []
        self._games_cache = None
        self._games_cache_timestamp = 0
        self._games_without_stats_cache = {}
        self._games_without_stats_cache_timestamp = {}
        self._games_with_stats_cache = None
        self._games_with_stats_cache_timestamp = 0

    def load_data_from_github(self, season_id=None):
        try:
            catalog = self.github_manager.load_catalog()
            resolved = self.github_manager.resolve_season_id(season_id or self.github_manager.season_id)
            if not resolved:
                logger.error("Не найден ни один сезон в data/seasons.json")
                return False

            self.github_manager.set_season(resolved)
            self.leagues_config = self.github_manager.get_leagues_config()
            teams_data = self.github_manager.get_teams_data()
            self.leagues = self.organize_teams_by_league(teams_data)
            self.venues = self.github_manager.get_venues_data() or []
            self.games = self.github_manager.get_games()
            self._invalidate_caches()
            logger.info("Данные сезона %s загружены", resolved)
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            return False

    def season_label(self):
        meta = self.github_manager.season_meta()
        label = meta.get("label") or self.github_manager.season_id
        if meta.get("archived"):
            return f"{label} (архив)"
        return label

    def league_label(self, league_id):
        config = (self.leagues_config or {}).get(league_id) or {}
        if config.get("name"):
            return config["name"]
        league = self.leagues.get(league_id) or {}
        return league.get("name") or league_id

    def organize_teams_by_league(self, teams_data):
        leagues = {}
        for league_id, config in (self.leagues_config or {}).items():
            leagues[league_id] = {
                "id": league_id,
                "name": config.get("name") or league_id,
                "teams": [],
                "full_data": []
            }

        for team in teams_data or []:
            league_id = team.get("league")
            if not league_id:
                continue
            if league_id not in leagues:
                leagues[league_id] = {
                    "id": league_id,
                    "name": league_id,
                    "teams": [],
                    "full_data": []
                }
            leagues[league_id]["teams"].append(team["name"])
            leagues[league_id]["full_data"].append(team)
        return leagues

    def expected_regular_games_per_team(self, league):
        config = (self.leagues_config or {}).get(league) or {}
        teams_in_league = self.leagues.get(league, {}).get("teams", [])
        num_teams = len(teams_in_league)
        if num_teams < 2:
            return 0

        kind = config.get("format") or "round"
        settings = config.get(kind) or {}

        if kind == "split-groups":
            stage1_rounds = int(settings.get("stage1Rounds") or 1)
            group_rounds = int(settings.get("groupRounds") or 1)
            groups = settings.get("groups") or []
            group_size = int(groups[0].get("size") or 0) if groups else 0
            extra = (group_size - 1) * group_rounds if group_size >= 2 else 0
            return (num_teams - 1) * stage1_rounds + extra

        regular_rounds = int(settings.get("numberOfRounds") or 1)
        return (num_teams - 1) * regular_rounds

    def determine_game_type(self, league, team_home, team_away, date):
        try:
            teams_in_league = self.leagues.get(league, {}).get("teams", [])
            num_teams = len(teams_in_league)
            if num_teams < 2:
                return "regular"

            matches_per_team = self.expected_regular_games_per_team(league)
            team_played = {team: 0 for team in teams_in_league}

            for game in self.games:
                info = game.get("match_info") or {}
                if info.get("league") != league or not game_has_score(info):
                    continue
                team_a = info.get("team_a", "")
                team_b = info.get("team_b", "")
                if team_a in team_played:
                    team_played[team_a] += 1
                if team_b in team_played:
                    team_played[team_b] += 1

            if matches_per_team and all(played >= matches_per_team for played in team_played.values()):
                return "playoff"
            return "regular"
        except Exception as e:
            logger.error(f"Ошибка при определении gameType для лиги '{league}': {e}")
            return "regular"

    def get_all_matches(self):
        """Несыгранные матчи текущего сезона (без счёта)."""
        matches = []
        for game in self.games:
            info = game.get("match_info") or {}
            if game_has_score(info):
                continue
            date = info.get("date")
            time_str = info.get("time") or "12:00"
            league = info.get("league")
            matches.append({
                "id": game.get("id"),
                "stage": "Плей-офф" if info.get("gameType") == "playoff" else "Регулярный сезон",
                "league": league,
                "teamHome": info.get("team_a"),
                "teamAway": info.get("team_b"),
                "date": date,
                "time": time_str,
                "location": info.get("venue") or info.get("location"),
                "datetime": f"{date} {time_str}",
                "timestamp": convert_to_timestamp(date, time_str),
                "gameType": info.get("gameType") or "regular"
            })
        return sorted(matches, key=lambda item: item["timestamp"])

    def find_game_index(self, game_id=None, team_home=None, team_away=None, date=None, time_str=None):
        for index, game in enumerate(self.games):
            if game_id and game.get("id") == game_id:
                return index
            info = game.get("match_info") or {}
            if (
                team_home and team_away and date and time_str and
                info.get("team_a") == team_home and
                info.get("team_b") == team_away and
                info.get("date") == date and
                info.get("time") == time_str
            ):
                return index
        return None

    def update_game_fields(self, match, **fields):
        index = self.find_game_index(
            game_id=match.get("id"),
            team_home=match.get("teamHome"),
            team_away=match.get("teamAway"),
            date=match.get("date"),
            time_str=match.get("time")
        )
        if index is None:
            return False
        info = self.games[index].setdefault("match_info", {})
        if "location" in fields and fields["location"] is not None:
            info["venue"] = fields["location"]
        if "date" in fields and fields["date"] is not None:
            info["date"] = fields["date"]
        if "time" in fields and fields["time"] is not None:
            info["time"] = fields["time"]
        if "score" in fields and fields["score"] is not None:
            info["score"] = fields["score"]
        return True

    def delete_game(self, match):
        index = self.find_game_index(
            game_id=match.get("id"),
            team_home=match.get("teamHome"),
            team_away=match.get("teamAway"),
            date=match.get("date"),
            time_str=match.get("time")
        )
        if index is None:
            return False
        self.games.pop(index)
        return True

    def save_games(self, commit_message):
        success = self.github_manager.save_games(self.games, commit_message)
        if success:
            self._invalidate_caches()
        return success

    def get_all_games_cached(self):
        current_time = time.time()
        if self._games_cache is not None and current_time - self._games_cache_timestamp < 60:
            return self._games_cache
        games = self.github_manager.get_all_games()
        self._games_cache = games
        self._games_cache_timestamp = current_time
        return games

    def get_games_with_statistics(self):
        current_time = time.time()
        if (
            self._games_with_stats_cache is not None and
            current_time - self._games_with_stats_cache_timestamp < 60
        ):
            return self._games_with_stats_cache
        games_with_stats = self.github_manager.get_games_with_statistics()
        self._games_with_stats_cache = games_with_stats
        self._games_with_stats_cache_timestamp = current_time
        return games_with_stats

    def get_all_games_without_stats(self):
        current_time = time.time()
        cache_key = "all_games_no_stats"
        if (
            cache_key in self._games_without_stats_cache and
            current_time - self._games_without_stats_cache_timestamp.get(cache_key, 0) < 30
        ):
            return self._games_without_stats_cache[cache_key]

        games_with_stats = self.get_games_with_statistics()
        games_without_stats = []
        for game in self.get_all_games_cached():
            info = (game.get("data") or {}).get("match_info") or {}
            if not game_has_score(info):
                continue
            game_number = game.get("game_number") or self.github_manager.extract_game_number(game.get("id"))
            if game_number and game_number not in games_with_stats:
                game["game_number"] = game_number
                games_without_stats.append(game)

        games_without_stats.sort(key=lambda item: item.get("game_number") or 0, reverse=True)
        result = games_without_stats[:10]
        self._games_without_stats_cache[cache_key] = result
        self._games_without_stats_cache_timestamp[cache_key] = current_time
        return result

    def get_game_by_number_cached(self, game_number):
        for game in self.get_all_games_cached():
            number = game.get("game_number") or self.github_manager.extract_game_number(game.get("id"))
            if number == game_number:
                game["game_number"] = number
                return game
        return None

    def update_games_cache_after_stats_added(self, game_number):
        if self._games_with_stats_cache is not None:
            self._games_with_stats_cache.add(game_number)
        for key in list(self._games_without_stats_cache.keys()):
            self._games_without_stats_cache[key] = [
                game for game in self._games_without_stats_cache[key]
                if game.get("game_number") != game_number
            ]

    def _invalidate_caches(self):
        self._games_cache = None
        self._games_cache_timestamp = 0
        self._games_without_stats_cache = {}
        self._games_without_stats_cache_timestamp = {}
        self._games_with_stats_cache = None
        self._games_with_stats_cache_timestamp = 0
