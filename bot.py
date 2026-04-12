import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🔑 ENV
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None
DB_NAME = "cari.db"

# 🔹 DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # transaction_counter tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_counter (
        date TEXT PRIMARY KEY,
        counter INTEGER
    )
    """)

    # records tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        amount INTEGER,
        person TEXT,
        site TEXT,
        date TEXT,
        transaction_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

# Günlük işlem sayacını al
def get_daily_counter(date: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT counter FROM transaction_counter WHERE date=?", (date,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return 0  # Eğer o gün için işlem yapılmamışsa sıfır

# Günlük sayaç artırma
def increment_daily_counter(date: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT counter FROM transaction_counter WHERE date=?", (date,))
    result = cursor.fetchone()

    if result:
        new_count = result[0] + 1
        cursor.execute("UPDATE transaction_counter SET counter=? WHERE date=?", (new_count, date))
    else:
        new_count = 1
        cursor.execute("INSERT INTO transaction_counter (date, counter) VALUES (?, ?)", (date, new_count))

    conn.commit()
    conn.close()
    return new_count

# 🔹 Mesaj böl
def split_message(text, chunk_size=4000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hazırım 👌")

# 🔹 EKLE
async def ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text("Kullanım: /ekle SKY1 500 Ahmet Yılmaz SiteA")
        return

    code = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Tutar sayısal olmalı!")
        return

    person = " ".join(context.args[2:-1])
    site = context.args[-1]
    today = datetime.now().strftime("%Y-%m-%d")

    # Günlük işlem sırasını al ve artır
    transaction_id = increment_daily_counter(today)

    conn = sqlite3.connect(DB_NAME)
    if conn is None:
        await update.message.reply_text("Veritabanı bağlantı hatası, işlemi tekrar deneyin.")
        return

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO records (code, amount, person, site, date, transaction_id) VALUES (?, ?, ?, ?, ?, ?)",
                (code, amount, person, site, today, transaction_id)
            )

        await update.message.reply_text(
            f"✅ {code} +{amount} TL\n{person} | {site}\nİşlem sırası: {transaction_id}"
        )
    except sqlite3.Error as e:
        await update.message.reply_text("Veritabanı hatası oluştu, lütfen tekrar deneyin.")

# 🔹 RAPOR
async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, amount, person, site, transaction_id FROM records WHERE date=? ORDER BY transaction_id", (date,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    text = f"📅 {date} - Taşeron Rapor\n\n"

    for id_, code, amount, person, site, transaction_id in rows:
        text += f"{transaction_id}. {code} - {amount} TL | {person} | {site}\n"

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 FİRMA
async def firma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT code, amount, person, site FROM records WHERE date=? ORDER BY site", (date,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    data = {}
    genel = 0

    for code, amount, person, site in rows:
        if site not in data:
            data[site] = {"list": [], "net": 0}

        tip = "EKLE" if amount >= 0 else "DÜŞ"
        data[site]["list"].append((person, abs(amount), code, tip))

        if amount >= 0:
            data[site]["net"] += amount
            genel += amount
        else:
            data[site]["net"] -= abs(amount)
            genel -= abs(amount)

    text = f"📅 {date} - Firma Raporu\n\n"

    for site, vals in data.items():
        text += f"🏢 {site}\n"
        for p, a, c, t in vals["list"]:
            text += f"{p} {a} TL {c} {t}\n"
        text += f"➡️ Net: {vals['net']} TL\n\n"

    text += f"💰 GENEL: {genel} TL"

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔐 YARDIM (SADECE ADMIN)
async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        return

    text = """
📘 KOMUTLAR

/start
Botu başlatır

/ekle SKY1 500 Ahmet Yılmaz SiteA
→ Taşerona para ekler

/dus SKY1 200 Ahmet Yılmaz SiteA
→ Taşerondan para düşer

/rapor
→ Günlük taşeron raporu

/rapor 2026-03-26
→ Belirli gün raporu

/firma
→ Site bazlı rapor

/bakiye
→ Tüm taşeron bakiyeleri
"""

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 BAKİYE
async def bakiye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT code, SUM(amount) FROM records GROUP BY code")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    text = "📊 Bakiyeler\n\n"
    for code, total in rows:
        text += f"{code} → {total} TL\n"

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 MAIN
def main():
    if not TOKEN:
        print("BOT_TOKEN yok!")
        return

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ekle", ekle))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("firma", firma))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("bakiye", bakiye))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
