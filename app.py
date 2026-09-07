import os
import json
import random
import threading
import asyncio
import time
import math

from flask import Flask, render_template, jsonify, request
from telegram import Update, WebAppInfo, MenuButtonWebApp, BotCommand, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler

app = Flask(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8991377045:AAHt8HZ-1Ms6WDuxTSb18FkjXQEPR8uKoFc")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://casino-stars-bot.onrender.com")
PORT = int(os.environ.get("PORT", 5000))

CRASH_CURVE = [
    (1.0, 0.03), (1.1, 0.13), (1.25, 0.24), (1.5, 0.42),
    (1.8, 0.56), (2.0, 0.65), (2.5, 0.77), (3.0, 0.84),
    (5.0, 0.91), (8.0, 0.95), (12.0, 0.97), (25.0, 0.985),
    (50.0, 0.993), (100.0, 1.0),
]

game_state = {
    "phase": "betting",
    "multiplier": 1.00,
    "crash_point": 0,
    "round_id": 0,
    "players": {},
    "history": [],
    "timer": 0,
    "start_time": 0,
}

lock = threading.Lock()


def get_crash_point():
    roll = random.random()
    low = 1.0
    high = 100.0
    for mult, prob in CRASH_CURVE:
        if roll <= prob:
            high = mult
            break
        low = mult
    raw = low + (high - low) * random.random()
    return round(raw, 2)


def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def game_loop():
    while True:
        with lock:
            game_state["round_id"] += 1
            game_state["phase"] = "betting"
            game_state["multiplier"] = 1.00
            game_state["players"] = {}
            game_state["timer"] = 5
            game_state["start_time"] = time.time()

        for i in range(5, 0, -1):
            with lock:
                game_state["timer"] = i
            time.sleep(1)

        crash_point = get_crash_point()
        with lock:
            game_state["phase"] = "flying"
            game_state["crash_point"] = crash_point

        current = 1.00
        speed = 0.10
        while current < crash_point:
            current = round(current + 0.01, 2)
            if current > crash_point:
                current = crash_point

            with lock:
                game_state["multiplier"] = current

                for uid, player in list(game_state["players"].items()):
                    if not player.get("cashed_out") and player.get("auto_cashout", 0) > 0:
                        if current >= player["auto_cashout"]:
                            player["cashed_out"] = True
                            player["cashout_mult"] = current
                            users = load_users()
                            if uid in users:
                                payout = round(player["bet"] * current, 1)
                                users[uid]["balance"] += payout
                                users[uid]["total_won"] = users[uid].get("total_won", 0) + payout
                                users[uid]["games"] = users[uid].get("games", 0) + 1
                                save_users(users)

            speed = speed + random.uniform(-0.02, 0.02)
            speed = max(0.04, min(0.18, speed))
            time.sleep(speed)

        with lock:
            game_state["phase"] = "crashed"
            game_state["multiplier"] = crash_point

            users = load_users()
            for uid, player in game_state["players"].items():
                if not player.get("cashed_out"):
                    if uid in users:
                        users[uid]["total_lost"] = users[uid].get("total_lost", 0) + player["bet"]
                        users[uid]["games"] = users[uid].get("games", 0) + 1
                        save_users(users)

            game_state["history"].insert(0, {
                "mult": crash_point,
                "id": game_state["round_id"]
            })
            game_state["history"] = game_state["history"][:20]

        time.sleep(3)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/user", methods=["POST"])
def api_user():
    data = request.json
    user_id = data.get("user_id")
    username = data.get("username", "Player")
    if not user_id:
        return jsonify({"error": "no user_id"}), 400
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"username": username, "balance": 0, "total_won": 0, "total_lost": 0, "games": 0}
        save_users(users)
    return jsonify(users[uid])


@app.route("/api/deposit", methods=["POST"])
def api_deposit():
    data = request.json
    user_id = str(data.get("user_id"))
    amount = data.get("amount", 0)
    if not user_id or amount <= 0:
        return jsonify({"error": "bad request"}), 400
    users = load_users()
    if user_id not in users:
        return jsonify({"error": "user not found"}), 404
    users[user_id]["balance"] += amount
    save_users(users)
    return jsonify({"balance": users[user_id]["balance"]})


@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    data = request.json
    user_id = str(data.get("user_id"))
    amount = data.get("amount", 0)
    users = load_users()
    if user_id not in users or users[user_id]["balance"] < amount:
        return jsonify({"error": "insufficient"}), 400
    users[user_id]["balance"] -= amount
    save_users(users)
    return jsonify({"balance": users[user_id]["balance"]})


@app.route("/api/game/state", methods=["GET"])
def api_game_state():
    with lock:
        s = game_state.copy()
        players_list = []
        for uid, p in s["players"].items():
            users = load_users()
            name = users.get(uid, {}).get("username", "Player")
            profit = 0
            if p.get("cashed_out"):
                profit = round(p["bet"] * p.get("cashout_mult", 1), 1)
            players_list.append({
                "user_id": uid,
                "username": name,
                "bet": p["bet"],
                "cashout_mult": p.get("cashout_mult"),
                "cashed_out": p.get("cashed_out", False),
                "profit": profit,
            })
        players_list.sort(key=lambda x: x["bet"], reverse=True)
        return jsonify({
            "phase": s["phase"],
            "multiplier": s["multiplier"],
            "crash_point": s["crash_point"] if s["phase"] == "crashed" else None,
            "round_id": s["round_id"],
            "timer": s["timer"],
            "history": s["history"],
            "players": players_list,
        })


@app.route("/api/game/bet", methods=["POST"])
def api_game_bet():
    data = request.json
    user_id = str(data.get("user_id"))
    bet = data.get("bet", 0)
    auto_cashout = data.get("auto_cashout", 0)

    with lock:
        if game_state["phase"] != "betting":
            return jsonify({"error": "Not betting phase"}), 400

        users = load_users()
        if user_id not in users:
            return jsonify({"error": "user not found"}), 404
        if bet < 10 or bet > users[user_id]["balance"]:
            return jsonify({"error": "insufficient balance"}), 400
        if user_id in game_state["players"]:
            return jsonify({"error": "already bet"}), 400

        users[user_id]["balance"] -= bet
        save_users(users)

        game_state["players"][user_id] = {
            "bet": bet,
            "auto_cashout": auto_cashout,
            "cashed_out": False,
            "cashout_mult": None,
        }

        return jsonify({"balance": users[user_id]["balance"]})


@app.route("/api/game/cashout", methods=["POST"])
def api_game_cashout():
    data = request.json
    user_id = str(data.get("user_id"))

    with lock:
        if game_state["phase"] != "flying":
            return jsonify({"error": "not flying"}), 400
        if user_id not in game_state["players"]:
            return jsonify({"error": "no bet"}), 400
        if game_state["players"][user_id].get("cashed_out"):
            return jsonify({"error": "already cashed out"}), 400

        mult = game_state["multiplier"]
        game_state["players"][user_id]["cashed_out"] = True
        game_state["players"][user_id]["cashout_mult"] = mult

        bet = game_state["players"][user_id]["bet"]
        payout = round(bet * mult, 1)

        users = load_users()
        if user_id in users:
            users[user_id]["balance"] += payout
            users[user_id]["total_won"] = users[user_id].get("total_won", 0) + payout
            users[user_id]["games"] = users[user_id].get("games", 0) + 1
            save_users(users)

        return jsonify({"balance": users[user_id]["balance"], "payout": payout, "multiplier": mult})


@app.route("/health")
def health():
    return "ok"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if WEBAPP_URL:
        button = MenuButtonWebApp(text="\u2b50 Open Casino", web_app=WebAppInfo(url=WEBAPP_URL))
        await context.bot.set_chat_menu_button(chat_id=user.id, menu_button=button)
    await context.bot.set_my_commands([BotCommand("start", "Open Casino Stars")])
    await update.message.reply_text(
        f"\u2b50 Welcome, {user.first_name}!\n\nPress the menu button below to open casino."
    )


def run_bot():
    import traceback
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def main():
            application = Application.builder().token(BOT_TOKEN).build()
            application.add_handler(CommandHandler("start", start_command))
            await application.initialize()
            await application.start()
            print("Bot started!", flush=True)
            await application.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()

        loop.run_until_complete(main())
    except Exception as e:
        tb = traceback.format_exc()
        print(f"BOT ERROR: {e}\n{tb}", flush=True)
        with open("bot_error.log", "w") as f:
            f.write(tb)


if __name__ == "__main__":
    gt = threading.Thread(target=game_loop, daemon=True)
    gt.start()

    bt = threading.Thread(target=run_bot, daemon=True)
    bt.start()

    print(f"Game + Bot started. URL={WEBAPP_URL}", flush=True)
    time.sleep(1)
    app.run(host="0.0.0.0", port=PORT, debug=False)
