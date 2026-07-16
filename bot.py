import os
import sqlite3
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)


# =====================
# AYARLAR
# =====================

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_ID", "").split(",")
    if x.strip()
]

DB_NAME = "kasa.db"

KOMISYON_ORANI = 0.003



# =====================
# DATABASE
# =====================

def connect_db():
    return sqlite3.connect(DB_NAME)



def init_db():

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS islemler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        miktar INTEGER NOT NULL,
        tur TEXT NOT NULL,
        tarih TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()



# =====================
# YARDIMCI
# =====================

def admin_mi(user_id):

    return user_id in ADMIN_IDS



def para(miktar):

    return "{:,.0f}".format(miktar).replace(",", ".")



# =====================
# START
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✅ Kasa bot çalışıyor.\n"
        "/help yazabilirsiniz."
    )



# =====================
# HELP
# =====================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mesaj = """
📌 KOMUTLAR

/yat 100000
➜ Yatırım ekler


/tt 50000
➜ TT iletilen tutarı ekler


/kasa
➜ Kasa durumunu gösterir


/rapor
➜ İşlem geçmişi


/sil +100000
➜ Yatırım siler


/sil -50000
➜ TT siler


/reset
➜ Tüm kayıtları siler (admin)


/help
➜ Yardım
"""

    await update.message.reply_text(mesaj)



# =====================
# YATIRIM
# =====================

async def yat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin_mi(update.effective_user.id):
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
            "Geçerli sayı girin."
        )
        return



    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO islemler
        (miktar,tur,tarih)
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

# =====================
# TT İLETİLEN
# =====================

async def tt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin_mi(update.effective_user.id):
        return


    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n/tt 50000"
        )
        return


    try:
        miktar = int(context.args[0])

    except:

        await update.message.reply_text(
            "Geçerli sayı girin."
        )
        return



    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT INTO islemler
        (miktar,tur,tarih)
        VALUES (?,?,?)
        """,
        (
            miktar,
            "tt",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )


    conn.commit()
    conn.close()


    await update.message.reply_text(
        f"✅ TT iletildi\n\n"
        f"💸 {para(miktar)} TL"
    )



# =====================
# KASA
# =====================

async def kasa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        "SELECT SUM(miktar) FROM islemler WHERE tur='yatirim'"
    )

    yatirim = cur.fetchone()[0] or 0



    cur.execute(
        "SELECT SUM(miktar) FROM islemler WHERE tur='tt'"
    )

    tt_toplam = cur.fetchone()[0] or 0


    conn.close()


    komisyon = yatirim * KOMISYON_ORANI

    kasa = yatirim - tt_toplam - komisyon



    mesaj = (
        "📊 KASA DURUMU\n\n"
        f"💰 Toplam Yatırım : {para(yatirim)} TL\n"
        f"💸 TT İletilen    : {para(tt_toplam)} TL\n"
        f"💼 Toplam Kom %3  : {para(komisyon)} TL\n"
        "━━━━━━━━━━━━━━\n"
        f"💵 Kasa           : {para(kasa)} TL"
    )


    await update.message.reply_text(mesaj)



# =====================
# RAPOR
# =====================

async def rapor(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        """
        SELECT id,miktar,tur,tarih
        FROM islemler
        ORDER BY id DESC
        """
    )


    veriler = cur.fetchall()

    conn.close()



    if not veriler:

        await update.message.reply_text(
            "Kayıt yok."
        )
        return



    mesaj = "📋 İŞLEM RAPORU\n\n"



    for id_, miktar, tur, tarih in veriler:


        if tur == "yatirim":

            mesaj += (
                f"#{id_} ➕ Yatırım "
                f"{para(miktar)} TL\n"
                f"{tarih}\n\n"
            )


        else:

            mesaj += (
                f"#{id_} 💸 TT "
                f"{para(miktar)} TL\n"
                f"{tarih}\n\n"
            )



    await update.message.reply_text(mesaj)

# =====================
# SİL
# =====================

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin_mi(update.effective_user.id):
        return


    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n"
            "/sil +100000\n"
            "/sil -50000"
        )
        return


    deger = context.args[0]


    try:
        miktar = int(
            deger.replace("+", "")
                 .replace("-", "")
        )

    except:

        await update.message.reply_text(
            "Yanlış format."
        )
        return



    if deger.startswith("+"):

        tur = "yatirim"


    elif deger.startswith("-"):

        tur = "tt"


    else:

        await update.message.reply_text(
            "Başına + veya - koyun."
        )
        return



    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        """
        SELECT id
        FROM islemler
        WHERE miktar=? AND tur=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            miktar,
            tur
        )
    )


    kayit = cur.fetchone()



    if not kayit:

        conn.close()

        await update.message.reply_text(
            "Bu tutarda kayıt bulunamadı."
        )
        return



    cur.execute(
        "DELETE FROM islemler WHERE id=?",
        (kayit[0],)
    )


    conn.commit()
    conn.close()


    await update.message.reply_text(
        f"🗑 Silindi\n\n"
        f"{para(miktar)} TL"
    )



# =====================
# RESET
# =====================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not admin_mi(update.effective_user.id):
        return


    conn = connect_db()
    cur = conn.cursor()


    cur.execute(
        "DELETE FROM islemler"
    )


    conn.commit()
    conn.close()


    await update.message.reply_text(
        "🗑 Tüm kayıtlar silindi."
    )



# =====================
# MAIN
# =====================

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
        CommandHandler("yat", yat)
    )


    app.add_handler(
        CommandHandler("tt", tt)
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



    print("✅ Kasa bot çalışıyor...")


    app.run_polling()



if __name__ == "__main__":
    main()
