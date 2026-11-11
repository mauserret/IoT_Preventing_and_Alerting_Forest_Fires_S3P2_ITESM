import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format= "%(asctime)s - %(name)s - %(levelname)s - %(message)s", level = logging.INFO
)

TOKEN = "8910902918:AAHC943TWfzELwUkx99UV5-6TgX8unZwamA"

# 1. Función que se ejecuta cuando el usuario escribe /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"¡Hola {user.first_name}! Mi bot ya está configurado.")

# 2. Función que responde a cualquier texto normal
async def responder_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.reply_text(f"Recibí tu mensaje: '{texto}'")

if __name__ == "__main__":
    # Construir la aplicación
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar los manejadores (cuándo debe reaccionar el bot)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder_texto))

    print("🤖 Bot iniciado correctamente. Presiona Ctrl+C para detenerlo.")
    
    # Arrancar el bot en modo bucle (Polling)
    app.run_polling()