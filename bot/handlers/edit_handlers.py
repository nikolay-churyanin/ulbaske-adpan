from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging
from utils.helpers import parse_user_info

logger = logging.getLogger(__name__)

class EditHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_schedule_for_editing(self, query, context):
        """Показать расписание для редактирования"""
        all_matches = self.bot.get_all_matches()
        
        if not all_matches:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Расписание пусто. Нечего редактировать!",
                reply_markup=reply_markup
            )
            return
        
        schedule_text = "✏️ Выберите матч для редактирования:\n\n"
        for i, match in enumerate(all_matches, 1):
            schedule_text += (
                f"{i}. 🏆 {self.bot.league_label(match['league'])}\n"
                f"   🏀 {match['teamHome']} vs {match['teamAway']}\n"
                f"   🏟️ {match['location']}\n"
                f"   📅 {match['date']} {match['time']}\n\n"
            )
        
        keyboard = []
        for i in range(len(all_matches)):
            keyboard.append([InlineKeyboardButton(f"✏️ Редактировать матч {i+1}", callback_data=f"edit_{i}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_schedule_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сохраняем список матчей в контексте
        context.user_data['matches_for_editing'] = all_matches
        
        await query.edit_message_text(schedule_text, reply_markup=reply_markup)
    
    async def show_edit_options(self, query, context, match_index):
        """Показать опции редактирования для выбранного матча"""
        all_matches = context.user_data.get('matches_for_editing', [])
        
        if match_index < 0 or match_index >= len(all_matches):
            await query.edit_message_text("❌ Ошибка: матч не найден!")
            return
        
        match = all_matches[match_index]
        context.user_data['current_edit_match'] = match
        context.user_data['current_edit_index'] = match_index
        
        match_text = (
            f"✏️ Редактирование матча:\n\n"
            f"🏆 Лига: {self.bot.league_label(match['league'])}\n"
            f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
            f"🏟️ Зал: {match['location']}\n"
            f"📅 Дата: {match['date']}\n"
            f"⏰ Время: {match['time']}\n\n"
            "Выберите что хотите изменить:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏟️ Изменить зал", callback_data="edit_venue")],
            [InlineKeyboardButton("📅 Изменить дату и время", callback_data="edit_datetime")],
            [InlineKeyboardButton("✏️ Изменить всё", callback_data="edit_all")],
            [InlineKeyboardButton("🗑️ Удалить матч", callback_data=f"delete_{match_index}")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="edit_schedule_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(match_text, reply_markup=reply_markup)
    
    async def handle_edit_selection(self, query, context, edit_type):
        """Обработка выбора типа редактирования"""
        match = context.user_data.get('current_edit_match')
        if not match:
            await query.edit_message_text("❌ Ошибка: матч не найден!")
            return
        
        if edit_type == "edit_venue":
            await self.show_venue_selection_for_edit(query, context)
        elif edit_type == "edit_datetime":
            await self.request_new_datetime_input(query, context)
        elif edit_type == "edit_all":
            await self.show_venue_selection_for_edit(query, context)
    
    async def show_venue_selection_for_edit(self, query, context):
        """Показать выбор зала для редактирования"""
        match = context.user_data.get('current_edit_match')
        
        if not self.bot.venues:
            await query.edit_message_text("❌ Нет данных о залах!")
            return
        
        keyboard = []
        row = []
        for i, venue in enumerate(self.bot.venues):
            row.append(InlineKeyboardButton(venue, callback_data=f"edit_select_venue_{venue}"))
            if len(row) == 2 or i == len(self.bot.venues) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_{context.user_data['current_edit_index']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ Выберите новый зал для матча:\n\n"
            f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
            f"📅 {match['date']} {match['time']}\n\n"
            "🏟️ Доступные залы:",
            reply_markup=reply_markup
        )
    
    async def handle_venue_edit(self, query, context, new_venue):
        """Обработка изменения зала"""
        match = context.user_data.get('current_edit_match')
        if not match:
            await query.edit_message_text("❌ Ошибка: матч не найден!")
            return
        
        success = self.bot.update_game_fields(match, location=new_venue)
        
        if success:
            user = query.from_user
            username = parse_user_info(user)
            
            commit_message = f"Изменен зал матча: {match['teamHome']} vs {match['teamAway']} | Новый зал: {new_venue} | Изменил: {username}"
            save_success = self.bot.save_games(commit_message)
            
            if save_success:
                await query.edit_message_text(
                    f"✅ Зал успешно изменен!\n\n"
                    f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
                    f"🏟️ Новый зал: {new_venue}\n"
                    f"📅 {match['date']} {match['time']}"
                )
            else:
                await query.edit_message_text("❌ Ошибка при сохранении изменений!")
        else:
            await query.edit_message_text("❌ Ошибка при изменении матча!")
        
        # Очищаем временные данные
        context.user_data.pop('current_edit_match', None)
        context.user_data.pop('current_edit_index', None)
        context.user_data.pop('matches_for_editing', None)
        
        from bot.handlers.main_handlers import MainHandlers
        main_handlers = MainHandlers(self.bot)
        await main_handlers.show_main_menu_after_query(query, context)
    
    async def request_new_datetime_input(self, query, context):
        """Запрос ввода новой даты и времени"""
        match = context.user_data.get('current_edit_match')
        
        await query.edit_message_text(
            f"✏️ Введите новую дату и время для матча:\n\n"
            f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
            f"🏟️ {match['location']}\n\n"
            "📅 Введите дату и время в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 15.12.2024 18:30\n\n"
            "Или в формате как в games.json:\n"
            "ГГГГ-ММ-ДД ЧЧ:ММ\n"
            "Например: 2025-10-11 12:00"
        )
        context.user_data['waiting_for_edit_date'] = True
    
    async def handle_edit_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода новой даты и времени"""
        if not context.user_data.get('waiting_for_edit_date'):
            return
        
        try:
            date_text = update.message.text
            user = update.message.from_user
            username = parse_user_info(user)
            
            match = context.user_data.get('current_edit_match')
            if not match:
                await update.message.reply_text("❌ Ошибка: матч не найден!")
                return
            
            # Пробуем разные форматы даты
            try:
                # Формат ДД.ММ.ГГГГ ЧЧ:ММ
                match_date = datetime.strptime(date_text, "%d.%m.%Y %H:%M")
                new_date_str = match_date.strftime("%Y-%m-%d")
                new_time_str = match_date.strftime("%H:%M")
            except ValueError:
                try:
                    # Формат ГГГГ-ММ-ДД ЧЧ:ММ (как в games.json)
                    match_date = datetime.strptime(date_text, "%Y-%m-%d %H:%M")
                    new_date_str = match_date.strftime("%Y-%m-%d")
                    new_time_str = match_date.strftime("%H:%M")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты! Используйте:\n"
                        "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.12.2024 18:30)\n"
                        "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2025-10-11 12:00)\n"
                        "Попробуйте снова:"
                    )
                    return
            
            success = self.bot.update_game_fields(
                match,
                date=new_date_str,
                time=new_time_str
            )
            
            if success:
                commit_message = f"Изменена дата матча: {match['teamHome']} vs {match['teamAway']} | Новая дата: {new_date_str} {new_time_str} | Изменил: {username}"
                save_success = self.bot.save_games(commit_message)
                
                if save_success:
                    await update.message.reply_text(
                        f"✅ Дата и время успешно изменены!\n\n"
                        f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
                        f"🏟️ {match['location']}\n"
                        f"📅 Новая дата: {new_date_str} {new_time_str}"
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при сохранении изменений!")
            else:
                await update.message.reply_text("❌ Ошибка при изменении матча!")
            
            # Очищаем временные данные
            context.user_data.pop('waiting_for_edit_date', None)
            context.user_data.pop('current_edit_match', None)
            context.user_data.pop('current_edit_index', None)
            context.user_data.pop('matches_for_editing', None)
            
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            await main_handlers.show_main_menu(update, context)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты! Используйте:\n"
                "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.12.2024 18:30)\n"
                "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2025-10-11 12:00)\n"
                "Попробуйте снова:"
            )
    
    async def delete_match(self, query, context, match_index):
        """Удалить матч"""
        try:
            all_matches = context.user_data.get('matches_for_editing', [])
            
            if 0 <= match_index < len(all_matches):
                match_to_delete = all_matches[match_index]
                if not self.bot.delete_game(match_to_delete):
                    await query.edit_message_text("❌ Матч не найден в games.json!")
                    return
                
                user = query.from_user
                username = parse_user_info(user)
                
                commit_message = f"Удален матч: {match_to_delete['teamHome']} vs {match_to_delete['teamAway']} | Удалил: {username}"
                success = self.bot.save_games(commit_message)
                
                if success:
                    await query.edit_message_text(f"✅ Матч удален!")
                else:
                    await query.edit_message_text("❌ Ошибка при сохранении!")
                
                # Очищаем временные данные
                context.user_data.pop('current_edit_match', None)
                context.user_data.pop('current_edit_index', None)
                context.user_data.pop('matches_for_editing', None)
                
                from bot.handlers.main_handlers import MainHandlers
                main_handlers = MainHandlers(self.bot)
                await main_handlers.show_main_menu_after_query(query, context)
            else:
                await query.edit_message_text("❌ Матч не найден!")
                
        except Exception as e:
            logger.error(f"Ошибка при удалении матча: {e}")
            await query.edit_message_text("❌ Произошла ошибка при удалении!")