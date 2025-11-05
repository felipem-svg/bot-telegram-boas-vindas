import os
import io
import logging
from dotenv import load_dotenv
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest, TelegramError

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("presente-do-jota")

# === CONFIG ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Defina TELEGRAM_TOKEN no .env ou nas Variables do Railway")

LINK_CADASTRO = "https://betboom.bet.br/registration/base/?utm_source=inf&utm_medium=bloggers&utm_campaign=309&utm_content=regcasino_br&utm_term=6064&aff=alanbase&qtag=a6064_t309_c147_s019a5553-fabe-7180-b1d2-8c55097d2b32_"
LINK_COMUNIDADE = "https://t.me/+4J5FfgfOm9U3ZDlh"
PHOTO_NAME = "presente_do_jota.jpg"

# === BOTÕES ===
def cta_markup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 Abrir minha caixa", callback_data="abrir_caixa")]]
    )

def options_markup():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)],
            [InlineKeyboardButton("🚀 Entrar na Comunidade VIP", url=LINK_COMUNIDADE)],
        ]
    )

# === COMANDO TESTE ===
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="pong ✅")

# === FUNIL PRINCIPAL ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    log.info("START from user_id=%s username=%s chat_id=%s", getattr(user, "id", None), getattr(user, "username", None), chat_id)

    caption = (
        "🎁 *Presente do Jota!*\n\n"
        "Clique no botão abaixo para abrir sua caixa e ver o que te espera."
    )

    photo_path = os.path.join(os.path.dirname(__file__), PHOTO_NAME)
    try:
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            # Converte qualquer formato em JPEG
            with Image.open(photo_path) as im:
                im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=90, optimize=True)
                buf.seek(0)
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=buf,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=cta_markup(),
            )
            log.info("Sent converted JPG + CTA.")
        else:
            raise FileNotFoundError("Imagem ausente ou vazia.")
    except Exception as e:
        log.warning("Falha ao enviar imagem (%s). Enviando texto.", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="Markdown",
            reply_markup=cta_markup(),
        )

async def abrir_caixa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    log.info("CLICK abrir_caixa by user_id=%s username=%s", user.id, user.username)

    # 1) Tenta enviar o áudio primeiro
    try:
        audio_path = os.path.join(os.path.dirname(__file__), AUDIO_NAME)
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=InputFile(audio_path),
                # title e caption são opcionais – ajuste como quiser:
                title="Mensagem do Jota",
                caption="🔊 Ouça essa mensagem rápida antes de continuar",
            )
            log.info("Audio enviado com sucesso: %s", AUDIO_NAME)
        else:
            log.warning("Áudio ausente ou vazio: %s", audio_path)
    except Exception as e:
        log.warning("Falha ao enviar áudio (%s). Seguindo sem áudio.", e)

    # 2) Depois mostra as opções
    text = (
        "🎁 *Presente Liberado!*\n\n"
        "Você acaba de desbloquear **acesso antecipado** à nossa comunidade VIP 💥\n\n"
        "Lá dentro rolam conteúdos exclusivos, bônus especiais e avisos de lives 🔥\n\n"
        "Escolha uma das opções abaixo para continuar:"
    )

    try:
        # se a mensagem original era foto c/ legenda, tenta editar:
        await query.edit_message_caption(
            caption=text, parse_mode="Markdown", reply_markup=options_markup()
        )
        log.info("Edited message with options.")
    except BadRequest:
        # se era texto ou não dá pra editar, manda uma nova:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=options_markup(),
        )
        log.info("Sent new message with options (fallback).")


# === MAIN ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(abrir_caixa, pattern="abrir_caixa"))

    log.info("🤖 Bot rodando (polling). Certifique-se que não há webhook ativo e só 1 instância.")
    app.run_polling()

if __name__ == "__main__":
    main()
