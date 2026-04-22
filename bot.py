import os
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==================================================
# CONFIGURACIÓN
# ==================================================

TOKEN = os.getenv("TOKEN")

# PON AQUÍ TU TELEGRAM USER ID
ADMIN_ID = 6588872844

# Coordenadas objetivo pregunta 4
TARGET_LAT = 51.540552, 
TARGET_LON = -0.181171

# Radio permitido (metros)
GPS_RADIUS_METERS = 40

logging.basicConfig(level=logging.INFO)

# ==================================================
# MEMORIA
# ==================================================

user_data = {}

# ==================================================
# CONTENIDO EXACTO DEL JUEGO
# ==================================================

HISTORIA = """
🏛️ EL CERBUNO PERDIDO

Un Cerbuno ha estado de fiesta en San Sebastian la noche anterior y se ha perdido.
Estaba tan borracho que ha perdido el movil y nadie le encuentra.

Hemos oído a gente de la ciudad hablando de un Cerbuno perdido la noche anterior y nos han dado algunas pistas para encontrarle.
"""

Q1 = {
    "A": {
        "question": """
Pregunta 1:

Algunos habitantes de San Sebastián dicen haberle visto entre las calles…

… Bermingham y San Francisco buscando algo para desayunar…

… ¿A dónde habrá ido?
""",
        "answer": "ogi berri",
        "hint": "Quizá tenía hambre y quería tomarse un croissant?"
    },
    "B": {
        "question": """
Pregunta 1:

Algunos habitantes de San Sebastián dicen haberle visto entre las calles…

… Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo…

… ¿A dónde habrá ido?
""",
        "answer": "eguzki",
        "hint": "Seguramente buscase un bistro o taberna para tomarse algo."
    },
    "C": {
        "question": """
Pregunta 1:

Algunos habitantes de San Sebastián dicen haberle visto entre las calles…

… Secundino Esnaola y Gran Vía desconcertado y sin sus gafas…

… ¿A dónde habrá ido?
""",
        "answer": "harotz",
        "hint": "Será que ha ido a por gafas nuevas?"
    }
}

Q2 = {
    "A": """
Pregunta 2:

En la Panadería os dicen que vieron al Cerbuno esta mañana acompañado de un tal Daniel Ibáñez.
Entre ellos estaban hablando de adonde ir, pero no quedó muy claro. Dijeron algo así:

Blanca por fuera, de lujo por dentro,
frente al río espera con porte de cuento.
Reyes y estrellas descansan allí,
si visitas Donosti… ¿duermes en mí?

Quizá debais mandarle un selfie a Daniel, y si estáis en el sitio correcto,
os diga a dónde vio al Cerbuno dirigirse después?
""",

    "B": """
Pregunta 2:

En el Bar os dicen que vieron al Cerbuno esta mañana acompañado de un tal Daniel Ibáñez.
Entre ellos estaban hablando de adonde ir, pero no quedó muy claro. Dijeron algo así:

Bajo arcos y puestos empieza el trajín,
huele a pescado, verdura y jazmín.
Si buscas sabores del norte con gracia,
¿qué mercado eres, junto a la Parte Vieja?

Quizá debais mandarle un selfie a Daniel, y si estáis en el sitio correcto,
os diga a dónde vio al Cerbuno dirigirse después?
""",

    "C": """
Pregunta 2:

En la Optica os dicen que vieron al Cerbuno esta mañana acompañado de un tal Daniel Ibáñez.
Entre ellos estaban hablando de adonde ir, pero no quedó muy claro. Dijeron algo así:

Árboles y bancos guardan la quietud,
en pleno centro regalan salud.
Con jardín elegante y aire señorial,
¿qué plaza donostiarra te invita a parar?

Quizá debais mandarle un selfie a Daniel, y si estáis en el sitio correcto,
os diga a dónde vio al Cerbuno dirigirse después?
"""
}

Q2_ANSWER = "plaza de la constitucion"

Q3 = {
    "A": """
Pregunta 3:

Vieron al Cerbuno en la Plaza de la Constitución mirando hacia el reloj de la fachada al Oeste,
y los edificios que lo rodean, apuntando algo en su cuaderno.

Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(B3-H2)°(A1+R1)’(A1+Q1)”N
(B1-A1)°(AP1+Q1)’(A1+K1)”W

¿Qué coordenadas ha apuntado?
""",

    "B": """
Pregunta 3:

Vieron al Cerbuno en la Plaza de la Constitución mirando hacia el reloj de la fachada al Oeste,
y los edificios que lo rodean, apuntando algo en su cuaderno.

Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(R1+X1)°(E1+N1)’(F1+L1)”N
(V1-U1)°(AS3-K2)’(E1+G1)”W

¿Qué coordenadas ha apuntado?
""",

    "C": """
Pregunta 3:

Vieron al Cerbuno en la Plaza de la Constitución mirando hacia el reloj de la fachada al Oeste,
y los edificios que lo rodean, apuntando algo en su cuaderno.

Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(U2-AA1)°(I1+J1)’(H1+J1)”N
(I1-H1)°(AD1+AC1)’(T1-H1)”W

¿Qué coordenadas ha apuntado?
"""
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

def normalize(txt):
    return txt.strip().lower()

def distance_meters(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.sqrt(dx * dx + dy * dy)

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
        HISTORIA + "\n\nElegid equipo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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

    if data["step"] != 1:
        await update.message.reply_text("Solo hay pista en la Pregunta 1.")
        return

    if not data["can_use_hint"]:
        await update.message.reply_text("Primero intentad responder.")
        return

    if data["hint_used"]:
        await update.message.reply_text("Ya habéis usado la pista.")
        return

    team = data["team"]
    data["hint_used"] = True
    data["points"] -= 1

    await update.message.reply_text(
        f"💡 {Q1[team]['hint']}\n\n-1 punto"
    )

# ==================================================
# ADMIN
# ==================================================

async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not user_data:
        await update.message.reply_text("No hay jugadores.")
        return

    msg = "📊 ESTADO DEL JUEGO\n\n"

    for uid, d in user_data.items():
        msg += f"User {uid}\nEquipo {d['team']}\nPaso {d['step']}\nPuntos {d['points']}\n\n"

    await update.message.reply_text(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_data.clear()
    await update.message.reply_text("Juego reiniciado.")

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🏁 Juego finalizado.\nEl administrador ha dado por terminada la gymkana."
    )

# ==================================================
# GPS
# ==================================================

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if data["step"] != 4:
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
            "✅ Estáis en el lugar correcto.\n\nPregunta 5:"
        )

        await update.message.reply_text(
            "Encontráis un papel en el suelo con una silueta. "
            "Quizá quería ir en barco a algún lugar pero no sabía el nombre "
            "y se lo dibujó al capitán.\n\n"
            "El capitán tiene muchos clientes y no recuerda haber llevado a ningún Cerbuno, "
            "pero si le decís a dónde se dirigió, quizá le refresqueis la memoria.\n\n"
            "¿Reconocéis vosotros el lugar?"
        )

        await update.message.reply_photo(photo=Q5_IMAGES[team])

    else:
        await update.message.reply_text("❌ No estáis en el lugar correcto.")

# ==================================================
# ROUTER
# ==================================================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = normalize(update.message.text)

    # Elegir equipo
    if text in ["a", "b", "c"] and user_id not in user_data:
        team = text.upper()
        init_user(user_id, team)
        await update.message.reply_text(Q1[team]["question"])
        return

    if user_id not in user_data:
        await update.message.reply_text("Escribe /start")
        return

    data = user_data[user_id]
    team = data["team"]
    step = data["step"]

    # P1
    if step == 1:
        if text == Q1[team]["answer"]:
            data["step"] = 2
            await update.message.reply_text("✅ Correcto.")
            await update.message.reply_text(Q2[team])
        else:
            data["points"] -= 1
            data["can_use_hint"] = True
            await update.message.reply_text(
                "❌ Incorrecto.\nPodeis pedir una pista, pero eso os restará puntos (/pista)"
            )
        return

    # P2
    if step == 2:
        if text == Q2_ANSWER:
            data["step"] = 3
            await update.message.reply_text("✅ Correcto.")
            await update.message.reply_text(Q3[team])
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # P3
    if step == 3:
        if text == Q3_ANSWER:
            data["step"] = 4

            keyboard = [[KeyboardButton("📍 Enviar ubicación", request_location=True)]]

            await update.message.reply_text(
                "✅ Correcto.\n\nPregunta 4:\n"
                "Si poneis estas coordenadas en vuestro Google Maps, a dónde os llevan?\n"
                "Escribid: “Ya estamos” cuando lleguéis.",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # P4
    if step == 4:
        await update.message.reply_text("📍 Debéis enviar vuestra ubicación.")
        return

    # P5
    if step == 5:
        if text == Q5_ANSWERS[team]:
            data["step"] = 6
            await update.message.reply_text(
                "✅ Correcto.\n\nPregunta 6:\n\n"
                "El capitán por fin recuerda al Cerbuno. Dice que le llevó hasta su destino "
                "pero el Cerbuno no encontró lo que buscaba y le pidió que regresara a puerto, "
                "que buscaría en otro lado.\n\n"
                "Cuando le despidió parece que se dirigía a un bar llamado Desy Vegas.\n"
                "Quizá os está esperando allí tomándose una gilda y una pinta de cerveza?\n\n"
                "Cuando lleguéis al bar mencionado, el administrador del juego "
                "os estará esperando allí y dará por terminado el juego."
            )
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # FINAL
    if step == 6:
        await update.message.reply_text("🏁 Buscad al administrador del juego.")

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
