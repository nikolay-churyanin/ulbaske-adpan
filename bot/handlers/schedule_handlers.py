from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class ScheduleHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_schedule_menu(self, query, context):
        """Показать меню расписания"""
        pending_matches_count = len(self.bot.pending_matches)
        pending_results_count = len(self.bot.pending_results)
        
        keyboard = [
            [InlineKeyboardButton("📋 Все матчи", callback_data="schedule_all")],
            [InlineKeyboardButton("🏆 По лигам", callback_data="select_league_schedule")],
            [InlineKeyboardButton("✏️ Редактировать расписание", callback_data="edit_schedule_menu")],  # ← ДОБАВЛЕНО
        ]
        
        if pending_matches_count > 0:
            keyboard.append([InlineKeyboardButton("👀 Показать ожидающие матчи", callback_data="show_pending_matches")])
        
        if pending_results_count > 0:
            keyboard.append([InlineKeyboardButton("👀 Показать ожидающие результаты", callback_data="show_pending_results")])
        
        if pending_matches_count > 0 or pending_results_count > 0:
            keyboard.append([InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        all_matches = self.bot.get_all_matches()
        total_matches = len(all_matches)
        matches_by_league = {}
        
        for match in all_matches:
            league = match['league']
            matches_by_league[league] = matches_by_league.get(league, 0) + 1
        
        schedule_text = "📊 Статистика расписания:\n"
        schedule_text += f"• Всего матчей: {total_matches}\n"
        schedule_text += f"• Ожидающих матчей: {pending_matches_count}\n"
        schedule_text += f"• Ожидающих результатов: {pending_results_count}\n"
        for league, count in matches_by_league.items():
            schedule_text += f"• {league}: {count} матчей\n"
        
        await query.edit_message_text(
            f"{schedule_text}\nВыберите вариант просмотра:",
            reply_markup=reply_markup
        )
    
    async def show_full_schedule(self, query, context):
        """Показать полное расписание всех лиг"""
        pending_matches_count = len(self.bot.pending_matches)
        pending_results_count = len(self.bot.pending_results)
        
        pending_info = ""
        if pending_matches_count > 0:
            pending_info += f"\n⏳ Ожидают применения: {pending_matches_count} матчей"
        if pending_results_count > 0:
            pending_info += f"\n🏀 Ожидают результатов: {pending_results_count} матчей"
        
        all_matches = self.bot.get_all_matches()
        
        if not all_matches and not self.bot.pending_matches:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📋 Расписание пусто.\nДобавьте первый матч!",
                reply_markup=reply_markup
            )
            return
        
        schedule_text = f"🏀 Полное расписание матчей:{pending_info}\n\n"
        current_stage = None
        
        for i, match in enumerate(all_matches, 1):
            if match['stage'] != current_stage:
                current_stage = match['stage']
                schedule_text += f"\n🎯 {current_stage}:\n"
            
            schedule_text += (
                f"  {i}. {match['teamHome']} vs {match['teamAway']}\n"
                f"     🏟️ {match['location']}\n"
                f"     📅 {match['date']} {match['time']}\n"
                f"     🏆 {match['league']}\n\n"
            )
        
        keyboard = []
        
        if pending_matches_count > 0 or pending_results_count > 0:
            keyboard.append([InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(schedule_text, reply_markup=reply_markup)
    
    async def show_league_schedule(self, query, context, league_name):
        """Показать расписание конкретной лиги"""
        all_matches = self.bot.get_all_matches()
        league_matches = [match for match in all_matches if match['league'] == league_name]
        
        if not league_matches:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="select_league_schedule")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📋 В лиге '{league_name}' пока нет матчей.",
                reply_markup=reply_markup
            )
            return
        
        schedule_text = f"🏀 Расписание лиги '{league_name}':\n\n"
        for i, match in enumerate(league_matches, 1):
            schedule_text += (
                f"{i}. {match['teamHome']} vs {match['teamAway']}\n"
                f"   🏟️ {match['location']}\n"
                f"   📅 {match['date']} {match['time']}\n"
                f"   🎯 {match['stage']}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="select_league_schedule")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(schedule_text, reply_markup=reply_markup)
    
    async def show_pending_matches(self, query, context):
        """Показать ожидающие матчи"""
        if not self.bot.pending_matches:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⏳ Нет матчей, ожидающих применения.",
                reply_markup=reply_markup
            )
            return
        
        schedule_text = "⏳ Матчи, ожидающие применения:\n\n"
        
        for i, match in enumerate(self.bot.pending_matches, 1):
            schedule_text += (
                f"{i}. 🏆 {match['league']}\n"
                f"   🏀 {match['teamHome']} vs {match['teamAway']}\n"
                f"   🏟️ {match['location']}\n"
                f"   📅 {match['date']} {match['time']}\n"
                f"   👤 {match.get('added_by', 'Неизвестно')}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
            [InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(schedule_text, reply_markup=reply_markup)
    
    async def show_pending_results(self, query, context):
        """Показать ожидающие результаты"""
        if not self.bot.pending_results:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⏳ Нет результатов, ожидающих применения.",
                reply_markup=reply_markup
            )
            return
        
        results_text = "⏳ Результаты, ожидающие применения:\n\n"
        
        for i, result in enumerate(self.bot.pending_results, 1):
            match = result['match_info']
            results_text += (
                f"{i}. 🏆 {match['league']}\n"
                f"   🏀 {match['teamHome']} vs {match['teamAway']}\n"
                f"   📊 Счет: {result['match_info']['score']}\n"
                f"   🏟️ {match['location']}\n"
                f"   📅 {match['date']} {match['time']}\n"
                f"   👤 {result.get('added_by', 'Неизвестно')}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
            [InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(results_text, reply_markup=reply_markup)