import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
print("Bot running...")

logging.basicConfig(level=logging.INFO)

# -----------------------------
# ESTADO
# -----------------------------
user_data = {}

# -----------------------------
# PREGUNTA ÚNICA
# -----------------------------
QUESTION = {
    "A": {
        "q": "👣 Algunos le vieron entre Bermingham y San Francisco buscando algo para desayunar...\n\n¿Dónde fue?",
        "answer": "Ogi Berri",
        "hint": "Quizá tenía hambre y quería un croissant 🥐"
    },
    "B": {
        "q": "👣 Algunos le vieron entre Secundino Esnaola y Segundi Izpizua buscando un bar...\n\n¿Dónde fue?",
        "answer": "Eguzki",
        "hint": "Seguramente buscaba un sitio para tomar algo 🍺"
    },
    "C": {
        "q": "👣 Algunos le vieron entre Secundino Esnaola y Gran Vía sin sus gafas...\n\n¿Dónde fue?",
        "answer": "Harotz",
        "hint": "No veía bien… quizá necesitaba ayuda óptica 👓"
    }
}

# -----------------------------
# START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["A", "B", "C"]]

    await update.message.reply_text(
        "🏛️ EL CERBUNO PERDIDO\n\n"
        "Un Cerbuno ha desaparecido tras una noche de fiesta en San Sebastián.\n"
        "Se ha perdido y necesita volver al Cerbuna.\n\n"
        "Elige tu equipo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )

# -----------------------------
# SELECCIÓN EQUIPO
# -----------------------------
async def choose_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    team = update.message.text.upper()

    if team not in QUESTION:
        await update.message.reply_text("Elige A, B o C")
        return

    user_data[user_id] = {
        "team": team,
        "hint_used": False
    }

    await update.message.reply_text(QUESTION[team]["q"])

# -----------------------------
# RESPUESTAS
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data:
        await update.message.reply_text("Escribe /start para comenzar")
        return

    team = user_data[user_id]["team"]
    answer = update.message.text.strip()

    correct = QUESTION[team]["answer"]

    # -------------------------
    # RESPUESTA CORRECTA
    # -------------------------
    if answer.lower() == correct.lower():
        await update.message.reply_text(
            f"✅ ¡Correcto!\n\n"
            f"El Cerbuno fue encontrado en {correct} 🏁"
        )
        user_data.pop(user_id)
        return

    # -------------------------
    # PISTA (solo 1 vez)
    # -------------------------
    if not user_data[user_id]["hint_used"]:
        user_data[user_id]["hint_used"] = True
        await update.message.reply_text(f"💡 Pista: {QUESTION[team]['hint']}")
    else:
        await update.message.reply_text("❌ No es correcto. Intenta otra vez.")

# -----------------------------
# MAIN
# -----------------------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_team))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
