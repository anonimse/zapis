import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from database import Database
from config import BOT_TOKEN, UNIVERSITIES, SCHEDULE, ADMIN_USERNAMES
from utils import generate_time_slots, format_appointment_info, format_date

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

# Состояния для ConversationHandler
SELECT_UNIVERSITY, INPUT_FIO, INPUT_PHONE, INPUT_TELEGRAM, CONFIRM_DATA, SELECT_DATE, SELECT_TIME, FINAL_CONFIRM = range(8)

# Временное хранилище данных пользователя
user_data_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Проверка на админа
    if username in ADMIN_USERNAMES:
        keyboard = [
            [InlineKeyboardButton("👨‍💼 Админ-панель", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Добро пожаловать, администратор!\n\nВыберите действие:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Обычный пользователь
    return await show_university_selection(update, context)

async def show_university_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор вуза"""
    keyboard = []
    for key, name in UNIVERSITIES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"uni_{key}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🏛 <b>Выберите ваш ВУЗ:</b>"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    return SELECT_UNIVERSITY

async def university_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора вуза"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    uni_key = query.data.replace('uni_', '')

    if user_id not in user_data_storage:
        user_data_storage[user_id] = {}

    user_data_storage[user_id]['university_key'] = uni_key
    user_data_storage[user_id]['university'] = UNIVERSITIES[uni_key]

    await query.edit_message_text(
        f"✅ Выбран: <b>{UNIVERSITIES[uni_key]}</b>\n\n"
        f"👤 Введите ваше <b>ФИО</b> (полностью):",
        parse_mode='HTML'
    )

    return INPUT_FIO

async def fio_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ФИО"""
    user_id = update.effective_user.id
    fio = update.message.text.strip()

    if len(fio) < 5:
        await update.message.reply_text("❌ ФИО слишком короткое. Введите полное ФИО:")
        return INPUT_FIO

    user_data_storage[user_id]['fio'] = fio

    await update.message.reply_text(
        "📱 Введите ваш <b>номер телефона</b> (в формате +7XXXXXXXXXX или 8XXXXXXXXXX):",
        parse_mode='HTML'
    )

    return INPUT_PHONE

async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода телефона"""
    user_id = update.effective_user.id
    phone = update.message.text.strip()

    if not (phone.startswith('+7') or phone.startswith('8')) or len(phone) < 11:
        await update.message.reply_text("❌ Неверный формат телефона. Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX:")
        return INPUT_PHONE

    user_data_storage[user_id]['phone'] = phone

    await update.message.reply_text(
        "💬 Введите ваш <b>ник в Telegram</b> (например, @username):",
        parse_mode='HTML'
    )

    return INPUT_TELEGRAM

async def telegram_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода Telegram ника"""
    user_id = update.effective_user.id
    telegram_nick = update.message.text.strip()

    if not telegram_nick.startswith('@'):
        telegram_nick = '@' + telegram_nick

    user_data_storage[user_id]['telegram_nick'] = telegram_nick

    # Показываем данные для проверки
    data = user_data_storage[user_id]
    text = (
        f"📋 <b>Проверьте введенные данные:</b>\n\n"
        f"🏛 <b>Вуз:</b> {data['university']}\n"
        f"👤 <b>ФИО:</b> {data['fio']}\n"
        f"📱 <b>Телефон:</b> {data['phone']}\n"
        f"💬 <b>Telegram:</b> {data['telegram_nick']}\n\n"
        f"Все верно?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, все верно", callback_data="confirm_data_yes")],
        [InlineKeyboardButton("🔙 Назад (изменить)", callback_data="confirm_data_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

    return CONFIRM_DATA

async def data_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения данных"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_data_no":
        return await show_university_selection(update, context)

    # Показываем выбор даты
    user_id = update.effective_user.id
    uni_key = user_data_storage[user_id]['university_key']
    dates = SCHEDULE.get(uni_key, [])

    if not dates:
        await query.edit_message_text("❌ Для выбранного вуза нет доступных дат.")
        return ConversationHandler.END

    keyboard = []
    for date in dates:
        keyboard.append([InlineKeyboardButton(format_date(date), callback_data=f"date_{date}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_uni")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📅 <b>Выберите дату приема:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return SELECT_DATE

async def date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора даты"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_uni":
        return await show_university_selection(update, context)

    user_id = update.effective_user.id
    date = query.data.replace('date_', '')
    user_data_storage[user_id]['date'] = date

    # Получаем занятые слоты
    occupied_slots = db.get_occupied_slots(date)
    all_slots = generate_time_slots()
    available_slots = [slot for slot in all_slots if slot not in occupied_slots]

    if not available_slots:
        await query.edit_message_text(
            f"❌ К сожалению, на {format_date(date)} все места заняты.\n\n"
            f"Выберите другую дату.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_dates")]])
        )
        return SELECT_DATE

    # Показываем доступные слоты (по 3 в ряд)
    keyboard = []
    row = []
    for i, slot in enumerate(available_slots):
        row.append(InlineKeyboardButton(slot, callback_data=f"time_{slot}"))
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_dates")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🕐 <b>Выберите время на {format_date(date)}:</b>\n\n"
        f"Доступно слотов: {len(available_slots)}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return SELECT_TIME

async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_dates":
        return await data_confirmed(update, context)

    user_id = update.effective_user.id
    time_slot = query.data.replace('time_', '')
    user_data_storage[user_id]['time_slot'] = time_slot

    # Финальная проверка всех данных
    data = user_data_storage[user_id]
    text = format_appointment_info(
        data['university'],
        data['fio'],
        data['phone'],
        data['telegram_nick'],
        format_date(data['date']),
        data['time_slot']
    )

    text += "\n\n<b>Подтвердить запись?</b>"

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить запись", callback_data="final_confirm_yes")],
        [InlineKeyboardButton("🔙 Назад", callback_data="final_confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    return FINAL_CONFIRM

async def final_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальное подтверждение записи"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    if query.data == "final_confirm_no":
        return await date_selected(update, context)

    # Сохраняем запись в БД
    data = user_data_storage[user_id]
    success = db.create_appointment(
        user_id,
        data['university'],
        data['fio'],
        data['phone'],
        data['telegram_nick'],
        data['date'],
        data['time_slot']
    )

    if not success:
        await query.edit_message_text(
            "❌ <b>Ошибка!</b>\n\n"
            "К сожалению, это время уже занято. Выберите другое время.",
            parse_mode='HTML'
        )
        return await date_selected(update, context)

    # Уведомление админов
    if db.are_notifications_enabled():
        await notify_admins(context, f"📝 Новая запись!\n\n{format_appointment_info(data['university'], data['fio'], data['phone'], data['telegram_nick'], format_date(data['date']), data['time_slot'])}")

    keyboard = [[InlineKeyboardButton("❌ Отменить запись", callback_data="cancel_appointment")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✅ <b>Запись подтверждена!</b>\n\n"
        f"{format_appointment_info(data['university'], data['fio'], data['phone'], data['telegram_nick'], format_date(data['date']), data['time_slot'])}\n\n"
        "Ждем вас в назначенное время!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return ConversationHandler.END

async def cancel_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена записи"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    appointment = db.get_user_appointment(user_id)

    if not appointment:
        await query.edit_message_text("❌ У вас нет активной записи.")
        return

    success = db.delete_appointment(user_id, appointment['date'], appointment['time_slot'])

    if success:
        await query.edit_message_text(
            "✅ Запись успешно отменена.\n\n"
            "Для новой записи используйте команду /start"
        )
    else:
        await query.edit_message_text("❌ Ошибка при отмене записи.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель"""
    query = update.callback_query
    if query:
        await query.answer()

    username = update.effective_user.username
    user_id = update.effective_user.id

    if username not in ADMIN_USERNAMES:
        if query:
            await query.edit_message_text("❌ У вас нет доступа к админ-панели.")
        return

    # Сохраняем chat_id админа для уведомлений
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_chats (
            username TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL
        )
    ''')
    cursor.execute('INSERT OR REPLACE INTO admin_chats (username, chat_id) VALUES (?, ?)',
                   (username, user_id))
    conn.commit()
    conn.close()

    notifications_status = "🔔 Включены" if db.are_notifications_enabled() else "🔕 Выключены"

    keyboard = [
        [InlineKeyboardButton("📊 Просмотр записей", callback_data="admin_view_appointments")],
        [InlineKeyboardButton(f"🔔 Уведомления: {notifications_status}", callback_data="admin_toggle_notifications")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "👨‍💼 <b>Админ-панель</b>\n\nВыберите действие:"

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_view_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр записей по датам"""
    query = update.callback_query
    await query.answer()

    # Получаем все даты из расписания
    all_dates = []
    for dates in SCHEDULE.values():
        all_dates.extend(dates)
    all_dates = sorted(set(all_dates))

    keyboard = []
    for date in all_dates:
        keyboard.append([InlineKeyboardButton(format_date(date), callback_data=f"admin_date_{date}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📅 <b>Выберите дату для просмотра записей:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def admin_show_date_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать записи на конкретную дату"""
    query = update.callback_query
    await query.answer()

    date = query.data.replace('admin_date_', '')
    appointments = db.get_appointments_by_date(date)
    all_slots = generate_time_slots()
    occupied_slots = db.get_occupied_slots(date)
    free_slots = [slot for slot in all_slots if slot not in occupied_slots]

    text = f"📊 <b>Записи на {format_date(date)}</b>\n\n"

    if appointments:
        text += "<b>Занятые слоты:</b>\n"
        for app in appointments:
            text += f"\n🕐 {app['time_slot']} - {app['fio']}\n"
            text += f"   📱 {app['phone']}\n"
            text += f"   💬 {app['telegram_nick']}\n"
            text += f"   🏛 {app['university']}\n"
    else:
        text += "Записей нет.\n"

    text += f"\n<b>Свободные слоты ({len(free_slots)}):</b>\n"
    if free_slots:
        text += ", ".join(free_slots)
    else:
        text += "Все слоты заняты"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_view_appointments")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение уведомлений"""
    query = update.callback_query
    await query.answer()

    new_state = db.toggle_notifications()
    status = "включены" if new_state else "выключены"

    await query.answer(f"Уведомления {status}", show_alert=True)
    await admin_panel(update, context)

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Отправка уведомлений админам"""
    conn = db.get_connection()
    cursor = conn.cursor()

    # Создаем таблицу для хранения chat_id админов, если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_chats (
            username TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('SELECT chat_id FROM admin_chats')
    admin_chats = [row[0] for row in cursor.fetchall()]
    conn.close()

    for chat_id in admin_chats:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {chat_id}: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text("Операция отменена. Используйте /start для начала.")
    return ConversationHandler.END

def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для записи
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(show_university_selection, pattern='^user_start$')
        ],
        states={
            SELECT_UNIVERSITY: [CallbackQueryHandler(university_selected, pattern='^uni_')],
            INPUT_FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, fio_received)],
            INPUT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            INPUT_TELEGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_received)],
            CONFIRM_DATA: [CallbackQueryHandler(data_confirmed, pattern='^confirm_data_')],
            SELECT_DATE: [CallbackQueryHandler(date_selected, pattern='^(date_|back_to_)')],
            SELECT_TIME: [CallbackQueryHandler(time_selected, pattern='^(time_|back_to_)')],
            FINAL_CONFIRM: [CallbackQueryHandler(final_confirm, pattern='^final_confirm_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_view_appointments, pattern='^admin_view_appointments$'))
    application.add_handler(CallbackQueryHandler(admin_show_date_appointments, pattern='^admin_date_'))
    application.add_handler(CallbackQueryHandler(admin_toggle_notifications, pattern='^admin_toggle_notifications$'))
    application.add_handler(CallbackQueryHandler(cancel_appointment, pattern='^cancel_appointment$'))

    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
