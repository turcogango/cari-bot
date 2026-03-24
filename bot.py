import os
import sqlite3
import re
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)

# 🔑 ENV
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_NAME = "cari.db"

# 🔹 DB oluştur
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        amount INTEGER,
        person TEXT,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

# 🔹 DB bağlantı
def get_db():
    return sqlite3.connect(DB_NAME)

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hazırım 👌")

# 🔹 PARSE (+/- TUTAR)
def parse_message(text):
    """
    Mesaj formatı: code (+/-)tutar kişi
    Örn:
        sky03 +300 mehmet
        abc -150 ali
    """
    text = text.strip()
    parts = text.split()

    if len(parts) < 2:
        return None

    code = parts[0]

    # + veya - işaretli sayı
    match = re.search(r'([+-]\d+)', text)
    if not match:
        return None

    amount_str = match.group(1)
    amount = int(amount_str)

    # kişi
    idx = text.find(amount_str) + len(amount_str)
    person = text[idx:].strip()

    return code, amount, person

# 🔹 MESAJ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    msg = update.message.text
    print("Mesaj geldi:", msg)  # 🔹 Debug log

    result = parse_message(msg)
    print("Parse sonucu:", result)  # 🔹 Debug log

    if not result:
        await update.message.reply_text(
            "⚠️ Mesaj formatı hatalı. Örn: sky03 +300 mehmet"
        )
        return

    code, amount, person = result
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (code, amount, person, date) VALUES (?, ?, ?, ?)",
        (code, amount, person, today)
    )
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()

    await update.message.reply_text(
        f"✅ Kaydedildi\nKod: {code}\nTutar: {amount} TL\nKişi: {person}\nNo: {last_id}"
    )

# 🔹 RAPOR
async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except:
        await update.message.reply_text("Tarih formatı: YYYY-MM-DD")
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, code, amount, person FROM records WHERE date=?", (date,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    text = f"📅 {date}:\n\n"
    toplam = 0
    for id_, code, amount, person in rows:
        text += f"🔹 {id_} | {code} | {amount} TL\n👤 {person}\n\n"
        toplam += amount
    text += f"💰 Toplam: {toplam} TL"

    await update.message.reply_text(text)

# 🔹 SİL
async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Yetkin yok.")
        return

    if not context.args:
        await update.message.reply_text("Kullanım: /sil 5")
        return

    try:
        record_id = int(context.args[0])
    except:
        await update.message.reply_text("Geçersiz numara.")
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id=?", (record_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await update.message.reply_text("Kayıt bulunamadı.")
        return

    cursor.execute("DELETE FROM records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🗑️ {record_id} numaralı kayıt silindi")

# 🔹 BAKİYE
async def bakiye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, SUM(amount) FROM records GROUP BY code")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    text = "📊 Bakiyeler:\n\n"
    for code, total in rows:
        text += f"{code} → {total} TL\n"

    await update.message.reply_text(text)

# 🔥 MAIN
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN tanımlı değil!")
        return

    print("🤖 Bot başlatılıyor...")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("bakiye", bakiye))

    # 🔹 Tüm text mesajlarını yakala
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
