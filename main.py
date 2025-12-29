import os
from keep_alive import keep_alive
keep_alive()
import telebot

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

# 存储报名数据（Render重启会清空，可后续改文件存储）
registrations = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Записаться за себя", "Записаться за другого")
    bot.send_message(message.chat.id, "Привет! Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "Записаться за себя")
def register_self(message):
    user_id = message.from_user.id
    registrations[user_id] = "self"
    count = len(registrations)
    bot.send_message(message.chat.id, f"✅ Вы записаны!\nВсего записей: {count}")

@bot.message_handler(func=lambda msg: msg.text == "Записаться за другого")
def register_other(message):
    user_id = message.from_user.id
    registrations[user_id] = "other"
    count = len(registrations)
    bot.send_message(message.chat.id, f"✅ Записано за другого!\nВсего записей: {count}")

@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.from_user.id
    if user_id in registrations:
        del registrations[user_id]
        count = len(registrations)
        bot.send_message(message.chat.id, f"❌ Запись отменена!\nВсего записей: {count}")
    else:
        bot.send_message(message.chat.id, "❌ Вы не записаны.")

bot.infinity_polling()
