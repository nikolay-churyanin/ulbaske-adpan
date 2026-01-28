from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from utils.helpers import parse_user_info

logger = logging.getLogger(__name__)

class VenueHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_venues_management(self, query, context):
        """Показать управление залами"""
        venues_text = f"🏟️ Управление залами\n\nВсего залов: {len(self.bot.venues)}\n\n"
        
        if self.bot.venues:
            venues_text += "Список залов:\n"
            for i, venue in enumerate(self.bot.venues, 1):
                venues_text += f"{i}. {venue}\n"
        else:
            venues_text += "❌ Нет добавленных залов\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить зал", callback_data="add_venue")],
        ]
        
        if self.bot.venues:
            keyboard.append([InlineKeyboardButton("🗑️ Удалить зал", callback_data="delete_venue_menu")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(venues_text, reply_markup=reply_markup)

    async def request_new_venue_name(self, query, context):
        """Запрос названия нового зала"""
        await query.edit_message_text(
            "🏟️ Добавление нового зала\n\n"
            "Введите название спортивного зала:\n\n"
            "Примеры:\n"
            "• Манеж УлГПУ\n"
            "• Дворец спорта\n"
            "• Спорткомплекс Олимп"
        )
        context.user_data['waiting_for_venue_name'] = True

    async def handle_venue_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода названия зала"""
        if not context.user_data.get('waiting_for_venue_name'):
            return
        
        try:
            venue_name = update.message.text.strip()
            user = update.message.from_user
            username = parse_user_info(user)
            
            if not venue_name:
                await update.message.reply_text("❌ Название зала не может быть пустым! Попробуйте снова:")
                return
            
            # Проверяем, существует ли уже такой зал
            if venue_name in self.bot.venues:
                await update.message.reply_text(
                    f"❌ Зал '{venue_name}' уже существует!\n"
                    "Введите другое название:"
                )
                return
            
            # Добавляем зал в список
            self.bot.venues.append(venue_name)
            
            # Сохраняем изменения
            commit_message = f"Добавлен зал: {venue_name} | Добавил: {username}"
            success = self.bot.github_manager.save_venues_data(self.bot.venues, commit_message)
            
            if success:
                storage_info = "локально" if not self.bot.github_manager.github_available else "в GitHub"
                
                await update.message.reply_text(
                    f"✅ Зал '{venue_name}' успешно добавлен и сохранен {storage_info}!\n\n"
                    f"🏟️ Всего залов: {len(self.bot.venues)}"
                )
            else:
                # Откатываем изменения в случае ошибки
                self.bot.venues.remove(venue_name)
                await update.message.reply_text(
                    "❌ Ошибка при сохранении! Зал не был добавлен.\n"
                    "Попробуйте позже."
                )
            
            # Очистка временных данных
            context.user_data.pop('waiting_for_venue_name', None)
            
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            await main_handlers.show_main_menu(update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении зала: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при добавлении зала. Попробуйте снова:"
            )

    async def show_venues_for_deletion(self, query, context):
        """Показать залы для удаления"""
        if not self.bot.venues:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="show_venues")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Нет залов для удаления!",
                reply_markup=reply_markup
            )
            return
        
        venues_text = "🗑️ Выберите зал для удаления:\n\n"
        for i, venue in enumerate(self.bot.venues, 1):
            venues_text += f"{i}. {venue}\n"
        
        keyboard = []
        for i in range(len(self.bot.venues)):
            keyboard.append([InlineKeyboardButton(f"❌ Удалить зал {i+1}", callback_data=f"delete_venue_{i}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_venues")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(venues_text, reply_markup=reply_markup)

    async def delete_venue(self, query, context, venue_index):
        """Удалить зал"""
        if 0 <= venue_index < len(self.bot.venues):
            venue_to_delete = self.bot.venues[venue_index]
            
            # Проверяем, используется ли зал в расписании
            used_in_schedule = False
            schedule_matches = []
            
            all_matches = self.bot.get_all_matches()
            for match in all_matches:
                if match['location'] == venue_to_delete:
                    used_in_schedule = True
                    schedule_matches.append(match)
            
            if used_in_schedule:
                # Показываем предупреждение и список матчей
                warning_text = (
                    f"⚠️ Невозможно удалить зал '{venue_to_delete}'!\n\n"
                    f"Этот зал используется в следующих матчах:\n\n"
                )
                
                for i, match in enumerate(schedule_matches[:5], 1):
                    warning_text += (
                        f"{i}. {match['teamHome']} vs {match['teamAway']}\n"
                        f"   📅 {match['date']} {match['time']}\n"
                        f"   🏆 {match['league']}\n\n"
                    )
                
                if len(schedule_matches) > 5:
                    warning_text += f"... и еще {len(schedule_matches) - 5} матчей\n\n"
                
                warning_text += "Сначала удалите или измените эти матчи."
                
                keyboard = [
                    [InlineKeyboardButton("📋 Показать расписание", callback_data="show_schedule_menu")],
                    [InlineKeyboardButton("🏟️ Назад к залам", callback_data="show_venues")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(warning_text, reply_markup=reply_markup)
                return
            
            # Удаляем зал из списка
            self.bot.venues.pop(venue_index)
            
            # Сохраняем изменения
            user = query.from_user
            username = parse_user_info(user)
            commit_message = f"Удален зал: {venue_to_delete} | Удалил: {username}"
            success = self.bot.github_manager.save_venues_data(self.bot.venues, commit_message)
            
            if not success:
                await query.edit_message_text("❌ Ошибка при сохранении!")
                return
            
            storage_info = "локально" if not self.bot.github_manager.github_available else "в GitHub"
            
            await query.edit_message_text(
                f"✅ Зал '{venue_to_delete}' удален и изменения сохранены {storage_info}!\n\n"
                f"🏟️ Осталось залов: {len(self.bot.venues)}"
            )
            
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            await main_handlers.show_main_menu_after_query(query, context)
        else:
            await query.edit_message_text("❌ Ошибка при удалении зала!")