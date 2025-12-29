import telebot
from telebot import types
from datetime import datetime
import logging
import os
from keep_alive import keep_alive  # 导入保活函数

# 🔑 从环境变量读取配置（Render用）
TOKEN = os.getenv('TOKEN')  # 不再硬编码，从Render环境变量获取
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # 管理员ID也从环境变量获取

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化Bot + 启动保活服务
bot = telebot.TeleBot(TOKEN)
keep_alive()  # 启动Render保活服务

# 全局数据存储
events = {}
next_event_id = 1
next_reg_num = 1
user_state = {}

# --- 生成主键盘 ---
def get_main_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("📋 Просмотреть все мероприятия"),
        types.KeyboardButton("📝 Выбрать мероприятие для регистрации"),
        types.KeyboardButton("🏠 Главная")
    )
    if user_id == ADMIN_ID:
        keyboard.add(
            types.KeyboardButton("➕ Создать мероприятие"),
            types.KeyboardButton("✏️ Редактировать мероприятие"),
            types.KeyboardButton("🗑️ Удалить мероприятие")
        )
    return keyboard

# --- 发送管理员通知 ---
def send_admin_notification(text):
    try:
        bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу: {str(e)}")

# --- 基础命令处理 ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id, 
        "Добро пожаловать в клуб бадминтона DKBC!\nНажмите кнопки ниже для действий～",
        reply_markup=get_main_keyboard(user_id)
    )

# --- 键盘按钮点击处理 ---
@bot.message_handler(func=lambda msg: msg.text in ["📋 Просмотреть все мероприятия", "📝 Выбрать мероприятие для регистрации", "🏠 Главная", "➕ Создать мероприятие", "✏️ Редактировать мероприятие", "🗑️ Удалить мероприятие"])
def handle_keyboard_click(message):
    user_id = message.from_user.id
    text = message.text

    if text == "🏠 Главная":
        send_welcome(message)
    
    elif text == "📋 Просмотреть все мероприятия":
        if not events:
            bot.send_message(message.chat.id, "Нет доступных мероприятий!", reply_markup=get_main_keyboard(user_id))
            return
        for e_id, event in events.items():
            send_event_card(message.chat.id, e_id)
    
    elif text == "📝 Выбрать мероприятие для регистрации":
        if not events:
            bot.send_message(message.chat.id, "Нет мероприятий для регистрации!", reply_markup=get_main_keyboard(user_id))
            return
        event_list = "Выберите ID мероприятия для регистрации (введите цифру):\n"
        for e_id, event in events.items():
            event_list += f"{e_id}. {event['title']} ({event['date']} {event['time']})\n"
        user_state[user_id] = {"state": "register_select_id", "data": {}}
        bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))
    
    elif text == "➕ Создать мероприятие":
        user_state[user_id] = {"state": "create_title", "data": {}}
        bot.send_message(message.chat.id, "Введите название мероприятия (например: Бадминтон в субботу после обеда 3 января)", reply_markup=get_main_keyboard(user_id))
    
    elif text == "✏️ Редактировать мероприятие":
        if not events:
            bot.send_message(message.chat.id, "Нет мероприятий для редактирования!", reply_markup=get_main_keyboard(user_id))
            return
        event_list = "Выберите ID мероприятия для редактирования (введите цифру):\n"
        for e_id, event in events.items():
            event_list += f"{e_id}. {event['title']} ({event['date']})\n"
        user_state[user_id] = {"state": "edit_select_id", "data": {}}
        bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))
    
    elif text == "🗑️ Удалить мероприятие":
        if not events:
            bot.send_message(message.chat.id, "Нет мероприятий для удаления!", reply_markup=get_main_keyboard(user_id))
            return
        event_list = "Выберите ID мероприятия для удаления (введите цифру):\n"
        for e_id, event in events.items():
            event_list += f"{e_id}. {event['title']} ({event['date']})\n"
        user_state[user_id] = {"state": "del_select_id", "data": {}}
        bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))

# --- 指令处理 ---
@bot.message_handler(commands=['list'])
def show_events(message):
    user_id = message.from_user.id
    if not events:
        bot.send_message(message.chat.id, "Нет мероприятий!", reply_markup=get_main_keyboard(user_id))
        return
    for e_id, event in events.items():
        send_event_card(message.chat.id, e_id)

@bot.message_handler(commands=['register'])
def register_command(message):
    user_id = message.from_user.id
    if not events:
        bot.send_message(message.chat.id, "Нет мероприятий для регистрации!", reply_markup=get_main_keyboard(user_id))
        return
    event_list = "Выберите ID мероприятия для регистрации (введите цифру):\n"
    for e_id, event in events.items():
        event_list += f"{e_id}. {event['title']} ({event['date']} {event['time']})\n"
    user_state[message.from_user.id] = {"state": "register_select_id", "data": {}}
    bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(commands=['create_event'])
def create_event(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для создания мероприятия!", reply_markup=get_main_keyboard(user_id))
        return
    user_state[user_id] = {"state": "create_title", "data": {}}
    bot.send_message(message.chat.id, "Введите название мероприятия (например: Бадминтон в субботу после обеда 3 января)", reply_markup=get_main_keyboard(user_id))

@bot.message_handler(commands=['edit_event'])
def edit_event(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для редактирования мероприятия!", reply_markup=get_main_keyboard(user_id))
        return
    if not events:
        bot.send_message(message.chat.id, "Нет мероприятий для редактирования!", reply_markup=get_main_keyboard(user_id))
        return
    event_list = "Выберите ID мероприятия для редактирования (введите цифру):\n"
    for e_id, event in events.items():
        event_list += f"{e_id}. {event['title']} ({event['date']})\n"
    user_state[user_id] = {"state": "edit_select_id", "data": {}}
    bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(commands=['del_event'])
def del_event(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для удаления мероприятия!", reply_markup=get_main_keyboard(user_id))
        return
    if not events:
        bot.send_message(message.chat.id, "Нет мероприятий для удаления!", reply_markup=get_main_keyboard(user_id))
        return
    event_list = "Выберите ID мероприятия для удаления (введите цифру):\n"
    for e_id, event in events.items():
        event_list += f"{e_id}. {event['title']} ({event['date']})\n"
    user_state[user_id] = {"state": "del_select_id", "data": {}}
    bot.send_message(message.chat.id, event_list, reply_markup=get_main_keyboard(user_id))

# --- 用户状态处理 ---
@bot.message_handler(func=lambda msg: msg.from_user.id in user_state)
def handle_user_state(message):
    user_id = message.from_user.id
    state = user_state[user_id]["state"]
    data = user_state[user_id]["data"]
    text = message.text.strip()
    global next_event_id, next_reg_num

    try:
        if state == "create_title":
            if not text:
                bot.send_message(message.chat.id, "Название мероприятия не может быть пустым! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return
            data["title"] = text
            user_state[user_id]["state"] = "create_date"
            bot.send_message(message.chat.id, "Введите дату мероприятия (формат: DD.MM.YYYY, например: 03.01.2026)", reply_markup=get_main_keyboard(user_id))

        elif state == "create_date":
            try:
                event_date = datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
            except ValueError:
                bot.send_message(message.chat.id, "Неверный формат даты! Введите по шаблону DD.MM.YYYY:", reply_markup=get_main_keyboard(user_id))
                return
            data["date"] = event_date
            user_state[user_id]["state"] = "create_time"
            bot.send_message(message.chat.id, "Введите время мероприятия (например: 15:00-18:00)", reply_markup=get_main_keyboard(user_id))

        elif state == "create_time":
            if not text:
                bot.send_message(message.chat.id, "Время мероприятия не может быть пустым! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return
            data["time"] = text
            user_state[user_id]["state"] = "create_courts"
            bot.send_message(message.chat.id, "Введите количество кортов (цифра, например: 3)", reply_markup=get_main_keyboard(user_id))

        elif state == "create_courts":
            try:
                courts = int(text)
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифру! Введите количество кортов заново:", reply_markup=get_main_keyboard(user_id))
                return
            data["courts"] = courts
            user_state[user_id]["state"] = "create_slots"
            bot.send_message(message.chat.id, "Введите общее количество мест для регистрации (цифра, например: 24)", reply_markup=get_main_keyboard(user_id))

        elif state == "create_slots":
            try:
                total_slots = int(text)
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифру! Введите общее количество мест заново:", reply_markup=get_main_keyboard(user_id))
                return
            events[next_event_id] = {
                "title": data["title"],
                "date": data["date"],
                "time": data["time"],
                "courts": data["courts"],
                "total_slots": total_slots,
                "free_slots": total_slots,
                "registrations": [],
                "waitlist": []
            }
            bot.send_message(message.chat.id, f"✅ Мероприятие создано! ID мероприятия: {next_event_id}", reply_markup=get_main_keyboard(user_id))
            send_event_card(message.chat.id, next_event_id)
            del user_state[user_id]
            next_event_id += 1

        elif state == "edit_select_id":
            try:
                edit_id = int(text)
                if edit_id not in events:
                    bot.send_message(message.chat.id, "ID мероприятия не существует! Введите заново:", reply_markup=get_main_keyboard(user_id))
                    return
                data["edit_id"] = edit_id
                user_state[user_id]["state"] = "edit_title"
                old_event = events[edit_id]
                bot.send_message(message.chat.id, f"Текущее название мероприятия: {old_event['title']}\nВведите новое название (оставьте пустым для сохранения старого)", reply_markup=get_main_keyboard(user_id))
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифровой ID! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return

        elif state == "edit_title":
            old_event = events[data["edit_id"]]
            if text:
                old_event["title"] = text
            data["old_event"] = old_event
            user_state[user_id]["state"] = "edit_date"
            bot.send_message(message.chat.id, f"Текущая дата мероприятия: {old_event['date']}\nВведите новую дату (DD.MM.YYYY, оставьте пустым для сохранения старой)", reply_markup=get_main_keyboard(user_id))

        elif state == "edit_date":
            old_event = data["old_event"]
            if text:
                try:
                    new_date = datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
                    old_event["date"] = new_date
                except ValueError:
                    bot.send_message(message.chat.id, "Неверный формат даты! Введите по шаблону DD.MM.YYYY:", reply_markup=get_main_keyboard(user_id))
                    return
            user_state[user_id]["state"] = "edit_time"
            bot.send_message(message.chat.id, f"Текущее время мероприятия: {old_event['time']}\nВведите новое время (оставьте пустым для сохранения старого)", reply_markup=get_main_keyboard(user_id))

        elif state == "edit_time":
            old_event = data["old_event"]
            if text:
                old_event["time"] = text
            user_state[user_id]["state"] = "edit_courts"
            bot.send_message(message.chat.id, f"Текущее количество кортов: {old_event['courts']}\nВведите новое количество кортов (цифра, оставьте пустым для сохранения старого)", reply_markup=get_main_keyboard(user_id))

        elif state == "edit_courts":
            old_event = data["old_event"]
            if text:
                try:
                    old_event["courts"] = int(text)
                except ValueError:
                    bot.send_message(message.chat.id, "Введите цифру! Введите количество кортов заново:", reply_markup=get_main_keyboard(user_id))
                    return
            user_state[user_id]["state"] = "edit_slots"
            bot.send_message(message.chat.id, f"Текущее общее количество мест: {old_event['total_slots']}\nВведите новое общее количество мест (цифра, оставьте пустым для сохранения старого)", reply_markup=get_main_keyboard(user_id))

        elif state == "edit_slots":
            old_event = data["old_event"]
            edit_id = data["edit_id"]
            if text:
                try:
                    new_total = int(text)
                    old_event["total_slots"] = new_total
                    old_event["free_slots"] = new_total - len(old_event["registrations"])
                except ValueError:
                    bot.send_message(message.chat.id, "Введите цифру! Введите общее количество мест заново:", reply_markup=get_main_keyboard(user_id))
                    return
            events[edit_id] = old_event
            bot.send_message(message.chat.id, f"✅ Мероприятие {edit_id} отредактировано!", reply_markup=get_main_keyboard(user_id))
            send_event_card(message.chat.id, edit_id)
            del user_state[user_id]

        elif state == "del_select_id":
            try:
                del_id = int(text)
                if del_id not in events:
                    bot.send_message(message.chat.id, "ID мероприятия не существует! Введите заново:", reply_markup=get_main_keyboard(user_id))
                    return
                del events[del_id]
                bot.send_message(message.chat.id, f"✅ Мероприятие {del_id} успешно удалено!", reply_markup=get_main_keyboard(user_id))
                del user_state[user_id]
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифровой ID! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return

        elif state == "register_select_id":
            try:
                select_id = int(text)
                if select_id not in events:
                    bot.send_message(message.chat.id, "ID мероприятия не существует! Введите заново:", reply_markup=get_main_keyboard(user_id))
                    return
                data["event_id"] = select_id
                user_state[user_id]["state"] = "register"
                bot.send_message(message.chat.id, "Введите ваше имя для регистрации:", reply_markup=get_main_keyboard(user_id))
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифровой ID! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return

        elif state == "register":
            if not text:
                bot.send_message(message.chat.id, "Имя не может быть пустым! Введите заново:", reply_markup=get_main_keyboard(user_id))
                return
            if "event_id" not in data:
                bot.send_message(message.chat.id, "❌ ID мероприятия потерян, пожалуйста, начните регистрацию заново!", reply_markup=get_main_keyboard(user_id))
                del user_state[user_id]
                return
            event_id = data["event_id"]
            if event_id not in events:
                bot.send_message(message.chat.id, "❌ Это мероприятие было удалено!", reply_markup=get_main_keyboard(user_id))
                del user_state[user_id]
                return
            
            event = events[event_id]
            if event["free_slots"] > 0:
                event["registrations"].append((next_reg_num, text, user_id))
                event["free_slots"] -= 1
                bot.send_message(message.chat.id, f"✅ Регистрация успешна! Ваш номер на мероприятии: {len(event['registrations'])}", reply_markup=get_main_keyboard(user_id))
                send_admin_notification(f"🆕 Новая регистрация!\n<b>Мероприятие:</b> {event['title']} (ID {event_id})\n<b>Имя:</b> {text}\n<b>Номер:</b> {len(event['registrations'])}")
            else:
                event["waitlist"].append((next_reg_num, text, user_id))
                bot.send_message(message.chat.id, f"⚠️ Мест нет! Вы добавлены в список ожидания, номер: {len(event['waitlist'])}", reply_markup=get_main_keyboard(user_id))
                send_admin_notification(f"📋 Новый участник в списке ожидания!\n<b>Мероприятие:</b> {event['title']} (ID {event_id})\n<b>Имя:</b> {text}\n<b>Номер в ожидании:</b> {len(event['waitlist'])}")
            
            send_event_card(message.chat.id, event_id)
            del user_state[user_id]
            next_reg_num += 1

        elif state == "cancel":
            try:
                select_idx = int(text) - 1
                if "user_regs" not in data or "event_id" not in data:
                    bot.send_message(message.chat.id, "❌ Данные регистрации потеряны, пожалуйста, нажмите кнопку отмены заново!", reply_markup=get_main_keyboard(user_id))
                    del user_state[user_id]
                    return
                user_regs = data["user_regs"]
                event_id = data["event_id"]
                if select_idx < 0 or select_idx >= len(user_regs):
                    bot.send_message(message.chat.id, "Неверный номер! Введите заново:", reply_markup=get_main_keyboard(user_id))
                    return
                if event_id not in events:
                    bot.send_message(message.chat.id, "❌ Это мероприятие было удалено!", reply_markup=get_main_keyboard(user_id))
                    del user_state[user_id]
                    return
                
                event = events[event_id]
                reg_idx, _, name = user_regs[select_idx]
                del event["registrations"][reg_idx]
                event["free_slots"] += 1

                if event["waitlist"]:
                    wait_user = event["waitlist"].pop(0)
                    event["registrations"].append(wait_user)
                    event["free_slots"] -= 1
                    wait_user_id = wait_user[2]
                    bot.send_message(wait_user_id, f"🎉 Вы перемещены из списка ожидания в основную регистрацию!\nМероприятие: {event['title']}\nВаш новый номер: {len(event['registrations'])}", reply_markup=get_main_keyboard(wait_user_id))
                    send_admin_notification(f"🔄 Перемещение из ожидания!\n<b>Мероприятие:</b> {event['title']} (ID {event_id})\n<b>Пользователь:</b> {wait_user[1]}\n<b>Новый номер:</b> {len(event['registrations'])}")

                new_registrations = []
                for new_num, (old_num, reg_name, uid) in enumerate(event["registrations"], start=1):
                    new_registrations.append((new_num, reg_name, uid))
                event["registrations"] = new_registrations

                bot.send_message(message.chat.id, f"✅ Отмена регистрации успешна! Удалено: {name}", reply_markup=get_main_keyboard(user_id))
                send_admin_notification(f"❌ Отмена регистрации!\n<b>Мероприятие:</b> {event['title']} (ID {event_id})\n<b>Имя:</b> {name}")
                send_event_card(message.chat.id, event_id)
                del user_state[user_id]
            except ValueError:
                bot.send_message(message.chat.id, "Введите цифру! Введите номер для отмены заново:", reply_markup=get_main_keyboard(user_id))

    except Exception as e:
        logger.error(f"Ошибка обработки состояния пользователя {user_id}: {str(e)}, состояние: {state}")
        bot.send_message(message.chat.id, f"❌ Ошибка операции: {str(e)}, пожалуйста, начните заново!", reply_markup=get_main_keyboard(user_id))
        if user_id in user_state:
            del user_state[user_id]

# --- 生成活动卡片 ---
def send_event_card(chat_id, event_id):
    event = events.get(event_id)
    if not event:
        bot.send_message(chat_id, "Мероприятие не существует!", reply_markup=get_main_keyboard(chat_id))
        return
    card = f"""<b>Мероприятие {event_id}: {event['title']}</b>
📅 Дата: {event['date']}
⏰ Время: {event['time']}
🏸 Корты: {event['courts']} шт.
🎫 Всего мест: {event['total_slots']} | Свободно: {event['free_slots']}

<b>Список зарегистрированных:</b>
"""
    if event["registrations"]:
        for num, name, _ in event["registrations"]:
            card += f"{num}. {name}\n"
    else:
        card += "Никто не зарегистрировался\n"
    
    if event["waitlist"]:
        card += f"\n<b>Список ожидания ({len(event['waitlist'])} человек):</b>\n"
        for idx, (num, name, _) in enumerate(event["waitlist"], start=1):
            card += f"{idx}. {name}\n"
    else:
        card += "\nСписок ожидания: пуст\n"

    card += f"\nВремя обновления: {datetime.now().strftime('%H:%M')}"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Зарегистрироваться", callback_data=f"reg_{event_id}"),
        types.InlineKeyboardButton("Отменить регистрацию", callback_data=f"can_{event_id}")
    )
    event_link = f"https://t.me/c/{str(chat_id).lstrip('-')}/{event_id}"
    markup.add(types.InlineKeyboardButton("📎 Детали мероприятия", url=event_link))

    bot.send_message(chat_id, card, parse_mode="HTML", reply_markup=markup)

# --- 处理内联按钮 ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        action, event_id = call.data.split("_")
        event_id = int(event_id)
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if event_id not in events:
            bot.answer_callback_query(call.id, "Мероприятие не существует!")
            return
        event = events[event_id]

        if action == "reg":
            user_state[user_id] = {"state": "register", "data": {"event_id": event_id}}
            bot.send_message(chat_id, "Введите ваше имя:", reply_markup=get_main_keyboard(user_id))
            bot.answer_callback_query(call.id, "Введите ваше имя")

        elif action == "can":
            user_regs = [(i, num, name) for i, (num, name, uid) in enumerate(event["registrations"]) if uid == user_id]
            user_wait = [(i, num, name) for i, (num, name, uid) in enumerate(event["waitlist"]) if uid == user_id]
            all_user_regs = user_regs + user_wait
            
            if not all_user_regs:
                bot.answer_callback_query(call.id, "Вы не зарегистрированы и не в списке ожидания!")
                return
            
            reg_text = "Ваши записи:\n"
            for idx, (_, num, name) in enumerate(all_user_regs):
                reg_text += f"{idx+1}. Номер {num}: {name}\n"
            reg_text += "\nВведите номер для отмены (цифра):"
            user_state[user_id] = {"state": "cancel", "data": {"event_id": event_id, "user_regs": all_user_regs}}
            bot.send_message(chat_id, reg_text, reply_markup=get_main_keyboard(user_id))
            bot.answer_callback_query(call.id, "Выберите номер для отмены")

    except Exception as e:
        logger.error(f"Ошибка обработки инлайн-кнопки: {str(e)}")
        bot.answer_callback_query(call.id, f"Ошибка операции: {str(e)}")

# --- 启动Bot ---
if __name__ == "__main__":
    logger.info("Бот клуба бадминтона DKBC запущен успешно!")
    bot.polling(none_stop=True, skip_pending=True, timeout=120)
