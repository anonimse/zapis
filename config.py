import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USERNAMES = os.getenv('ADMIN_IDS', '').split(',')

UNIVERSITIES = {
    'vma': 'Военно-медицинская академия им С.М.Кирова',
    'szgmu': 'СЗГМУ',
    'pspbgmu': 'ПСПБГМУ им ак.Павлова',
    'spbgpmu': 'СПБГПМУ',
    'other': 'Алмазова, МСИ, РЕАВИЗ, СПБГУ',
    'reserve': 'Резерв'
}

SCHEDULE = {
    'vma': ['2026-05-15', '2026-05-16', '2026-05-19', '2026-05-20'],
    'szgmu': ['2026-05-21', '2026-05-22', '2026-05-23', '2026-05-27', '2026-05-28', '2026-05-29'],
    'pspbgmu': ['2026-05-30', '2026-06-02', '2026-06-03', '2026-06-04'],
    'spbgpmu': ['2026-06-05', '2026-06-06', '2026-06-08', '2026-06-09'],
    'other': ['2026-06-10', '2026-06-11'],
    'reserve': ['2026-06-13', '2026-06-16']
}

WORK_START = '12:00'
WORK_END = '19:15'
BREAK_START = '15:00'
BREAK_END = '15:30'
SLOT_DURATION = 15
