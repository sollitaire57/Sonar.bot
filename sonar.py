import json
import os
import random
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# =========================
# 🔑 BOT TOKEN
# =========================
bot_token = "8294222308:AAHyOz4MoQ-8n5gCL17Jmsp2nwk5u_WfuN0"

# =========================
# 📁 FILES
# =========================
USERS_FILE = "users.json"
GAMES_FILE = "games.json"

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_FILE)
games = load_json(GAMES_FILE)

# =========================
# 👤 USER
# =========================
def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "money": 10000,
            "bank": 0,
            "xp": 0,
            "level": 0
        }
    return users[uid]

# =========================
# ⭐ XP
# =========================
def add_xp(user, amount):
    user["xp"] += amount
    leveled = False
    while True:
        needed = (user["level"] + 1) * 100
        if user["xp"] >= needed:
            user["xp"] -= needed
            user["level"] += 1
            leveled = True
        else:
            break
    return leveled

def xp_needed(user):
    return (user["level"] + 1) * 100

# =========================
# 🎮 SONAR
# =========================
def generate_treasures():
    t = []
    while len(t) < 5:
        x = random.randint(0,9)
        y = random.randint(0,9)
        if (x,y) not in t:
            t.append((x,y))
    return t

def parse_coord(coord):
    col = ord(coord[0].upper()) - ord('A')
    row = int(coord[1:]) - 1
    return col, row

def distance(x1, y1, x2, y2):
    return int(math.sqrt((x1 - x2)**2 + (y1 - y2)**2))

def nearest(x, y, treasures):
    return min(distance(x, y, tx, ty) for tx, ty in treasures)

# =========================
# 🗺️ GRID
# =========================
def draw_grid(game):
    grid = [["⬜" for _ in range(10)] for _ in range(10)]
    for x, y in game["shots"]:
        grid[y][x] = "📡"
    for x, y in game.get("found", []):
        grid[y][x] = "❌"
    header = "   " + " ".join([chr(i) for i in range(65,75)])
    rows = []
    for i, row in enumerate(grid):
        rows.append(f"{i+1:<2} " + " ".join(row))
    return header + "\n" + "\n".join(rows)

# =========================
# ▶️ COMMANDES PRINCIPALES
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🎮 SONAR GAME

📜 Commandes :

/sonar → lancer une partie
/put A5 → scanner
/p A5 → rapide

📊 /statut
🏦 /deposit 1000
💸 /withdraw 500

💡 Scan = 3000
💰 Trésor = 25 000
"""
    await update.message.reply_text(msg)

async def sonar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    games[cid] = {
        "treasures": generate_treasures(),
        "shots": [],
        "found": []
    }
    save_json(GAMES_FILE, games)
    await update.message.reply_text("🎮 Nouvelle partie lancée !")

async def put(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in games:
        return await update.message.reply_text("❌ Lance une partie avec /sonar")
    if len(context.args) == 0:
        return await update.message.reply_text("❌ Indique une coordonnée (ex: A5)")

    coord = context.args[0]
    try:
        x, y = parse_coord(coord)
    except:
        return await update.message.reply_text("❌ Coordonnée invalide (A5)")

    game = games[cid]
    user = get_user(update.effective_user.id)

    if user["money"] < 3000:
        return await update.message.reply_text("❌ Solde insuffisant (3000 requis)")
    if (x, y) in game["shots"]:
        return await update.message.reply_text("❌ Déjà scanné ici")

    user["money"] -= 3000
    game["shots"].append((x,y))
    treasures = game["treasures"]

    if (x,y) in treasures:
        treasures.remove((x,y))
        game["found"].append((x,y))
        user["money"] += 25000
        leveled = add_xp(user, 10)
        msg = "💰 Trésor trouvé ! +25 000 | +10 XP\n"
        if leveled:
            msg += "🎉 LEVEL UP !\n"
        msg += draw_grid(game)
        if not treasures:
            msg += "\n🏆 Tous les trésors trouvés !"
            del games[cid]
        await update.message.reply_text(msg)
    else:
        dist = nearest(x, y, treasures)
        msg = f"📡 Signal : {min(dist,9)}\n\n" + draw_grid(game)
        await update.message.reply_text(msg)

    save_json(USERS_FILE, users)
    save_json(GAMES_FILE, games)

async def statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    name = update.effective_user.username or update.effective_user.first_name
    msg = f"""
✨━━━ 🎮 PROFIL 🎮 ━━━✨

👤 {name}

💰 Cash : {user['money']}
🏦 Banque : {user['bank']}

⭐ Niveau : {user['level']}
📊 XP : {user['xp']} / {xp_needed(user)}
"""
    await update.message.reply_text(msg)

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if len(context.args) == 0: return
    amount = int(context.args[0])
    if user["money"] < amount:
        return await update.message.reply_text("❌ Pas assez d'argent")
    user["money"] -= amount
    user["bank"] += amount
    save_json(USERS_FILE, users)
    await update.message.reply_text(f"🏦 Déposé : {amount}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if len(context.args) == 0: return
    amount = int(context.args[0])
    if user["bank"] < amount:
        return await update.message.reply_text("❌ Pas assez en banque")
    user["bank"] -= amount
    user["money"] += amount
    save_json(USERS_FILE, users)
    await update.message.reply_text(f"💸 Retiré : {amount}")

# =========================
# ▶️ COMMANDES SUPPLÉMENTAIRES (INVISIBLES DANS /start)
# =========================
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /pay @user montant")
    mention = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        return await update.message.reply_text("Montant invalide")
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Tu dois répondre à l'utilisateur à qui donner l'argent")
    receiver_id = update.message.reply_to_message.from_user.id
    sender = get_user(update.effective_user.id)
    receiver = get_user(receiver_id)
    if sender["money"] < amount:
        return await update.message.reply_text("❌ Pas assez d'argent")
    sender["money"] -= amount
    receiver["money"] += amount
    save_json(USERS_FILE, users)
    await update.message.reply_text(f"💸 Envoyé {amount} à {update.message.reply_to_message.from_user.first_name}")

async def tak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # seulement admin
    admin_ids = [update.effective_user.id]  # à modifier selon tes admins
    if update.effective_user.id not in admin_ids:
        return
    if len(context.args) == 0: return
    try:
        amount = int(context.args[0])
    except:
        return
    user = get_user(update.effective_user.id)
    user["money"] += amount
    save_json(USERS_FILE, users)
    await update.message.reply_text(f"💰 Tu as reçu {amount} du bot")

async def rev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in games:
        return await update.message.reply_text("❌ Pas de partie en cours")
    game = games[cid]
    coords = ", ".join([f"{chr(x+65)}{y+1}" for x,y in game["treasures"]])
    await update.message.reply_text(f"🗺️ Trésors actuels : {coords}")

# =========================
# 🚀 APPLICATION
# =========================
app = ApplicationBuilder().token(bot_token).build()
# Commandes principales
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("sonar", sonar))
app.add_handler(CommandHandler("put", put))
app.add_handler(CommandHandler("p", put))
app.add_handler(CommandHandler("statut", statut))
app.add_handler(CommandHandler("deposit", deposit))
app.add_handler(CommandHandler("withdraw", withdraw))
# Commandes invisibles
app.add_handler(CommandHandler("pay", pay))
app.add_handler(CommandHandler("tak", tak))
app.add_handler(CommandHandler("rev", rev))

print("Bot en ligne...")
app.run_polling()
