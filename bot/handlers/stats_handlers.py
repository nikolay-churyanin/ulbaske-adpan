from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from utils.helpers import parse_user_info

logger = logging.getLogger(__name__)

class StatsHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_stats_menu(self, query, context):
        """Показать меню управления статистикой"""
        # Получаем все игры без статистики
        games_without_stats = self.bot.get_all_games_without_stats()
        
        if not games_without_stats:
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить список", callback_data="stats_refresh")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📊 Управление статистикой матчей\n\n"
                "✅ У всех игр уже есть изображения со статистикой!",
                reply_markup=reply_markup
            )
            return
        
        # Показываем список игр без статистики
        games_text = "📊 Игры без статистики (показаны последние 10):\n\n"
        
        keyboard = []
        for i, game_info in enumerate(games_without_stats[:10], 1):
            game_data = game_info.get('data', {})
            match_info = game_data.get('match_info', {})
            
            # Формируем текст для кнопки
            team_a = match_info.get('team_a', '?')
            team_b = match_info.get('team_b', '?')
            score = match_info.get('score', '?:?')
            date = match_info.get('date', '?')
            league = self.bot.league_label(match_info.get('league'))
            
            button_text = f"{i}. {team_a} vs {team_b} ({score}) - {date}"
            game_number = game_info.get('game_number', self.bot.github_manager.extract_game_number(game_info['file_name']))
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"select_stats_game_{game_number}"
            )])
            
            games_text += f"{i}. 🏆 {league}\n   🏀 {team_a} vs {team_b} ({score})\n   📅 {date}\n\n"
        
        keyboard.append([
            InlineKeyboardButton("🔄 Обновить список", callback_data="stats_refresh"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            games_text,
            reply_markup=reply_markup
        )
    
    async def handle_game_selection_for_stats(self, query, context, game_number):
        """Обработка выбора игры для добавления статистики"""
        context.user_data['selected_game_for_stats'] = game_number
        
        # Получаем полную информацию об игре
        game_info = self.bot.get_game_by_number_cached(game_number)
        
        if not game_info:
            await query.edit_message_text("❌ Ошибка: игра не найдена!")
            return
        
        game_data = game_info.get('data', {})
        match_info = game_data.get('match_info', {})
        
        # Получаем информацию из разных возможных мест в структуре данных
        team_a = match_info.get('team_a') or match_info.get('teamHome') or game_data.get('teamHome') or '?'
        team_b = match_info.get('team_b') or match_info.get('teamAway') or game_data.get('teamAway') or '?'
        score = match_info.get('score', '?:?')
        date = match_info.get('date', '?')
        venue = match_info.get('venue', '?')
        league = match_info.get('league', 'Неизвестно')
        
        await query.edit_message_text(
            f"📊 Добавление статистики для игры:\n\n"
            f"🏆 Лига: {self.bot.league_label(league)}\n"
            f"🏀 {team_a} vs {team_b}\n"
            f"📊 Счет: {score}\n"
            f"📅 Дата: {date}\n"
            f"🏟️ Зал: {venue}\n"
            f"🔢 Номер игры: {game_number:03d}\n\n"
            "📎 Пожалуйста, отправьте изображение со статистикой.\n"
            "Поддерживаемые форматы: JPG, PNG.\n"
            "Изображение будет сохранено как game_{:03d}.jpg".format(game_number)
        )
        
        context.user_data['waiting_for_stats_image'] = True
    
    async def handle_stats_image_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода изображения статистики"""
        if not context.user_data.get('waiting_for_stats_image'):
            return
        
        try:
            # Проверяем, что сообщение содержит фото
            if not update.message.photo:
                await update.message.reply_text(
                    "❌ Это не изображение!\n"
                    "Пожалуйста, отправьте изображение со статистикой."
                )
                return
            
            # Получаем самое большое изображение
            photo = update.message.photo[-1]
            file_id = photo.file_id
            
            # Получаем файл
            file = await context.bot.get_file(file_id)
            
            # Скачиваем изображение
            image_data = await file.download_as_bytearray()
            
            # Получаем номер игры
            game_number = context.user_data.get('selected_game_for_stats')
            if not game_number:
                await update.message.reply_text("❌ Ошибка: номер игры не найден!")
                return
            
            # Получаем информацию об игре
            game_info = self.bot.get_game_by_number_cached(game_number)
            if not game_info:
                await update.message.reply_text("❌ Ошибка: данные игры не найдены!")
                return
            
            game_data = game_info.get('data', {})
            match_info = game_data.get('match_info', {})
            
            # Извлекаем информацию о командах
            team_a = match_info.get('team_a') or match_info.get('teamHome') or game_data.get('teamHome') or 'Неизвестно'
            team_b = match_info.get('team_b') or match_info.get('teamAway') or game_data.get('teamAway') or 'Неизвестно'
            
            user = update.message.from_user
            username = parse_user_info(user)
            
            # Сохраняем изображение
            commit_message = f"Добавлена статистика для игры {game_number:03d}: {team_a} vs {team_b} | Добавил: {username}"
            success = self.bot.github_manager.save_statistics_image(
                bytes(image_data),
                game_number,
                commit_message
            )
            
            if success:
                storage_info = "локально" if not self.bot.github_manager.github_available else "в GitHub"
                
                # Обновляем кэш после добавления статистики
                self.bot.update_games_cache_after_stats_added(game_number)
                
                await update.message.reply_text(
                    f"✅ Статистика успешно добавлена и сохранена {storage_info}!\n\n"
                    f"🏀 Игра: {team_a} vs {team_b}\n"
                    f"🔢 Номер: {game_number:03d}\n"
                    f"📁 Файл: game_{game_number:03d}.jpg"
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при сохранении статистики!\n"
                    "Попробуйте позже."
                )
            
            # Очистка временных данных
            context.user_data.pop('waiting_for_stats_image', None)
            context.user_data.pop('selected_game_for_stats', None)
            
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            await main_handlers.show_main_menu(update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения статистики: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке изображения.\n"
                "Попробуйте снова."
            )
    
    async def refresh_stats_list(self, query, context):
        """Обновить список игр без статистики"""
        # Сбрасываем кэш
        self.bot._games_without_stats_cache = {}
        self.bot._games_without_stats_cache_timestamp = {}
        self.bot._games_cache = None
        self.bot._games_with_stats_cache = None
        
        # Показываем обновленный список
        await self.show_stats_menu(query, context)