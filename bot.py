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
# CONFIG
# ==================================================

TOKEN = os.getenv("TOKEN")
# TU ID TELEGRAM
ADMIN_ID = 6588872844

# Coordenadas objetivo Pregunta 4
TARGET_LAT = 51.540511
TARGET_LON = -0.181271

GPS_RADIUS_METERS = 250

logging.basicConfig(level=logging.INFO)

# ==================================================
# STATE
# ==================================================

players = {}
finish_order = []

# ==================================================
# HISTORIA
# ==================================================

INTRO = """
🏛️ CERBUNO PERDIDO

Un Cerbuno ha estado de fiesta en San Sebastián la noche anterior y se ha perdido.
Estaba tan borracho que ha perdido el móvil y nadie le encuentra.

Hemos oído a gente de la ciudad hablando de un Cerbuno perdido la noche anterior y nos han dado algunas pistas para encontrarle.
"""

# ==================================================
# PREGUNTA 1
# ==================================================

Q1 = {
    "Naranja": {
        "text": """
Pregunta 1:
Algunos habitantes de San Sebastián dicen haberle visto entre las calles…
Equipo Naranja: …Bermingham y San Francisco buscando algo para desayunar…
… ¿A dónde habrá ido?
""",
        "answer": "ogi berri",
        "hint": "Quizá tenía hambre y quería tomarse un croissant?"
    },
    "Azul": {
        "text": """
Pregunta 1:
Algunos habitantes de San Sebastián dicen haberle visto entre las calles…
Equipo Azul: …Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo…
… ¿A dónde habrá ido?
""",
        "answer": "eguzki",
        "hint": "Seguramente buscase un bistro o taberna para tomarse algo."
    },
    "Verde": {
        "text": """
Pregunta 1:
Algunos habitantes de San Sebastián dicen haberle visto entre las calles…
Equipo Verde: …Secundino Esnaola y Gran Vía desconcertado y sin sus gafas…
… ¿A dónde habrá ido?
""",
        "answer": "harotz",
        "hint": "Será que ha ido a por gafas nuevas?"
    }
}

# ==================================================
# PREGUNTA 2
# ==================================================

Q2 = """
Pregunta 2:
En la (A: Panadería, B: Bar, C: Óptica) os dicen que vieron al Cerbuno con Daniel Ibáñez.

Dijeron esto:

A:
Blanca por fuera, de lujo por dentro,
frente al río espera con porte de cuento.
Reyes y estrellas descansan allí,
si visitas Donosti… ¿duermes en mí?

B:
Bajo arcos y puestos empieza el trajín,
huele a pescado, verdura y jazmín.
Si buscas sabores del norte con gracia,
¿qué mercado eres, junto a la Parte Vieja?

C:
Árboles y bancos guardan la quietud,
en pleno centro regalan salud.
Con jardín elegante y aire señorial,
¿qué plaza donostiarra te invita a parar?

Respuesta: Plaza de la Constitución
"""

Q2_ANSWER = "plaza de la constitucion"

# ==================================================
# PREGUNTA 3
# ==================================================

Q3 = """
Pregunta 3:
Vieron al Cerbuno en la Plaza de la Constitución mirando al oeste, apuntando coordenadas:

43°19'18"N 1°59'12"W
"""

Q3_ANSWER = '43°19\'18"n 1°59\'12"w'

# ==================================================
# PREGUNTA 5
# ==================================================

Q5_IMAGES = {
    "Naranja": "https://www.mercilona.com/cdn/shop/files/1_e178919e-6969-43b4-b48d-5b0eafc4a1d0_1024x1024@2x.jpg?v=1766409572",
    "Azul": "https://pasaiarte.com/cdn/shop/files/20205w_large.gif?v=1743160175",
    "Verde": "https://s1.ppllstatics.com/diariovasco/www/multimedia/201711/08/media/MM-palacio-miramar/1402366369.jpg"
}

Q5_ANSWERS = {
    "Naranja": "isla de santa clara",
    "Azul": "monte igeldo",
    "Verde": "palacio de miramar"
}

# ==================================================
# HELPERS
# ==================================================

def norm(t):
    return t.strip().lower()

def distance_meters(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.sqrt(dx * dx + dy * dy)

def new_player(uid, team):
    players[uid] = {
        "team": team,
        "step": 1,
        "points": 40,
        "hint": False,
        "finished": False
    }

# ==================================================
# START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Naranja", "Azul", "Verde"]]

    await update.message.reply_text(
        INTRO + "\n\nElige equipo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ==================================================
# PISTA
# ==================================================

async def pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in players:
        return

    p = players[uid]

    if p["step"] != 1:
        return

    if p["hint"]:
        await update.message.reply_text("Ya usaste pista.")
        return

    p["hint"] = True
    p["points"] -= 5

    await update.message.reply_text(
        f"💡 {Q1[p['team']]['hint']}\n-5 puntos"
    )

# ==================================================
# ADMIN
# ==================================================

async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = "📊 PUNTUACIONES\n\n"
    for uid, p in players.items():
        msg += f"{uid} | {p['team']} | {p['points']} pts | paso {p['step']}\n"

    await update.message.reply_text(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    players.clear()
    finish_order.clear()
    await update.message.reply_text("🔄 Juego reiniciado.")

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("🏁 Juego finalizado por el admin.")

# ==================================================
# GPS
# ==================================================

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in players:
        return

    p = players[uid]

    if p["step"] != 4:
        return

    loc = update.message.location

    dist = distance_meters(
        loc.latitude,
        loc.longitude,
        TARGET_LAT,
        TARGET_LON
    )

    if dist <= GPS_RADIUS_METERS:
        p["step"] = 5
        await update.message.reply_text("✅ Correcto, estáis en el punto.")

        await update.message.reply_text(
            "Pregunta 5:\nEncontráis una silueta en el suelo… ¿qué lugar es?"
        )

        await update.message.reply_photo(Q5_IMAGES[p["team"]])

    else:
        await update.message.reply_text(
            f"❌ Estáis a {int(dist)} metros. Alternativa: escribid 'club náutico' si creéis que es correcto."
        )

# ==================================================
# ROUTER
# ==================================================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = norm(update.message.text)

    if text in ["naranja", "azul", "verde"] and uid not in players:
        new_player(uid, text.capitalize())
        await update.message.reply_text(Q1[text.capitalize()]["text"])
        return

    if uid not in players:
        await update.message.reply_text("Escribe /start")
        return

    p = players[uid]

    # Q1
    if p["step"] == 1:
        if text == Q1[p["team"]]["answer"]:
            p["step"] = 2
            await update.message.reply_text("✅ Correcto")
            await update.message.reply_text(Q2)
        else:
            await update.message.reply_text("❌ Incorrecto (puedes pedir pista)")
        return

    # Q2
    if p["step"] == 2:
        if text == Q2_ANSWER:
            p["step"] = 3
            await update.message.reply_text("✅ Correcto")
            await update.message.reply_text(Q3)
        else:
            await update.message.reply_text("❌ Incorrecto")
        return

    # Q3
    if p["step"] == 3:
        if text == Q3_ANSWER:
            p["step"] = 4

            keyboard = [[KeyboardButton("📍 Enviar ubicación", request_location=True)]]

            await update.message.reply_text(
                "Pregunta 4: enviad ubicación cuando lleguéis",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Incorrecto")
        return

    # Q5
    if p["step"] == 5:
        if text == Q5_ANSWERS[p["team"]]:
            p["step"] = 6
            await update.message.reply_text(
                "Pregunta 6:\nEl Cerbuno fue visto dirigiéndose a Desy Vegas 🍻"
            )
        else:
            await update.message.reply_text("❌ Incorrecto")
        return

    # FINAL
    if p["step"] == 6:
        if not p["finished"]:
            p["finished"] = True
            finish_order.append(uid)

            bonus = {0:15,1:10,2:5}.get(len(finish_order)-1, 5)
            p["points"] += bonus

            await update.message.reply_text(f"🏁 Terminado +{bonus} puntos")

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

    print("Bot activo")
    app.run_polling()

if __name__ == "__main__":
    main()
# Radio amplio para evitar errores GPS
GPS_RADIUS_METERS = 250

logging.basicConfig(level=logging.INFO)

# ==================================================
# MEMORIA
# ==================================================

players = {}
finish_order = []

# ==================================================
# TEXTOS
# ==================================================

INTRO = """
🏛️ EL CERBUNO PERDIDO

Anoche un Cerbuno salió de fiesta por San Sebastián...
y la noche se le fue de las manos.

Esta mañana nadie sabe dónde está.

Iba tan borracho que perdió el móvil,
no responde a nadie
y no hay rastro suyo.

Solo vosotros podéis reconstruir su ruta
y encontrar al Cerbuno perdido.
"""

Q1 = {
    "Naranja": {
        "text": """
🧩 PREGUNTA 1

Algunos habitantes de San Sebastián dicen haberle visto entre Bermingham y San Francisco buscando algo para desayunar...

❓ ¿A dónde habrá ido?
""",
        "answer": "ogi berri",
        "hint": "Quizá tenía hambre y quería tomarse un croissant."
    },

    "Azul": {
        "text": """
🧩 PREGUNTA 1

Algunos habitantes de San Sebastián dicen haberle visto entre Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo...

❓ ¿A dónde habrá ido?
""",
        "answer": "eguzki",
        "hint": "Seguramente buscase un bistro o taberna para tomar algo."
    },

    "Verde": {
        "text": """
🧩 PREGUNTA 1

Algunos habitantes de San Sebastián dicen haberle visto entre Secundino Esnaola y Gran Vía desconcertado y sin sus gafas...

❓ ¿A dónde habrá ido?
""",
        "answer": "harotz",
        "hint": "Será que ha ido a por gafas nuevas?"
    }
}

Q2 = """
🧩 PREGUNTA 2

Os dicen que vieron al Cerbuno acompañado de Daniel Ibáñez.

Todos coinciden en el siguiente destino:

❓ ¿Dónde es?

Respuesta para todos:
Plaza de la Constitución
"""

Q2_ANSWER = "plaza de la constitucion"

Q3 = """
🧩 PREGUNTA 3

El Cerbuno apuntó unas coordenadas.

❓ ¿Cuáles son?

43°19'18"N 1°59'12"W
"""

Q3_ANSWER = '43°19\'18"n 1°59\'12"w'

Q5_IMAGES = {
    "Naranja": "https://www.mercilona.com/cdn/shop/files/1_e178919e-6969-43b4-b48d-5b0eafc4a1d0_1024x1024@2x.jpg?v=1766409572",
    "Azul": "https://pasaiarte.com/cdn/shop/files/20205w_large.gif?v=1743160175",
    "Verde": "https://s1.ppllstatics.com/diariovasco/www/multimedia/201711/08/media/MM-palacio-miramar/1402366369.jpg"
}

Q5_ANSWERS = {
    "Naranja": "isla de santa clara",
    "Azul": "monte igeldo",
    "Verde": "palacio de miramar"
}

# ==================================================
# HELPERS
# ==================================================

def norm(t):
    return t.strip().lower()

def distance_meters(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.sqrt(dx*dx + dy*dy)

def create_player(uid, team):
    players[uid] = {
        "team": team,
        "step": 1,
        "points": 40,
        "hint_used": False,
        "finished": False
    }

# ==================================================
# COMANDOS
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Naranja", "Azul", "Verde"]]

    await update.message.reply_text(
        INTRO + "\n\n🎨 Elegid equipo:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in players:
        return

    p = players[uid]

    if p["step"] != 1:
        await update.message.reply_text("Solo hay pista en la Pregunta 1.")
        return

    if p["hint_used"]:
        await update.message.reply_text("Ya habéis usado la pista.")
        return

    p["hint_used"] = True
    p["points"] -= 5

    await update.message.reply_text(
        f"💡 {Q1[p['team']]['hint']}\n⭐ -5 puntos\nTotal: {p['points']}"
    )

async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = "📊 PUNTUACIONES\n\n"

    for uid, p in players.items():
        msg += (
            f"User {uid}\n"
            f"Equipo: {p['team']}\n"
            f"Paso: {p['step']}\n"
            f"Puntos: {p['points']}\n\n"
        )

    await update.message.reply_text(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    players.clear()
    finish_order.clear()

    await update.message.reply_text("🔄 Juego reiniciado.")

# ==================================================
# GPS
# ==================================================

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in players:
        return

    p = players[uid]

    print("📍 Ubicación recibida")

    if p["step"] != 4:
        await update.message.reply_text(
            "Ubicación recibida, pero no estáis en la prueba GPS."
        )
        return

    loc = update.message.location

    dist = distance_meters(
        loc.latitude,
        loc.longitude,
        TARGET_LAT,
        TARGET_LON
    )

    print("Distancia:", dist)

    if dist <= GPS_RADIUS_METERS:
        p["step"] = 5

        await update.message.reply_text(
            "✅ ¡Ubicación correcta!"
        )

        await update.message.reply_text(
            """
🧩 PREGUNTA 5

Al llegar encontráis una silueta dibujada.

Quizá quería ir en barco a algún lugar.

❓ ¿Reconocéis el lugar?
"""
        )

        await update.message.reply_photo(
            photo=Q5_IMAGES[p["team"]]
        )

    else:
        await update.message.reply_text(
            f"📍 Estáis a {int(dist)} metros del punto correcto."
        )

# ==================================================
# MENSAJES
# ==================================================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = norm(update.message.text)

    # Elegir equipo
    if text in ["naranja", "azul", "verde"] and uid not in players:
        team = text.capitalize()
        create_player(uid, team)

        await update.message.reply_text(Q1[team]["text"])
        return

    if uid not in players:
        await update.message.reply_text("Escribe /start")
        return

    p = players[uid]
    step = p["step"]

    # -------------------------
    # Pregunta 1
    # -------------------------
    if step == 1:
        if text == Q1[p["team"]]["answer"]:
            p["step"] = 2
            await update.message.reply_text("✅ Correcto.")
            await update.message.reply_text(Q2)
        else:
            await update.message.reply_text(
                "❌ Incorrecto.\nPodéis pedir pista con /pista (-5 puntos)"
            )
        return

    # -------------------------
    # Pregunta 2
    # -------------------------
    if step == 2:
        if text == Q2_ANSWER:
            p["step"] = 3
            await update.message.reply_text("✅ Correcto.")
            await update.message.reply_text(Q3)
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # -------------------------
    # Pregunta 3
    # -------------------------
    if step == 3:
        if text == Q3_ANSWER:
            p["step"] = 4

            keyboard = [[KeyboardButton(
                "📍 Enviar ubicación",
                request_location=True
            )]]

            await update.message.reply_text(
                """
🧩 PREGUNTA 4

Poned las coordenadas en Google Maps.

Cuando lleguéis, enviad ubicación.
""",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard,
                    resize_keyboard=True
                )
            )
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # -------------------------
    # Pregunta 4
    # -------------------------
    if step == 4:
        await update.message.reply_text(
            "📍 Debéis enviar ubicación."
        )
        return

    # -------------------------
    # Pregunta 5
    # -------------------------
    if step == 5:
        if text == Q5_ANSWERS[p["team"]]:
            p["step"] = 6

            await update.message.reply_text(
                """
🧩 PREGUNTA 6

El capitán recuerda al Cerbuno.

Dice que luego fue a un bar llamado Desy Vegas.

🍻 Id allí.
Cuando lleguéis se validará vuestra llegada.
"""
            )
        else:
            await update.message.reply_text("❌ Incorrecto.")
        return

    # -------------------------
    # Final
    # -------------------------
    if step == 6:

        if not p["finished"]:
            p["finished"] = True
            finish_order.append(uid)

            pos = len(finish_order)

            if pos == 1:
                bonus = 15
            elif pos == 2:
                bonus = 10
            else:
                bonus = 5

            p["points"] += bonus

            await update.message.reply_text(
                f"🏁 Llegada registrada.\n⭐ Bonus +{bonus}\nTotal: {p['points']}"
            )
        else:
            await update.message.reply_text("Ya habéis terminado.")

# ==================================================
# MAIN
# ==================================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pista", pista))
    app.add_handler(CommandHandler("puntos", puntos))
    app.add_handler(CommandHandler("reset", reset))

    # IMPORTANTE: ubicación antes que texto
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("🤖 Bot funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
