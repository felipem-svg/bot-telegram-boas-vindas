import os
import io
import logging
from dotenv import load_dotenv
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

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

# ========= Botões =========
def btn_criar_conta() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)]]
    )

def btn_sim() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ SIM", callback_data=CB_CONFIRM_SIM)]])

def btn_acessar_comunidade() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚀 Acessar comunidade", url=LINK_COMUNIDADE_FINAL)]]
    )

# ========= Util: enviar imagem com Pillow (converte p/ JPEG) =========
async def send_image(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    path: str,
    caption: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = "Markdown",
):
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
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        log.info("Imagem enviada: %s", path)
    except Exception as e:
        log.warning("Falha ao enviar imagem %s (%s). Enviando texto.", path, e)
        if caption:
            await context.bot.send_message(
                chat_id=chat_id, text=caption, parse_mode=parse_mode, reply_markup=reply_markup
            )

# ========= /ping (teste) =========
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="pong ✅")

# ========= /start =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    log.info("START user_id=%s username=%s chat_id=%s", getattr(user, "id", None), getattr(user, "username", None), chat_id)

    # 1) Áudio inicial i.mp3
    try:
        audio_path = os.path.join(os.path.dirname(__file__), AUDIO_INICIAL)
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            with open(audio_path, "rb") as f:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=InputFile(f, filename="i.mp3"),
                    title="Mensagem inicial",
                    caption="🔊 Ouça essa mensagem rápida antes de continuar",
                )
            log.info("Áudio inicial enviado: %s", AUDIO_INICIAL)
        else:
            log.warning("Áudio inicial ausente/vazio: %s", audio_path)
    except Exception as e:
        log.warning("Falha ao enviar áudio inicial (%s).", e)

    # 2) Imagem + CTA "Presente do jota aguardando…"
    caption_inicial = "🎁 *Presente do Jota aguardando…*\n\nClique no botão abaixo."
    await send_image(
        context=context,
        chat_id=chat_id,
        path=IMG_INICIAL,
        caption=caption_inicial,
        reply_markup=btn_criar_conta(),
    )

    # 3) Agenda +2min a pergunta "Eae, já conseguiu finalizar...?"
    #    Guardamos o chat_id na job para responder no mesmo chat
    context.job_queue.run_once(
        send_followup_question,
        when=120,  # 2 minutos
        data={"chat_id": chat_id},
        name=f"followup-{chat_id}",
    )
    log.info("Follow-up agendado para +120s ao chat_id=%s", chat_id)

# ========= Job: pergunta após 2 min =========
async def send_followup_question(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    text = "Eae, já conseguiu finalizar a criação da sua conta?"
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=btn_sim())
    log.info("Follow-up enviado ao chat_id=%s", chat_id)

# ========= Clique no SIM =========
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

    # Envia imagem final + texto
    await send_image(
        context=context,
        chat_id=chat_id,
        path=IMG_FINAL,
        caption=texto_final,
        reply_markup=btn_acessar_comunidade(),
    )

# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_sim, pattern=f"^{CB_CONFIRM_SIM}$"))

    log.info("🤖 Bot rodando (polling). Certifique-se que não há webhook ativo e só 1 instância.")
    app.run_polling()

if __name__ == "__main__":
    main()
