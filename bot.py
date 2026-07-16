import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# =========================
# AYARLAR
# =========================

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_ID", "").split(",")
    if x.strip()
]

DB_NAME = "kasa.db"

COMMISSION_RATE = 0.03


# =========================
# VERİTABANI
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount INTEGER,
        type TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()



# =========================
# YARDIMCI
# =========================

def format_money(number):
    return f"{number:,.0f}".replace(",", ".")


def is_admin(user_id):
    return user_id in ADMIN_IDS



# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✅ Kasa botu hazır.\n\n"
        "Yatırım için:\n"
        "+100000\n\n"
        "Çekim için:\n"
        "-50000\n\n"
        "/help yazabilirsiniz."
    )



# =========================
# YARDIM
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
📖 KOMUTLAR

+100000
➜ Yatırım ekler

-100000
➜ Çekim ekler


/kasa
➜ Güncel kasa durumu


/rapor
➜ İşlem geçmişi


/sil +100000
➜ Yatırım siler


/sil -100000
➜ Çekim siler


/reset
➜ Tüm kayıtları siler (admin)


/help
➜ Komut listesi
"""

    await update.message.reply_text(text)



# =========================
# PARA GİRİŞİ
# =========================

async def money_input(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text.strip()

    if not text.startswith(("+", "-")):
        return

    try:
        amount = int(text)

    except ValueError:
        return


    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    if amount > 0:
        tip = "yatirim"
    else:
        tip = "cekim"


    conn = db()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO transactions
        (amount,type,date)
        VALUES (?,?,?)
        """,
        (
            abs(amount),
            tip,
            today
        )
    )


    conn.commit()
    conn.close()


    if amount > 0:

        await update.message.reply_text(
            "✅ Yatırım eklendi\n\n"
            f"💰 +{format_money(amount)} TL"
        )

    else:

        await update.message.reply_text(
            "✅ Çekim eklendi\n\n"
            f"💸 -{format_money(abs(amount))} TL"
        )
        # =========================
# KASA
# =========================

async def kasa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT SUM(amount) FROM transactions WHERE type='yatirim'"
    )
    yatirim = cur.fetchone()[0] or 0


    cur.execute(
        "SELECT SUM(amount) FROM transactions WHERE type='cekim'"
    )
    cekim = cur.fetchone()[0] or 0


    conn.close()


    komisyon = yatirim * COMMISSION_RATE

    kasa = yatirim - cekim - komisyon


    text = (
        "📊 KASA DURUMU\n\n"
        f"💰 Toplam Yatırım : {format_money(yatirim)} TL\n"
        f"💸 Toplam Çekim   : {format_money(cekim)} TL\n"
        f"💼 Toplam Kom %3  : {format_money(komisyon)} TL\n"
        "━━━━━━━━━━━━━━\n"
        f"💵 Kasa           : {format_money(kasa)} TL"
    )


    await update.message.reply_text(text)



# =========================
# RAPOR
# =========================

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = db()
    cur = conn.cursor()


    cur.execute(
        """
        SELECT id, amount, type, date
        FROM transactions
        ORDER BY id DESC
        """
    )


    rows = cur.fetchall()

    conn.close()


    if not rows:
        await update.message.reply_text(
            "Kayıt yok."
        )
        return


    text = "📋 İŞLEM RAPORU\n\n"


    for id_, amount, tip, date in rows:

        if tip == "yatirim":

            text += (
                f"#{id_} "
                f"➕ {format_money(amount)} TL "
                f"{date}\n"
            )

        else:

            text += (
                f"#{id_} "
                f"➖ {format_money(amount)} TL "
                f"{date}\n"
            )


    await update.message.reply_text(text)



# =========================
# SİL
# =========================

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return


    if not context.args:
        await update.message.reply_text(
            "Kullanım:\n/sil +100000\n/sil -50000"
        )
        return


    try:
        amount = int(context.args[0])

    except ValueError:
        await update.message.reply_text(
            "Geçersiz tutar."
        )
        return



    if amount > 0:
        tip = "yatirim"
        miktar = amount

    else:
        tip = "cekim"
        miktar = abs(amount)



    conn = db()
    cur = conn.cursor()


    cur.execute(
        """
        SELECT id FROM transactions
        WHERE amount=? AND type=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            miktar,
            tip
        )
    )


    row = cur.fetchone()


    if not row:

        conn.close()

        await update.message.reply_text(
            "Bu tutarda kayıt bulunamadı."
        )
        return



    cur.execute(
        "DELETE FROM transactions WHERE id=?",
        (row[0],)
    )


    conn.commit()
    conn.close()


    await update.message.reply_text(
        f"🗑 Silindi\n\n"
        f"{format_money(miktar)} TL"
    )



# =========================
# RESET
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return


    conn = db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM transactions"
    )

    conn.commit()
    conn.close()


    await update.message.reply_text(
        "🗑 Tüm kayıtlar silindi."
    )



# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        print("BOT_TOKEN bulunamadı")
        return


    init_db()


    app = ApplicationBuilder().token(TOKEN).build()



    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("kasa", kasa)
    )

    app.add_handler(
        CommandHandler("rapor", rapor)
    )

    app.add_handler(
        CommandHandler("sil", sil)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            money_input
        )
    )



    print("Kasa bot çalışıyor...")


    app.run_polling()



if __name__ == "__main__":
    main()
