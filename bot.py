import sqlite3
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ====== إعدادات ======
API_TOKEN = os.getenv("BOT_TOKEN")  # ضع التوكن هنا في متغير البيئة
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ضع ايدي الأدمن في متغير البيئة

# أرقام الشحن
NUMBERS = ["0985465842", "0990147281"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ====== قاعدة البيانات ======
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    code TEXT,
    status TEXT
)""")

conn.commit()

# ===== MENU =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💼 حسابي", callback_data="account"),
        InlineKeyboardButton("💳 شحن", callback_data="charge")
    )
    kb.add(
        InlineKeyboardButton("🎮 ivhancy", callback_data="ivhancy"),
        InlineKeyboardButton("📞 دعم", callback_data="support")
    )
    kb.add(InlineKeyboardButton("🔥 العروض", callback_data="offers"))
    return kb

# ===== START =====
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (msg.from_user.id,))
    conn.commit()
    await msg.answer("👋 أهلاً بك في MRXICHANCYBOT", reply_markup=main_menu())

# ===== ACCOUNT =====
@dp.callback_query_handler(lambda c: c.data == "account")
async def account(call: types.CallbackQuery):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    bal = cur.fetchone()[0]
    await call.message.edit_text(
        f"👤 ID: {call.from_user.id}\n💰 رصيدك: {bal}",
        reply_markup=main_menu()
    )

# ===== CHARGE =====
@dp.callback_query_handler(lambda c: c.data == "charge")
async def charge(call: types.CallbackQuery):
    numbers_text = "\n".join(NUMBERS)
    await call.message.edit_text(
        f"📱 حول إلى أحد الأرقام:\n{numbers_text}\n\nأرسل المبلغ:"
    )
    user_data[call.from_user.id] = {"step": "amount"}

# ===== STATES =====
user_data = {}

@dp.message_handler()
async def process(msg: types.Message):
    uid = msg.from_user.id
    if uid not in user_data:
        return
    step = user_data[uid]["step"]

    if step == "amount":
        user_data[uid]["amount"] = msg.text
        user_data[uid]["step"] = "code"
        await msg.answer("🔢 أرسل كود العملية")

    elif step == "code":
        amount = float(user_data[uid]["amount"])
        code = msg.text
        cur.execute(
            "INSERT INTO payments (user_id, amount, code, status) VALUES (?, ?, ?, ?)",
            (uid, amount, code, "pending")
        )
        conn.commit()
        pid = cur.lastrowid

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ قبول", callback_data=f"ok_{pid}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"no_{pid}")
        )

        await bot.send_message(
            ADMIN_ID,
            f"💰 طلب جديد\nUser: {uid}\nAmount: {amount}\nCode: {code}",
            reply_markup=kb
        )

        await msg.answer("⏳ تم إرسال طلبك")
        user_data.pop(uid)

# ===== ADMIN =====
@dp.callback_query_handler(lambda c: c.data.startswith("ok_"))
async def approve(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    cur.execute("SELECT user_id, amount FROM payments WHERE id=?", (pid,))
    uid, amount = cur.fetchone()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    cur.execute("UPDATE payments SET status='done' WHERE id=?", (pid,))
    conn.commit()
    await bot.send_message(uid, f"✅ تم شحن {amount}")
    await call.message.edit_text("✅ تم القبول")

@dp.callback_query_handler(lambda c: c.data.startswith("no_"))
async def reject(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    cur.execute("UPDATE payments SET status='رفض' WHERE id=?", (pid,))
    conn.commit()
    await call.message.edit_text("❌ تم الرفض")

# ===== RUN =====
if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp)