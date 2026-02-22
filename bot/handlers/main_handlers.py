from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class MainHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        # Сбрасываем все состояния пользователя
        self._clear_user_states(context)
        
        success = self.bot.load_data_from_github()
        
        if success:
            status_msg = "✅ Данные успешно загружены!"
            if not self.bot.github_manager.github_available:
                status_msg += " (используется локальное хранение)"
            await update.message.reply_text(status_msg)
            await self.show_main_menu(update, context)
        else:
            keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data="refresh_data")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ Не удалось загрузить данные. Проверьте настройки и попробуйте снова.",
                reply_markup=reply_markup
            )
        
    async def show_main_menu(self, update, context, is_query=False):
        """Показать главное меню"""
        pending_matches_count = len(self.bot.pending_matches)
        pending_results_count = len(self.bot.pending_results)
        
        all_matches = self.bot.get_all_matches()
        
        keyboard = [
            [InlineKeyboardButton("📅 Добавить матч", callback_data="select_league")],
            [InlineKeyboardButton("🏀 Внести результат", callback_data="add_result")],
            [InlineKeyboardButton("📊 Управление статистикой", callback_data="stats_menu")],
            [InlineKeyboardButton("📋 Показать расписание", callback_data="show_schedule_menu")],
            [InlineKeyboardButton("🏆 Управление лигами", callback_data="league_management")],
            [InlineKeyboardButton("🏟️ Список залов", callback_data="show_venues")],
        ]
        
        if pending_matches_count > 0 or pending_results_count > 0:
            keyboard.insert(3, [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")])
        
        keyboard.append([InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh_data")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        total_matches = len(all_matches)
        matches_by_league = {}
        for match in all_matches:
            league = match['league']
            matches_by_league[league] = matches_by_league.get(league, 0) + 1
        
        text = (
            "🏀 Добро пожаловать в бот чемпионата по баскетболу!\n\n"
            f"📊 Сезон: {self.bot.schedule_data.get('season', 'Не указан')}\n"
            "📊 Статистика:\n"
            f"• Всего матчей: {total_matches}\n"
            f"• Доступных залов: {len(self.bot.venues)}\n"
        )
        
        if pending_matches_count > 0:
            text += f"• ⏳ Ожидают применения: {pending_matches_count}\n"
        if pending_results_count > 0:
            text += f"• 🏀 Ожидают результатов: {pending_results_count}\n"
            
        text += "• Лиги и команды:\n"
        
        for league_name, league_data in self.bot.leagues.items():
            match_count = matches_by_league.get(league_name, 0)
            text += f"  - {league_name}: {len(league_data['teams'])} команд, {match_count} матчей\n"
        
        text += "\nВыберите действие:"
        
        if is_query:
            await update.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_main_menu_after_query(self, query, context):
        """Показать главное меню после callback запроса"""
        await self.show_main_menu(query, context, is_query=True)

    async def handle_refresh_data(self, query, context):
        """Обработчик обновления данных"""
        # Сбрасываем все состояния пользователя
        self._clear_user_states(context)
        
        success = self.bot.load_data_from_github()
        if success:
            status_msg = "✅ Данные обновлены!"
            if not self.bot.github_manager.github_available:
                status_msg += " (локальное хранение)"
            await query.edit_message_text(status_msg)
        else:
            await query.edit_message_text("❌ Не удалось обновить данные!")
        await self.show_main_menu(query, context, is_query=True)

    def _clear_user_states(self, context):
        """Очистить все состояния пользователя"""
        states_to_clear = [
            'waiting_for_date', 'waiting_for_score', 'waiting_for_venue_name',
            'waiting_for_edit_date', 'waiting_for_time', 'waiting_for_new_match',
            'waiting_state_time', 'new_match_result', 'current_league', 'team1',
            'team2', 'venue', 'selected_date', 'current_edit_match', 
            'current_edit_index', 'matches_for_editing',
            'available_matches_for_result', 'current_match_for_result',
            'waiting_for_stats_image', 'selected_game_for_stats',  # убрали stats_league
            'new_result_league', 'new_result_team1', 'new_result_team2',
            'new_result_venue', 'new_result_date', 'new_result_time',
            'new_result_username', 'new_result_gameType'
        ]
        
        for state in states_to_clear:
            context.user_data.pop(state, None)
        
        logger.info(f"Состояния пользователя очищены")