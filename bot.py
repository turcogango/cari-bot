import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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

def get_db():
    return sqlite3.connect(DB_NAME)

# 🔹 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hazırım 👌")

# 🔹 EKLE
async def ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /ekle code tutar [person]")
        return

    code = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("Tutar sayısal olmalı!")
        return

    person = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (code, amount, person, date) VALUES (?, ?, ?, ?)",
        (code, amount, person, today)
    )
    conn.commit()
    last_id = cursor.lastrowid

    # işlem sayısı
    cursor.execute("SELECT COUNT(*) FROM records WHERE code=?", (code,))
    count = cursor.fetchone()[0]
    conn.close()

    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {amount} TL\nüye: {person}\nişlem sayısı: {count}"
    )

# 🔹 DUS
async def dus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /dus code tutar [person]")
        return

    code = context.args[0]
    try:
        amount = int(context.args[1])
        amount = -abs(amount)
    except:
        await update.message.reply_text("Tutar sayısal olmalı!")
        return

    person = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (code, amount, person, date) VALUES (?, ?, ?, ?)",
        (code, amount, person, today)
    )
    conn.commit()
    last_id = cursor.lastrowid

    # işlem sayısı
    cursor.execute("SELECT COUNT(*) FROM records WHERE code=?", (code,))
    count = cursor.fetchone()[0]
    conn.close()

    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {abs(amount)} TL\nüye: {person}\nişlem sayısı: {count}"
    )

# 🔹 RAPOR (taşeron bazlı)
async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, SUM(amount) FROM records WHERE date=? GROUP BY code", (date,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    text = f"📅 {date} - Taşeron Bazlı Toplam:\n\n"
    for code, total in rows:
        text += f"Taşeron: {code} → Toplam: {total} TL\n"

    await update.message.reply_text(text)

# 🔹 DETAY (taşeron bazlı eklenen/düşülen)
async def detay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, amount FROM records WHERE date=?", (date,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return

    data = {}
    for code, amount in rows:
        if code not in data:
            data[code] = {"eklenecek": 0, "dusulecek": 0}
        if amount >= 0:
            data[code]["eklenecek"] += amount
        else:
            data[code]["dusulecek"] += abs(amount)

    text = f"📅 {date} - Detaylar:\n\n"
    for code, vals in data.items():
        text += f"Taşeron: {code}\nEklenecek: {vals['eklenecek']}\nDüşülecek: {vals['dusulecek']}\n\n"

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

# 🔹 ALFI (komut listesi)
async def alfi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Mevcut Komutlar:\n\n"
        "/start - Botu başlatır\n"
        "/ekle code tutar [üye] - Taşerona tutar ekler\n"
        "/dus code tutar [üye] - Taşerondan tutar düşer\n"
        "/rapor [yyyy-mm-dd] - Taşeron bazlı toplam rapor\n"
        "/detay [yyyy-mm-dd] - Taşeron bazlı ekleme/düşme detay\n"
        "/bakiye - Tüm taşeronların toplam bakiyesi\n"
        "/sil id - Kaydı sil (admin)\n"
        "/alfi - Komutları gösterir"
    )
    await update.message.reply_text(text)

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
    app.add_handler(CommandHandler("detay", detay))
    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("bakiye", bakiye))
    app.add_handler(CommandHandler("alfi", alfi))

    app.run_polling()

if __name__ == "__main__":
    main()
