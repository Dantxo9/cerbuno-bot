import os
import math
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==================================================
# CONFIG
# ==================================================

TOKEN = os.getenv("TOKEN")

# PON AQUÍ TU TELEGRAM USER ID
ADMIN_ID = 6588872844

# Coordenadas objetivo pregunta GPS
TARGET_LAT = 43.321667
TARGET_LON = -1.986667

# Radio permitido (metros)
GPS_RADIUS_METERS = 120

logging.basicConfig(level=logging.INFO)

# ==================================================
# MEMORIA
# ==================================================

user_data = {}

# user_data[user_id] = {
#   team: A/B/C
#   step: 1..6
#   points: 100
#   hint_used: False
#   can_use_hint: False
# }

# ==================================================
# CONTENIDO DEL JUEGO
# ==================================================

Q1 = {
    "A": {
        "question": "Algunos habitantes dicen haberle visto entre Bermingham y San Francisco buscando algo para desayunar...\n¿A dónde habrá ido?",
        "answer": "ogi berri",
        "display": "Ogi Berri",
        "hint": "🥐 Quizá tenía hambre y quería tomarse un croissant."
    },
    "B": {
        "question": "Algunos habitantes dicen haberle visto entre Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo...\n¿A dónde habrá ido?",
        "answer": "eguzki",
        "display": "Eguzki",
        "hint": "🍺 Seguramente buscase un bistro o taberna."
    },
    "C": {
        "question": "Algunos habitantes dicen haberle visto entre Secundino Esnaola y Gran Vía desconcertado y sin sus gafas...\n¿A dónde habrá ido?",
        "answer": "harotz",
        "display": "Harotz",
        "hint": "👓 Será que ha ido a por gafas nuevas."
    }
}

Q2 = {
    "A": """En la panadería os dicen que vieron al Cerbuno con Daniel Ibáñez.

Blanca por fuera, de lujo por dentro,
frente al río espera con porte de cuento.
Reyes y estrellas descansan allí,
si visitas Donosti… ¿duermes en mí?""",

    "B": """En el bar os dicen que vieron al Cerbuno con Daniel Ibáñez.

Bajo arcos y puestos empieza el trajín,
huele a pescado, verdura y jazmín.
Si buscas sabores del norte con gracia,
¿qué mercado eres, junto a la Parte Vieja?""",

    "C": """En la óptica os dicen que vieron al Cerbuno con Daniel Ibáñez.

Árboles y bancos guardan la quietud,
en pleno centro regalan salud.
Con jardín elegante y aire señorial,
¿qué plaza donostiarra te invita a parar?"""
}

Q2_ANSWER = "plaza de la constitucion"

Q3 = {
    "A": """Vieron al Cerbuno en Plaza de la Constitución apuntando:

(B3-H2)°(A1+R1)’(A1+Q1)”N
(B1-A1)°(AP1+Q1)’(A1+K1)”W

¿Qué coordenadas apuntó?""",

    "B": """Vieron al Cerbuno en Plaza de la Constitución apuntando:

(R1+X1)°(E1+N1)’(F1+L1)”N
(V1-U1)°(AS3-K2)’(E1+G1)”W

¿Qué coordenadas apuntó?""",

    "C": """Vieron al Cerbuno en Plaza de la Constitución apuntando:

(U2-AA1)°(I1+J1)’(H1+J1)”N
(I1-H1)°(AD1+AC1)’(T1-H1)”W

¿Qué coordenadas apuntó?"""
}

Q3_ANSWER = '43°19\'18"n 1°59\'12"w'

Q5_IMAGES = {
    "A": "https://www.mercilona.com/cdn/shop/files/1_e178919e-6969-43b4-b48d-5b0eafc4a1d0_1024x1024@2x.jpg?v=1766409572",
    "B": "https://pasaiarte.com/cdn/shop/files/20205w_large.gif?v=1743160175",
    "C": "https://s1.ppllstatics.com/diariovasco/www/multimedia/201711/08/media/MM-palacio-miramar/1402366369.jpg"
}

Q5_ANSWERS = {
    "A": "isla de santa clara",
    "B": "monte igeldo",
    "C": "palacio de miramar"
}

# ==================================================
# HELPERS
# ==================================================

def distance_meters(lat1, lon1, lat2, lon2):
    # Aproximación suficiente para ciudad
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.sqrt(dx * dx + dy * dy)

def normalize(txt):
    return txt.strip().lower()

def init_user(user_id, team):
    user_data[user_id] = {
        "team": team,
        "step": 1,
        "points": 100,
        "hint_used": False,
        "can_use_hint": False
    }

# ==================================================
# START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["A", "B", "C"]]

    await update.message.reply_text(
        "🏛️ EL CERBUNO PERDIDO\n\n"
        "Un Cerbuno se perdió tras la fiesta.\n"
        "Elegid equipo:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

# ==================================================
# PISTA
# ==================================================

async def pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("Primero escribe /start")
        return

    data = user_data[user_id]

    if not data["can_use_hint"]:
        await update.message.reply_text("❌ Aún no podéis pedir pista.")
        return

    if data["hint_used"]:
        await update.message.reply_text("❌ Ya habéis usado la pista.")
        return

    if data["step"] != 1:
        await update.message.reply_text("❌ Solo hay pista disponible en la primera pregunta.")
        return

    team = data["team"]
    data["hint_used"] = True
    data["points"] -= 15

    await update.message.reply_text(
        f"💡 {Q1[team]['hint']}\n\n"
        f"⭐ -15 puntos\n"
        f"Total: {data['points']}"
    )

# ==================================================
# ADMIN /PUNTOS
# ==================================================

async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sin permisos")
        return

    if not user_data:
        await update.message.reply_text("No hay jugadores activos.")
        return

    msg = "📊 ESTADO DEL JUEGO\n\n"

    for uid, d in user_data.items():
        msg += (
            f"User {uid}\n"
            f"Equipo: {d['team']}\n"
            f"Paso: {d['step']}\n"
            f"Puntos: {d['points']}\n\n"
        )

    await update.message.reply_text(msg)

# ==================================================
# ADMIN /RESET
# ==================================================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sin permisos")
        return

    user_data.clear()
    await update.message.reply_text("🔄 Juego reiniciado.")

# ==================================================
# ADMIN /FINISH
# ==================================================

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sin permisos")
        return

    if not user_data:
        await update.message.reply_text("No hay jugadores.")
        return

    scores = {"A": [], "B": [], "C": []}

    for _, d in user_data.items():
        scores[d["team"]].append(d["points"])

    msg = "🏁 FIN DEL JUEGO\n\n"

    best_team = None
    best_score = -1

    for team in ["A", "B", "C"]:
        if scores[team]:
            avg = sum(scores[team]) / len(scores[team])
            msg += f"Equipo {team}: {avg:.0f} puntos\n"
            if avg > best_score:
                best_score = avg
                best_team = team
        else:
            msg += f"Equipo {team}: sin jugadores\n"

    if best_team:
        msg += f"\n🏆 Ganador: Equipo {best_team}"

    await update.message.reply_text(msg)

# ==================================================
# LOCATION HANDLER (Pregunta GPS)
# ==================================================

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if data["step"] != 4:
        await update.message.reply_text("📍 Ahora no necesitáis enviar ubicación.")
        return

    loc = update.message.location
    dist = distance_meters(
        loc.latitude,
        loc.longitude,
        TARGET_LAT,
        TARGET_LON
    )

    if dist <= GPS_RADIUS_METERS:
        data["step"] = 5
        team = data["team"]

        await update.message.reply_text(
            "✅ Ubicación correcta.\n\n"
            "Encontráis un papel con una silueta..."
        )

        await update.message.reply_photo(
            photo=Q5_IMAGES[team],
            caption="¿Reconocéis el lugar?"
        )
    else:
        await update.message.reply_text(
            f"❌ No estáis en el sitio correcto.\n"
            f"Estáis a {int(dist)} metros."
        )

# ==================================================
# ROUTER TEXTO
# ==================================================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = normalize(update.message.text)

    # Elegir equipo
    if text in ["a", "b", "c"] and user_id not in user_data:
        team = text.upper()
        init_user(user_id, team)

        await update.message.reply_text(
            f"Equipo {team} seleccionado.\n\n"
            f"Pregunta 1:\n{Q1[team]['question']}"
        )
        return

    # Si no empezó
    if user_id not in user_data:
        await update.message.reply_text("Escribe /start")
        return

    data = user_data[user_id]
    team = data["team"]
    step = data["step"]

    # --------------------------------
    # PREGUNTA 1
    # --------------------------------
    if step == 1:
        if text == Q1[team]["answer"]:
            data["step"] = 2
            await update.message.reply_text(
                f"🎉 Correcto: {Q1[team]['display']}\n\n"
                f"Pregunta 2:\n{Q2[team]}"
            )
        else:
            data["points"] -= 10
            data["can_use_hint"] = True
            await update.message.reply_text(
                f"❌ Incorrecto (-10 puntos)\n"
                f"Puntos: {data['points']}\n\n"
                f"Podeis pedir una pista, pero eso os restará puntos (/pista)"
            )
        return

    # --------------------------------
    # PREGUNTA 2
    # --------------------------------
    if step == 2:
        if text == Q2_ANSWER:
            data["step"] = 3
            await update.message.reply_text(
                f"🎉 Correcto.\n\nPregunta 3:\n{Q3[team]}"
            )
        else:
            data["points"] -= 10
            await update.message.reply_text(
                f"❌ Incorrecto (-10)\nPuntos: {data['points']}"
            )
        return

    # --------------------------------
    # PREGUNTA 3
    # --------------------------------
    if step == 3:
        if text == Q3_ANSWER:
            data["step"] = 4

            keyboard = [[KeyboardButton("📍 Enviar ubicación", request_location=True)]]

            await update.message.reply_text(
                "🎉 Correcto.\n\n"
                "Pregunta 4:\n"
                "Cuando lleguéis al lugar, enviad vuestra ubicación.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard,
                    resize_keyboard=True
                )
            )
        else:
            data["points"] -= 10
            await update.message.reply_text(
                f"❌ Incorrecto (-10)\nPuntos: {data['points']}"
            )
        return

    # --------------------------------
    # PREGUNTA 4
    # --------------------------------
    if step == 4:
        await update.message.reply_text("📍 Debéis enviar ubicación.")
        return

    # --------------------------------
    # PREGUNTA 5
    # --------------------------------
    if step == 5:
        if text == Q5_ANSWERS[team]:
            data["step"] = 6
            await update.message.reply_text(
                "🎉 Correcto.\n\n"
                "El capitán recuerda al Cerbuno.\n"
                "Se dirigía al bar Desy Vegas.\n\n"
                "🍻 Id allí. El administrador validará vuestra llegada."
            )
        else:
            data["points"] -= 10
            await update.message.reply_text(
                f"❌ Incorrecto (-10)\nPuntos: {data['points']}"
            )
        return

    # --------------------------------
    # FINAL
    # --------------------------------
    if step == 6:
        await update.message.reply_text(
            "🏁 Ya estáis en la fase final. Buscad al administrador."
        )

# ==================================================
# MAIN
# ==================================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pista", pista))
    app.add_handler(CommandHandler("puntos", puntos))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("finish", finish))

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("🤖 Bot funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
