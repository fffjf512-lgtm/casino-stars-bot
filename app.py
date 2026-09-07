import os
import json
import random
import threading
import asyncio
import time

from flask import Flask, render_template, jsonify, request
from telegram import (
    Update, WebAppInfo, MenuButtonWebApp, BotCommand,
    LabeledPrice, PreCheckoutQuery, Message
)
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler

app = Flask(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8991377045:AAHt8HZ-1Ms6WDuxTSb18FkjXQEPR8uKoFc")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://casino-stars-bot.onrender.com")
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


@app.route("/health")
def health():
    return "ok"


@app.route("/logs")
def logs():
    if os.path.exists("bot_error.log"):
        with open("bot_error.log") as f:
            return f.read()
    return "no errors"


STAR_PACKS = {
    "5": 5, "10": 10, "25": 25, "50": 50,
    "100": 100, "250": 250, "500": 500, "1000": 1000,
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if WEBAPP_URL:
        button = MenuButtonWebApp(text="\u2b50 Open Casino", web_app=WebAppInfo(url=WEBAPP_URL))
        await context.bot.set_chat_menu_button(chat_id=user.id, menu_button=button)
    await context.bot.set_my_commands([
        BotCommand("start", "Open Casino Stars"),
        BotCommand("deposit", "Deposit Stars (5/10/25/50/100/250/500/1000)"),
    ])
    await update.message.reply_text(
        f"\u2b50 Welcome, {user.first_name}!\n\n"
        "Press the menu button below to open casino.\n"
        "Or use /deposit to buy stars."
    )


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("5 \u2b50", callback_data="buy_5"),
            InlineKeyboardButton("10 \u2b50", callback_data="buy_10"),
            InlineKeyboardButton("25 \u2b50", callback_data="buy_25"),
        ],
        [
            InlineKeyboardButton("50 \u2b50", callback_data="buy_50"),
            InlineKeyboardButton("100 \u2b50", callback_data="buy_100"),
            InlineKeyboardButton("250 \u2b50", callback_data="buy_250"),
        ],
        [
            InlineKeyboardButton("500 \u2b50", callback_data="buy_500"),
            InlineKeyboardButton("1000 \u2b50", callback_data="buy_1000"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "\u2b50 Choose amount of Stars to deposit:", reply_markup=reply_markup
    )


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    amount_str = query.data.replace("buy_", "")
    if amount_str not in STAR_PACKS:
        return

    amount = STAR_PACKS[amount_str]
    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=f"Deposit {amount} Stars",
        description=f"Add {amount} Stars to your casino balance",
        payload=f"deposit_{amount}_{query.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)],
    )


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload_parts = payment.invoice_payload.split("_")
    if len(payload_parts) >= 3 and payload_parts[0] == "deposit":
        amount = int(payload_parts[1])
        user_id = str(payload_parts[2])
        users = load_users()
        if user_id in users:
            users[user_id]["balance"] += amount
            save_users(users)
            await update.message.reply_text(
                f"\u2705 Successfully deposited {amount} \u2b50!\n"
                f"Balance: {users[user_id]['balance']} \u2b50"
            )


def run_bot():
    import traceback
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def main():
            application = Application.builder().token(BOT_TOKEN).build()
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(CommandHandler("deposit", deposit_command))
            application.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy_"))
            application.add_handler(PreCheckoutQueryHandler(pre_checkout))
            application.add_handler(
                MessageHandler(
                    telegram_ext_filters.SUCCESSFUL_PAYMENT, successful_payment
                )
            )
            await application.initialize()
            await application.start()
            print("Bot polling started!", flush=True)
            await application.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()

        loop.run_until_complete(main())
    except Exception as e:
        tb = traceback.format_exc()
        print(f"BOT ERROR: {e}\n{tb}", flush=True)
        with open("bot_error.log", "w") as f:
            f.write(tb)


if __name__ == "__main__":
    import telegram.ext.filters as telegram_ext_filters
    from telegram.ext import CallbackQueryHandler, MessageHandler

    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    print(f"Bot starting... WEBAPP_URL={WEBAPP_URL}", flush=True)
    time.sleep(1)
    app.run(host="0.0.0.0", port=PORT, debug=False)
