import os
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# === CONFIGURAÇÃO ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Defina TELEGRAM_TOKEN no arquivo .env")

# === LINKS DE DESTINO ===
LINK_CADASTRO = "https://betboom.bet.br/registration/base/?utm_source=inf&utm_medium=bloggers&utm_campaign=309&utm_content=regcasino_br&utm_term=6064&aff=alanbase&qtag=a6064_t309_c147_s019a5553-fabe-7180-b1d2-8c55097d2b32_"
LINK_COMUNIDADE = "https://t.me/+4J5FfgfOm9U3ZDlh"

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Primeira interação do usuário: envia imagem do presente"""
    user = update.effective_user
    photo_path = os.path.join(os.path.dirname(__file__), "presente_do_jota.jpg")

    caption = (
        "🎁 *Presente do Jota!*\\n\\n"
        "Clique no botão abaixo para abrir sua caixa e ver o que te espera."
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Abrir minha caixa", callback_data="abrir_caixa")]
    ])

    if os.path.exists(photo_path):
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(photo_path),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=markup)


async def abrir_caixa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quando o usuário clica para abrir a caixa"""
    query = update.callback_query
    await query.answer()

    text = (
        "🎁 *Presente Liberado!*\\n\\n"
        "Você acaba de desbloquear **acesso antecipado** à nossa comunidade VIP 💥\\n\\n"
        "Lá dentro rolam conteúdos exclusivos, bônus especiais e avisos de lives 🔥\\n\\n"
        "Escolha uma das opções abaixo para continuar:"
    )

    keyboard = [
        [InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)],
        [InlineKeyboardButton("🚀 Entrar na Comunidade VIP", url=LINK_COMUNIDADE)],
    ]

    try:
        await query.edit_message_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(abrir_caixa, pattern="abrir_caixa"))

    print("🤖 Bot rodando com sucesso!")
    app.run_polling()

if __name__ == "__main__":
    main()
