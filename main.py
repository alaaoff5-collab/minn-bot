from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!", 200

def run_flask():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_flask).start()
import sqlite3
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# --------------------------
BOT_TOKEN = "8568901833:AAFwLqjWCc0PgukvGBUsmt65ccWdxbl2DsU" 
# بيانات حسابك الشخصي للتواصل مع البوت الثاني
API_ID= 26299944
API_HASH = "9adcc1a849ef755bef568475adebee77"
BOT2_USERNAME = "@tg_acccobot"
# --------------------------

# قاعدة البيانات
conn = sqlite3.connect("user_balances.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS balances
       (chat_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)"""
)
conn.commit()


def get_balance(chat_id):
    cursor.execute("SELECT balance FROM balances WHERE chat_id=?", (chat_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def update_balance(chat_id, amount):
    cursor.execute(
        "INSERT OR IGNORE INTO balances (chat_id, balance) VALUES (?,0)", (chat_id,)
    )
    cursor.execute(
        "UPDATE balances SET balance = balance + ? WHERE chat_id=?",
        (amount, chat_id),
    )
    conn.commit()


# Telethon client
session_string = os.getenv("SESSION", "")
if session_string:
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
else:
    client = TelegramClient("session", API_ID, API_HASH)


# --------------------------
# وظيفة التعامل مع الرسائل
# --------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat_id
    lower_text = text.lower() if text else ""

    if "balance" in lower_text or "رصيد" in lower_text:
        balance = get_balance(chat_id)
        await context.bot.send_message(chat_id=chat_id, text=f"Your current balance is: {balance}")
        return

    if "withdraw" in lower_text or "سحب" in lower_text:
        await context.bot.send_message(chat_id=chat_id, text="Your withdrawal request has been sent to admins for approval.")
        return

    # إرسال النص إلى البوت الثاني عبر Telethon
    async def send_to_bot2():
        await client.connect()
        if not await client.is_user_authorized():
            print("⚠ لم يتم تسجيل الدخول في Telethon. تحتاج إلى إدخال كود التحقق مرة واحدة محليًا.")
            return

        await client.send_message(BOT2_USERNAME, text)
        await asyncio.sleep(1.5)
        response = await client.get_messages(BOT2_USERNAME, limit=1)

        if response:
            reply_msg = response[0]
            reply = reply_msg.text or ""

            if "Please enter the amount you want to withdraw" in reply:
                reply = "Please enter the amount you want to withdraw (Minimum: 100.0)"

            if "+" in reply:
                try:
                    amount = float(reply.split("+")[1].split()[0])
                    update_balance(chat_id, amount)
                except:
                    pass

            buttons = []
            if reply_msg.reply_markup and reply_msg.reply_markup.rows:
                for row in reply_msg.reply_markup.rows:
                    buttons.append([InlineKeyboardButton(btn.text, callback_data=btn.text) for btn in row.buttons])

            markup = InlineKeyboardMarkup(buttons) if buttons else None
            await context.bot.send_message(chat_id=chat_id, text=reply, reply_markup=markup)

    asyncio.create_task(send_to_bot2())


# --------------------------
# تشغيل البوت
# --------------------------
async def main():
    await client.start()
    print("✅ Personal Telegram Client running...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
