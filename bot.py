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
        site TEXT,
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
    cursor.execute("SELECT COUNT(*) FROM records WHERE code=?", (code,))
    count = cursor.fetchone()[0]
    conn.close()
    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {amount} TL\nÜye: {person}\nSite: {site}\nİşlem sayısı: {count}"
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
    cursor.execute("SELECT COUNT(*) FROM records WHERE code=?", (code,))
    count = cursor.fetchone()[0]
    conn.close()
    await update.message.reply_text(
        f"✅ Başarılı\nTaşeron: {code}\nTutar: {abs(amount)} TL\nÜye: {person}\nSite: {site}\nİşlem sayısı: {count}"
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
    await update.message.reply_text(text)

# 🔹 DETAY
async def detay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, amount, site FROM records WHERE date=?", (date,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Kayıt yok.")
        return
    data = {}
    for code, amount, site in rows:
        if code not in data:
            data[code] = {"eklenecek": 0, "dusulecek": 0, "sites": set()}
        if amount >= 0:
            data[code]["eklenecek"] += amount
        else:
            data[code]["dusulecek"] += abs(amount)
        data[code]["sites"].add(site)
    text = f"📅 {date} - Detaylar:\n\n"
    for code, vals in data.items():
        text += f"Taşeron: {code}\nEklenecek: {vals['eklenecek']}\nDüşülecek: {vals['dusulecek']}\nSite: {', '.join(vals['sites'])}\n\n"
    await update.message.reply_text(text)

# 🔹 SİL
async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Yetkin yok.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /sil işlem_numarası")
        return
    try:
        record_id = int(context.args[0])
    except ValueError:
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
    await update.message.reply_text(f"🗑️ {record_id} numaralı işlem silindi")

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

# 🔹 ALFI
async def alfi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Mevcut Komutlar:\n\n"
        "/start - Botu başlatır\n"
        "/ekle <taşeron> <tutar> <üye adı soyadı> <site> - Taşerona tutar ekler\n"
        "/dus <taşeron> <tutar> <üye adı soyadı> <site> - Taşerondan tutar düşer\n"
        "/rapor [yyyy-mm-dd] - Taşeron bazlı tüm işlemler\n"
        "/detay [yyyy-mm-dd] - Taşeron bazlı ekleme/düşme toplam\n"
        "/bakiye - Tüm taşeronların toplam bakiyesi\n"
        "/sil işlem_numarası - Kaydı sil (admin)\n"
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
