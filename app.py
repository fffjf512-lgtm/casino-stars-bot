import os
import json
import random
import sys

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
PORT = int(os.environ.get("PORT", 5000))

CRASH_POINTS = [
    (1.0, 0.03), (1.1, 0.15), (1.2, 0.25), (1.5, 0.45),
    (1.8, 0.58), (2.0, 0.68), (2.5, 0.78), (3.0, 0.85),
    (5.0, 0.92), (10.0, 0.96), (20.0, 0.985), (50.0, 1.0),
]


def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_crash_point():
    roll = random.random()
    for mult, prob in CRASH_POINTS:
        if roll <= prob:
            return mult
    return CRASH_POINTS[-1][0]


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
        users[uid] = {"username": username, "balance": 100, "total_won": 0, "total_lost": 0, "games": 0}
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


@app.route("/api/rocket/start", methods=["POST"])
def api_rocket_start():
    data = request.json
    user_id = str(data.get("user_id"))
    bet = data.get("bet", 0)
    users = load_users()
    if user_id not in users:
        return jsonify({"error": "user not found"}), 404
    if bet <= 0 or bet > users[user_id]["balance"]:
        return jsonify({"error": "bad bet"}), 400
    users[user_id]["balance"] -= bet
    save_users(users)
    crash_point = get_crash_point()
    return jsonify({"crash_point": crash_point, "balance": users[user_id]["balance"]})


@app.route("/api/rocket/cashout", methods=["POST"])
def api_rocket_cashout():
    data = request.json
    user_id = str(data.get("user_id"))
    bet = data.get("bet", 0)
    multiplier = data.get("multiplier", 1.0)
    crashed = data.get("crashed", False)
    users = load_users()
    if user_id not in users:
        return jsonify({"error": "user not found"}), 404
    if crashed:
        users[user_id]["total_lost"] += bet
        users[user_id]["games"] += 1
        save_users(users)
        return jsonify({"balance": users[user_id]["balance"], "won": 0})
    payout = int(bet * multiplier)
    profit = payout - bet
    users[user_id]["balance"] += payout
    users[user_id]["total_won"] += payout
    users[user_id]["games"] += 1
    save_users(users)
    return jsonify({"balance": users[user_id]["balance"], "won": profit})


if __name__ == "__main__":
    if BOT_TOKEN:
        import threading
        import asyncio
        from telegram import Update, WebAppInfo, MenuButtonWebApp, BotCommand
        from telegram.ext import Application, CommandHandler, ContextTypes

        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if WEBAPP_URL:
                button = MenuButtonWebApp(text="Open Casino", web_app=WebAppInfo(url=WEBAPP_URL))
                await context.bot.set_chat_menu_button(chat_id=user.id, menu_button=button)
            await context.bot.set_my_commands([BotCommand("start", "Open Casino Stars")])
            await update.message.reply_text(
                f"Hi, {user.first_name}!\n\nPress the menu button below to open casino."
            )

        async def run_bot():
            app_bot = Application.builder().token(BOT_TOKEN).build()
            app_bot.add_handler(CommandHandler("start", start_command))
            await app_bot.initialize()
            await app_bot.start()
            await app_bot.updater.start_polling()
            print("Bot started polling!")
            await asyncio.Event().wait()

        def start_bot_thread():
            asyncio.run(run_bot())

        t = threading.Thread(target=start_bot_thread, daemon=True)
        t.start()
        print(f"Bot thread started, WEBAPP_URL={WEBAPP_URL}")

    app.run(host="0.0.0.0", port=PORT, debug=False)
