import logging
import asyncio
from telegram import Bot
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = ""
CHAT_ID = 

async def prueba_unica():
    bot = Bot(token=TOKEN)
    async with bot:
        await bot.send_message(
            chat_id = CHAT_ID,
            text = "67"
        )
    print("Mensaje enviado correctamente")

if __name__ == "__main__":
    asyncio.run(prueba_unica())