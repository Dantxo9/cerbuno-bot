import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------------------------
# TOKEN DESDE RAILWAY / VARIABLES
# ---------------------------------
TOKEN = os.getenv("TOKEN")
print("TOKEN:", TOKEN)
# ---------------------------------
# LOGS
# ---------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------------------------------
# ESTADO DE USUARIOS
# ---------------------------------
# user_data[user_id] = {
#   "team": "A",
#   "hint_used": False
# }
user_data = {}

# ---------------------------------
# DATOS DEL JUEGO
# ---------------------------------
QUESTION = {
    "A": {
        "question": (
            "👣 Algunos habitantes de San Sebastián dicen haber visto al Cerbuno "
            "entre Bermingham y San Francisco buscando algo para desayunar...\n\n"
            "❓ ¿A dónde habrá ido?"
        ),
        "answer": "ogi berri",
        "display_answer": "Ogi Berri",
        "hint": "💡 Quizá tenía hambre y quería tomarse un croissant 🥐"
    },
    "B": {
        "question": (
            "👣 Algunos habitantes de San Sebastián dicen haber visto al Cerbuno "
            "entre Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo...\n\n"
            "❓ ¿A dónde habrá ido?"
        ),
        "answer": "eguzki",
        "display_answer": "Eguzki",
        "hint": "💡 Seguramente buscase un bistro o taberna para tomarse algo 🍻"
    },
    "C": {
        "question": (
            "👣 Algunos habitantes de San Sebastián dicen haber visto al Cerbuno "
            "entre Secundino Esnaola y Gran Vía desconcertado y sin sus gafas...\n\n"
            "❓ ¿A dónde habrá ido?"
        ),
        "answer": "harotz",
        "display_answer": "Harotz",
        "hint": "💡 Será que ha ido a por gafas nuevas 👓"
    }
}

# ---------------------------------
# /start
# ---------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["A", "B", "C"]]

    await update.message.reply_text(
        "🏛️ EL CERBUNO PERDIDO\n\n"
        "Un Cerbuno salió de fiesta anoche en San Sebastián.\n"
        "Estaba tan borracho que perdió el móvil y nadie sabe dónde está.\n\n"
        "Hemos oído a varios vecinos hablar de un Cerbuno perdido...\n"
        "Nos han dado algunas pistas para encontrarle.\n\n"
        "👥 Elige tu equipo:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

# ---------------------------------
# SELECCIONAR EQUIPO
# ---------------------------------
async def choose_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()

    if text not in ["A", "B", "C"]:
        await update.message.reply_text("❌ Elige un equipo válido: A, B o C.")
        return

    user_data[user_id] = {
        "team": text,
        "hint_used": False
    }

    await update.message.reply_text(
        f"✅ Equipo {text} seleccionado.\n\n"
        f"{QUESTION[text]['question']}\n\n"
        "👉 Escribe tu respuesta."
    )

# ---------------------------------
# RESPUESTAS
# ---------------------------------
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    # Si no empezó
    if user_id not in user_data:
        await update.message.reply_text(
            "👋 Escribe /start para comenzar."
        )
        return

    team = user_data[user_id]["team"]
    correct_answer = QUESTION[team]["answer"]

    # Correcto
    if text == correct_answer:
        await update.message.reply_text(
            f"🎉 ¡Correcto!\n\n"
            f"Habéis encontrado al Cerbuno en {QUESTION[team]['display_answer']}.\n"
            f"🏁 Fin de la prueba."
        )

        # Reiniciar usuario para poder volver a jugar
        user_data.pop(user_id, None)
        return

    # Incorrecto → pista solo una vez
    if not user_data[user_id]["hint_used"]:
        user_data[user_id]["hint_used"] = True
        await update.message.reply_text(
            QUESTION[team]["hint"]
        )
    else:
        await update.message.reply_text(
            "❌ No es correcto. Inténtalo otra vez."
        )

# ---------------------------------
# MAIN
# ---------------------------------
def main():
    if not TOKEN:
        print("ERROR: No se encontró la variable TOKEN.")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Todo texto pasa aquí
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, route_text)
    )

    print("🤖 Bot funcionando...")
    app.run_polling()

# ---------------------------------
# ROUTER
# Decide si es equipo o respuesta
# ---------------------------------
async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()

    # Si usuario no tiene estado y escribe A/B/C => elegir equipo
    if user_id not in user_data and text in ["A", "B", "C"]:
        await choose_team(update, context)
        return

    # Si no tiene estado
    if user_id not in user_data:
        await update.message.reply_text(
            "👋 Escribe /start para comenzar."
        )
        return

    # Si ya tiene estado => respuesta
    await handle_answer(update, context)

# ---------------------------------
# RUN
# ---------------------------------
if __name__ == "__main__":
    main()
