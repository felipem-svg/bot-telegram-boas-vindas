import os
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Defina TELEGRAM_TOKEN no arquivo .env")

# Links configuráveis
LINK_CADASTRO = "https://betboom.bet.br/registration/base/?utm_source=inf&utm_medium=bloggers&utm_campaign=309&utm_content=regcasino_br&utm_term=6064&aff=alanbase&qtag=a6064_t309_c147_s019a5553-fabe-7180-b1d2-8c55097d2b32_"
LINK_COMUNIDADE = "https://t.me/+4J5FfgfOm9U3ZDlh"

# ===== Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Envia imagem inicial (presente do Jota)
    photo_path = os.path.join(os.path.dirname(__file__), "presente_do_jota.jpg")
    if os.path.exists(photo_path):
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(photo_path),
            caption="🎁 *Presente do Jota!*\n\nClique no botão abaixo para abrir sua caixa.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎁 Abrir minha caixa", callback_data="abrir_caixa")]]
            ),
        )
    else:
        await update.message.reply_text(
            "🎁 Presente do Jota! Clique abaixo para abrir sua caixa.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎁 Abrir minha caixa", callback_data="abrir_caixa")]]
            ),
        )

async def abrir_caixa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    keyboard = [
        [InlineKeyboardButton("🚀 Entrar na Comunidade VIP", url=LINK_COMUNIDADE)],
        [InlineKeyboardButton("🟢 Criar conta agora", url=LINK_CADASTRO)],
    ]
    text = (
        "🎁 *Presente Liberado!*\n\n"
        "Você acaba de desbloquear **acesso antecipado** à nossa comunidade VIP 💥\n\n"
        "Lá dentro rolam conteúdos exclusivos, bônus especiais e avisos de lives 🔥\n\n"
        "Escolha uma opção abaixo para continuar:"
    )
    await q.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(abrir_caixa, pattern="abrir_caixa"))
    print("🤖 Bot rodando...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
