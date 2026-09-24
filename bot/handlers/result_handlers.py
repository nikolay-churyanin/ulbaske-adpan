from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging
from utils.helpers import parse_user_info, validate_score_input, convert_to_timestamp, format_date_for_display

logger = logging.getLogger(__name__)

class ResultHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_matches_for_result(self, query, context):
        """Показать матчи для внесения результата"""
        all_matches = self.bot.get_all_matches()
        
        if not all_matches:
            keyboard = [
                [InlineKeyboardButton("➕ Результат без анонса", callback_data="add_result_new_match")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Нет матчей без счёта для внесения результатов.\n"
                "Можно добавить результат прошедшей игры сразу в games.json.",
                reply_markup=reply_markup
            )
            return
        
        # Показываем только матчи, которые уже прошли
        current_time = datetime.now()
        available_matches = []
        
        for match in all_matches:
            match_time = convert_to_timestamp(match['date'], match['time'])
            if match_time < current_time.timestamp():
                available_matches.append(match)
        
        if not available_matches:
            keyboard = [
                [InlineKeyboardButton("➕ Результат без анонса", callback_data="add_result_new_match")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Нет завершенных матчей без счёта.\n"
                "Можно добавить результат прошедшей игры сразу в games.json.",
                reply_markup=reply_markup
            )
            return
        
        text = "🏀 Выберите матч для внесения результата:\n\n"
        
        for i, match in enumerate(available_matches):
            text += (
                f"{i+1}. 🏆 {self.bot.league_label(match['league'])}\n"
                f"   🏀 {match['teamHome']} vs {match['teamAway']}\n"
                f"   🏟️ {match['location']}\n"
                f"   📅 {match['date']} {match['time']}\n\n"
            )
        
        keyboard = []
        for i in range(len(available_matches)):
            keyboard.append([InlineKeyboardButton(
                f"🏀 Внести результат {i+1}", 
                callback_data=f"result_{i}"
            )])
        
        context.user_data['available_matches_for_result'] = available_matches
        
        keyboard.append([InlineKeyboardButton("➕ Результат без анонса", callback_data="add_result_new_match")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def request_score_input(self, query, context, match_index):
        """Запрос ввода счета для выбранного матча"""
        available_matches = context.user_data.get('available_matches_for_result', [])
        
        if match_index < 0 or match_index >= len(available_matches):
            await query.edit_message_text("❌ Ошибка: матч не найден!")
            return
        
        match = available_matches[match_index]
        context.user_data['current_match_for_result'] = match
        context.user_data['waiting_for_score'] = True
        
        await query.edit_message_text(
            f"🏀 Введите счет для матча:\n\n"
            f"🏆 Лига: {self.bot.league_label(match['league'])}\n"
            f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
            f"🏟️ {match['location']}\n"
            f"📅 {match['date']} {match['time']}\n\n"
            "📊 Введите счет в формате:\n"
            "**ЧЧ:ЧЧ**\n\n"
            "Например: 73:60\n"
            "Где первое число - счет домашней команды, второе - гостевой."
        )
    
    async def handle_score_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода счета"""
        if not context.user_data.get('waiting_for_score'):
            return
        
        try:
            score_text = update.message.text.strip()
            user = update.message.from_user
            username = parse_user_info(user)
            
            # Проверяем формат счета
            is_valid, result = validate_score_input(score_text)
            if not is_valid:
                await update.message.reply_text(f"❌ {result}\nПопробуйте снова:")
                return
            
            score_home, score_away = result
            match = context.user_data['current_match_for_result']

            game_type = match.get('gameType', 'regular')

            # Создаем запись результата
            result_data = {
                'game_id': match.get('id'),
                'match_info': {
                    'id': match.get('id'),
                    'team_a': match['teamHome'],
                    'team_b': match['teamAway'],
                    'score': f"{score_home}:{score_away}",
                    'date': match['date'],
                    'venue': match['location'],
                    'time': match['time'],
                    'league': match['league'],
                    'gameType': game_type
                },
                'added_by': username
            }
            
            # Добавляем в ожидающие результаты
            self.bot.pending_results.append(result_data)
            
            # Очистка временных данных
            context.user_data.pop('waiting_for_score', None)
            context.user_data.pop('current_match_for_result', None)
            context.user_data.pop('available_matches_for_result', None)
            
            # Показываем кнопку применения
            keyboard = [
                [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
                [InlineKeyboardButton("🏀 Добавить еще результат", callback_data="add_result")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Результат добавлен в очередь!\n\n"
                f"🏆 Лига: {self.bot.league_label(match['league'])}\n"
                f"🏀 {match['teamHome']} vs {match['teamAway']}\n"
                f"📊 Счет: {score_home}:{score_away}\n"
                f"🏟️ {match['location']}\n"
                f"📅 {match['date']} {match['time']}\n"
                f"👤 Добавил: {username}\n\n"
                f"⏳ Ожидающих результатов: {len(self.bot.pending_results)}\n"
                f"Нажмите 'Применить изменения' чтобы сохранить.",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке счета: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке счета. Попробуйте снова:"
            )

    async def show_new_match_result_menu(self, query, context):
        """Показать меню для внесения результата нового матча"""
        keyboard = [
            [InlineKeyboardButton("🏆 Выбрать лигу", callback_data="new_result_select_league")],
            [InlineKeyboardButton("🔙 Назад", callback_data="add_result")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏀 Внесение результата прошедшего матча\n\n"
            "Выберите лигу для начала:",
            reply_markup=reply_markup
        )

    async def show_league_selection_for_new_result(self, query, context):
        """Показать выбор лиги для нового результата"""
        if not self.bot.leagues:
            keyboard = [[InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh_data")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Нет данных о лигах. Попробуйте обновить данные.",
                reply_markup=reply_markup
            )
            return
        
        keyboard = []
        for league_id in self.bot.leagues.keys():
            team_count = len(self.bot.leagues[league_id]["teams"])
            keyboard.append([InlineKeyboardButton(
                f"{self.bot.league_label(league_id)} ({team_count} команд)",
                callback_data=f"new_result_league_{league_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="add_result_new_match")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите лигу для прошедшего матча:",
            reply_markup=reply_markup
        )

    async def handle_league_selection_for_new_result(self, query, context, league_name):
        """Обработка выбора лиги для нового результата"""
        context.user_data['new_result_league'] = league_name
        await self.show_team_selection_for_new_result(query, context, "new_result_team1", league_name)

    async def show_team_selection_for_new_result(self, query, context, selection_type, league_name, excluded_team=None):
        """Показать выбор команды для нового результата"""
        if league_name not in self.bot.leagues:
            await query.edit_message_text("❌ Лига не найдена!")
            return
        
        available_teams = self.bot.leagues[league_name]["teams"].copy()
        
        if excluded_team and excluded_team in available_teams:
            available_teams.remove(excluded_team)
        
        keyboard = []
        row = []
        for i, team in enumerate(available_teams):
            row.append(InlineKeyboardButton(team, callback_data=f"{selection_type}_{team}"))
            if len(row) == 2 or i == len(available_teams) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к лигам", callback_data="new_result_select_league"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selection_text = "первую команду" if selection_type == "new_result_team1" else "вторую команду"
        
        await query.edit_message_text(
            f"🏆 Лига: {self.bot.league_label(league_name)}\n"
            f"Выберите {selection_text}:",
            reply_markup=reply_markup
        )

    async def show_venue_selection_for_new_result(self, query, context):
        """Показать выбор зала для нового результата"""
        league_name = context.user_data['new_result_league']
        
        if not self.bot.venues:
            await query.edit_message_text("❌ Нет данных о залах!")
            return
        
        keyboard = []
        row = []
        for i, venue in enumerate(self.bot.venues):
            row.append(InlineKeyboardButton(venue, callback_data=f"new_result_venue_{venue}"))
            if len(row) == 2 or i == len(self.bot.venues) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к командам", callback_data=f"new_result_league_{league_name}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏆 Лига: {self.bot.league_label(league_name)}\n"
            f"🏀 Команды: {context.user_data['new_result_team1']} vs {context.user_data['new_result_team2']}\n\n"
            "🏟️ Выберите спортивный зал:",
            reply_markup=reply_markup
        )

    async def request_date_for_new_result(self, query, context):
        """Запрос даты и времени для прошедшего матча"""
        venue = context.user_data['new_result_venue']
        team1 = context.user_data['new_result_team1']
        team2 = context.user_data['new_result_team2']
        league = context.user_data['new_result_league']
        
        # Показываем только даты в прошлом
        today = datetime.now().date()
        
        text = (
            f"🏆 Лига: {self.bot.league_label(league)}\n"
            f"🏀 Матч: {team1} vs {team2}\n"
            f"🏟️ Зал: {venue}\n\n"
            "📅 Введите дату и время ПРОШЕДШЕГО матча в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 15.01.2024 18:30\n\n"
            "Или в формате как в games.json:\n"
            "ГГГГ-ММ-ДД ЧЧ:ММ\n"
            "Например: 2024-01-15 18:30"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к залам", callback_data=f"new_result_venue_{venue}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        context.user_data['waiting_for_new_match_date'] = True

    async def handle_new_match_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода даты для нового результата"""
        if not context.user_data.get('waiting_for_new_match_date'):
            return
        
        try:
            date_text = update.message.text
            user = update.message.from_user
            username = parse_user_info(user)
            
            # Пробуем разные форматы даты
            try:
                # Формат ДД.ММ.ГГГГ ЧЧ:ММ
                match_date = datetime.strptime(date_text, "%d.%m.%Y %H:%M")
                date_str = match_date.strftime("%Y-%m-%d")
                time_str = match_date.strftime("%H:%M")
            except ValueError:
                try:
                    # Формат ГГГГ-ММ-ДД ЧЧ:ММ (как в games.json)
                    match_date = datetime.strptime(date_text, "%Y-%m-%d %H:%M")
                    date_str = match_date.strftime("%Y-%m-%d")
                    time_str = match_date.strftime("%H:%M")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты! Используйте:\n"
                        "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.01.2024 18:30)\n"
                        "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2024-01-15 18:30)\n"
                        "Попробуйте снова:"
                    )
                    return
            
            # Проверяем что дата в прошлом
            if match_date > datetime.now():
                await update.message.reply_text(
                    "❌ Дата должна быть в прошлом!\n"
                    "Этот матч еще не состоялся.\n"
                    "Введите дату прошедшего матча:"
                )
                return
            
            # Сохраняем данные о дате
            context.user_data['new_result_date'] = date_str
            context.user_data['new_result_time'] = time_str
            context.user_data['new_result_username'] = username
            
            # Очищаем состояние ожидания даты
            context.user_data.pop('waiting_for_new_match_date', None)
            
            # Запрашиваем счет
            await update.message.reply_text(
                f"✅ Дата и время сохранены!\n\n"
                f"Теперь введите счет матча:\n"
                f"🏀 {context.user_data['new_result_team1']} vs {context.user_data['new_result_team2']}\n\n"
                "📊 Введите счет в формате:\n"
                "**ЧЧ:ЧЧ**\n\n"
                "Например: 73:60\n"
                "Где первое число - счет домашней команды, второе - гостевой."
            )
            context.user_data['waiting_for_new_match_score'] = True
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты! Используйте:\n"
                "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.01.2024 18:30)\n"
                "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2024-01-15 18:30)\n"
                "Попробуйте снова:"
            )

    async def handle_new_match_score_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода счета для нового результата"""
        if not context.user_data.get('waiting_for_new_match_score'):
            return
        
        try:
            score_text = update.message.text.strip()
            user = update.message.from_user
            username = parse_user_info(user)
            
            # Проверяем формат счета
            is_valid, result = validate_score_input(score_text)
            if not is_valid:
                await update.message.reply_text(f"❌ {result}\nПопробуйте снова:")
                return
            
            score_home, score_away = result
            
            # Получаем все сохраненные данные
            league = context.user_data.get('new_result_league')
            team_home = context.user_data.get('new_result_team1')
            team_away = context.user_data.get('new_result_team2')
            venue = context.user_data.get('new_result_venue')
            date_str = context.user_data.get('new_result_date')
            time_str = context.user_data.get('new_result_time')
            game_type = context.user_data.get('new_result_gameType') or self.bot.determine_game_type(
                league, team_home, team_away, date_str
            )
            
            if not all([league, team_home, team_away, venue, date_str, time_str]):
                await update.message.reply_text("❌ Ошибка: не все данные заполнены!")
                # Очищаем состояния и возвращаем в меню
                from bot.handlers.main_handlers import MainHandlers
                main_handlers = MainHandlers(self.bot)
                main_handlers._clear_user_states(context)
                await main_handlers.show_main_menu(update, context)
                return
            
            result_data = {
                'match_info': {
                    'team_a': team_home,
                    'team_b': team_away,
                    'score': f"{score_home}:{score_away}",
                    'date': date_str,
                    'venue': venue,
                    'league': league,
                    'time': time_str,
                    'gameType': game_type
                },
                'added_by': username
            }
            
            # Добавляем в ожидающие результаты
            self.bot.pending_results.append(result_data)
            
            # Очистка временных данных
            from bot.handlers.main_handlers import MainHandlers
            main_handlers = MainHandlers(self.bot)
            main_handlers._clear_user_states(context)
            
            # Показываем кнопку применения
            keyboard = [
                [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
                [InlineKeyboardButton("🏀 Добавить еще результат", callback_data="add_result")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            formatted_date = format_date_for_display(date_str)
            
            await update.message.reply_text(
                f"✅ Результат добавлен в очередь!\n\n"
                f"🏆 Лига: {self.bot.league_label(league)}\n"
                f"🏀 {team_home} vs {team_away}\n"
                f"📊 Счет: {score_home}:{score_away}\n"
                f"🏟️ {venue}\n"
                f"📅 {formatted_date}\n"
                f"⏰ {time_str}\n"
                f"👤 Добавил: {username}\n\n"
                f"⏳ Ожидающих результатов: {len(self.bot.pending_results)}\n"
                f"Нажмите 'Применить изменения' чтобы сохранить.",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке счета: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке счета. Попробуйте снова:"
            )