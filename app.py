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
from telegram.error import BadRequest, TelegramError, RetryAfter, TimedOut
from telegram.request import HTTPXRequest

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
PENDING_FOLLOWUPS: set[int] = set()

# ========== BOTÕES ==========
def btn_criar_conta():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)]])

def btn_sim():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ SIM", callback_data=CB_CONFIRM_SIM)]])

def btn_acessar_comunidade():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Acessar comunidade", url=LINK_COMUNIDADE_FINAL)]])

# ========== HELPERS DE ENVIO COM RETRY ==========
async def _retry_send(coro_factory, *, max_attempts=2):
    """Executa uma chamada ao Telegram com retry simples em TimedOut/RetryAfter."""
    attempt = 0
    last_exc = None
    while attempt < max_attempts:
        try:
            return await coro_factory()
        except RetryAfter as e:
            wait = getattr(e, "retry_after", 1)
            log.warning("RetryAfter: aguardando %ss ...", wait)
            await asyncio.sleep(wait)
            attempt += 1
            last_exc = e
        except TimedOut:
            log.warning("TimedOut: tentando novamente ...")
            await asyncio.sleep(1)
            attempt += 1
        except Exception as e:
            last_exc = e
            break
    if last_exc:
        raise last_exc

# ========== ENVIO DE IMAGEM (converte p/ JPEG + retry) ==========
async def send_image(context: ContextTypes.DEFAULT_TYPE, chat_id: int, path: str, caption=None, reply_markup=None):
    try:
        full = os.path.join(os.path.dirname(__file__), path)
        if not (os.path.exists(full) and os.path.getsize(full) > 0):
            raise FileNotFoundError(f"Imagem ausente/vazia: {full}")

        with Image.open(full) as im:
            im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85, optimize=True)
            buf.seek(0)

        await _retry_send(lambda: context.bot.send_photo(
            chat_id=chat_id,
            photo=buf,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        ))
        log.info("Imagem enviada: %s", path)
    except Exception as e:
        log.warning("Falha ao enviar imagem %s (%s). Enviando texto.", path, e)
        if caption:
            await _retry_send(lambda: context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            ))

# ========== ENVIO DE ÁUDIO (retry) ==========
async def send_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, local_path: str, caption=None):
    full = os.path.join(os.path.dirname(__file__), local_path)
    if not (os.path.exists(full) and os.path.getsize(full) > 0):
        log.warning("Áudio ausente/vazio: %s", full)
        return
    with open(full, "rb") as f:
        await _retry_send(lambda: context.bot.send_audio(
            chat_id=chat_id,
            audio=InputFile(f, filename=os.path.basename(local_path)),
            caption=caption,
        ))
    log.info("Áudio enviado: %s", local_path)

# ========== COMANDOS DE TESTE ==========
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _retry_send(lambda: context.bot.send_message(chat_id=update.effective_chat.id, text="pong ✅"))

async def test10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    schedule_followup(context, chat_id, wait_seconds=10)
    await _retry_send(lambda: context.bot.send_message(chat_id=chat_id, text="⏱️ Follow-up de TESTE agendado para 10s."))

# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    log.info("START user_id=%s username=%s chat_id=%s", user.id, user.username, chat_id)

    # 1) áudio inicial
    try:
        await send_audio(context, chat_id, AUDIO_INICIAL, caption="🔊 Ouça essa mensagem rápida antes de continuar")
    except Exception as e:
        log.warning("Falha ao enviar áudio (%s).", e)

    # 2) imagem + CTA
    await send_image(context, chat_id, IMG_INICIAL, "🎁 *Presente do Jota aguardando…*\n\nClique no botão abaixo para abrir sua conta e garantir seu presente de membros novos.", btn_criar_conta())

    # 3) agenda follow-up
    schedule_followup(context, chat_id, WAIT_SECONDS)

# ========== AGENDAMENTO ==========
def schedule_followup(context: ContextTypes.DEFAULT_TYPE, chat_id: int, wait_seconds: int):
    if chat_id in PENDING_FOLLOWUPS:
        log.info("Follow-up já pendente para chat_id=%s", chat_id)
        return
    PENDING_FOLLOWUPS.add(chat_id)
    jq = context.application.job_queue
    if not jq:
        log.error("JobQueue não inicializado (instale o extra job-queue).")
        return
    job_name = f"followup-{chat_id}"
    jq.run_once(send_followup_job, when=wait_seconds, data={"chat_id": chat_id}, name=job_name)
    log.info("Follow-up (%ss) agendado via JobQueue: %s", wait_seconds, job_name)

async def send_followup_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    log.info("JobQueue disparou follow-up para chat_id=%s", chat_id)
    if chat_id in PENDING_FOLLOWUPS:
        await send_followup_message(context, chat_id)
        PENDING_FOLLOWUPS.discard(chat_id)

async def send_followup_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await _retry_send(lambda: context.bot.send_message(
        chat_id=chat_id,
        text="Eae, já conseguiu finalizar a criação da sua conta?",
        reply_markup=btn_sim(),
    ))
    log.info("Follow-up enviado ao chat_id=%s", chat_id)

# ========== Clique no SIM ==========
async def confirm_sim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    log.info("CONFIRM_SIM chat_id=%s user_id=%s", chat_id, query.from_user.id)

    texto_final = (
        "🎁 *Presente Liberado!!!*\n\n"
        "Basta você entrar na comunidade e buscar o sorteio que já vou te enviar,\n"
        "e fica de olho que o resultado sai na live de *HOJE*."
    )
    await send_image(context, chat_id, IMG_FINAL, texto_final, btn_acessar_comunidade())

# ========== Error handler ==========
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error: %s | update=%s", context.error, update)

# ========== MAIN ==========
def main():
    # timeouts maiores no cliente HTTP => menos ReadTimeout
    request = HTTPXRequest(
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=10.0,
        pool_timeout=10.0,
    )

    app = ApplicationBuilder()\
        .token(TOKEN)\
        .request(request)\
        .job_queue(JobQueue())\
        .build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("test10", test10))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_sim, pattern=f"^{CB_CONFIRM_SIM}$"))

    app.add_error_handler(on_error)

    log.info("🤖 Bot rodando (polling) com timeouts aumentados e retries. Dropando updates pendentes.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
