import os
import io
import asyncio
import logging
from dotenv import load_dotenv
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)
from telegram.error import BadRequest, TelegramError

# ========= LOGGING =========
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("presente-do-jota")

# ========= CONFIG =========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Defina TELEGRAM_TOKEN no .env ou nas Variables do Railway")

# Links
LINK_CADASTRO = (
    "https://betboom.bet.br/registration/base/?utm_source=inf&utm_medium=bloggers"
    "&utm_campaign=309&utm_content=regcasino_br&utm_term=6064&aff=alanbase&"
    "qtag=a6064_t309_c147_s019a5553-fabe-7180-b1d2-8c55097d2b32_"
)
LINK_COMUNIDADE_FINAL = "https://t.me/+rtq84bGVBhQyZmJh"

# Arquivos
AUDIO_INICIAL = "Audio i.mp3"
IMG_INICIAL = "presente_do_jota.jpg"
IMG_FINAL = "presente_do_jota_2.jpg"

# Callback data
CB_CONFIRM_SIM = "confirm_sim"
WAIT_SECONDS = 120  # 2 minutos
PENDING_FOLLOWUPS: set[int] = set()  # chats com follow-up pendente


# ========= BOTÕES =========
def btn_criar_conta():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)]]
    )

def btn_sim():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ SIM", callback_data=CB_CONFIRM_SIM)]])

def btn_acessar_comunidade():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚀 Acessar comunidade", url=LINK_COMUNIDADE_FINAL)]]
    )


# ========= UTIL: Enviar imagem (converte p/ JPEG) =========
async def send_image(context, chat_id, path, caption=None, reply_markup=None):
    try:
        full = os.path.join(os.path.dirname(__file__), path)
        if not (os.path.exists(full) and os.path.getsize(full) > 0):
            raise FileNotFoundError(f"Imagem ausente/vazia: {full}")

        with Image.open(full) as im:
            im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=90, optimize=True)
            buf.seek(0)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=buf,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        log.info("Imagem enviada: %s", path)
    except Exception as e:
        log.warning("Falha ao enviar imagem %s (%s). Enviando texto.", path, e)
        if caption:
            await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown", reply_markup=reply_markup)


# ========= COMANDOS DE TESTE =========
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="pong ✅")

async def test10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    schedule_followup(context, chat_id, wait_seconds=10)
    await context.bot.send_message(chat_id=chat_id, text="⏱️ Follow-up de TESTE agendado para 10s.")


# ========= /start =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    log.info("START user_id=%s username=%s chat_id=%s", user.id, user.username, chat_id)

    # 1️⃣ Envia áudio inicial
    try:
        audio_path = os.path.join(os.path.dirname(__file__), AUDIO_INICIAL)
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            with open(audio_path, "rb") as f:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=InputFile(f, filename="i.mp3"),
                    caption="🔊 Ouça essa mensagem rápida antes de continuar",
                )
            log.info("Áudio inicial enviado: %s", AUDIO_INICIAL)
        else:
            log.warning("Áudio inicial ausente/vazio: %s", audio_path)
    except Exception as e:
        log.warning("Falha ao enviar áudio inicial (%s).", e)

    # 2️⃣ Envia imagem + CTA
    caption_inicial = "🎁 *Presente do Jota aguardando…*\n\nClique no botão abaixo para abrir sua conta e garantir seu presente de membros novos."
    await send_image(context, chat_id, IMG_INICIAL, caption_inicial, reply_markup=btn_criar_conta())

    # 3️⃣ Agenda follow-up
    schedule_followup(context, chat_id, WAIT_SECONDS)


# ========= Agendamento do Follow-up =========
def schedule_followup(context: ContextTypes.DEFAULT_TYPE, chat_id: int, wait_seconds: int):
    if chat_id in PENDING_FOLLOWUPS:
        log.info("Follow-up já pendente para chat_id=%s", chat_id)
        return

    PENDING_FOLLOWUPS.add(chat_id)
    jq = context.application.job_queue
    if not jq:
        log.warning("⚠️ JobQueue não inicializado. Nenhum job será criado.")
        return

    job_name = f"followup-{chat_id}"
    jq.run_once(send_followup_job, when=wait_seconds, data={"chat_id": chat_id}, name=job_name)
    log.info("Follow-up (%ss) agendado via JobQueue: %s", wait_seconds, job_name)


# ========= Job executado após o tempo =========
async def send_followup_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    log.info("JobQueue disparou follow-up para chat_id=%s", chat_id)
    if chat_id in PENDING_FOLLOWUPS:
        await send_followup_message(context, chat_id)
        PENDING_FOLLOWUPS.discard(chat_id)


async def send_followup_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    text = "Eae, já conseguiu finalizar a criação da sua conta?"
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=btn_sim())
    log.info("Follow-up enviado ao chat_id=%s", chat_id)


# ========= Clique no SIM =========
async def confirm_sim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user = query.from_user
    log.info("CONFIRM_SIM user_id=%s chat_id=%s", user.id, chat_id)

    texto_final = (
        "🎁 *Presente Liberado!!!*\n\n"
        "Basta você entrar na comunidade e buscar o sorteio que já vou te enviar,\n"
        "e fica de olho que o resultado sai na live de *HOJE*."
    )
    await send_image(context, chat_id, IMG_FINAL, texto_final, reply_markup=btn_acessar_comunidade())


# ========= Error Handler =========
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error: %s | update=%s", context.error, update)


# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(TOKEN).job_queue(JobQueue()).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("test10", test10))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_sim, pattern=f"^{CB_CONFIRM_SIM}$"))

    app.add_error_handler(on_error)

    log.info("🤖 Bot rodando com JobQueue habilitado e fallback asyncio pronto.")
    app.run_polling()

if __name__ == "__main__":
    main()
