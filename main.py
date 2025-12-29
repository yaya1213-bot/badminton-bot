import os
from keep_alive import keep_alive
import telebot
from datetime import datetime

# 启动保活服务
keep_alive()

# 初始化Bot
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

# 配置项
MAX_PARTICIPANTS = 20  # 最大报名人数
registrations = {}     # 存储报名数据 {user_id: {name: '', type: '', time: ''}}
bot_help = """
📝 羽毛球俱乐部报名指令：
/start - 开始报名
/cancel - 取消报名
/list - 查看报名列表
/help - 查看帮助
"""

# 开始报名
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in registrations:
        bot.send_message(user_id, "❌ 你已经报名过啦，如需取消请发送 /cancel")
        return
    if len(registrations) >= MAX_PARTICIPANTS:
        bot.send_message(user_id, f"❌ 报名人数已满（上限{MAX_PARTICIPANTS}人），下次早点哦！")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Записаться за себя", "Записаться за другого")
    bot.send_message(user_id, "Привет! Выберите тип записи:", reply_markup=markup)

# 个人报名
@bot.message_handler(func=lambda msg: msg.text == "Записаться за себя")
def register_self(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    registrations[user_id] = {
        "name": username,
        "type": "个人",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    bot.send_message(user_id, f"✅ 个人报名成功！当前已报名：{len(registrations)}/{MAX_PARTICIPANTS}人")

# 代他人报名
@bot.message_handler(func=lambda msg: msg.text == "Записаться за другого")
def register_other(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    registrations[user_id] = {
        "name": username + "（代报）",
        "type": "代报",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    bot.send_message(user_id, f"✅ 代他人报名成功！当前已报名：{len(registrations)}/{MAX_PARTICIPANTS}人")

# 取消报名
@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.from_user.id
    if user_id not in registrations:
        bot.send_message(user_id, "❌ 你还没有报名哦")
        return
    del registrations[user_id]
    bot.send_message(user_id, f"✅ 取消报名成功！当前已报名：{len(registrations)}/{MAX_PARTICIPANTS}人")

# 查看报名列表
@bot.message_handler(commands=['list'])
def show_list(message):
    if not registrations:
        bot.send_message(message.chat.id, "📜 暂无报名人员")
        return
    list_text = "📜 羽毛球俱乐部报名列表：\n"
    for idx, (user_id, info) in enumerate(registrations.items(), 1):
        list_text += f"{idx}. {info['name']} - {info['type']} - {info['time']}\n"
    list_text += f"\n总报名人数：{len(registrations)}/{MAX_PARTICIPANTS}"
    bot.send_message(message.chat.id, list_text)

# 帮助指令
@bot.message_handler(commands=['help'])
def show_help(message):
    bot.send_message(message.chat.id, bot_help)

# 启动Bot
if __name__ == "__main__":
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
