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
        keyboard = [
            [InlineKeyboardButton("📊 Добавить статистику к игре", callback_data="add_stats_select_league")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 Управление статистикой матчей\n\n"
            "Здесь вы можете добавить изображение со статистикой для завершенной игры.",
            reply_markup=reply_markup
        )
    
    async def show_league_selection_for_stats(self, query, context):
        """Показать выбор лиги для добавления статистики"""
        if not self.bot.leagues:
            keyboard = [[InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh_data")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Нет данных о лигах. Попробуйте обновить данные.",
                reply_markup=reply_markup
            )
            return
        
        keyboard = []
        for league_name in self.bot.leagues.keys():
            team_count = len(self.bot.leagues[league_name]["teams"])
            keyboard.append([InlineKeyboardButton(
                f"{league_name} ({team_count} команд)", 
                callback_data=f"stats_league_{league_name}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="stats_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите лигу для добавления статистики:",
            reply_markup=reply_markup
        )
    
    async def handle_league_selection_for_stats(self, query, context, league_name):
        """Обработка выбора лиги для статистики"""
        context.user_data['stats_league'] = league_name
        
        # ИСПОЛЬЗУЕМ ОПТИМИЗИРОВАННЫЙ МЕТОД
        games_without_stats = self.bot.get_games_without_stats_optimized(league_name)
        
        if not games_without_stats:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к лигам", callback_data="add_stats_select_league")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🏆 Лига: {league_name}\n\n"
                "✅ Все игры уже имеют изображения со статистикой.",
                reply_markup=reply_markup
            )
            return
        
        games_text = f"🏆 Лига: {league_name}\n\n"
        games_text += "📊 Игры без статистики (показаны последние 5):\n\n"
        
        keyboard = []
        for i, game_info in enumerate(games_without_stats[:5], 1):
            game_data = game_info.get('data', {})
            match_info = game_data.get('match_info', {})
            
            # Формируем текст для кнопки
            team_a = match_info.get('team_a', '?')
            team_b = match_info.get('team_b', '?')
            score = match_info.get('score', '?:?')
            
            button_text = f"{i}. {team_a} vs {team_b} ({score})"
            game_number = game_info.get('game_number', self.bot.github_manager.extract_game_number(game_info['file_name']))
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"select_stats_game_{game_number}"
            )])
            
            # Добавляем в текст сообщения
            date = match_info.get('date', '?')
            games_text += f"{i}. {team_a} vs {team_b} ({score})\n   📅 {date}\n\n"
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к лигам", callback_data="add_stats_select_league"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            games_text,
            reply_markup=reply_markup
        )
    
    async def handle_game_selection_for_stats(self, query, context, game_number):
        """Обработка выбора игры для добавления статистики"""
        context.user_data['selected_game_for_stats'] = game_number
        
        # Используем кэшированный метод для получения полной информации об игре
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
        
        # Пробуем получить дату из разных мест
        date = (match_info.get('date') or  '?')
        
        # Пробуем получить зал из разных мест
        venue = (match_info.get('venue') or '?')
        
        # Получаем лигу из контекста или из данных игры
        league = context.user_data.get('stats_league', 'Неизвестно')
        if league == 'Неизвестно':
            league = self.bot.github_manager.get_game_league(game_data)
        
        await query.edit_message_text(
            f"📊 Добавление статистики для игры:\n\n"
            f"🏆 Лига: {league}\n"
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
            
            # Извлекаем информацию о командах с учетом разных форматов
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
            context.user_data.pop('stats_league', None)
            
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            await main_handlers.show_main_menu(update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения статистики: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке изображения.\n"
                "Попробуйте снова."
            )