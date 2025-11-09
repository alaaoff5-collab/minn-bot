import os
import threading
import sqlite3
import asyncio
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --------------------------
# CONFIG
# --------------------------
BOT_TOKEN = "8534393339:AAHJS-Q3rXD8M97n2dbeuoVBPCFTuygb3DE"
API_ID = 26299944
API_HASH = "9adcc1a849ef755bef568475adebee77"
BOT2_USERNAME = "@tg_acccobot"
SESSION_STRING = ""  # ضع هنا StringSession إذا كنت تستخدم Telethon

# --------------------------
# DATABASE
# --------------------------
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
    cursor.execute("INSERT OR IGNORE INTO balances (chat_id, balance) VALUES (?,0)", (chat_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE chat_id=?", (amount, chat_id))
    conn.commit()

# --------------------------
# TELETHON CLIENT
# --------------------------
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("session", API_ID, API_HASH)

# --------------------------
# FLASK
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!", 200

# --------------------------
# MESSAGE HANDLER
# --------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        chat_id = update.message.chat_id
        lower_text = text.lower() if text else ""

        print(f"📩 Received message from {chat_id}: {text}")

        if "balance" in lower_text or "رصيد" in lower_text:
            balance = get_balance(chat_id)
            await update.message.reply_text(f"رصيدك الحالي: {balance / 2}")
            return

        if "withdraw" in lower_text or "سحب" in lower_text:
            balance = get_balance(chat_id)
            if balance <= 0:
                await update.message.reply_text("رصيدك غير كافٍ للسحب.")
                return
            await update.message.reply_text("ادخل المبلغ الذي تريد سحبه:")

        async def send_to_bot2():
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    print("⚠ Telethon غير مصرح. تحتاج إدخال كود التحقق مرة واحدة محليًا.")
                    return

                await client.send_message(BOT2_USERNAME, text)
                await asyncio.sleep(1.5)
                response = await client.get_messages(BOT2_USERNAME, limit=1)

                if response:
                    reply_msg = response[0]
                    reply = reply_msg.text or ""

                    if "+" in reply:
                        try:
                            amount = float(reply.split("+")[1].split()[0]) / 2
                            update_balance(chat_id, amount)
                        except:
                            pass

                    buttons = []
                    if reply_msg.reply_markup and reply_msg.reply_markup.rows:
                        for row in reply_msg.reply_markup.rows:
                            buttons.append([InlineKeyboardButton(btn.text, callback_data=btn.text) for btn in row.buttons])

                    markup = InlineKeyboardMarkup(buttons) if buttons else None
                    await update.message.reply_text(reply, reply_markup=markup)
            except Exception as e:
                print(f"❌ Telethon error: {e}")

        await send_to_bot2()

    except Exception as e:
        print(f"❌ Handler error: {e}")

# --------------------------
# MAIN RUN
# --------------------------
async def main():
    await client.start()
    print("✅ Telethon Client Running...")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تشغيل Flask في Thread مع البورت من البيئة (Koyeb)
    port = int(os.environ.get("PORT", 8000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    print(f"🌐 Flask running on port {port}")

    # تشغيل Bot polling
    print("🔄 Bot polling started...")
    await application.run_polling()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
