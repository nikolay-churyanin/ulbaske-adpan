import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import *
from github_manager import GitHubManager
from bot.basketball_bot import BasketballChampionshipBot
from bot.handlers.main_handlers import MainHandlers
from bot.handlers.match_handlers import MatchHandlers
from bot.handlers.result_handlers import ResultHandlers
from bot.handlers.schedule_handlers import ScheduleHandlers
from bot.handlers.venue_handlers import VenueHandlers
from bot.handlers.league_handlers import LeagueHandlers
from bot.handlers.edit_handlers import EditHandlers
from bot.handlers.stats_handlers import StatsHandlers
from utils.helpers import parse_user_info

# Настройка логирования
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)

logger = logging.getLogger(__name__)

class BotApplication:
    def __init__(self):
        self.github_manager = GitHubManager(GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
        self.bot = BasketballChampionshipBot(TELEGRAM_TOKEN, self.github_manager)
        
        # Инициализация обработчиков
        self.main_handlers = MainHandlers(self.bot)
        self.match_handlers = MatchHandlers(self.bot)
        self.result_handlers = ResultHandlers(self.bot)
        self.schedule_handlers = ScheduleHandlers(self.bot)
        self.venue_handlers = VenueHandlers(self.bot)
        self.league_handlers = LeagueHandlers(self.bot)
        self.edit_handlers = EditHandlers(self.bot)
        self.stats_handlers = StatsHandlers(self.bot)
        
        self.application = None
    
    async def handle_reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset для сброса состояний"""
        from bot.handlers.main_handlers import MainHandlers
        main_handlers = MainHandlers(self.bot)
        main_handlers._clear_user_states(context)
        
        await update.message.reply_text("✅ Все состояния сброшены!")
        await main_handlers.show_main_menu(update, context)

    def setup_handlers(self):
        """Настройка всех обработчиков"""
        # Главное меню
        self.application.add_handler(CommandHandler("start", self.main_handlers.start))
        self.application.add_handler(CommandHandler("reset", self.handle_reset_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        # Обработчики статистики
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Центральный обработчик callback запросов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Обработка основных действий
        if data == "refresh_data":
            await self.main_handlers.handle_refresh_data(query, context)
        elif data == "back_to_menu":
            await self.main_handlers.show_main_menu(query, context, is_query=True)
        elif data == "select_league":
            await self.match_handlers.show_league_selection(query, context, "add_match")
        elif data == "add_result":
            await self.result_handlers.show_matches_for_result(query, context)
        elif data == "show_schedule_menu":
            await self.schedule_handlers.show_schedule_menu(query, context)
        elif data == "league_management":
            await self.league_handlers.show_league_management(query, context)
        elif data == "show_venues":
            await self.venue_handlers.show_venues_management(query, context)
        
        elif data == "stats_menu":
            await self.stats_handlers.show_stats_menu(query, context)
        elif data == "stats_refresh":
            await self.stats_handlers.refresh_stats_list(query, context)
        elif data.startswith("select_stats_game_"):
            game_number = int(data.replace("select_stats_game_", ""))
            await self.stats_handlers.handle_game_selection_for_stats(query, context, game_number)
        
        elif data.startswith("quick_date_"):
            selected_date = data.replace("quick_date_", "")
            await self.match_handlers.handle_quick_date_selection(query, context, selected_date)
        elif data.startswith("quick_time_"):
            selected_time = data.replace("quick_time_", "")
            await self.match_handlers.handle_quick_time_selection(query, context, selected_time)
        elif data == "manual_date_input":
            await self.match_handlers.request_manual_date_input(query, context)
        elif data == "manual_time_input":
            await self.match_handlers.request_manual_time_input(query, context)

        # Обработка лиг
        elif data.startswith("league_"):
            await self.match_handlers.handle_league_selection(query, context, data)
        elif data.startswith("select_team1_"):
            parts = data.split("_")
            league = context.user_data['current_league']
            team1 = "_".join(parts[2:])
            context.user_data['team1'] = team1
            await self.match_handlers.show_team_selection(query, context, "team2", league, team1)
        elif data.startswith("select_team2_"):
            parts = data.split("_")
            league = context.user_data['current_league']
            team2 = "_".join(parts[2:])
            context.user_data['team2'] = team2
            await self.match_handlers.show_venue_selection(query, context)
        elif data.startswith("select_venue_"):
            parts = data.split("_")
            venue = "_".join(parts[2:])
            context.user_data['venue'] = venue
            await self.match_handlers.request_date_input(query, context)
        
        # Обработка расписания
        elif data == "schedule_all":
            await self.schedule_handlers.show_full_schedule(query, context)
        elif data == "select_league_schedule":
            await self.match_handlers.show_league_selection(query, context, "view_schedule")
        elif data.startswith("schedule_"):
            league_name = data.replace("schedule_", "")
            await self.schedule_handlers.show_league_schedule(query, context, league_name)
        elif data == "show_pending_matches":
            await self.schedule_handlers.show_pending_matches(query, context)
        elif data == "show_pending_results":
            await self.schedule_handlers.show_pending_results(query, context)
        
        # Обработка результатов
        elif data.startswith("result_"):
            match_index = int(data.replace("result_", ""))
            await self.result_handlers.request_score_input(query, context, match_index)
        
        # Обработка залов
        elif data == "add_venue":
            await self.venue_handlers.request_new_venue_name(query, context)
        elif data == "delete_venue_menu":
            await self.venue_handlers.show_venues_for_deletion(query, context)
        elif data.startswith("delete_venue_"):
            venue_index = int(data.replace("delete_venue_", ""))
            await self.venue_handlers.delete_venue(query, context, venue_index)
        
        # Обработка лиг (просмотр команд)
        elif data.startswith("view_teams_"):
            league_name = data.replace("view_teams_", "")
            await self.league_handlers.show_league_teams(query, context, league_name)
        
        # Обработка применения изменений
        elif data == "apply_changes":
            await self.apply_pending_changes(query, context)
        elif data == "select_season":
            await self.main_handlers.show_season_selection(query, context)
        elif data.startswith("season_"):
            await self.main_handlers.handle_season_selection(query, context, data.replace("season_", ""))

        # Обработка редактирования расписания
        elif data == "edit_schedule_menu":
            await self.edit_handlers.show_schedule_for_editing(query, context)
        elif data.startswith("edit_"):
            if data.startswith("edit_select_venue_"):
                new_venue = data.replace("edit_select_venue_", "")
                await self.edit_handlers.handle_venue_edit(query, context, new_venue)
            elif data in ["edit_venue", "edit_datetime", "edit_all"]:
                await self.edit_handlers.handle_edit_selection(query, context, data)
            else:
                # edit_{index} - выбор матча для редактирования
                match_index = int(data.replace("edit_", ""))
                await self.edit_handlers.show_edit_options(query, context, match_index)

        # Обработка удаления матча ← ДОБАВЛЕНО
        elif data.startswith("delete_"):
            # Проверяем, это удаление из меню редактирования или обычное
            if 'current_edit_match' in context.user_data:
                match_index = int(data.replace("delete_", ""))
                await self.edit_handlers.delete_match(query, context, match_index)
            else:
                # Обычное удаление (старый функционал)
                match_index = int(data.replace("delete_", ""))
                await self.delete_match_from_schedule(query, context, match_index)

        # Обработка нового результата матча
        elif data == "add_result_new_match":
            await self.result_handlers.show_new_match_result_menu(query, context)
        elif data == "new_result_select_league":
            await self.result_handlers.show_league_selection_for_new_result(query, context)
        elif data.startswith("new_result_league_"):
            league_name = data.replace("new_result_league_", "")
            await self.result_handlers.handle_league_selection_for_new_result(query, context, league_name)
        elif data.startswith("new_result_team1_"):
            parts = data.split("_")
            league = context.user_data['new_result_league']
            team1 = "_".join(parts[3:])  # new_result_team1_TeamName
            context.user_data['new_result_team1'] = team1
            await self.result_handlers.show_team_selection_for_new_result(query, context, "new_result_team2", league, team1)
        elif data.startswith("new_result_team2_"):
            parts = data.split("_")
            league = context.user_data['new_result_league']
            team2 = "_".join(parts[3:])  # new_result_team2_TeamName
            context.user_data['new_result_team2'] = team2
            await self.result_handlers.show_venue_selection_for_new_result(query, context)
        elif data.startswith("new_result_venue_"):
            parts = data.split("_")
            venue = "_".join(parts[3:])  # new_result_venue_VenueName
            context.user_data['new_result_venue'] = venue
            await self.result_handlers.request_date_for_new_result(query, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Центральный обработчик текстовых сообщений"""
        try:
            if context.user_data.get('waiting_for_date'):
                await self.match_handlers.handle_date_input(update, context)
            elif context.user_data.get('waiting_for_score'):
                await self.result_handlers.handle_score_input(update, context)
            elif context.user_data.get('waiting_for_venue_name'):
                await self.venue_handlers.handle_venue_name_input(update, context)
            elif context.user_data.get('waiting_for_edit_date'):
                await self.edit_handlers.handle_edit_date_input(update, context)
            elif context.user_data.get('waiting_for_time'):
                await self.match_handlers.handle_time_input(update, context)
            elif context.user_data.get('waiting_for_new_match_date'):
                await self.result_handlers.handle_new_match_date_input(update, context)
            elif context.user_data.get('waiting_for_new_match_score'):
                await self.result_handlers.handle_new_match_score_input(update, context)
            # Не добавляем сюда обработку waiting_for_stats_image - она обрабатывается в handle_photo_message
            else:
                # Если бот не ожидает ввода, показываем главное меню
                from bot.handlers.main_handlers import MainHandlers
                main_handlers = MainHandlers(self.bot)
                await main_handlers.show_main_menu(update, context)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            # При ошибке сбрасываем состояния и показываем меню
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            main_handlers._clear_user_states(context)
            await update.message.reply_text(
                "❌ Произошла ошибка. Состояние сброшено.\n"
                "Попробуйте снова."
            )
            await main_handlers.show_main_menu(update, context)
    
    async def apply_pending_changes(self, query, context):
        """Применить ожидающие изменения в games.json текущего сезона"""
        if not self.bot.pending_matches and not self.bot.pending_results:
            await query.edit_message_text("❌ Нет ожидающих изменений!")
            await self.main_handlers.show_main_menu(query, context, is_query=True)
            return

        user = query.from_user
        username = parse_user_info(user)
        added_matches = 0
        added_results = 0

        for match in self.bot.pending_matches:
            game_id, _ = self.bot.github_manager.next_game_id(self.bot.games)
            self.bot.games.append({
                "id": game_id,
                "match_info": {
                    "team_a": match["teamHome"],
                    "team_b": match["teamAway"],
                    "date": match["date"],
                    "time": match["time"],
                    "venue": match["location"],
                    "league": match["league"],
                    "gameType": match.get("gameType") or "regular"
                }
            })
            added_matches += 1
        self.bot.pending_matches = []

        for result in self.bot.pending_results:
            info = result.get("match_info") or {}
            updated = self.bot.update_game_fields(
                {
                    "id": result.get("game_id") or info.get("id"),
                    "teamHome": info.get("team_a") or info.get("teamHome"),
                    "teamAway": info.get("team_b") or info.get("teamAway"),
                    "date": info.get("date"),
                    "time": info.get("time")
                },
                score=info.get("score")
            )
            if not updated:
                game_id, _ = self.bot.github_manager.next_game_id(self.bot.games)
                self.bot.games.append({
                    "id": game_id,
                    "match_info": {
                        "team_a": info.get("team_a") or info.get("teamHome"),
                        "team_b": info.get("team_b") or info.get("teamAway"),
                        "score": info.get("score"),
                        "date": info.get("date"),
                        "time": info.get("time"),
                        "venue": info.get("venue") or info.get("location"),
                        "league": info.get("league"),
                        "gameType": info.get("gameType") or "regular"
                    }
                })
            added_results += 1
        self.bot.pending_results = []

        parts = []
        if added_matches:
            parts.append(f"матчей: {added_matches}")
        if added_results:
            parts.append(f"результатов: {added_results}")
        commit_message = f"Обновлён games.json ({', '.join(parts)}) | {username}"

        if self.bot.save_games(commit_message):
            await query.edit_message_text(
                "✅ Изменения сохранены в games.json сезона "
                f"{self.bot.season_label()}!\n\n"
                + "\n".join([f"• {part}" for part in parts])
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при сохранении! Изменения не применены.\n"
                "Попробуйте позже."
            )

        await self.main_handlers.show_main_menu(query, context, is_query=True)

    async def delete_match_from_schedule(self, query, context, match_index):
        """Удалить матч из games.json"""
        try:
            all_matches = self.bot.get_all_matches()
            if 0 <= match_index < len(all_matches):
                match_to_delete = all_matches[match_index]
                if self.bot.delete_game(match_to_delete):
                    user = query.from_user
                    username = parse_user_info(user)
                    commit_message = (
                        f"Удалён матч: {match_to_delete['teamHome']} vs {match_to_delete['teamAway']} "
                        f"| {username}"
                    )
                    success = self.bot.save_games(commit_message)
                    await query.edit_message_text("✅ Матч удален!" if success else "❌ Ошибка при сохранении!")
                else:
                    await query.edit_message_text("❌ Матч не найден в games.json!")
                await self.main_handlers.show_main_menu_after_query(query, context)
            else:
                await query.edit_message_text("❌ Матч не найден!")
        except Exception as e:
            logger.error(f"Ошибка при удалении матча: {e}")
            await query.edit_message_text("❌ Произошла ошибка при удалении!")

    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик фотографий (для статистики)"""
        if context.user_data.get('waiting_for_stats_image'):
            await self.stats_handlers.handle_stats_image_input(update, context)
        else:
            # Если фотография отправлена не в контексте добавления статистики
            await update.message.reply_text(
                "📎 Получено изображение.\n"
                "Для добавления статистики к игре используйте меню '📊 Управление статистикой'."
            )
            await self.main_handlers.show_main_menu(update, context)

    def run(self):
        """Запуск бота"""
        # Загружаем данные при старте
        self.bot.load_data_from_github()
        
        # Создание приложения
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Настройка обработчиков
        self.setup_handlers()
        
        # Запуск бота
        logger.info("Бот запущен...")
        self.application.run_polling()

def main():
    """Запуск бота"""
    app = BotApplication()
    app.run()

if __name__ == "__main__":
    main()