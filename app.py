import os, json, asyncio, logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)
from telegram.error import RetryAfter, TimedOut
from telegram.request import HTTPXRequest

# ========= LOGGING =========
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger("presente-do-jota")

# ========= CONFIG =========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN") or ""
if not TOKEN:
    raise RuntimeError("❌ Defina TELEGRAM_TOKEN no .env ou nas Variables do Railway")

# Links
LINK_CADASTRO = (
    "https://betboom.bet.br/registration/base/?utm_source=inf&utm_medium=bloggers"
    "&utm_campaign=309&utm_content=regcasino_br&utm_term=6064&aff=alanbase&"
    "qtag=a6064_t309_c147_s019a5553-fabe-7180-b1d2-8c55097d2b32_"
)
LINK_COMUNIDADE_FINAL = "https://t.me/+rtq84bGVBhQyZmJh"

# Arquivos locais (garanta que não estão em LFS e têm > 0 bytes)
AUDIO_INICIAL = "Audio i.mp3"
IMG_INICIAL   = "presente_do_jota.jpg"
IMG_FINAL     = "presente_do_jota_2.jpg"

# file_ids por ENV (opcional). Se você preencher, envio fica instantâneo.
ENV_AUDIO_ID = os.getenv("FILE_ID_AUDIO")
ENV_IMG1_ID  = os.getenv("FILE_ID_IMG_INICIAL")
ENV_IMG2_ID  = os.getenv("FILE_ID_IMG_FINAL")

# Cache JSON local de file_ids
CACHE_PATH = os.path.join(os.path.dirname(__file__), "file_ids.json")
def load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def save_cache(d: dict):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception as e:
        log.warning("Não consegui salvar cache de file_id: %s", e)

FILE_IDS = load_cache()

# Callback e timers
CB_CONFIRM_SIM = "confirm_sim"
WAIT_SECONDS = 120
PENDING_FOLLOWUPS: set[int] = set()

# ====== Botões ======
def btn_criar_conta():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)]])
def btn_sim():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ SIM", callback_data=CB_CONFIRM_SIM)]])
def btn_acessar_comunidade():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Acessar comunidade", url=LINK_COMUNIDADE_FINAL)]])

# ====== Retry curto ======
async def _retry_send(coro_factory, max_attempts=2):
    last = None
    for _ in range(max_attempts):
        try:
            return await coro_factory()
        except RetryAfter as e:
            wait = getattr(e, "retry_after", 1)
            log.warning("RetryAfter: aguardando %ss ...", wait)
            await asyncio.sleep(wait)
            last = e
        except TimedOut:
            log.warning("TimedOut: tentando novamente ...")
            await asyncio.sleep(1)
        except Exception as e:
            last = e
            break
    if last:
        raise last

# ====== Envio de ÁUDIO (ENV/cache/local) ======
async def send_audio_fast(context: ContextTypes.DEFAULT_TYPE, chat_id: int, *, file_id_env: str|None, file_id_key: str, local_path: str, caption: str|None=None):
    try:
        # 1) ENV
        if file_id_env:
            log.info("Enviando áudio via file_id ENV ...")
            return await _retry_send(lambda: context.bot.send_audio(chat_id=chat_id, audio=file_id_env, caption=caption))
        # 2) CACHE
        fid = FILE_IDS.get(file_id_key)
        if fid:
            log.info("Enviando áudio via file_id cache ...")
            try:
                return await _retry_send(lambda: context.bot.send_audio(chat_id=chat_id, audio=fid, caption=caption))
            except Exception:
                log.warning("file_id cache (audio) falhou, removendo do cache e tentando local...")
                FILE_IDS.pop(file_id_key, None); save_cache(FILE_IDS)
        # 3) LOCAL
        full = os.path.join(os.path.dirname(__file__), local_path)
        if not (os.path.exists(full) and os.path.getsize(full) > 0):
            log.warning("Áudio ausente/vazio: %s", full); return
        with open(full, "rb") as f:
            msg = await _retry_send(lambda: context.bot.send_audio(chat_id=chat_id, audio=InputFile(f, filename=os.path.basename(local_path)), caption=caption))
        if msg and msg.audio and msg.audio.file_id:
            FILE_IDS[file_id_key] = msg.audio.file_id
            save_cache(FILE_IDS)
            log.info("Cacheado file_id audio: %s", msg.audio.file_id)
        return msg
    except Exception as e:
        log.warning("Falha ao enviar áudio: %s", e)

# ====== Envio de FOTO (ENV/cache/local) com FALLBACK de TEXTO ======
async def send_photo_fast(context: ContextTypes.DEFAULT_TYPE, chat_id: int, *, file_id_env: str|None, file_id_key: str, local_path: str, caption: str|None=None, reply_markup=None):
    try:
        # 1) ENV
        if file_id_env:
            log.info("Enviando foto via file_id ENV (%s)...", file_id_key)
            return await _retry_send(lambda: context.bot.send_photo(chat_id=chat_id, photo=file_id_env, caption=caption, parse_mode="Markdown", reply_markup=reply_markup))
        # 2) CACHE
        fid = FILE_IDS.get(file_id_key)
        if fid:
            log.info("Enviando foto via file_id cache (%s)...", file_id_key)
            try:
                return await _retry_send(lambda: context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, parse_mode="Markdown", reply_markup=reply_markup))
            except Exception:
                log.warning("file_id cache (%s) falhou, removendo e tentando local...", file_id_key)
                FILE_IDS.pop(file_id_key, None); save_cache(FILE_IDS)
        # 3) LOCAL
        full = os.path.join(os.path.dirname(__file__), local_path)
        if not (os.path.exists(full) and os.path.getsize(full) > 0):
            log.warning("Imagem ausente/vazia: %s", full)
            if caption:
                return await _retry_send(lambda: context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown", reply_markup=reply_markup))
            return
        with open(full, "rb") as f:
            msg = await _retry_send(lambda: context.bot.send_photo(chat_id=chat_id, photo=InputFile(f, filename=os.path.basename(local_path)), caption=caption, parse_mode="Markdown", reply_markup=reply_markup))
        if msg and msg.photo:
            new_id = msg.photo[-1].file_id
            FILE_IDS[file_id_key] = new_id
            save_cache(FILE_IDS)
            log.info("Cacheado file_id %s: %s", file_id_key, new_id)
        return msg
    except Exception as e:
        log.warning("Falha geral ao enviar foto (%s). Enviando texto como fallback.", e)
        if caption:
            try:
                return await _retry_send(lambda: context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown", reply_markup=reply_markup))
            except Exception as e2:
                log.warning("Falha até no fallback de texto: %s", e2)

# ====== Utilitários ======
async def ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = {
        "FILE_ID_AUDIO": FILE_IDS.get("audio"),
        "FILE_ID_IMG_INICIAL": FILE_IDS.get("img1"),
        "FILE_ID_IMG_FINAL": FILE_IDS.get("img2"),
    }
    txt = "file_ids salvos:\n" + "\n".join(f"{k}: {v or '-'}" for k, v in data.items())
    await _retry_send(lambda: context.bot.send_message(chat_id=update.effective_chat.id, text=txt))

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _retry_send(lambda: context.bot.send_message(chat_id=update.effective_chat.id, text="pong ✅"))

# ====== TESTES de foto isolados ======
async def photo1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_photo_fast(context, update.effective_chat.id, file_id_env=ENV_IMG1_ID, file_id_key="img1", local_path=IMG_INICIAL, caption="(teste) imagem 1", reply_markup=btn_criar_conta())

async def photo2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_photo_fast(context, update.effective_chat.id, file_id_env=ENV_IMG2_ID, file_id_key="img2", local_path=IMG_FINAL, caption="(teste) imagem 2", reply_markup=btn_acessar_comunidade())

# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    log.info("START user_id=%s username=%s chat_id=%s", user.id, user.username, chat_id)

    # resposta imediata (sensação de rapidez)
    await _retry_send(lambda: context.bot.send_message(chat_id=chat_id, text="⏳ preparando seu presente…"))

    # 1) áudio
    await send_audio_fast(context, chat_id, file_id_env=ENV_AUDIO_ID, file_id_key="audio", local_path=AUDIO_INICIAL, caption="🔊 Mensagem rápida antes de continuar")

    # 2) imagem + CTA
    caption = "🎁 *Presente do Jota aguardando…*\n\nClique no botão abaixo."
    await send_photo_fast(context, chat_id, file_id_env=ENV_IMG1_ID, file_id_key="img1", local_path=IMG_INICIAL, caption=caption, reply_markup=btn_criar_conta())

    # 3) follow-up em 2 min
    schedule_followup(context, chat_id, WAIT_SECONDS)

# ====== Follow-up ======
def schedule_followup(context: ContextTypes.DEFAULT_TYPE, chat_id: int, wait_seconds: int):
    if chat_id in PENDING_FOLLOWUPS:
        log.info("Follow-up já pendente para chat_id=%s", chat_id); return
    PENDING_FOLLOWUPS.add(chat_id)
    jq = context.application.job_queue
    if not jq:
        log.error("JobQueue não inicializado (instale o extra job-queue)."); return
    jq.run_once(send_followup_job, when=wait_seconds, data={"chat_id": chat_id}, name=f"followup-{chat_id}")
    log.info("Follow-up (%ss) agendado via JobQueue.", wait_seconds)

async def send_followup_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    log.info("JobQueue disparou follow-up para chat_id=%s", chat_id)
    if chat_id in PENDING_FOLLOWUPS:
        await _retry_send(lambda: context.bot.send_message(chat_id=chat_id, text="Eae, já conseguiu finalizar a criação da sua conta?", reply_markup=btn_sim()))
        PENDING_FOLLOWUPS.discard(chat_id)

# ====== Clique no SIM ======
async def confirm_sim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    log.info("CONFIRM_SIM user_id=%s chat_id=%s", q.from_user.id, chat_id)
    texto_final = (
        "🎁 *Presente Liberado!!!*\n\n"
        "Basta você entrar na comunidade e buscar o sorteio que já vou te enviar,\n"
        "e fica de olho que o resultado sai na live de *HOJE*."
    )
    await send_photo_fast(context, chat_id, file_id_env=ENV_IMG2_ID, file_id_key="img2", local_path=IMG_FINAL, caption=texto_final, reply_markup=btn_acessar_comunidade())

# ====== MAIN ======
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error: %s | update=%s", context.error, update)

def main():
    request = HTTPXRequest(read_timeout=20.0, write_timeout=20.0, connect_timeout=10.0, pool_timeout=10.0)
    app = ApplicationBuilder().token(TOKEN).request(request).job_queue(JobQueue()).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("ids", ids))
    app.add_handler(CommandHandler("photo1", photo1))
    app.add_handler(CommandHandler("photo2", photo2))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_sim, pattern=f"^{CB_CONFIRM_SIM}$"))
    app.add_error_handler(on_error)

    log.info("🤖 Bot rodando. Imagens/áudio via file_id (ENV/cache) com fallback de upload + texto.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
