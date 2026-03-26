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

# 🔹 Uzun mesaj böl
def split_message(text, chunk_size=4000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hazırım 👌")

# 🔹 EKLE
async def ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text("Kullanım: /ekle <taşeron> <tutar> <üye adı soyadı> <site>")
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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO records (code, amount, person, site, date) VALUES (?, ?, ?, ?, ?)",
        (code, amount, person, site, today)
    )
    conn.commit()

    # 🔥 GÜNLÜK SAYAÇ
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE code=? AND date=?",
        (code, today)
    )
    count = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {amount} TL\nÜye: {person}\nSite: {site}\nBugünkü işlem: {count}"
    )

# 🔹 DUS
async def dus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text("Kullanım: /dus <taşeron> <tutar> <üye adı soyadı> <site>")
        return

    code = context.args[0]

    try:
        amount = -abs(int(context.args[1]))
    except ValueError:
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

    # 🔥 GÜNLÜK SAYAÇ
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE code=? AND date=?",
        (code, today)
    )
    count = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {abs(amount)} TL\nÜye: {person}\nSite: {site}\nBugünkü işlem: {count}"
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
            data[code] = {"eklenecek": [], "dusulecek": []}

        if amount >= 0:
            data[code]["eklenecek"].append((id_, person, site, amount))
        else:
            data[code]["dusulecek"].append((id_, person, site, abs(amount)))

    text = f"📅 {date} - Taşeron Bazlı Detaylı Rapor\n\n"

    for code, vals in data.items():
        text += f"Taşeron: {code}\n"

        if vals["eklenecek"]:
            total_add = sum(a for _, _, _, a in vals["eklenecek"])
            text += f"Eklenecek: {total_add} TL\n"
            for id_, person, site, amt in vals["eklenecek"]:
                text += f"  {id_}. {person} ({site}) {amt} TL\n"

        if vals["dusulecek"]:
            total_sub = sum(a for _, _, _, a in vals["dusulecek"])
            text += f"Düşülecek: {total_sub} TL\n"
            for id_, person, site, amt in vals["dusulecek"]:
                text += f"  {id_}. {person} ({site}) {amt} TL\n"

        text += "\n"

    # 🔥 PARÇALA
    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 GERİ AL (SON İŞLEM)
async def geri_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Yetkin yok.")
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM records ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    if not row:
        conn.close()
        await update.message.reply_text("Silinecek kayıt yok.")
        return

    last_id = row[0]

    cursor.execute("DELETE FROM records WHERE id=?", (last_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"↩️ Son işlem geri alındı (ID: {last_id})")

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

    for part in split_message(text):
        await update.message.reply_text(part)

# 🔹 MAIN
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN tanımlı değil!")
        return

    print("🤖 Bot başlatılıyor...")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ekle", ekle))
    app.add_handler(CommandHandler("dus", dus))
    app.add_handler(CommandHandler("rapor", rapor))
    app.add_handler(CommandHandler("geri_al", geri_al))
    app.add_handler(CommandHandler("bakiye", bakiye))

    app.run_polling()

if __name__ == "__main__":
    main()
