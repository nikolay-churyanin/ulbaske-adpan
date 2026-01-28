from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class LeagueHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_league_management(self, query, context):
        """Показать управление лигами"""
        if not self.bot.leagues:
            await query.edit_message_text("❌ Нет данных о лигам!")
            return
        
        keyboard = []
        for league_name in self.bot.leagues.keys():
            team_count = len(self.bot.leagues[league_name]["teams"])
            keyboard.append([InlineKeyboardButton(
                f"👥 {league_name} ({team_count} команд)", 
                callback_data=f"view_teams_{league_name}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏆 Управление лигами\n\nВыберите лигу для просмотра команд:",
            reply_markup=reply_markup
        )
    
    async def show_league_teams(self, query, context, league_name):
        """Показать команды лиги"""
        if league_name not in self.bot.leagues:
            await query.edit_message_text("❌ Лига не найдена!")
            return
        
        league_data = self.bot.leagues[league_name]
        
        teams_text = "👥 Команды:\n"
        for team in league_data["full_data"]:
            city = team.get('city', 'Не указан')
            teams_text += f"• {team['name']} ({city})\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="league_management")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏆 Лига: {league_name}\n\n{teams_text}",
            reply_markup=reply_markup
        )