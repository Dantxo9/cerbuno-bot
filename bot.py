import os
import math
import logging
import unicodedata
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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
ADMIN_ID = 6588872844  # CAMBIA ESTO POR TU TELEGRAM USER ID

# Coordenadas objetivo pregunta 4
TARGET_LAT = 43.321667
TARGET_LON = -1.986667
GPS_RADIUS_METERS = 50

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================================================
# ESTADO GLOBAL
# ==================================================

players = {}
finish_order = []
game_closed = False

# Estructura:
# players[user_id] = {
#   "team": "Naranja" | "Azul" | "Verde",
#   "step": 1..6,
#   "points": 40,
#   "used_hints": {1: False, 2: False, 3: False, 5: False},
#   "finished": False,
#   "name": "Nombre usuario"
# }

# ==================================================
# HELPERS
# ==================================================

def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def normalize(text: str) -> str:
    text = text.strip().lower()
    text = strip_accents(text)
    text = " ".join(text.split())
    return text

def normalize_keep_symbols(text: str) -> str:
    # Para coordenadas, conservamos símbolos pero normalizamos espacios y tildes
    text = text.strip().lower()
    text = strip_accents(text)
    text = " ".join(text.replace("\n", " ").split())
    return text

def distance_meters(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 110540
    return math.sqrt(dx * dx + dy * dy)

def create_player(user_id: int, team: str, name: str):
    players[user_id] = {
        "team": team,
        "step": 1,
        "points": 40,
        "used_hints": {1: False, 2: False, 3: False, 5: False},
        "finished": False,
        "name": name
    }

def get_player_name(update: Update) -> str:
    user = update.effective_user
    if user.username:
        return f"@{user.username}"
    if user.full_name:
        return user.full_name
    return str(user.id)

def current_bonus(position: int) -> int:
    if position == 1:
        return 15
    if position == 2:
        return 10
    return 5

def format_scoreboard() -> str:
    if not players:
        return "📊 No hay jugadores activos todavía."

    lines = ["📊 *Puntuaciones actuales*\n"]
    for uid, p in players.items():
        estado = "✅ Terminado" if p["finished"] else f"➡️ Pregunta {p['step']}"
        lines.append(
            f"• {p['name']} | Equipo {p['team']} | ⭐ {p['points']} puntos | {estado}"
        )
    return "\n".join(lines)

def is_step_with_hint(step: int) -> bool:
    return step in {1, 2, 3, 5}

# ==================================================
# HISTORIA Y PREGUNTAS
# ==================================================

INTRO = """
🏛️ *EL CERBUNO PERDIDO* 🍻📱

Un Cerbuno ha estado de fiesta en San Sebastián la noche anterior… y se ha perdido.

🤯 Iba tan borracho que ha perdido el móvil y nadie le encuentra.

Sin embargo, hemos oído a varias personas de la ciudad hablar de un Cerbuno perdido la noche anterior, y entre rumores, recuerdos borrosos y pistas sueltas… parece que podríamos reconstruir su recorrido.

🕵️‍♂️ Vuestra misión es seguir las pistas, averiguar por dónde pasó y encontrarle antes que los demás equipos.

🎯 *Sistema de puntuación*:
• Todos los equipos empiezan con *40 puntos*
• Cada pista resta *5 puntos*
• Probar respuestas *no resta puntos*
• El primer equipo en terminar gana *+15 puntos*
• El segundo gana *+10 puntos*
• El tercero gana *+5 puntos*

Escribid vuestro equipo para empezar:
🟠 Naranja
🔵 Azul
🟢 Verde
"""

Q1 = {
    "Naranja": {
        "text": """
🧩 *Pregunta 1*

Algunos habitantes de San Sebastián dicen haberle visto entre las calles Bermingham y San Francisco buscando algo para desayunar…

❓ *¿A dónde habrá ido?*
""",
        "answers": ["ogi berri"],
        "hint": "🥐 Quizá tenía hambre y quería tomarse un croissant?"
    },
    "Azul": {
        "text": """
🧩 *Pregunta 1*

Algunos habitantes de San Sebastián dicen haberle visto entre las calles Secundino Esnaola y Segundi Izpizua buscando un bar para tomar algo…

❓ *¿A dónde habrá ido?*
""",
        "answers": ["eguzki"],
        "hint": "🍷 Seguramente buscase un bistro o taberna para tomarse algo."
    },
    "Verde": {
        "text": """
🧩 *Pregunta 1*

Algunos habitantes de San Sebastián dicen haberle visto entre las calles Secundino Esnaola y Gran Vía desconcertado y sin sus gafas…

❓ *¿A dónde habrá ido?*
""",
        "answers": ["harotz"],
        "hint": "👓 Será que ha ido a por gafas nuevas?"
    }
}

Q2 = {
    "Naranja": """
🧩 *Pregunta 2*

En la *Panadería* os dicen que vieron al Cerbuno esta mañana acompañado de un tal *Daniel Ibáñez*. Entre ellos estaban hablando de adónde ir, pero no quedó muy claro. Dijeron algo así:

Blanca por fuera, de lujo por dentro,  
frente al río espera con porte de cuento.  
Reyes y estrellas descansan allí,  
si visitas Donosti… ¿duermes en mí?

📸 Quizá debáis mandarle un selfie a Daniel, y si estáis en el sitio correcto, os diga a dónde vio al Cerbuno dirigirse después.

❓ *¿Cuál es la respuesta?*
""",
    "Azul": """
🧩 *Pregunta 2*

En el *Bar* os dicen que vieron al Cerbuno esta mañana acompañado de un tal *Daniel Ibáñez*. Entre ellos estaban hablando de adónde ir, pero no quedó muy claro. Dijeron algo así:

Bajo arcos y puestos empieza el trajín,  
huele a pescado, verdura y jazmín.  
Si buscas sabores del norte con gracia,  
¿qué mercado eres, junto a la Parte Vieja?

📸 Quizá debáis mandarle un selfie a Daniel, y si estáis en el sitio correcto, os diga a dónde vio al Cerbuno dirigirse después.

❓ *¿Cuál es la respuesta?*
""",
    "Verde": """
🧩 *Pregunta 2*

En la *Óptica* os dicen que vieron al Cerbuno esta mañana acompañado de un tal *Daniel Ibáñez*. Entre ellos estaban hablando de adónde ir, pero no quedó muy claro. Dijeron algo así:

Árboles y bancos guardan la quietud,  
en pleno centro regalan salud.  
Con jardín elegante y aire señorial,  
¿qué plaza donostiarra te invita a parar?

📸 Quizá debáis mandarle un selfie a Daniel, y si estáis en el sitio correcto, os diga a dónde vio al Cerbuno dirigirse después.

❓ *¿Cuál es la respuesta?*
"""
}

Q2_ANSWERS = ["plaza de la constitucion"]
Q2_HINTS = {
    "Naranja": "🏨 ¿Será un hotel al lado de la ría?",
    "Azul": "🍔 ¿Será el mercado donde actualmente hay un McDonalds?",
    "Verde": "🏛️ ¿Será la plaza con soportales en el centro de Donosti?"
}

Q3 = {
    "Naranja": """
🧩 *Pregunta 3*

Vieron al Cerbuno en la *Plaza de la Constitución* mirando hacia los edificios y sus balcones, apuntando algo en su cuaderno.

📝 ¿Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(B3-H2)°(A1+R1)’(A1+Q1)”N (B1-A1)°(AP1+Q1)’(A1+K1)”W

❓ *¿Qué coordenadas ha apuntado?*
""",
    "Azul": """
🧩 *Pregunta 3*

Vieron al Cerbuno en la *Plaza de la Constitución* mirando hacia los edificios y sus balcones, apuntando algo en su cuaderno.

📝 ¿Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(R1+X1)°(E1+N1)’(F1+L1)”N (V1-U1)°(AS3-K2)’(E1+G1)”W

❓ *¿Qué coordenadas ha apuntado?*
""",
    "Verde": """
🧩 *Pregunta 3*

Vieron al Cerbuno en la *Plaza de la Constitución* mirando hacia los edificios y sus balcones, apuntando algo en su cuaderno.

📝 ¿Estaría apuntando las coordenadas de su siguiente destino?

Se le vio apuntar lo siguiente:

(U2-AA1)°(I1+J1)’(H1+J1)N (I1-H1)°(AD1+AC1)’(T1-H1)”W

❓ *¿Qué coordenadas ha apuntado?*
"""
}

Q3_ANSWERS = [
    '43°19\'18"n 1°59\'12"w',
    '43°19\'18"n 1°59\'12"w'
]
Q3_HINT = '📍 Añadid las coordenadas en formato #°#\'#"N #°#\'#"W'

Q4_TEXT = """
🧩 *Pregunta 4*

Si ponéis estas coordenadas en vuestro Google Maps, ¿a dónde os llevan? 📍

✅ *Respuesta esperada*:
Telegram os pedirá la ubicación y verificará que os encontráis cerca de las coordenadas *43°19'18"N 1°59'12"W*.

"""

Q5_TEXT = """
🧩 *Pregunta 5*

Al llegar, encontráis un papel en el suelo con una silueta. Quizá quería ir en barco a algún lugar, pero no sabía el nombre y se lo dibujó al capitán.

⛵ El capitán tiene muchos clientes y no recuerda haber llevado a ningún Cerbuno, pero si le decís a dónde se dirigió, quizá le refresquéis la memoria.

❓ *¿Reconocéis vosotros el lugar?*
"""

# Convertidos a raw.githubusercontent.com para que Telegram los cargue mejor
Q5_IMAGES = {
    "Naranja": "https://raw.githubusercontent.com/Dantxo9/cerbuno-bot/871f9f7f465498c844ad138bb48c6af373bc4ae9/images/Isla%20de%20Santa%20Clara.png",
    "Azul": "https://raw.githubusercontent.com/Dantxo9/cerbuno-bot/871f9f7f465498c844ad138bb48c6af373bc4ae9/images/Monte%20Igeldo.png",
    "Verde": "https://raw.githubusercontent.com/Dantxo9/cerbuno-bot/871f9f7f465498c844ad138bb48c6af373bc4ae9/images/Palacio%20de%20Miramar.png"
}

Q5_ANSWERS = {
    "Naranja": ["isla de santa clara", "isla santa clara"],
    "Azul": ["monte igeldo"],
    "Verde": ["palacio de miramar", "palacio miramar"]
}

Q5_HINTS = {
    "Naranja": "🚤 Solo se puede llegar en barco",
    "Azul": "🎡 En él se encuentra un parque de atracciones del mismo nombre",
    "Verde": "🏖️ Entre las playas de La Concha y Ondarreta"
}

Q6_TEXT = """
🧩 *Pregunta 6*

El capitán por fin recuerda al Cerbuno. Dice que le llevó hasta su destino, pero el Cerbuno no encontró lo que buscaba y le pidió que regresara a puerto, que buscaría en otro lado.

Cuando le despidió, parece que se dirigía a un bar llamado *Desy Vegas*.

🍺 Quizá os está esperando allí, tomándose una gilda y una pinta de cerveza.

✅ *Respuesta*: sin respuesta escrita.
Cuando lleguéis, el administrador del juego validará vuestra llegada manualmente.
"""

# ==================================================
# COMANDOS
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game_closed:
        await update.message.reply_text("🏁 El juego ya ha sido cerrado por el administrador.")
        return

    keyboard = [["Naranja", "Azul", "Verde"]]
    await update.message.reply_text(
        INTRO,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in players:
        await update.message.reply_text("Escribe /start para comenzar.")
        return

    p = players[uid]
    step = p["step"]

    if not is_step_with_hint(step):
        await update.message.reply_text("ℹ️ En esta pregunta no hay pista disponible.")
        return

    if p["used_hints"].get(step, False):
        await update.message.reply_text("⚠️ Ya habéis usado la pista de esta pregunta.")
        return

    p["used_hints"][step] = True
    p["points"] -= 5

    if step == 1:
        hint_text = Q1[p["team"]]["hint"]
    elif step == 2:
        hint_text = Q2_HINTS[p["team"]]
    elif step == 3:
        hint_text = Q3_HINT
    elif step == 5:
        hint_text = Q5_HINTS[p["team"]]
    else:
        hint_text = "Sin pista."

    await update.message.reply_text(
        f"💡 *Pista*\n{hint_text}\n\n⭐ -5 puntos\nPuntuación actual: *{p['points']}*",
        parse_mode="Markdown"
    )

async def puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        format_scoreboard(),
        parse_mode="Markdown"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_closed

    if update.effective_user.id != ADMIN_ID:
        return

    players.clear()
    finish_order.clear()
    game_closed = False

    await update.message.reply_text("🔄 Juego reiniciado. Todo listo para empezar otra vez.")

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_closed

    if update.effective_user.id != ADMIN_ID:
        return

    # Uso recomendado: responder al mensaje del jugador que ha llegado al bar
    target_uid = None

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_uid = int(context.args[0])
        except ValueError:
            pass

    if target_uid is None:
        await update.message.reply_text(
            "ℹ️ Usa /finish respondiendo al mensaje del jugador o /finish USER_ID"
        )
        return

    if target_uid not in players:
        await update.message.reply_text("❌ Ese jugador no está en la partida.")
        return

    p = players[target_uid]

    if p["finished"]:
        await update.message.reply_text("⚠️ Ese jugador ya estaba marcado como terminado.")
        return

    p["finished"] = True
    finish_order.append(target_uid)

    pos = len(finish_order)
    bonus = current_bonus(pos)
    p["points"] += bonus

    await update.message.reply_text(
        f"🏁 *Llegada validada*\n\n"
        f"Jugador: {p['name']}\n"
        f"Equipo: {p['team']}\n"
        f"Posición: {pos}º\n"
        f"Bonus: +{bonus} puntos\n"
        f"Puntuación final provisional: *{p['points']}*",
        parse_mode="Markdown"
    )

async def cerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_closed

    if update.effective_user.id != ADMIN_ID:
        return

    game_closed = True
    await update.message.reply_text("🔒 Juego cerrado. Ya no se aceptarán más respuestas.")

# ==================================================
# GPS
# ==================================================

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in players or game_closed:
        return

    p = players[uid]

    if p["step"] != 4:
        await update.message.reply_text("📍 Ubicación recibida, pero ahora mismo no estáis en la prueba GPS.")
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

        await update.message.reply_text(
            "✅ *¡Ubicación correcta!*\n\nHabéis llegado al punto indicado.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

        await update.message.reply_text(Q5_TEXT, parse_mode="Markdown")

        await update.message.reply_photo(
            photo=Q5_IMAGES[p["team"]],
            caption=f"🖼️ Pista visual del *Equipo {p['team']}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"📍 Aún no estáis en el lugar correcto.\n"
            f"Estáis aproximadamente a *{int(dist)} metros* del punto.\n\n"
            f"Si el GPS falla, podéis escribir *club náutico* como alternativa.",
            parse_mode="Markdown"
        )

# ==================================================
# ROUTER PRINCIPAL
# ==================================================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game_closed:
        await update.message.reply_text("🔒 El juego ha sido cerrado por el administrador.")
        return

    uid = update.effective_user.id
    raw_text = update.message.text
    text = normalize(raw_text)
    coord_text = normalize_keep_symbols(raw_text)

    # Selección de equipo
    if text in ["naranja", "azul", "verde"] and uid not in players:
        team = text.capitalize()
        create_player(uid, team, get_player_name(update))
        await update.message.reply_text(
            f"🎉 Equipo *{team}* seleccionado.\n\n"
            f"Empezáis con *40 puntos*.\n"
            f"Podéis pedir pista con /pista cuando queráis, pero cada pista resta *5 puntos*.\n\n"
            f"{Q1[team]['text']}",
            parse_mode="Markdown"
        )
        return

    if uid not in players:
        await update.message.reply_text("Escribe /start para comenzar.")
        return

    p = players[uid]
    team = p["team"]
    step = p["step"]

    # =========================
    # PREGUNTA 1
    # =========================
    if step == 1:
        if text in [normalize(a) for a in Q1[team]["answers"]]:
            p["step"] = 2
            await update.message.reply_text(
                "✅ *¡Correcto!*\n\nSiguiente pista…",
                parse_mode="Markdown"
            )
            await update.message.reply_text(Q2[team], parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "❌ No es correcto.\n"
                "Podéis seguir probando sin perder puntos, o pedir una pista con /pista (-5 puntos)."
            )
        return

    # =========================
    # PREGUNTA 2
    # =========================
    if step == 2:
        if text in [normalize(a) for a in Q2_ANSWERS]:
            p["step"] = 3
            await update.message.reply_text(
                "✅ *¡Correcto!*\n\nParece que el Cerbuno siguió su camino hasta la Plaza de la Constitución…",
                parse_mode="Markdown"
            )
            await update.message.reply_text(Q3[team], parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "❌ No es correcto.\n"
                "Podéis seguir intentando o pedir una pista con /pista (-5 puntos)."
            )
        return

    # =========================
    # PREGUNTA 3
    # =========================
    if step == 3:
        valid_q3 = [normalize_keep_symbols(a) for a in Q3_ANSWERS]

        if coord_text in valid_q3:
            p["step"] = 4

            keyboard = [[KeyboardButton("📍 Enviar ubicación", request_location=True)]]

            await update.message.reply_text(
                "✅ *¡Correcto!*\n\n"
                "Ahora toca comprobar el destino en el mapa…",
                parse_mode="Markdown"
            )

            await update.message.reply_text(
                Q4_TEXT,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "❌ No es correcto.\n"
                "Podéis seguir intentando o pedir una pista con /pista (-5 puntos)."
            )
        return

    # =========================
    # PREGUNTA 4
    # =========================
    if step == 4:
        if text == "club nautico":
            p["step"] = 5

            await update.message.reply_text(
                "✅ *Respuesta alternativa aceptada.*\n\n"
                "Parece que el GPS no quería colaborar… seguimos adelante 🚤",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

            await update.message.reply_text(Q5_TEXT, parse_mode="Markdown")
            await update.message.reply_photo(
                photo=Q5_IMAGES[team],
                caption=f"🖼️ Pista visual del *Equipo {team}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "📍 En esta prueba debéis enviar vuestra ubicación o escribir *club náutico* si el GPS falla.",
                parse_mode="Markdown"
            )
        return

    # =========================
    # PREGUNTA 5
    # =========================
    if step == 5:
        valid_q5 = [normalize(a) for a in Q5_ANSWERS[team]]

        if text in valid_q5:
            p["step"] = 6

            await update.message.reply_text(
                "✅ *¡Correcto!*\n\n"
                "El capitán parece empezar a recordar…",
                parse_mode="Markdown"
            )

            await update.message.reply_text(Q6_TEXT, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "❌ No es correcto.\n"
                "Podéis seguir intentando o pedir una pista con /pista (-5 puntos)."
            )
        return

    # =========================
    # PREGUNTA 6 / FINAL
    # =========================
    if step == 6:
        if p["finished"]:
            await update.message.reply_text(
                f"🏁 Ya tenéis la llegada validada.\n"
                f"Puntuación actual: *{p['points']}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "🍻 Ya estáis en la fase final.\n"
                "Id a *Desy Vegas* y el administrador validará vuestra llegada manualmente con /finish.",
                parse_mode="Markdown"
            )
        return

# ==================================================
# MAIN
# ==================================================

def main():
    if not TOKEN:
        print("ERROR: Falta la variable de entorno TOKEN.")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pista", pista))
    app.add_handler(CommandHandler("puntos", puntos))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("finish", finish))
    app.add_handler(CommandHandler("cerrar", cerrar))

    # Primero ubicación, luego texto
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("🤖 Bot funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
