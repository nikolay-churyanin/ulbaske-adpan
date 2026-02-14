from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging
from utils.helpers import parse_user_info, get_next_weekend_dates, get_available_times_for_venue, format_date_for_display

logger = logging.getLogger(__name__)

class MatchHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def show_league_selection(self, query, context, action):
        """Показать выбор лиги"""
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
            if action == "add_match":
                callback_data = f"league_{league_name}"
            else:
                callback_data = f"schedule_{league_name}"
            
            team_count = len(self.bot.leagues[league_name]["teams"])
            keyboard.append([InlineKeyboardButton(
                f"{league_name} ({team_count} команд)", 
                callback_data=callback_data
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        action_text = "добавления матча" if action == "add_match" else "просмотра расписания"
        
        await query.edit_message_text(
            f"Выберите лигу для {action_text}:",
            reply_markup=reply_markup
        )
    
    async def handle_league_selection(self, query, context, data):
        """Обработка выбора лиги для добавления матча"""
        league_name = data.replace("league_", "")
        context.user_data['current_league'] = league_name
        await self.show_team_selection(query, context, "team1", league_name)
    
    async def show_team_selection(self, query, context, selection_type, league_name, excluded_team=None):
        """Показать выбор команды для конкретной лиги"""
        if league_name not in self.bot.leagues:
            await query.edit_message_text("❌ Лига не найдена!")
            return
        
        available_teams = self.bot.leagues[league_name]["teams"].copy()
        
        if excluded_team and excluded_team in available_teams:
            available_teams.remove(excluded_team)
        
        keyboard = []
        row = []
        for i, team in enumerate(available_teams):
            row.append(InlineKeyboardButton(team, callback_data=f"select_{selection_type}_{team}"))
            if len(row) == 2 or i == len(available_teams) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к лигам", callback_data="select_league"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏆 Лига: {league_name}\n"
            f"Выберите {('первую команду' if selection_type == 'team1' else 'вторую команду')}:",
            reply_markup=reply_markup
        )
    
    async def show_venue_selection(self, query, context):
        """Показать выбор зала"""
        league_name = context.user_data['current_league']
        
        if not self.bot.venues:
            await query.edit_message_text("❌ Нет данных о залах!")
            return
        
        keyboard = []
        row = []
        for i, venue in enumerate(self.bot.venues):
            row.append(InlineKeyboardButton(venue, callback_data=f"select_venue_{venue}"))
            if len(row) == 2 or i == len(self.bot.venues) - 1:
                keyboard.append(row)
                row = []
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к командам", callback_data=f"league_{league_name}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏆 Лига: {league_name}\n"
            f"🏀 Команды: {context.user_data['team1']} vs {context.user_data['team2']}\n\n"
            "🏟️ Выберите спортивный зал:",
            reply_markup=reply_markup
        )
    
    async def request_date_input(self, query, context):
        """Запрос ввода даты и времени с быстрым выбором"""
        league = context.user_data['current_league']
        venue = context.user_data['venue']
        
        # Получаем даты выходных
        weekend_dates = get_next_weekend_dates()
        
        text = (
            f"🏆 Лига: {league}\n"
            f"🏀 Матч: {context.user_data['team1']} vs {context.user_data['team2']}\n"
            f"🏟️ Зал: {venue}\n\n"
            "📅 Выберите дату матча:"
        )
        
        keyboard = []
        
        # Кнопки с датами выходных
        for display_text, date_str in weekend_dates:
            formatted_date = format_date_for_display(date_str)
            keyboard.append([InlineKeyboardButton(
                f"{display_text} - {formatted_date}", 
                callback_data=f"quick_date_{date_str}"
            )])
        
        # Кнопка для ручного ввода
        keyboard.append([InlineKeyboardButton("✏️ Ввести дату вручную", callback_data="manual_date_input")])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Назад к залам", callback_data=f"select_venue_{venue}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_quick_date_selection(self, query, context, selected_date):
        """Обработка быстрого выбора даты"""
        context.user_data['selected_date'] = selected_date
        venue = context.user_data['venue']
        
        # Получаем доступные времена для этого зала и даты
        available_times = get_available_times_for_venue(venue, selected_date, self.bot.schedule_data)
        
        formatted_date = format_date_for_display(selected_date)
        
        text = (
            f"📅 Дата: {formatted_date}\n"
            f"🏟️ Зал: {venue}\n"
            f"🏀 Матч: {context.user_data['team1']} vs {context.user_data['team2']}\n\n"
        )
        
        if available_times:
            text += "⏰ Выберите время матча:"
        else:
            text += "❌ На эту дату нет доступного времени.\nВыберите другую дату."
        
        keyboard = []
        
        # Кнопки с доступными временами
        if available_times:
            row = []
            for i, time_slot in enumerate(available_times):
                if time_slot.startswith("⏰"):
                    # Это специальное предложение "через 1.5ч"
                    callback_time = time_slot.split("(")[1].replace(")", "")
                    row.append(InlineKeyboardButton(time_slot, callback_data=f"quick_time_{callback_time}"))
                else:
                    row.append(InlineKeyboardButton(f"🕐 {time_slot}", callback_data=f"quick_time_{time_slot}"))
                
                if len(row) == 2 or i == len(available_times) - 1:
                    keyboard.append(row)
                    row = []
        
        # Кнопка для ручного ввода времени
        keyboard.append([InlineKeyboardButton("✏️ Ввести время вручную", callback_data="manual_time_input")])
        
        # Кнопка для выбора другой даты
        keyboard.append([InlineKeyboardButton("🔙 Выбрать другую дату", callback_data=f"select_venue_{venue}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_quick_time_selection(self, query, context, selected_time):
        """Обработка быстрого выбора времени"""
        selected_date = context.user_data['selected_date']
        venue = context.user_data['venue']
        team1 = context.user_data['team1']
        team2 = context.user_data['team2']
        league = context.user_data['current_league']
        
        user = query.from_user
        username = parse_user_info(user)
        
        game_type = self.bot.determine_game_type(league, team1, team2, selected_date)

        # Создание записи о матче
        match_data = {
            'date': selected_date,
            'time': selected_time,
            'teamHome': team1,
            'teamAway': team2,
            'location': venue,
            'added_by': username,
            'added_at': datetime.now().strftime("%d.%m.%Y %H:%M"),
            'league': league,
            'gameType': game_type
        }
        
        # Добавляем в ожидающие матчи
        self.bot.pending_matches.append(match_data)
        
        # Очистка временных данных
        context.user_data.clear()
        
        formatted_date = format_date_for_display(selected_date)
        
        # Показываем кнопку применения
        keyboard = [
            [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
            [InlineKeyboardButton("📅 Добавить еще матч", callback_data="select_league")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Матч добавлен в очередь!\n\n"
            f"🏆 Лига: {league}\n"
            f"🏀 {team1} vs {team2}\n"
            f"🏟️ {venue}\n"
            f"📅 {formatted_date}\n"
            f"⏰ {selected_time}\n"
            f"👤 Добавил: {username}\n\n"
            f"⏳ Ожидающих матчей: {len(self.bot.pending_matches)}\n"
            f"Нажмите 'Применить изменения' чтобы сохранить.",
            reply_markup=reply_markup
        )
    
    async def request_manual_date_input(self, query, context):
        """Запрос ручного ввода даты"""
        await query.edit_message_text(
            "📅 Введите дату и время матча в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
            "Например: 15.12.2024 18:30\n\n"
            "Или в формате как в schedule.json:\n"
            "ГГГГ-ММ-ДД ЧЧ:ММ\n"
            "Например: 2025-10-11 12:00"
        )
        context.user_data['waiting_for_date'] = True
    
    async def request_manual_time_input(self, query, context):
        """Запрос ручного ввода времени"""
        selected_date = context.user_data['selected_date']
        formatted_date = format_date_for_display(selected_date)
        
        await query.edit_message_text(
            f"📅 Дата: {formatted_date}\n\n"
            "⏰ Введите время матча в формате ЧЧ:ММ\n\n"
            "Например: 18:30\n"
            "Или: 09:00"
        )
        context.user_data['waiting_for_time'] = True
    
    async def handle_time_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода времени"""
        if not context.user_data.get('waiting_for_time'):
            return
        
        try:
            time_text = update.message.text.strip()
            user = update.message.from_user
            username = parse_user_info(user)
            
            # Проверяем формат времени
            try:
                # Пробуем разные форматы времени
                time_obj = datetime.strptime(time_text, "%H:%M")
                selected_time = time_obj.strftime("%H:%M")
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат времени! Используйте ЧЧ:ММ\n"
                    "Например: 18:30 или 09:00\n"
                    "Попробуйте снова:"
                )
                return
            
            selected_date = context.user_data['selected_date']
            venue = context.user_data['venue']
            team1 = context.user_data['team1']
            team2 = context.user_data['team2']
            league = context.user_data['current_league']
            
            # Создание записи о матче
            match_data = {
                'date': selected_date,
                'time': selected_time,
                'teamHome': team1,
                'teamAway': team2,
                'location': venue,
                'added_by': username,
                'added_at': datetime.now().strftime("%d.%m.%Y %H:%M"),
                'league': league
            }
            
            # Добавляем в ожидающие матчи
            self.bot.pending_matches.append(match_data)
            
            # Очистка временных данных
            context.user_data.clear()
            
            formatted_date = format_date_for_display(selected_date)
            
            # Показываем кнопку применения
            keyboard = [
                [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
                [InlineKeyboardButton("📅 Добавить еще матч", callback_data="select_league")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Матч добавлен в очередь!\n\n"
                f"🏆 Лига: {league}\n"
                f"🏀 {team1} vs {team2}\n"
                f"🏟️ {venue}\n"
                f"📅 {formatted_date}\n"
                f"⏰ {selected_time}\n"
                f"👤 Добавил: {username}\n\n"
                f"⏳ Ожидающих матчей: {len(self.bot.pending_matches)}\n"
                f"Нажмите 'Применить изменения' чтобы сохранить.",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке времени: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке времени. Попробуйте снова:"
            )
    
    async def handle_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода даты и времени (старый метод для обратной совместимости)"""
        if not context.user_data.get('waiting_for_date'):
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
                    # Формат ГГГГ-ММ-ДД ЧЧ:ММ (как в schedule.json)
                    match_date = datetime.strptime(date_text, "%Y-%m-%d %H:%M")
                    date_str = match_date.strftime("%Y-%m-%d")
                    time_str = match_date.strftime("%H:%M")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты! Используйте:\n"
                        "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.12.2024 18:30)\n"
                        "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2025-10-11 12:00)\n"
                        "Попробуйте снова:"
                    )
                    return
            
            # Проверка что дата в будущем
            if match_date < datetime.now():
                await update.message.reply_text("❌ Дата должна быть в будущем! Попробуйте снова:")
                return
            
            # Создание записи о матче в формате schedule.json
            match_data = {
                'date': date_str,
                'time': time_str,
                'teamHome': context.user_data['team1'],
                'teamAway': context.user_data['team2'],
                'location': context.user_data['venue'],
                'added_by': username,
                'added_at': datetime.now().strftime("%d.%m.%Y %H:%M"),
                'league': context.user_data['current_league']
            }
            
            # Добавляем в ожидающие матчи
            self.bot.pending_matches.append(match_data)
            
            # Очистка временных данных
            context.user_data.clear()
            
            # Показываем кнопку применения
            keyboard = [
                [InlineKeyboardButton("✅ Применить изменения", callback_data="apply_changes")],
                [InlineKeyboardButton("📅 Добавить еще матч", callback_data="select_league")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Матч добавлен в очередь!\n\n"
                f"🏆 Лига: {match_data['league']}\n"
                f"🏀 {match_data['teamHome']} vs {match_data['teamAway']}\n"
                f"🏟️ {match_data['location']}\n"
                f"📅 {match_data['date']} {match_data['time']}\n"
                f"👤 Добавил: {username}\n\n"
                f"⏳ Ожидающих матчей: {len(self.bot.pending_matches)}\n"
                f"Нажмите 'Применить изменения' чтобы сохранить.",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты! Используйте:\n"
                "ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.12.2024 18:30)\n"
                "Или: ГГГГ-ММ-ДД ЧЧ:ММ (например: 2025-10-11 12:00)\n"
                "Попробуйте снова:"
            )