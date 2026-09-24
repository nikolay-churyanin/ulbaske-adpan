from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def convert_to_timestamp(date_str, time_str):
    """Конвертировать дату и время в timestamp"""
    try:
        if date_str and time_str:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            return dt.timestamp()
        return 0
    except Exception as e:
        logger.error(f"Ошибка конвертации даты: {e}")
        return 0

def parse_user_info(user):
    """Получить информацию о пользователе для логирования"""
    if user.username:
        return user.username
    elif user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    else:
        return user.first_name or "Неизвестный пользователь"

def game_has_score(info):
    """Есть ли у записи матча счёт."""
    if not isinstance(info, dict):
        return False
    score = info.get("score")
    if isinstance(score, str) and ":" in score:
        parts = score.split(":")
        return len(parts) == 2 and all(part.strip().isdigit() for part in parts)
    return False


def validate_score_input(score_text):
    """Проверить корректность введенного счета"""
    if ":" not in score_text:
        return False, "Неверный формат счета! Используйте: ЧЧ:ЧЧ"
    
    score_parts = score_text.split(":")
    if len(score_parts) != 2:
        return False, "Неверный формат счета! Используйте: ЧЧ:ЧЧ"
    
    try:
        score_home = int(score_parts[0].strip())
        score_away = int(score_parts[1].strip())
        return True, (score_home, score_away)
    except ValueError:
        return False, "Счет должен содержать только числа!"

def format_match_info(match):
    """Форматировать информацию о матче для отображения"""
    return (
        f"🏆 {match.get('league', 'Неизвестная лига')}\n"
        f"🏀 {match.get('teamHome', '?')} vs {match.get('teamAway', '?')}\n"
        f"🏟️ {match.get('location', 'Не указан')}\n"
        f"📅 {match.get('date', '?')} {match.get('time', '?')}"
    )

def get_next_weekend_dates():
    """Получить даты следующих суббот и воскресений"""
    today = datetime.now()
    current_weekday = today.weekday()  # 0-понедельник, 6-воскресенье
    
    weekend_dates = []
    
    # Если сегодня суббота (5)
    if current_weekday == 5:
        # Предлагаем завтра (воскресенье)
        tomorrow = today + timedelta(days=1)
        display_text = "🗓️ Завтра"
        weekend_dates.append((display_text, tomorrow.strftime("%Y-%m-%d")))
        
        # И субботу через неделю
        next_saturday = today + timedelta(days=7)
        display_text = "🗓️ Суббота через неделю"
        weekend_dates.append((display_text, next_saturday.strftime("%Y-%m-%d")))
        
        # И воскресенье через неделю
        next_sunday = tomorrow + timedelta(days=7)
        display_text = "🗓️ Воскресенье через неделю"
        weekend_dates.append((display_text, next_sunday.strftime("%Y-%m-%d")))
    
    # Если сегодня воскресенье (6)
    elif current_weekday == 6:
        # Предлагаем следующую субботу
        next_saturday = today + timedelta(days=6)
        display_text = "🗓️ След. суббота"
        weekend_dates.append((display_text, next_saturday.strftime("%Y-%m-%d")))
        
        # И воскресенье через неделю
        next_sunday = today + timedelta(days=7)
        display_text = "🗓️ Воскресенье через неделю"
        weekend_dates.append((display_text, next_sunday.strftime("%Y-%m-%d")))
    
    # Если сегодня пятница (4)
    elif current_weekday == 4:
        # Предлагаем завтра (субботу) и послезавтра (воскресенье)
        tomorrow = today + timedelta(days=1)
        display_text = "🗓️ Завтра"
        weekend_dates.append((display_text, tomorrow.strftime("%Y-%m-%d")))
        
        day_after_tomorrow = today + timedelta(days=2)
        display_text = "🗓️ Послезавтра"
        weekend_dates.append((display_text, day_after_tomorrow.strftime("%Y-%m-%d")))
        
        # И выходные через неделю
        next_saturday = tomorrow + timedelta(days=7)
        display_text = "🗓️ Суббота через неделю"
        weekend_dates.append((display_text, next_saturday.strftime("%Y-%m-%d")))
        
        next_sunday = day_after_tomorrow + timedelta(days=7)
        display_text = "🗓️ Воскресенье через неделю"
        weekend_dates.append((display_text, next_sunday.strftime("%Y-%m-%d")))
    
    # Если сегодня понедельник-четверг (0-3)
    else:
        # Находим следующую субботу
        days_until_saturday = (5 - current_weekday) % 7
        if days_until_saturday == 0:  # Если сегодня суббота (но эта проверка уже выше)
            days_until_saturday = 7
        
        next_saturday = today + timedelta(days=days_until_saturday)
        next_sunday = next_saturday + timedelta(days=1)
        
        # Определяем описание для субботы
        if days_until_saturday == 1:
            sat_text = "🗓️ Завтра"
        elif days_until_saturday == 2:
            sat_text = "🗓️ Послезавтра"
        else:
            sat_text = "🗓️ След. суббота"
            
        # Определяем описание для воскресенья
        if days_until_saturday == 1:  # Если суббота завтра, то воскресенье послезавтра
            sun_text = "🗓️ Послезавтра"
        elif days_until_saturday == 2:  # Если суббота послезавтра, то воскресенье через 3 дня
            sun_text = "🗓️ Через 3 дня"
        else:
            sun_text = "🗓️ След. воскресенье"
        
        weekend_dates.append((sat_text, next_saturday.strftime("%Y-%m-%d")))
        weekend_dates.append((sun_text, next_sunday.strftime("%Y-%m-%d")))
        
        # Также добавим субботу и воскресенье через неделю
        saturday_after_next = next_saturday + timedelta(days=7)
        sunday_after_next = next_sunday + timedelta(days=7)
        
        weekend_dates.append(("🗓️ Суббота через неделю", saturday_after_next.strftime("%Y-%m-%d")))
        weekend_dates.append(("🗓️ Воскресенье через неделю", sunday_after_next.strftime("%Y-%m-%d")))
    
    return weekend_dates

def get_available_times_for_venue(venue, date, games):
    """Получить доступные времена для зала на указанную дату"""
    standard_times = [
        "09:00", "10:30", "12:00", "13:30", "15:00",
        "16:30", "18:00", "19:30", "21:00"
    ]

    occupied_times = []
    for game in games or []:
        info = game.get("match_info") or game
        game_venue = info.get("venue") or info.get("location")
        if game_venue == venue and info.get("date") == date and info.get("time"):
            occupied_times.append(info.get("time"))
    
    # Фильтруем стандартные времена
    available_times = [time for time in standard_times if time not in occupied_times]
    
    # Если есть занятые времена, предлагаем время через 1.5 часа после последней игры
    if occupied_times:
        last_time = max(occupied_times)
        try:
            last_dt = datetime.strptime(f"{date} {last_time}", "%Y-%m-%d %H:%M")
            next_dt = last_dt + timedelta(hours=1.5)
            next_time = next_dt.strftime("%H:%M")
            
            # Добавляем это время в доступные, если оно не занято и в пределах дня
            if (next_time not in occupied_times and 
                next_time not in available_times and
                next_dt.hour < 22):  # Не позже 22:00
                available_times.append(f"⏰ Через 1.5ч ({next_time})")
        except:
            pass
    
    return available_times

def format_date_for_display(date_str):
    """Форматировать дату для отображения"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Определяем относительное описание даты
        today = datetime.now().date()
        date_obj = dt.date()
        
        if date_obj == today + timedelta(days=1):
            day_description = "Завтра"
        elif date_obj == today + timedelta(days=2):
            day_description = "Послезавтра"
        else:
            day_description = ""
        
        weekday_ru = dt.strftime("%A").replace("Monday", "Понедельник")\
                                    .replace("Tuesday", "Вторник")\
                                    .replace("Wednesday", "Среда")\
                                    .replace("Thursday", "Четверг")\
                                    .replace("Friday", "Пятница")\
                                    .replace("Saturday", "Суббота")\
                                    .replace("Sunday", "Воскресенье")
        
        formatted_date = dt.strftime("%d.%m.%Y")
        
        if day_description:
            return f"{day_description} ({weekday_ru}) - {formatted_date}"
        else:
            return f"{weekday_ru} - {formatted_date}"
            
    except:
        return date_str

def format_game_for_stats_display(game_data):
    """Форматировать информацию об игре для отображения в статистике"""
    match_info = game_data.get('match_info', {})
    
    team_a = match_info.get('team_a', '?')
    team_b = match_info.get('team_b', '?')
    score = match_info.get('score', '?:?')
    date = match_info.get('date', '?')
    
    return f"{team_a} vs {team_b} ({score}) - {date}"