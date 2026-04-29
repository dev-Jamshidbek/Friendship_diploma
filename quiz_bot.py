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
║  YANGI XUSUSIYATLAR:                                         ║
║    ✅ Quiz 15 kunda avtomatik o'chiriladi                    ║
║    ✅ Quiz yaratishda progress DB ga saqlanadi               ║
║    ✅ Do'st quizni ikki marta ishlay olmaydi                 ║
║    ✅ Havola + poster rasm bilan forward qilinadi            ║
╚══════════════════════════════════════════════════════════════╝
"""

import io
import json
import logging
import random
import sqlite3
import uuid
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
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
BOT_TOKEN = "8588187763:AAF-wgS8DNoda1hZnrbu2OYU6t66mCUhPjs"   # ← @BotFather dan oling

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Quiz 15 kun amal qiladi
QUIZ_EXPIRE_DAYS = 15

# ──────────────────────────────────────────────────────────────
#  20 TA DEFAULT SAVOL  —  XOHLAGANINGIZDA O'ZGARTIRING
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

Q10_IMAGE = "https://images.unsplash.com/photo-1633613286991-611fe299c4be?w=800"

# ──────────────────────────────────────────────────────────────
#  STATES
# ──────────────────────────────────────────────────────────────
(
    ST_MENU,
    ST_CREATOR_ANS,
    ST_Q10_TEXT,
    ST_Q10_ANS,
    ST_Q10_OPTS,
    ST_SOLVING,
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
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at   DATETIME
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
        CREATE TABLE IF NOT EXISTS draft_sessions (
            user_id      INTEGER PRIMARY KEY,
            quiz_id      TEXT,
            questions    TEXT,
            step         INTEGER DEFAULT 0,
            answers      TEXT DEFAULT '[]',
            q10          TEXT DEFAULT '{}',
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # expires_at ustunini eski DBga qo'shish (migration)
        try:
            c.execute("ALTER TABLE quizzes ADD COLUMN expires_at DATETIME")
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
#  QUIZ CRUD
# ──────────────────────────────────────────────────────────────
def db_save_quiz(quiz_id, creator_id, creator_name, questions):
    expires = datetime.utcnow() + timedelta(days=QUIZ_EXPIRE_DAYS)
    with db() as c:
        c.execute(
            "INSERT INTO quizzes (quiz_id, creator_id, creator_name, expires_at) VALUES (?,?,?,?)",
            (quiz_id, creator_id, creator_name, expires.strftime("%Y-%m-%d %H:%M:%S")),
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
        # Muddati o'tgan quizni qaytarma
        if row["expires_at"]:
            try:
                exp = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                if datetime.utcnow() > exp:
                    return None
            except Exception:
                pass
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
            "SELECT quiz_id,created_at,expires_at FROM quizzes"
            " WHERE creator_id=? ORDER BY created_at DESC",
            (creator_id,),
        ).fetchall()


def db_has_played(quiz_id, solver_id) -> bool:
    """Do'st bu quizni avval ishlaganmi?"""
    with db() as c:
        row = c.execute(
            "SELECT id FROM scores WHERE quiz_id=? AND solver_id=?",
            (quiz_id, solver_id),
        ).fetchone()
        return row is not None


def db_delete_quiz(quiz_id):
    """Quizni va unga tegishli barcha ma'lumotlarni o'chiradi."""
    with db() as c:
        c.execute("DELETE FROM questions WHERE quiz_id=?", (quiz_id,))
        c.execute("DELETE FROM scores    WHERE quiz_id=?", (quiz_id,))
        c.execute("DELETE FROM quizzes   WHERE quiz_id=?", (quiz_id,))


def db_delete_expired_quizzes():
    """15 kundan o'tgan quizlarni o'chirib tashlash."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with db() as c:
        expired = c.execute(
            "SELECT quiz_id FROM quizzes WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        ).fetchall()
        for row in expired:
            qid = row["quiz_id"]
            c.execute("DELETE FROM questions WHERE quiz_id=?", (qid,))
            c.execute("DELETE FROM scores    WHERE quiz_id=?", (qid,))
            c.execute("DELETE FROM quizzes   WHERE quiz_id=?", (qid,))
        if expired:
            log.info(f"O'chirilgan quizlar soni: {len(expired)}")


# ──────────────────────────────────────────────────────────────
#  DRAFT SESSION (progress saqlash)
# ──────────────────────────────────────────────────────────────
def draft_save(user_id, quiz_id, questions, step, answers, q10):
    with db() as c:
        c.execute("""
            INSERT INTO draft_sessions (user_id, quiz_id, questions, step, answers, q10, updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                quiz_id=excluded.quiz_id,
                questions=excluded.questions,
                step=excluded.step,
                answers=excluded.answers,
                q10=excluded.q10,
                updated_at=excluded.updated_at
        """, (
            user_id, quiz_id,
            json.dumps(questions, ensure_ascii=False),
            step,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(q10, ensure_ascii=False),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ))


def draft_load(user_id):
    with db() as c:
        row = c.execute(
            "SELECT * FROM draft_sessions WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "quiz_id":   row["quiz_id"],
            "questions": json.loads(row["questions"]),
            "step":      row["step"],
            "answers":   json.loads(row["answers"]),
            "q10":       json.loads(row["q10"]),
        }


def draft_delete(user_id):
    with db() as c:
        c.execute("DELETE FROM draft_sessions WHERE user_id=?", (user_id,))


# ──────────────────────────────────────────────────────────────
#  KEYBOARD HELPERS
# ──────────────────────────────────────────────────────────────
def main_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎯 Quiz yaratish")],
            [KeyboardButton("📊 Statistika"), KeyboardButton("🔗 Mening havolam")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_options(options: list) -> list:
    return [
        [InlineKeyboardButton(opt, callback_data=f"opt_{i}")]
        for i, opt in enumerate(options)
    ]


# ──────────────────────────────────────────────────────────────
#  SAVOL YUBORISH HELPER
# ──────────────────────────────────────────────────────────────
async def send_question(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    session: dict,
    caption: str,
    options: list,
    image_url: str,
):
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
#  POSTER RASM YARATISH (Pillow)
# ──────────────────────────────────────────────────────────────
def make_quiz_poster(creator_name: str, quiz_id: str, link: str, expire_days: int = 15) -> bytes:
    """Quiz uchun poster rasm PNG formatida qaytaradi."""
    W, H = 800, 600
    img = Image.new("RGB", (W, H), color=(18, 10, 40))
    draw = ImageDraw.Draw(img)

    # Gradient fon (qo'lda)
    for y in range(H):
        r = int(18 + (30 - 18) * y / H)
        g = int(10 + (15 - 10) * y / H)
        b = int(40 + (70 - 40) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Border
    border_color = (215, 172, 38)
    draw.rectangle([12, 12, W - 13, H - 13], outline=border_color, width=3)
    draw.rectangle([22, 22, W - 23, H - 23], outline=border_color, width=1)

    # Fontlar
    try:
        font_big   = ImageFont.truetype(FONT_BOLD, 52)
        font_med   = ImageFont.truetype(FONT_BOLD, 30)
        font_small = ImageFont.truetype(FONT_REG,  22)
        font_tiny  = ImageFont.truetype(FONT_REG,  18)
    except Exception:
        font_big = font_med = font_small = font_tiny = ImageFont.load_default()

    # Sarlavha
    title = "🧠 QUIZ"
    draw.text((W // 2, 80), title, font=font_big, fill=(245, 218, 88), anchor="mm")

    # Chiziq
    draw.line([(80, 130), (W - 80, 130)], fill=border_color, width=1)

    # Asosiy matn
    draw.text((W // 2, 195), "Meni qanchalik yaxshi bilasiz?",
              font=font_med, fill=(210, 210, 240), anchor="mm")

    # Yaratuvchi nomi
    name_short = creator_name[:22] + ("..." if len(creator_name) > 22 else "")
    draw.text((W // 2, 265), f"✨  {name_short}  ✨",
              font=font_med, fill=(245, 218, 88), anchor="mm")

    # Savollar soni
    draw.text((W // 2, 330), "📝 10 ta savol   |   🏆 Sertifikat",
              font=font_small, fill=(180, 180, 220), anchor="mm")

    # Muddati
    expire_date = (datetime.now() + timedelta(days=expire_days)).strftime("%d.%m.%Y")
    draw.text((W // 2, 390), f"⏳ Muddati: {expire_date} gacha",
              font=font_tiny, fill=(160, 160, 200), anchor="mm")

    # Havola qutisi
    draw.rounded_rectangle([60, 430, W - 60, 510], radius=16,
                            fill=(30, 18, 60), outline=border_color, width=2)
    link_display = link if len(link) <= 44 else link[:41] + "..."
    draw.text((W // 2, 470), f"🔗 {link_display}",
              font=font_tiny, fill=(100, 200, 255), anchor="mm")

    # Pastki matn
    draw.line([(80, 530), (W - 80, 530)], fill=border_color, width=1)
    draw.text((W // 2, 555), "Friendship Diploma  •  @frienship_diploma_bot",
              font=font_tiny, fill=(100, 100, 140), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


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
    W, H = 900, 600
    img  = Image.new("RGB", (W, H), color=(18, 10, 40))
    draw = ImageDraw.Draw(img)

    # Gradient fon
    for y in range(H):
        r = int(18 + (30 - 18) * y / H)
        g = int(10 + (15 - 10) * y / H)
        b = int(40 + (80 - 40) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Border
    gold = (215, 172, 38)
    draw.rectangle([12, 12, W - 13, H - 13], outline=gold, width=3)
    draw.rectangle([22, 22, W - 23, H - 23], outline=gold, width=1)

    # Fontlar
    try:
        fb = ImageFont.truetype(FONT_BOLD, 48)
        fm = ImageFont.truetype(FONT_BOLD, 28)
        fs = ImageFont.truetype(FONT_REG,  22)
        ft = ImageFont.truetype(FONT_REG,  17)
    except Exception:
        fb = fm = fs = ft = ImageFont.load_default()

    # Sarlavha
    draw.text((W // 2, 60),  "🏆 SERTIFIKAT",
              font=fb, fill=(245, 218, 88), anchor="mm")
    draw.line([(80, 100), (W - 80, 100)], fill=gold, width=1)

    # Taqdim etiladi
    draw.text((W // 2, 135), "Ushbu sertifikat hurmat bilan taqdim etiladi:",
              font=ft, fill=(170, 170, 210), anchor="mm")

    # Ism
    name_d = solver_name[:28] + ("..." if len(solver_name) > 28 else "")
    draw.text((W // 2, 195), name_d,
              font=fm, fill=(245, 218, 88), anchor="mm")
    nw = fm.getlength(name_d)
    draw.line([(W // 2 - nw // 2, 215), (W // 2 + nw // 2, 215)], fill=gold, width=1)

    # Tavsif
    draw.text((W // 2, 255),
              f'"{creator_name}" haqidagi viktorinani muvaffaqiyatli yakunladi',
              font=ft, fill=(200, 200, 230), anchor="mm")

    # Natija qutisi
    draw.rounded_rectangle([W // 2 - 110, 290, W // 2 + 110, 390],
                            radius=14, fill=(25, 15, 55), outline=gold, width=2)
    pct = int(score / total * 100)
    draw.text((W // 2, 318), "NATIJA",   font=ft, fill=(170, 170, 210), anchor="mm")
    draw.text((W // 2, 352), f"{score}/{total}", font=fm, fill=(245, 218, 88), anchor="mm")
    draw.text((W // 2, 378), f"{pct}% to'g'ri", font=ft, fill=(130, 220, 130), anchor="mm")

    # Baho
    if pct == 100:
        lbl, lc = "MUKAMMAL! ⭐⭐⭐⭐⭐", (245, 218, 88)
    elif pct >= 70:
        lbl, lc = "A'LO NATIJA! ⭐⭐⭐⭐", (130, 220, 130)
    elif pct >= 40:
        lbl, lc = "YAXSHI! ⭐⭐⭐", (100, 170, 245)
    else:
        lbl, lc = "DAVOM ETING! ⭐⭐", (230, 160, 90)

    draw.text((W // 2, 430), lbl, font=fs, fill=lc, anchor="mm")

    # Pastki info
    draw.line([(80, 470), (W - 80, 470)], fill=gold, width=1)
    draw.text((W // 2, 498),
              f"Sana: {datetime.now().strftime('%d.%m.%Y')}   |   Quiz ID: {quiz_id}",
              font=ft, fill=(120, 120, 160), anchor="mm")
    draw.text((W // 2, 530),
              "Meni qanchalik yaxshi bilasiz? — Quiz Bot",
              font=ft, fill=(100, 100, 140), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────
#  CREATOR SAVOL YUBORISH
# ──────────────────────────────────────────────────────────────
async def show_creator_question(context, chat_id, user_id):
    s     = sessions[user_id]
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

    shuffled = list(options)
    random.shuffle(shuffled)
    s["current_options"] = shuffled

    # Progressni DB ga saqlash
    draft_save(
        user_id,
        s["quiz_id"],
        s["questions"],
        step,
        s.get("creator_answers", []),
        s.get("q10", {}),
    )

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
                "❌ Viktorina topilmadi yoki muddati tugagan.\n\n"
                "⏳ Quizlar <b>15 kun</b> amal qiladi.",
                reply_markup=main_kb(),
                parse_mode="HTML",
            )
            return ST_MENU

        # Yaratuvchi o'z testini ishlay olmaydi
        if quiz["creator_id"] == user.id:
            await update.message.reply_text(
                "🚫 Siz bu viktorinaning yaratuvchisisiz!\n"
                "O'z testingizni ishlab bo'lmaydi 😄\n\n"
                "Havolani do'stlaringizga yuboring! 📲",
                reply_markup=main_kb(),
            )
            return ST_MENU

        # Ikki marta ishlash tekshiruvi
        if db_has_played(quiz_id, user.id):
            rows = db_get_scores(quiz_id)
            my_row = None
            with db() as conn:
                my_row = conn.execute(
                    "SELECT score, total FROM scores WHERE quiz_id=? AND solver_id=?",
                    (quiz_id, user.id),
                ).fetchone()
            score_txt = ""
            if my_row:
                pct = int(my_row["score"] / my_row["total"] * 100)
                score_txt = f"\n📊 Sizning natijangiz: <b>{my_row['score']}/{my_row['total']}</b> ({pct}%)"
            await update.message.reply_text(
                f"⚠️ Siz bu viktorinani allaqachon ishlagansiz!\n"
                f"Bir kishiga faqat <b>1 marta</b> ruxsat beriladi.{score_txt}\n\n"
                "📊 /natijalar — umumiy natijalarni ko'rish",
                reply_markup=main_kb(),
                parse_mode="HTML",
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

    # Oddiy /start — draft bormi tekshiramiz
    draft = draft_load(user.id)
    if draft:
        # Davom etish tugmasi
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("▶️ Davom etish", callback_data="draft_continue"),
            InlineKeyboardButton("🗑️ O'chirish", callback_data="draft_delete"),
        ]])
        await update.message.reply_text(
            f"👋 Salom, <b>{user.first_name}</b>!\n\n"
            f"📌 Sizda tugallanmagan quiz bor!\n"
            f"📝 <b>{draft['step']}/9</b> ta savolga javob berilgan.\n\n"
            "Davom etasizmi?",
            reply_markup=kb,
            parse_mode="HTML",
        )
        return ST_CREATOR_ANS

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
#  DRAFT CALLBACK (davom etish / o'chirish)
# ──────────────────────────────────────────────────────────────
async def draft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = update.effective_user

    # ── Draft davom etish ──
    if query.data == "draft_continue":
        draft = draft_load(user.id)
        if not draft:
            await query.message.reply_text("⚠️ Draft topilmadi.", reply_markup=main_kb())
            return ST_MENU
        sessions[user.id] = {
            "mode":            "creating",
            "quiz_id":         draft["quiz_id"],
            "questions":       draft["questions"],
            "step":            draft["step"],
            "creator_answers": draft["answers"],
            "current_options": [],
            "msg_id":          None,
            "q10":             draft["q10"],
        }
        await query.message.reply_text(
            f"▶️ Davom etilmoqda... <b>{draft['step'] + 1}</b>-savoldan.",
            parse_mode="HTML",
        )
        await show_creator_question(context, query.message.chat_id, user.id)
        return ST_CREATOR_ANS

    # ── Draft o'chirish ──
    elif query.data == "draft_delete":
        draft_delete(user.id)
        await query.message.reply_text(
            "🗑️ Draft o'chirildi.\n\n👉 <b>Quiz yaratish</b> tugmasini bosing.",
            reply_markup=main_kb(),
            parse_mode="HTML",
        )
        return ST_MENU

    # ── Eski aktiv quizni o'chirib yangi yaratish ──
    elif query.data.startswith("delete_old_"):
        old_quiz_id = query.data.replace("delete_old_", "")
        db_delete_quiz(old_quiz_id)
        await query.message.reply_text(
            "🗑️ Eski quiz o'chirildi!\n\n"
            "🎯 Endi <b>Quiz yaratish</b> tugmasini bosib yangi quiz yarating.",
            reply_markup=main_kb(),
            parse_mode="HTML",
        )
        return ST_MENU

    # ── Bekor qilish ──
    elif query.data == "cancel_create":
        await query.message.reply_text(
            "❌ Bekor qilindi.",
            reply_markup=main_kb(),
        )
        return ST_MENU

    return ST_MENU

# ──────────────────────────────────────────────────────────────
#  PASTKI MENYU TUGMALARI
# ──────────────────────────────────────────────────────────────
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if text == "🎯 Quiz yaratish":
        # Draft borligini tekshir
        draft = draft_load(user.id)
        if draft:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Davom etish", callback_data="draft_continue"),
                InlineKeyboardButton("🗑️ Yangidan boshlash", callback_data="draft_delete"),
            ]])
            await update.message.reply_text(
                f"📌 Sizda tugallanmagan quiz bor!\n"
                f"📝 <b>{draft['step']}/9</b> ta savolga javob berilgan.\n\n"
                "Davom etasizmi yoki yangidan boshlaysizmi?",
                reply_markup=kb,
                parse_mode="HTML",
            )
            return ST_CREATOR_ANS

        # Aktiv quiz borligini tekshir
        existing = db_user_quizzes(user.id)
        # Muddati o'tmagan quizlarni filter qilish
        active_quizzes = []
        for q in existing:
            if q["expires_at"]:
                try:
                    exp = datetime.strptime(q["expires_at"], "%Y-%m-%d %H:%M:%S")
                    if datetime.utcnow() < exp:
                        active_quizzes.append(q)
                except Exception:
                    pass

        if active_quizzes:
            aq = active_quizzes[0]
            exp_date = aq["expires_at"][:10] if aq["expires_at"] else "—"
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑️ Eskisini o'chirib yangi yaratish",
                                     callback_data=f"delete_old_{aq['quiz_id']}"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_create"),
            ]])
            await update.message.reply_text(
                f"⚠️ Sizda allaqachon aktiv quiz bor!\n\n"
                f"🆔 <code>{aq['quiz_id']}</code>\n"
                f"📅 Yaratilgan: <b>{aq['created_at'][:10]}</b>\n"
                f"⏳ Muddati: <b>{exp_date}</b> gacha\n\n"
                "Yangi quiz yaratish uchun eskisini o'chirish kerak.\n"
                "O'chirilgan quiz natijalari ham o'chib ketadi!",
                reply_markup=kb,
                parse_mode="HTML",
            )
            return ST_MENU

        # Quiz yo'q — yangi yaratish
        picked = random.sample(DEFAULT_QUESTIONS, min(9, len(DEFAULT_QUESTIONS)))
        sessions[user.id] = {
            "mode": "creating",
            "quiz_id": "quiz_" + str(uuid.uuid4())[:8],
            "questions": [dict(q) for q in picked],
            "step": 0,
            "creator_answers": [],
            "current_options": [],
            "msg_id": None,
            "q10": {},
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

    # Progressni saqlash
    draft_save(
        user.id,
        s["quiz_id"],
        s["questions"],
        s["step"],
        s["creator_answers"],
        s.get("q10", {}),
    )

    await query.message.reply_text(
        f"✅ <b>{correct}</b> — saqlandi!",
        parse_mode="HTML",
    )

    if s["step"] < len(s["questions"]):
        await show_creator_question(context, update.effective_chat.id, user.id)
        return ST_CREATOR_ANS

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
    if not s or s.get("mode") != "creating":
        await update.message.reply_text(
            "⚠️ Sessiya tugadi. /start bilan qayta boshlang.",
            reply_markup=main_kb(),
        )
        return ConversationHandler.END
    if "q10" not in s:
        s["q10"] = {}
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
    if not s or s.get("mode") != "creating":
        await update.message.reply_text(
            "⚠️ Sessiya tugadi. /start bilan qayta boshlang.",
            reply_markup=main_kb(),
        )
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
    if not s or s.get("mode") != "creating":
        await update.message.reply_text(
            "⚠️ Sessiya tugadi. /start bilan qayta boshlang.",
            reply_markup=main_kb(),
        )
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

    # Draft o'chirish
    draft_delete(user.id)
    del sessions[user.id]

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={quiz_id}"
    expire_date = (datetime.now() + timedelta(days=QUIZ_EXPIRE_DAYS)).strftime("%d.%m.%Y")

    # Matnli xabar
    await update.message.reply_text(
        "🎊 <b>Viktorinangiz tayyor!</b> 🎉\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Havola:</b>\n{link}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Quiz <b>{expire_date}</b> gacha amal qiladi.\n"
        "📲 Quyidagi posterni do'stlaringizga yuboring!\n"
        "🚫 Siz o'z testingizni ishlay olmaysiz.\n\n"
        "📊 /natijalar — natijalarni ko'rish\n"
        "🔗 /havola — havolangizni olish",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )

    # Poster rasm yuborish
    try:
        poster_bytes = make_quiz_poster(user.first_name, quiz_id, link, QUIZ_EXPIRE_DAYS)
        caption = (
            f"🧠 <b>{user.first_name}</b>ning quizi!\n\n"
            f"🔗 {link}\n\n"
            f"👆 Mana shu rasmni do'stlaringizga <b>forward</b> qiling!\n"
            f"⏳ Muddati: {expire_date} gacha"
        )
        await update.message.reply_photo(
            photo=io.BytesIO(poster_bytes),
            caption=caption,
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Poster error: {e}")
        # Rasm ishlamasa oddiy havola yuboramiz
        await update.message.reply_text(
            f"🔗 Forward qilish uchun havola:\n{link}",
            reply_markup=main_kb(),
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
        kb = [[InlineKeyboardButton("🏅 Reyting jadvalini ko'rish", callback_data=f"lb_{quiz_id}")]]
        await context.bot.send_photo(
            chat_id=user.id,
            photo=io.BytesIO(cert),
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
        m     = medals[i] if i < 3 else f"{i + 1}."
        p     = int(row["score"] / row["total"] * 100)
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
        exp  = q["expires_at"][:10] if q["expires_at"] else "—"
        text += f"🎯 <b>{q['quiz_id']}</b>  📅 <i>{date}</i>  ⏳ <i>{exp} gacha</i>\n"
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
#  /havola  —  havola + poster
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

    for q in quizzes:
        link = f"https://t.me/{bot_username}?start={q['quiz_id']}"
        exp  = q["expires_at"][:10] if q["expires_at"] else "—"
        date = q["created_at"][:10]

        # Matnli xabar
        await update.message.reply_text(
            f"📅 <i>{date}</i>  |  ⏳ <i>{exp} gacha</i>\n"
            f"🔗 {link}",
            reply_markup=main_kb(),
            parse_mode="HTML",
        )

        # Poster rasm
        try:
            quiz = db_get_quiz(q["quiz_id"])
            creator_name = quiz["creator_name"] if quiz else user.first_name
            poster_bytes = make_quiz_poster(creator_name, q["quiz_id"], link, QUIZ_EXPIRE_DAYS)
            caption = (
                f"🧠 <b>{creator_name}</b>ning quizi!\n\n"
                f"🔗 {link}\n\n"
                f"👆 Mana shu rasmni <b>forward</b> qiling!\n"
                f"⏳ Muddati: {exp} gacha"
            )
            await update.message.reply_photo(
                photo=io.BytesIO(poster_bytes),
                caption=caption,
                parse_mode="HTML",
            )
        except Exception as e:
            log.error(f"Poster error in /havola: {e}")


# ──────────────────────────────────────────────────────────────
#  /bekor
# ──────────────────────────────────────────────────────────────
async def cmd_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    sessions.pop(uid, None)
    draft_delete(uid)
    await update.message.reply_text(
        "🚫 Bekor qilindi. Draft ham o'chirildi.\n\n👉 /start bilan qayta boshlang!",
        reply_markup=main_kb(),
    )
    return ST_MENU


# ──────────────────────────────────────────────────────────────
#  EXPIRED QUIZ CLEANUP — har 6 soatda ishga tushadi
# ──────────────────────────────────────────────────────────────
async def cleanup_expired(context: ContextTypes.DEFAULT_TYPE):
    db_delete_expired_quizzes()


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
                CallbackQueryHandler(draft_callback, pattern=r"^delete_old_"),  # ← yangi
                CallbackQueryHandler(draft_callback, pattern=r"^cancel_create$"),  # ← yangi
            ],
            ST_CREATOR_ANS: [
                CallbackQueryHandler(creator_answer,  pattern=r"^opt_\d+$"),
                CallbackQueryHandler(draft_callback,  pattern=r"^draft_"),
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
                CallbackQueryHandler(solver_answer,  pattern=r"^opt_\d+$"),
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

    # Har 6 soatda eski quizlarni o'chirish
    app.job_queue.run_repeating(cleanup_expired, interval=6 * 3600, first=60)

    log.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
