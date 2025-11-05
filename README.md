# Bot Telegram – Presente do Jota (versão final)

Funil de boas-vindas com imagem, botões e links de redirecionamento.

## 🚀 Como rodar localmente
1. Copie `.env.example` para `.env` e adicione o seu TOKEN do @BotFather.
2. Instale dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Execute:
   ```bash
   python app.py
   ```

## ☁️ Railway (24/7)
1. Faça upload deste projeto no GitHub.
2. Conecte o repo ao Railway.
3. Nas variáveis de ambiente, adicione:
   ```
   TELEGRAM_TOKEN=seu_token_aqui
   ```
4. Deploy automático. Logs mostrarão “🤖 Bot rodando (polling)”.
