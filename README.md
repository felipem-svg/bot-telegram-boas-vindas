# Bot Telegram – Presente do Jota (versão segura)

Este bot entrega um funil de boas-vindas no estilo “abrir caixa”,
com botões interativos e direcionamento para uma comunidade Telegram.

## 🚀 Como usar

1. Copie `.env.example` para `.env` e insira seu token do @BotFather.
2. Crie ambiente virtual e instale dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Execute o bot:
   ```bash
   python app.py
   ```

## ⚙️ Funcionalidades
- Envia imagem inicial (“Presente do Jota”)
- Botão “Abrir minha caixa” inicia o fluxo
- Direciona o usuário para:
  - Criar conta (link configurado)
  - Entrar na comunidade Telegram
- Log básico de eventos
