from datetime import datetime, timedelta
from typing import List
from config import WORK_START, WORK_END, BREAK_START, BREAK_END, SLOT_DURATION

def generate_time_slots() -> List[str]:
    """Генерирует временные слоты с учетом перерыва"""
    slots = []

    start_time = datetime.strptime(WORK_START, '%H:%M')
    end_time = datetime.strptime(WORK_END, '%H:%M')
    break_start = datetime.strptime(BREAK_START, '%H:%M')
    break_end = datetime.strptime(BREAK_END, '%H:%M')

    current_time = start_time

    while current_time <= end_time:
        if not (break_start <= current_time < break_end):
            slots.append(current_time.strftime('%H:%M'))
        current_time += timedelta(minutes=SLOT_DURATION)

    return slots

def format_appointment_info(university: str, fio: str, phone: str,
                            telegram_nick: str, date: str, time_slot: str) -> str:
    """Форматирует информацию о записи для отображения"""
    return (
        f"📋 <b>Проверьте данные:</b>\n\n"
        f"🏛 <b>Вуз:</b> {university}\n"
        f"👤 <b>ФИО:</b> {fio}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"💬 <b>Telegram:</b> {telegram_nick}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"🕐 <b>Время:</b> {time_slot}"
    )

def format_date(date_str: str) -> str:
    """Форматирует дату в читаемый вид"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        months = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        return f"{date_obj.day} {months[date_obj.month]} {date_obj.year}"
    except:
        return date_str
