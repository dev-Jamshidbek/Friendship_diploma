"""
╔══════════════════════════════════════════════════════════════╗
║   "Meni qanchalik yaxshi bilasiz?" — Telegram Quiz Bot       ║
╠══════════════════════════════════════════════════════════════╣
║  O'rnatish:                                                  ║
║    pip install python-telegram-bot reportlab pillow          ║
║                                                              ║
║  BOT_TOKEN ni quyida o'zgartiring, keyin:                    ║
║    python quiz_bot.py                                        ║
╠══════════════════════════════════════════════════════════════╣
║  SAVOLLARNI O'ZGARTIRISH:                                    ║
║    DEFAULT_QUESTIONS ro'yxatini tahrirlang (quyida).         ║
║    Har savol: question, options, image_url                   ║
║    "correct" maydoni YO'Q — uni yaratuvchi o'zi tanlaydi!    ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
from dotenv import load_dotenv
load_dotenv()
import io
import json
import logging
import random
import sqlite3
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")   # ← @BotFather dan oling

_base = os.path.dirname(os.path.abspath(__file__))
FONT_REG  = os.environ.get("FONT_REG",  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = os.environ.get("FONT_BOLD", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# ──────────────────────────────────────────────────────────────
#  20 TA DEFAULT SAVOL  —  XOHLAGANINGIZDA O'ZGARTIRING
#
#  ✅ question  — savol matni
#  ✅ options   — barcha variantlar ro'yxati
#  ✅ image_url — rasm URL  (bo'sh "" qolsa rasm yo'q)
#
#  "correct" maydoni YO'Q — uni yaratuvchi /start da o'zi tanlaydi!
# ──────────────────────────────────────────────────────────────
DEFAULT_QUESTIONS = [
    {
        "question": "🎨 Sevimli rangi qaysi?",
        "options": ["❤️ Qizil", "💙 Ko'k", "💚 Yashil", "💛 Sariq",
                    "🧡 To'q sariq", "💜 Binafsha", "🖤 Qora", "🤍 Oq"],
        "image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=800",
    },
    {
        "question": "🌸 Qaysi faslni yaxshi ko'radi?",
        "options": ["🌸 Bahor", "☀️ Yoz", "🍂 Kuz", "❄️ Qish"],
        "image_url": "https://images.unsplash.com/photo-1462275646964-a0e3386b89fa?w=800",
    },
    {
        "question": "🎂 Tug'ilgan oyi qaysi?",
        "options": ["❄️ Yanvar", "💝 Fevral", "🌱 Mart", "🌷 Aprel",
                    "🌼 May", "☀️ Iyun", "🏖️ Iyul", "🌻 Avgust",
                    "🍂 Sentabr", "🎃 Oktabr", "🍁 Noyabr", "🎄 Dekabr"],
        "image_url": "https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=800",
    },
    {
        "question": "🌅 Ertalab erta turuvchimi yoki kechqurunchi?",
        "options": ["🌅 Ertalab erta turuvchi", "🌙 Kechqurunchi"],
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    },
    {
        "question": "🐾 Sevimli hayvoni qaysi?",
        "options": ["🐶 It", "🐱 Mushuk", "🐰 Quyon",
                    "🐠 Baliq", "🦜 Qush", "🐢 Toshbaqa", "🐴 Ot"],
        "image_url": "https://images.unsplash.com/photo-1415369629372-26f2fe60c467?w=800",
    },
    {
        "question": "🍽️ Sevimli oziq-ovqat turi qaysi?",
        "options": ["🥘 O'zbek taomlari", "🍕 Italyan taomlari",
                    "🍜 Xitoy taomlari", "🍔 Fast food",
                    "🦞 Dengiz mahsulotlari", "🥗 Vegetarian taomlar"],
        "image_url": "https://images.unsplash.com/photo-1567529692333-de9fd6772897?w=800",
    },
    {
        "question": "☕ Choy ichuvchimi yoki kofe?",
        "options": ["🍵 Choy", "☕ Kofe", "😋 Ikkalasi ham", "🚫 Ikkalasini ham ichmaydi"],
        "image_url": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800",
    },
    {
        "question": "📚 Kitob o'qishni yoqtiradimi yoki film ko'rishni?",
        "options": ["📖 Kitob o'qish", "🎬 Film ko'rish",
                    "🎭 Ikkalasini ham", "😴 Ikkalasini ham yoqtirmaydi"],
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=800",
    },
    {
        "question": "🌊 Dengizni yoqtiradimi yoki togʻni?",
        "options": ["🌊 Dengiz", "⛰️ Tog'", "🌍 Ikkalasini ham", "🌲 O'rmon"],
        "image_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",
    },
    {
        "question": "🎵 Qaysi musiqa uslubini yaxshi ko'radi?",
        "options": ["🎤 Pop", "🎸 Rock", "🎧 Hip-hop",
                    "🎻 Klassik", "🎷 Jazz", "🎛️ Electronic", "🎼 O'zbek estradasi"],
        "image_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=800",
    },
    {
        "question": "🛋️ Dam olish kunlari nima qilishni yoqtiradi?",
        "options": ["🛋️ Uyda dam oladi", "🌿 Tabiatga chiqadi",
                    "👫 Do'stlar bilan uchrashadi", "🏃 Sport bilan shug'ullanadi",
                    "✈️ Sayohat qiladi", "🛒 Bozorga boradi"],
        "image_url": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=800",
    },
    {
        "question": "⚽ Qaysi sport turini yaxshi ko'radi?",
        "options": ["⚽ Futbol", "🏀 Basketbol", "🎾 Tennis",
                    "🏊 Suzish", "🏃 Yugurish", "🚴 Velosiped",
                    "🥋 Jang san'ati", "🙅 Sportni yoqtirmaydi"],
        "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800",
    },
    {
        "question": "🤝 Ijtimoiy odammi yoki yolg'iz qolishni yaxshi ko'radimi?",
        "options": ["🤝 Ijtimoiy odam", "🧘 Yolg'iz qolishni yaxshi ko'radi",
                    "🤔 Vaziyatga qarab"],
        "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=800",
    },
    {
        "question": "🍲 Sevimli o'zbek taomi qaysi?",
        "options": ["🍚 Osh (palov)", "🥟 Manti", "🍜 Lag'mon",
                    "🥐 Somsa", "🍢 Shashlik", "🫕 Qozon kabob", "🌯 Do'lma"],
        "image_url": "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=800",
    },
    {
        "question": "✈️ Qaysi davlatga sayohat qilishni orzu qiladi?",
        "options": ["🇹🇷 Turkiya", "🇦🇪 UAE (Dubai)", "🇮🇹 Italiya",
                    "🇯🇵 Yaponiya", "🇺🇸 AQSh", "🇫🇷 Fransiya",
                    "🇹🇭 Tailand", "🇲🇾 Malayziya"],
        "image_url": "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800",
    },
    {
        "question": "🌙 Ertasi kuni dam olish kuni bo'lsa kechasi nima qiladi?",
        "options": ["🦉 Kech yotadi", "😴 Odatdagidek yotadi", "🐦 Ertaroq yotadi"],
        "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800",
    },
    {
        "question": "👗 Qaysi rang kiyim ko'proq kiyadi?",
        "options": ["🖤 Qora", "🤍 Oq", "💙 Ko'k",
                    "🩶 Kulrang", "💚 Yashil", "❤️ Qizil", "🌈 Rangli"],
        "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
    },
    {
        "question": "🛍️ Xarid qilishni yoqtiradimi?",
        "options": ["🤩 Ha, juda yoqtiradi", "🛍️ Ha, yoqtiradi",
                    "😐 Unchalik yo'q", "🙅 Yo'q, yoqtirmaydi"],
        "image_url": "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800",
    },
    {
        "question": "🧠 Ijodiy kishimi yoki mantiqiy fikrlovchimi?",
        "options": ["🎨 Ijodiy", "🔢 Mantiqiy", "⚖️ Ikkalasi ham teng"],
        "image_url": "https://images.unsplash.com/photo-1527610276295-f4c1c1e3b590?w=800",
    },
    {
        "question": "👋 Birinchi tanishganda qanday bo'ladi?",
        "options": ["😊 Tortinchoq", "🤗 Ochiq va do'stona",
                    "🤔 Vaziyatga qarab", "🎉 Juda faol"],
        "image_url": "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=800",
    },
]

# 10-savol uchun universal default rasm
Q10_IMAGE = "https://images.unsplash.com/photo-1633613286991-611fe299c4be?w=800"

# ──────────────────────────────────────────────────────────────
#  STATES
# ──────────────────────────────────────────────────────────────
(
    ST_MENU,             # bosh menyu
    ST_CREATOR_ANS,      # yaratuvchi 9 savolga javob beradi
    ST_Q10_TEXT,         # 10-savol matni
    ST_Q10_ANS,          # 10-savol to'g'ri javob
    ST_Q10_OPTS,         # 10-savol noto'g'ri variantlar
    ST_SOLVING,          # do'st testni ishlaydi
) = range(6)

# ──────────────────────────────────────────────────────────────
#  IN-MEMORY SESSIONS
# ──────────────────────────────────────────────────────────────
sessions: dict = {}

# ──────────────────────────────────────────────────────────────
#  DATABASE
# ──────────────────────────────────────────────────────────────
DB_PATH = "quiz.db"


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id      TEXT PRIMARY KEY,
            creator_id   INTEGER,
            creator_name TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS questions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id   TEXT,
            step      INTEGER,
            question  TEXT,
            correct   TEXT,
            options   TEXT,
            image_url TEXT
        );
        CREATE TABLE IF NOT EXISTS scores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id     TEXT,
            solver_id   INTEGER,
            solver_name TEXT,
            score       INTEGER,
            total       INTEGER,
            played_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)


def db_save_quiz(quiz_id, creator_id, creator_name, questions):
    with db() as c:
        c.execute(
            "INSERT INTO quizzes (quiz_id, creator_id, creator_name) VALUES (?,?,?)",
            (quiz_id, creator_id, creator_name),
        )
        for i, q in enumerate(questions):
            c.execute(
                "INSERT INTO questions (quiz_id,step,question,correct,options,image_url)"
                " VALUES (?,?,?,?,?,?)",
                (quiz_id, i, q["question"], q["correct"],
                 json.dumps(q["options"], ensure_ascii=False), q.get("image_url", "")),
            )


def db_get_quiz(quiz_id):
    with db() as c:
        row = c.execute("SELECT * FROM quizzes WHERE quiz_id=?", (quiz_id,)).fetchone()
        if not row:
            return None
        qs = c.execute(
            "SELECT question,correct,options,image_url FROM questions"
            " WHERE quiz_id=? ORDER BY step", (quiz_id,)
        ).fetchall()
        return dict(row) | {"questions": [dict(q) for q in qs]}


def db_save_score(quiz_id, solver_id, solver_name, score, total):
    with db() as c:
        c.execute(
            "INSERT INTO scores (quiz_id,solver_id,solver_name,score,total)"
            " VALUES (?,?,?,?,?)",
            (quiz_id, solver_id, solver_name, score, total),
        )


def db_get_scores(quiz_id):
    with db() as c:
        return c.execute(
            "SELECT solver_name,score,total FROM scores"
            " WHERE quiz_id=? ORDER BY score DESC, played_at ASC",
            (quiz_id,),
        ).fetchall()


def db_user_quizzes(creator_id):
    with db() as c:
        return c.execute(
            "SELECT quiz_id,created_at FROM quizzes"
            " WHERE creator_id=? ORDER BY created_at DESC",
            (creator_id,),
        ).fetchall()


# ──────────────────────────────────────────────────────────────
#  KEYBOARD HELPERS
# ──────────────────────────────────────────────────────────────
def main_kb():
    """Pastki doimiy menyu."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎯 Quiz yaratish")],
            [KeyboardButton("📊 Statistika"), KeyboardButton("🔗 Mening havolam")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_options(options: list) -> list:
    """Javob variantlari uchun InlineKeyboard. callback_data = idx (matn emas!)."""
    return [
        [InlineKeyboardButton(opt, callback_data=f"opt_{i}")]
        for i, opt in enumerate(options)
    ]


# ──────────────────────────────────────────────────────────────
#  MESSAGE HELPER  —  avvalgi savolni o'chiradi, yangi yuboradi
# ──────────────────────────────────────────────────────────────
async def send_question(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    session: dict,
    caption: str,
    options: list,
    image_url: str,
):
    """Avvalgi savol xabarini o'chirib, yangi savol xabar yuboradi."""
    # Avvalgi xabarni o'chirish
    old_id = session.get("msg_id")
    if old_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_id)
        except Exception:
            pass
        session["msg_id"] = None

    keyboard = InlineKeyboardMarkup(inline_options(options))

    if image_url:
        try:
            msg = await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            session["msg_id"] = msg.message_id
            return
        except Exception:
            pass

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=caption,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    session["msg_id"] = msg.message_id


# ──────────────────────────────────────────────────────────────
#  CERTIFICATE
# ──────────────────────────────────────────────────────────────
def _reg_fonts():
    try:
        pdfmetrics.registerFont(TTFont("DJ",  FONT_REG))
        pdfmetrics.registerFont(TTFont("DJB", FONT_BOLD))
    except Exception:
        pass


def _bf():
    return "DJB" if "DJB" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"


def _rf():
    return "DJ" if "DJ" in pdfmetrics.getRegisteredFontNames() else "Helvetica"


def make_certificate(solver_name, creator_name, score, total, quiz_id) -> bytes:
    _reg_fonts()
    buf = io.BytesIO()
    W, H = A4
    c = rl_canvas.Canvas(buf, pagesize=A4)

    # Background gradient
    for i in range(120):
        t = i / 120
        c.setFillColorRGB(0.07 + 0.03 * t, 0.04 + 0.02 * t, 0.16 + 0.07 * t)
        c.rect(0, H * t / 1.5, W, H / 120 + 2, fill=1, stroke=0)

    # Borders
    c.setStrokeColorRGB(0.85, 0.68, 0.15)
    c.setLineWidth(4)
    c.rect(22, 22, W - 44, H - 44, fill=0, stroke=1)
    c.setLineWidth(1)
    c.rect(32, 32, W - 64, H - 64, fill=0, stroke=1)

    # Corner marks
    c.setFont(_bf(), 18)
    c.setFillColorRGB(0.85, 0.68, 0.15)
    for sx, sy in [(52, 52), (W - 52, 52), (52, H - 52), (W - 52, H - 52)]:
        c.drawCentredString(sx, sy - 8, "+")

    c.setStrokeColorRGB(0.85, 0.68, 0.15)
    c.setLineWidth(0.8)
    c.line(90, H - 98, W - 90, H - 98)

    c.setFillColorRGB(0.95, 0.82, 0.28)
    c.setFont(_bf(), 46)
    c.drawCentredString(W / 2, H - 150, "SERTIFIKAT")

    c.setFillColorRGB(0.80, 0.80, 0.92)
    c.setFont(_rf(), 12)
    c.drawCentredString(W / 2, H - 175, "Meni qanchalik yaxshi bilasiz? — Quiz Bot")

    c.line(110, H - 195, W - 110, H - 195)

    c.setFillColorRGB(0.70, 0.70, 0.85)
    c.setFont(_rf(), 11)
    c.drawCentredString(W / 2, H - 228, "Ushbu sertifikat hurmat bilan taqdim etiladi:")

    name_d = solver_name[:28] + ("..." if len(solver_name) > 28 else "")
    c.setFillColorRGB(0.97, 0.86, 0.35)
    c.setFont(_bf(), 36)
    c.drawCentredString(W / 2, H - 272, name_d)

    nw = c.stringWidth(name_d, _bf(), 36)
    c.setStrokeColorRGB(0.97, 0.86, 0.35)
    c.setLineWidth(1.2)
    c.line(W / 2 - nw / 2, H - 280, W / 2 + nw / 2, H - 280)

    c.setFillColorRGB(0.82, 0.82, 0.95)
    c.setFont(_rf(), 12)
    c.drawCentredString(W / 2, H - 315,
        f'"{creator_name}" haqidagi viktorinani muvaffaqiyatli yakunladi')

    by = H - 415
    c.setFillColorRGB(0.10, 0.07, 0.25)
    c.roundRect(W / 2 - 100, by - 55, 200, 100, 14, fill=1, stroke=0)
    c.setStrokeColorRGB(0.85, 0.68, 0.15)
    c.setLineWidth(2.2)
    c.roundRect(W / 2 - 100, by - 55, 200, 100, 14, fill=0, stroke=1)

    pct = int(score / total * 100)
    c.setFillColorRGB(0.70, 0.70, 0.85)
    c.setFont(_rf(), 10)
    c.drawCentredString(W / 2, by + 27, "NATIJA")

    c.setFillColorRGB(0.97, 0.86, 0.35)
    c.setFont(_bf(), 34)
    c.drawCentredString(W / 2, by - 5, f"{score}/{total}")

    c.setFillColorRGB(0.72, 0.90, 0.72)
    c.setFont(_rf(), 10)
    c.drawCentredString(W / 2, by - 30, f"{pct}% to'g'ri javob")

    if pct == 100:
        lbl, lc = "MUKAMMAL!", (0.97, 0.86, 0.35)
    elif pct >= 70:
        lbl, lc = "A'LO NATIJA!", (0.55, 0.92, 0.55)
    elif pct >= 40:
        lbl, lc = "YAXSHI!", (0.55, 0.78, 0.97)
    else:
        lbl, lc = "DAVOM ETING!", (0.90, 0.65, 0.40)

    c.setFillColorRGB(*lc)
    c.setFont(_bf(), 17)
    c.drawCentredString(W / 2, H - 488, lbl)

    c.setFillColorRGB(0.50, 0.50, 0.62)
    c.setFont(_rf(), 9)
    c.drawCentredString(W / 2, H - 528,
        f"Sana: {datetime.now().strftime('%d.%m.%Y')}    |    Quiz ID: {quiz_id}")

    c.setStrokeColorRGB(0.85, 0.68, 0.15)
    c.setLineWidth(0.8)
    c.line(80, 88, W - 80, 88)

    c.setFillColorRGB(0.85, 0.68, 0.15)
    c.setFont(_bf(), 9)
    c.drawCentredString(W / 2, 70, "Meni qanchalik yaxshi bilasiz? — Quiz Bot")

    c.setFillColorRGB(0.48, 0.48, 0.60)
    c.setFont(_rf(), 7)
    c.drawCentredString(W / 2, 54, "Ushbu sertifikat bot tomonidan avtomatik yaratilgan")

    c.save()
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────
#  CREATOR SAVOL YUBORISH
# ──────────────────────────────────────────────────────────────
async def show_creator_question(context, chat_id, user_id):
    s = sessions[user_id]
    step  = s["step"]
    total = len(s["questions"])
    q     = s["questions"][step]

    options  = q["options"]
    progress = "🟦" * step + "⬜" * (total - step)
    caption  = (
        f"📝 <b>Savol {step + 1}/{total}</b> — O'z javobingizni tanlang:\n"
        f"{progress}\n\n"
        f"{q['question']}"
    )

    # Shuffled options stored so we can retrieve by index
    shuffled = list(options)
    random.shuffle(shuffled)
    s["current_options"] = shuffled

    await send_question(context, chat_id, s, caption, shuffled, q.get("image_url", ""))


# ──────────────────────────────────────────────────────────────
#  SOLVER SAVOL YUBORISH
# ──────────────────────────────────────────────────────────────
async def show_solver_question(context, chat_id, user_id):
    s    = sessions[user_id]
    quiz = db_get_quiz(s["quiz_id"])
    step = s["step"]
    q    = quiz["questions"][step]

    total    = len(quiz["questions"])
    options  = json.loads(q["options"])
    shuffled = list(options)
    random.shuffle(shuffled)
    s["current_options"] = shuffled

    progress = "🟩" * step + "⬜" * (total - step)
    icon     = "🔐" if step == total - 1 else "❓"
    caption  = (
        f"{icon} <b>Savol {step + 1}/{total}</b>\n"
        f"{progress}\n\n"
        f"{q['question']}"
    )

    await send_question(context, chat_id, s, caption, shuffled, q.get("image_url", ""))


# ──────────────────────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    # Deep link — do'st testni ishlaydi
    if args and args[0].startswith("quiz_"):
        quiz_id = args[0]
        quiz    = db_get_quiz(quiz_id)

        if not quiz:
            await update.message.reply_text(
                "❌ Viktorina topilmadi.",
                reply_markup=main_kb(),
            )
            return ST_MENU

        if quiz["creator_id"] == user.id:
            await update.message.reply_text(
                "🚫 Siz bu viktorinaning yaratuvchisisiz!\n"
                "O'z testingizni ishlab bo'lmaydi 😄\n\n"
                "Havolani do'stlaringizga yuboring! 📲",
                reply_markup=main_kb(),
            )
            return ST_MENU

        sessions[user.id] = {
            "mode":            "solving",
            "quiz_id":         quiz_id,
            "step":            0,
            "score":           0,
            "current_options": [],
            "msg_id":          None,
        }
        await update.message.reply_text(
            f"👋 Salom, <b>{user.first_name}</b>!\n\n"
            f"🧠 <b>{quiz['creator_name']}</b> haqidagi viktorinaga xush kelibsiz!\n\n"
            f"📝 Jami <b>{len(quiz['questions'])}</b> ta savol.\n"
            "💪 Boshlaylik! 🎯",
            reply_markup=main_kb(),
            parse_mode="HTML",
        )
        await show_solver_question(context, update.effective_chat.id, user.id)
        return ST_SOLVING

    # Oddiy /start
    await update.message.reply_text(
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        "🎯 <b>Meni qanchalik yaxshi bilasiz?</b>\n\n"
        "🤖 Bot avtomatik <b>9 ta savol</b> tanlaydi\n"
        "✍️ Har savolga <b>o'z javobingizni</b> belgilaysiz\n"
        "➕ Keyin <b>1 ta yashirin savol</b> qo'shasiz\n"
        "🔗 Havolani do'stlaringizga yuboring\n"
        "🏆 Kim sizni eng yaxshi bilishini aniqlang!\n\n"
        "👇 Quyidagi tugmalardan foydalaning:",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )
    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  PASTKI MENYU TUGMALARI
# ──────────────────────────────────────────────────────────────
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if text == "🎯 Quiz yaratish":
        picked = random.sample(DEFAULT_QUESTIONS, min(9, len(DEFAULT_QUESTIONS)))
        sessions[user.id] = {
            "mode":            "creating",
            "quiz_id":         "quiz_" + str(uuid.uuid4())[:8],
            "questions":       [dict(q) for q in picked],
            "step":            0,
            "creator_answers": [],
            "current_options": [],
            "msg_id":          None,
            "q10":             {},
        }
        await update.message.reply_text(
            "🎲 <b>9 ta savol avtomatik tanlandi!</b> ✅\n\n"
            "✍️ Endi har bir savolga <b>o'z javobingizni</b> tanlang.\n"
            "Do'stlaringiz aynan shu javoblarni topishi kerak! 👇",
            parse_mode="HTML",
        )
        await show_creator_question(context, update.effective_chat.id, user.id)
        return ST_CREATOR_ANS

    elif text == "📊 Statistika":
        await cmd_natijalar(update, context)
        return ST_MENU

    elif text == "🔗 Mening havolam":
        await cmd_havola(update, context)
        return ST_MENU

    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  CREATOR — tugma javoblari  (ST_CREATOR_ANS state)
# ──────────────────────────────────────────────────────────────
async def creator_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    s    = sessions.get(user.id)

    if not s or s.get("mode") != "creating":
        return ST_CREATOR_ANS

    # callback_data = "opt_N"
    try:
        idx = int(query.data.split("_")[1])
    except (ValueError, IndexError):
        return ST_CREATOR_ANS

    correct = s["current_options"][idx]
    q       = s["questions"][s["step"]]

    s["creator_answers"].append({
        "question":  q["question"],
        "correct":   correct,
        "options":   q["options"],
        "image_url": q.get("image_url", ""),
    })
    s["step"] += 1

    await query.message.reply_text(
        f"✅ <b>{correct}</b> — saqlandi!",
        parse_mode="HTML",
    )

    if s["step"] < len(s["questions"]):
        await show_creator_question(context, update.effective_chat.id, user.id)
        return ST_CREATOR_ANS

    # 9 ta savol tugadi → Q10
    await query.message.reply_text(
        "🎉 <b>9 ta savolga javob berdingiz!</b> ✅\n\n"
        "➕ Endi <b>10-savolni</b> yozasiz — bu sizning <b>yashirin faktingiz!</b>\n"
        "Do'stlaringiz bu savolga javob bera olmasa kerak 😄\n\n"
        "📝 Savol matnini yozing 👇",
        parse_mode="HTML",
    )
    return ST_Q10_TEXT


# ──────────────────────────────────────────────────────────────
#  Q10 — 3 qadam
# ──────────────────────────────────────────────────────────────
async def q10_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = sessions.get(update.effective_user.id)
    if not s:
        return ConversationHandler.END
    s["q10"]["question"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Savol qabul qilindi!\n\n"
        "💡 Endi <b>to'g'ri javobni</b> yozing 👇\n"
        "<i>(Bu javobni faqat siz bilasiz!)</i>",
        parse_mode="HTML",
    )
    return ST_Q10_ANS


async def q10_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = sessions.get(update.effective_user.id)
    if not s:
        return ConversationHandler.END
    s["q10"]["correct"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ To'g'ri javob saqlandi!\n\n"
        "📋 Endi <b>noto'g'ri variantlarni</b> yozing — <b>vergul bilan</b> ajrating:\n\n"
        "<i>Masalan: Toshkent, Buxoro, Namangan, Samarqand</i>\n\n"
        "👇 Qancha ko'p variant — shuncha qiziqarli!",
        parse_mode="HTML",
    )
    return ST_Q10_OPTS


async def q10_opts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    s    = sessions.get(user.id)
    if not s:
        return ConversationHandler.END

    wrong = [x.strip() for x in update.message.text.strip().split(",") if x.strip()]
    if not wrong:
        await update.message.reply_text(
            "⚠️ Kamida 1 ta noto'g'ri variant kiriting!\n"
            "<i>Vergul bilan ajrating: Toshkent, Buxoro, Namangan</i>",
            parse_mode="HTML",
        )
        return ST_Q10_OPTS

    correct     = s["q10"]["correct"]
    all_options = [correct] + wrong

    all_questions = s["creator_answers"] + [{
        "question":  s["q10"]["question"],
        "correct":   correct,
        "options":   all_options,
        "image_url": Q10_IMAGE,
    }]

    quiz_id = s["quiz_id"]
    db_save_quiz(quiz_id, user.id, user.first_name, all_questions)
    del sessions[user.id]

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={quiz_id}"

    await update.message.reply_text(
        "🎊 <b>Viktorinangiz tayyor!</b> 🎉\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Havola:</b>\n{link}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📲 Do'stlaringizga yuboring!\n"
        "🚫 Siz o'z testingizni ishlay olmaysiz.\n\n"
        "📊 /natijalar — natijalarni ko'rish\n"
        "🔗 /havola — havolangizni olish",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )
    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  SOLVER — tugma javoblari  (ST_SOLVING state)
# ──────────────────────────────────────────────────────────────
async def solver_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    s    = sessions.get(user.id)

    if not s or s.get("mode") != "solving":
        return ST_SOLVING

    try:
        idx = int(query.data.split("_")[1])
    except (ValueError, IndexError):
        return ST_SOLVING

    chosen  = s["current_options"][idx]
    quiz    = db_get_quiz(s["quiz_id"])
    correct = quiz["questions"][s["step"]]["correct"]

    if chosen == correct:
        s["score"] += 1
        fb = random.choice(["✅ To'g'ri! 🎉", "✅ Zo'r! 🌟", "✅ Ajoyib! 🔥", "✅ Barakalla! 👏"])
        await query.message.reply_text(fb)
    else:
        await query.message.reply_text(
            f"❌ Noto'g'ri!\n\n💡 To'g'ri javob: <b>{correct}</b>",
            parse_mode="HTML",
        )

    s["step"] += 1

    if s["step"] < len(quiz["questions"]):
        await show_solver_question(context, update.effective_chat.id, user.id)
        return ST_SOLVING

    # Test tugadi
    score   = s["score"]
    total   = len(quiz["questions"])
    quiz_id = s["quiz_id"]
    db_save_score(quiz_id, user.id, user.first_name, score, total)
    del sessions[user.id]

    pct = score / total
    if pct == 1.0:
        result = "🏆 <b>MUKAMMAL!</b> Siz uni juda yaxshi bilasiz! 🌟"
    elif pct >= 0.7:
        result = "🥈 <b>YAXSHI NATIJA!</b> Ko'proq bilib olish mumkin edi. 👍"
    elif pct >= 0.4:
        result = "🥉 <b>O'RTACHA.</b> Ko'proq vaqt o'tkazish kerak! 😅"
    else:
        result = "😂 <b>PAST NATIJA.</b> Tanishuvingiz endigina boshlanayotganga o'xshaydi!"

    stars = "⭐" * round(pct * 5)
    await query.message.reply_text(
        f"🎊 <b>Viktorina tugadi!</b>\n\n"
        f"👤 <b>{user.first_name}</b>\n"
        f"📊 Natija: <b>{score}/{total}</b> ({int(pct * 100)}%)\n"
        f"{stars}\n\n{result}\n\n"
        "⏳ Sertifikatingiz tayyorlanmoqda... 🎓",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )

    try:
        cert = make_certificate(user.first_name, quiz["creator_name"], score, total, quiz_id)
        kb   = [[InlineKeyboardButton("🏅 Reyting jadvalini ko'rish", callback_data=f"lb_{quiz_id}")]]
        await context.bot.send_document(
            chat_id=user.id,
            document=io.BytesIO(cert),
            filename=f"sertifikat_{user.first_name}.pdf",
            caption=(
                f"🎓 <b>{user.first_name}</b> uchun sertifikat!\n"
                f"🏆 Natija: <b>{score}/{total}</b> ({int(pct * 100)}%)\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y')}"
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Certificate error: {e}")

    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  REYTING TUGMASI
# ──────────────────────────────────────────────────────────────
async def leaderboard_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    quiz_id  = query.data[3:]
    rows     = db_get_scores(quiz_id)
    quiz     = db_get_quiz(quiz_id)

    if not rows:
        await query.message.reply_text("😴 Hali hech kim viktorinani yechmagan.")
        return

    medals = ["🥇", "🥈", "🥉"]
    text   = f"🏆 <b>{quiz['creator_name']} viktorinasi — Reyting:</b>\n\n"
    for i, row in enumerate(rows):
        m    = medals[i] if i < 3 else f"{i + 1}."
        p    = int(row["score"] / row["total"] * 100)
        stars = "⭐" * round(p / 20)
        text += f"{m} <b>{row['solver_name']}</b> — {row['score']}/{row['total']} ({p}%) {stars}\n\n"

    await query.message.reply_text(text, parse_mode="HTML")


# ──────────────────────────────────────────────────────────────
#  /natijalar
# ──────────────────────────────────────────────────────────────
async def cmd_natijalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    quizzes = db_user_quizzes(user.id)

    if not quizzes:
        await update.message.reply_text(
            "📭 Siz hali viktorina yaratmagansiz!\n👉 /start bilan boshlang 🚀",
            reply_markup=main_kb(),
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    text   = "📊 <b>Sizning viktorinalaring natijalari:</b>\n\n"
    for q in quizzes:
        rows = db_get_scores(q["quiz_id"])
        date = q["created_at"][:10]
        text += f"🎯 <b>{q['quiz_id']}</b>  📅 <i>{date}</i>\n"
        if not rows:
            text += "  😴 Hali hech kim ishlamagan.\n\n"
            continue
        for i, row in enumerate(rows[:5]):
            m = medals[i] if i < 3 else f"  {i + 1}."
            p = int(row["score"] / row["total"] * 100)
            text += f"  {m} {row['solver_name']} — {row['score']}/{row['total']} ({p}%)\n"
        if len(rows) > 5:
            text += f"  👥 ... va yana {len(rows) - 5} kishi\n"
        text += "\n"

    await update.message.reply_text(text, reply_markup=main_kb(), parse_mode="HTML")


# ──────────────────────────────────────────────────────────────
#  /havola
# ──────────────────────────────────────────────────────────────
async def cmd_havola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    quizzes = db_user_quizzes(user.id)

    if not quizzes:
        await update.message.reply_text(
            "📭 Siz hali viktorina yaratmagansiz!\n👉 /start bilan boshlang 🚀",
            reply_markup=main_kb(),
        )
        return

    bot_username = (await context.bot.get_me()).username
    text = "🔗 <b>Sizning viktorina havolalaringiz:</b>\n\n"
    for q in quizzes:
        link = f"https://t.me/{bot_username}?start={q['quiz_id']}"
        date = q["created_at"][:10]
        text += f"📅 <i>{date}</i>\n🔗 {link}\n\n"

    await update.message.reply_text(
        text + "👆 Havolani do'stlaringizga yuboring! 📲",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
#  /bekor
# ──────────────────────────────────────────────────────────────
async def cmd_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "🚫 Bekor qilindi.\n\n👉 /start bilan qayta boshlang!",
        reply_markup=main_kb(),
    )
    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
MENU_PATTERN = "^(🎯 Quiz yaratish|📊 Statistika|🔗 Mening havolam)$"


def main():
    init_db()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex(MENU_PATTERN), menu_handler),
        ],
        states={
            ST_MENU: [
                MessageHandler(filters.Regex(MENU_PATTERN), menu_handler),
                CallbackQueryHandler(leaderboard_cb, pattern=r"^lb_"),
            ],
            ST_CREATOR_ANS: [
                CallbackQueryHandler(creator_answer, pattern=r"^opt_\d+$"),
            ],
            ST_Q10_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, q10_text),
            ],
            ST_Q10_ANS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, q10_ans),
            ],
            ST_Q10_OPTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, q10_opts),
            ],
            ST_SOLVING: [
                CallbackQueryHandler(solver_answer, pattern=r"^opt_\d+$"),
                CallbackQueryHandler(leaderboard_cb, pattern=r"^lb_"),
            ],
        },
        fallbacks=[
            CommandHandler("bekor", cmd_bekor),
            CommandHandler("start", cmd_start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("natijalar",  cmd_natijalar))
    app.add_handler(CommandHandler("havola",     cmd_havola))
    app.add_handler(CommandHandler("statistika", cmd_natijalar))

    log.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
