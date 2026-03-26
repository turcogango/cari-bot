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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        amount INTEGER,
        person TEXT,
        site TEXT,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)

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
    except:
        await update.message.reply_text("Tutar sayısal olmalı!")
        return

    person = " ".join(context.args[2:-1])
    site = context.args[-1]
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO records (code, amount, person, site, date) VALUES (?, ?, ?, ?, ?)",
        (code, amount, person, site, today)
    )
    conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE code=? AND date=?",
        (code, today)
    )
    count = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        f"✅ {code} +{amount} TL\n{person} | {site}\nBugünkü işlem: {count}"
    )

# 🔹 DUS
async def dus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text("Kullanım: /dus SKY1 200 Ahmet Yılmaz SiteA")
        return

    code = context.args[0]
    try:
        amount = -abs(int(context.args[1]))
    except:
        await update.message.reply_text("Tutar sayısal olmalı!")
        return

    person = " ".join(context.args[2:-1])
    site = context.args[-1]
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO records (code, amount, person, site, date) VALUES (?, ?, ?, ?, ?)",
        (code, amount, person, site, today)
    )
    conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE code=? AND date=?",
        (code, today)
    )
    count = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        f"✅ {code} -{abs(amount)} TL\n{person} | {site}\nBugünkü işlem: {count}"
    )

# 🔹 RAPOR
async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, amount, person, site FROM records WHERE date=? ORDER BY id", (date,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    data = {}

    for id_, code, amount, person, site in rows:
        if code not in data:
            data[code] = {"ekle": [], "dus": []}

        if amount >= 0:
            data[code]["ekle"].append((id_, person, site, amount))
        else:
            data[code]["dus"].append((id_, person, site, abs(amount)))

    text = f"📅 {date} - Taşeron Rapor\n\n"

    for code, vals in data.items():
        text += f"{code}\n"

        if vals["ekle"]:
            total = sum(x[3] for x in vals["ekle"])
            text += f"  EKLE: {total} TL\n"
            for id_, p, s, a in vals["ekle"]:
                text += f"    {id_}. {p} ({s}) {a}\n"

        if vals["dus"]:
            total = sum(x[3] for x in vals["dus"])
            text += f"  DÜŞ: {total} TL\n"
            for id_, p, s, a in vals["dus"]:
                text += f"    {id_}. {p} ({s}) {a}\n"

        text += "\n"

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 FİRMA
async def firma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
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

# 🔓 GERİ AL (ARTIK HERKES)
async def geri_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM records ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    if not row:
        conn.close()
        await update.message.reply_text("Kayıt yok.")
        return

    last_id = row[0]
    cursor.execute("DELETE FROM records WHERE id=?", (last_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"↩️ Son işlem silindi (ID: {last_id})")

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
    conn = get_db()
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
    app.add_handler(CommandHandler("dus", dus))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("firma", firma))
    app.add_handler(CommandHandler("geri_al", geri_al))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("bakiye", bakiye))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
