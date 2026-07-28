"""TestMind Telegram bot — delivers the result, and can also run the test.

Main job: the website's result screen links to t.me/<bot>?start=<archetype-slug>,
and the bot replies with that archetype's result plus the 8-page PDF guide.
Opening the bot directly also lets you take the 50 questions in-chat.

Answers live only in memory for the duration of a session; nothing is stored or
sent anywhere. Uses long-polling, so it needs no public server to run.
"""
import html
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes)

import testmind_core as core

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("testmind-bot")

SITE = "https://raximovv.github.io/TestMind/"
GUIDE_URL = SITE + "guides/%s.pdf"
# The PDFs live in the WEBSITE repo — that is the single source of truth, so the
# bot never ships a stale copy. Set TESTMIND_GUIDES to a local guides/ folder to
# upload from disk instead (useful before the site is pushed, or if offline).
GUIDES_DIR = os.environ.get("TESTMIND_GUIDES", "").strip()
N = len(core.ITEMS)  # 50

# user_id -> {"answers": [0]*N, "current": int}. In-memory only (v1).
sessions = {}
# slug -> Telegram file_id. Telegram keeps every file it has seen, so after the
# first upload the same PDF is re-sent instantly and without fetching it again.
guide_file_ids = {}


def esc(s):
    return html.escape(str(s))


def get_token():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if tok:
        return tok.strip()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


# ---------- rendering ----------
def progress_bar(done, total, width=12):
    filled = round(done / total * width)
    return "▰" * filled + "▱" * (width - filled)


def welcome_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Testni shu yerda ishlash", callback_data="begin")],
        [InlineKeyboardButton("🌐 Saytda ishlash", url=SITE)],
    ])


WELCOME = (
    "🧭 <b>TestMind — bepul shaxsiyat testi</b>\n\n"
    "Odatda natijangizni va 8 sahifalik PDF qoʻllanmangizni saytda test "
    "topshirgach shu yerga yuboramiz. Lekin xohlasangiz, testni shu yerda ham "
    "ishlashingiz mumkin.\n\n"
    "50 ta savol, taxminan 7 daqiqa. Toʻgʻri yoki notoʻgʻri javob yoʻq — oʻzingizga "
    "qarab, chin dildan javob bering. Javoblaringiz hech qayerga saqlanmaydi."
)


def render_question(idx, answers):
    it = core.ITEMS[idx]
    text = (f"<b>Savol {idx + 1} / {N}</b>\n"
            f"{progress_bar(idx, N)}\n\n"
            f"{esc(it['t'])}")
    if it.get("h"):
        text += f"\n\n<i>{esc(it['h'])}</i>"
    text += "\n\nQuyidagilardan birini tanlang:"

    rows = []
    for v in range(1, 6):
        mark = " ✅" if answers[idx] == v else ""
        rows.append([InlineKeyboardButton(core.LABELS[v - 1] + mark, callback_data=f"a:{v}")])
    if idx > 0:
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back")])
    return text, InlineKeyboardMarkup(rows)


def render_archetype(a):
    """Build the result message from an archetype dict — used both by the in-bot
    test (via archetype_of(scores)) and by delivery from the website (via slug)."""
    lines = "\n\n".join(esc(l) for l in a["lines"])
    text = (
        f"🎉 Natijangiz tayyor!\n\n"
        f"🎭 <b>{esc(a['name'])}</b>\n"
        f"<i>{esc(a['famName'])}</i>\n\n"
        f"{lines}\n\n"
        f"💪 <b>Kuchli tomoningiz:</b> {esc(a['strength'])}\n\n"
        f"⚠️ <b>Eʼtibor bering:</b> {esc(a['watch'])}\n\n"
        f"📜 <b>{esc(a['figure']['who'])}</b> "
        f"<i>({esc(a['figure']['years'])})</i>\n"
        f"{esc(a['figure']['why'])}\n\n"
        f"— Bu bugungi suratingiz, oʻzgarmas yorliq emas. 13–18 yoshda shaxsiyat "
        f"hali shakllanmoqda.\n\n"
        f"🔗 {SITE}"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Qaytadan", callback_data="begin")]])
    return text, kb


async def send_guide(chat, a):
    """Send the archetype's PDF guide. Falls back to a plain link if the file
    cannot be delivered — a student must never be left with nothing."""
    slug = a["slug"]
    caption = ("📘 <b>%s</b> — toʻliq qoʻllanma (8 sahifa)\n"
               "Kuchli tomonlaringiz, oʻsish nuqtalari, maktab va kelajak "
               "yoʻnalishlari, ikki haftalik amaliyot." % esc(a["name"]))
    filename = "TestMind-%s.pdf" % slug

    # 1. already uploaded once  2. local folder  3. straight from the website
    sources = []
    if slug in guide_file_ids:
        sources.append(guide_file_ids[slug])
    if GUIDES_DIR:
        path = os.path.join(GUIDES_DIR, slug + ".pdf")
        if os.path.isfile(path):
            sources.append(path)
    sources.append(GUIDE_URL % slug)

    for src in sources:
        try:
            if isinstance(src, str) and os.path.isfile(src):
                with open(src, "rb") as f:
                    msg = await chat.reply_document(f, filename=filename,
                                                    caption=caption, parse_mode="HTML")
            else:
                msg = await chat.reply_document(src, filename=filename,
                                                caption=caption, parse_mode="HTML")
            if msg and msg.document:
                guide_file_ids[slug] = msg.document.file_id
            return True
        except Exception as e:                      # noqa: BLE001 — any failure, try next
            log.warning("guide send failed for %s via %.40s: %s", slug, src, e)

    await chat.reply_text(
        "Qoʻllanmani hozir yuborib boʻlmadi. Uni shu havoladan yuklab olishingiz "
        "mumkin:\n" + (GUIDE_URL % slug), disable_web_page_preview=True)
    return False


# ---------- handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Deep link from the website result screen: t.me/<bot>?start=<archetype-slug>
    # -> deliver that result immediately, no questions.
    args = context.args
    if args and args[0] in core.BY_SLUG:
        a = core.BY_SLUG[args[0]]
        text, kb = render_archetype(a)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML",
                                        disable_web_page_preview=True)
        await send_guide(update.message, a)
        return
    await update.message.reply_text(WELCOME, reply_markup=welcome_markup(),
                                    parse_mode="HTML")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "begin":
        sessions[uid] = {"answers": [0] * N, "current": 0}
        text, kb = render_question(0, sessions[uid]["answers"])
        await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return

    st = sessions.get(uid)
    if not st:
        await q.edit_message_text("Sessiya tugagan. /start bosing.", parse_mode="HTML")
        return

    if data == "back":
        st["current"] = max(0, st["current"] - 1)
        text, kb = render_question(st["current"], st["answers"])
        await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if data.startswith("a:"):
        v = int(data[2:])
        st["answers"][st["current"]] = v
        st["current"] += 1
        if st["current"] >= N:
            a = core.archetype_of(core.score_answers(st["answers"]))
            text, kb = render_archetype(a)
            await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML",
                                      disable_web_page_preview=True)
            sessions.pop(uid, None)
            await send_guide(q.message, a)
        else:
            text, kb = render_question(st["current"], st["answers"])
            await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")


def main():
    app = Application.builder().token(get_token()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    log.info("TestMind bot starting (long-polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
