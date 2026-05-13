import sqlite3
from datetime import datetime
from typing import List, Optional, Dict

class Database:
    def __init__(self, db_name='appointments.db'):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                university TEXT NOT NULL,
                fio TEXT NOT NULL,
                phone TEXT NOT NULL,
                telegram_nick TEXT NOT NULL,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, time_slot)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_settings (
                id INTEGER PRIMARY KEY,
                notifications_enabled INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL
            )
        ''')

        cursor.execute('SELECT COUNT(*) FROM admin_settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO admin_settings (id, notifications_enabled) VALUES (1, 1)')

        conn.commit()
        conn.close()

    def create_appointment(self, user_id: int, university: str, fio: str,
                          phone: str, telegram_nick: str, date: str, time_slot: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO appointments (user_id, university, fio, phone, telegram_nick, date, time_slot)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, university, fio, phone, telegram_nick, date, time_slot))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_occupied_slots(self, date: str) -> List[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT time_slot FROM appointments WHERE date = ?', (date,))
        slots = [row[0] for row in cursor.fetchall()]
        conn.close()
        return slots

    def delete_appointment(self, user_id: int, date: str, time_slot: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM appointments
            WHERE user_id = ? AND date = ? AND time_slot = ?
        ''', (user_id, date, time_slot))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_user_appointment(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT university, fio, phone, telegram_nick, date, time_slot
            FROM appointments
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'university': row[0],
                'fio': row[1],
                'phone': row[2],
                'telegram_nick': row[3],
                'date': row[4],
                'time_slot': row[5]
            }
        return None

    def get_appointments_by_date(self, date: str) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fio, phone, telegram_nick, time_slot, university
            FROM appointments
            WHERE date = ?
            ORDER BY time_slot
        ''', (date,))
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                'fio': row[0],
                'phone': row[1],
                'telegram_nick': row[2],
                'time_slot': row[3],
                'university': row[4]
            })
        conn.close()
        return appointments

    def get_all_dates_with_appointments(self) -> List[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT date FROM appointments ORDER BY date')
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates

    def toggle_notifications(self) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT notifications_enabled FROM admin_settings WHERE id = 1')
        current = cursor.fetchone()[0]
        new_state = 0 if current == 1 else 1
        cursor.execute('UPDATE admin_settings SET notifications_enabled = ? WHERE id = 1', (new_state,))
        conn.commit()
        conn.close()
        return bool(new_state)

    def are_notifications_enabled(self) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT notifications_enabled FROM admin_settings WHERE id = 1')
        enabled = bool(cursor.fetchone()[0])
        conn.close()
        return enabled

    def save_admin_chat_id(self, username: str, chat_id: int):
        """Сохранить chat_id админа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO admins (username, chat_id)
            VALUES (?, ?)
        ''', (username, chat_id))
        conn.commit()
        conn.close()

    def get_admin_chat_ids(self) -> List[int]:
        """Получить все chat_id админов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM admins')
        chat_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return chat_ids
