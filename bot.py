import os
import sqlite3
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
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

KOMISYON = 0.03



# =========================
# DATABASE
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

def admin(user_id):

    return user_id in ADMIN_IDS



def para(x):

    return f"{x:,.0f}".replace(",", ".")



# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✅ Kasa bot aktif.\n\n"
        "/help yazabilirsiniz."
    )



# =========================
# HELP
# =========================

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
📌 KOMUTLAR

/yat 100000
➜ Yatırım ekler


/çek 50000
➜ Çekim ekler


/kasa
➜ Kasa durumunu gösterir


/rapor
➜ İşlem geçmişi


/sil +100000
➜ Yatırım siler


/sil -50000
➜ Çekim siler


/reset
➜ Tüm kayıtları siler (admin)


/help
➜ Yardım
"""

    await update.message.reply_text(text)



# =========================
# YATIRIM
# =========================

async def yat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin(update.effective_user.id):
        return


    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n/yat 100000"
        )

        return


    try:

        miktar = int(context.args[0])

    except:

        await update.message.reply_text(
            "Tutar sayı olmalı."
        )

        return



    conn = db()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO transactions
        (amount,type,date)
        VALUES (?,?,?)
        """,
        (
            miktar,
            "yatirim",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )


    conn.commit()
    conn.close()



    await update.message.reply_text(
        f"✅ Yatırım eklendi\n\n"
        f"💰 +{para(miktar)} TL"
    )



# =========================
# ÇEKİM
# =========================

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin(update.effective_user.id):
        return


    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n/çek 50000"
        )

        return


    try:

        miktar = int(context.args[0])

    except:

        await update.message.reply_text(
            "Tutar sayı olmalı."
        )

        return



    conn = db()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO transactions
        (amount,type,date)
        VALUES (?,?,?)
        """,
        (
            miktar,
            "cekim",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )


    conn.commit()
    conn.close()



    await update.message.reply_text(
        f"✅ Çekim eklendi\n\n"
        f"💸 -{para(miktar)} TL"
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



    komisyon = yatirim * KOMISYON

    toplam = yatirim - cekim - komisyon



    text = (
        "📊 KASA\n\n"
        f"💰 Toplam Yatırım : {para(yatirim)} TL\n"
        f"💸 Toplam Çekim   : {para(cekim)} TL\n"
        f"💼 Toplam Kom %3  : {para(komisyon)} TL\n"
        "━━━━━━━━━━━━━━\n"
        f"💵 Kasa           : {para(toplam)} TL"
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
        SELECT id,amount,type,date
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



    text = "📋 RAPOR\n\n"


    for i, amount, tip, date in rows:


        if tip == "yatirim":

            text += (
                f"#{i} ➕ {para(amount)} TL\n"
                f"{date}\n\n"
            )

        else:

            text += (
                f"#{i} ➖ {para(amount)} TL\n"
                f"{date}\n\n"
            )



    await update.message.reply_text(text)



# =========================
# SİL
# =========================

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin(update.effective_user.id):
        return


    if not context.args:

        await update.message.reply_text(
            "/sil +100000\n/sil -50000"
        )

        return



    deger = context.args[0]


    if deger.startswith("+"):

        tip = "yatirim"
        miktar = int(deger[1:])


    elif deger.startswith("-"):

        tip = "cekim"
        miktar = int(deger[1:])


    else:

        await update.message.reply_text(
            "Format yanlış."
        )

        return



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


    kayit = cur.fetchone()



    if kayit:

        cur.execute(
            "DELETE FROM transactions WHERE id=?",
            (kayit[0],)
        )

        conn.commit()

        mesaj = "🗑 Silindi."


    else:

        mesaj = "Kayıt bulunamadı."



    conn.close()


    await update.message.reply_text(mesaj)



# =========================
# RESET
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin(update.effective_user.id):
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

        print("BOT_TOKEN yok")

        return


    init_db()


    app = ApplicationBuilder().token(TOKEN).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))

    app.add_handler(CommandHandler("yat", yat))
    app.add_handler(CommandHandler("çek", cek))

    app.add_handler(CommandHandler("kasa", kasa))
    app.add_handler(CommandHandler("rapor", rapor))

    app.add_handler(CommandHandler("sil", sil))
    app.add_handler(CommandHandler("reset", reset))


    print("Bot çalışıyor...")


    app.run_polling()



if __name__ == "__main__":
    main()
