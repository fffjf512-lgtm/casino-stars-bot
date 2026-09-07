import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import init_db, get_user, update_balance, add_transaction, update_stats, get_balance, get_leaderboard
from rocket_game import rocket_game, get_crash_point, calculate_payout
from config import BOT_TOKEN, MIN_BET, MAX_BET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_user(user.id, user.username)
    
    text = (
        f"🎰 Добро пожаловать в Casino Stars, {user.first_name}!\n\n"
        "💰 Баланс: используй /balance\n"
        "🚀 Ракета: /rocket [сумма]\n"
        "💳 Депозит: /deposit [сумма]\n"
        "💸 Вывод: /withdraw [сумма]\n"
        "📊 Статистика: /stats\n"
        "🏆 Таблица лидеров: /leaderboard\n\n"
        "Удачи! 🍀"
    )
    await update.message.reply_text(text)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    await update.message.reply_text(f"💰 Ваш баланс: {user['balance']} ⭐")


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /deposit [сумма]\nПример: /deposit 10")
        return
    
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Введите число!")
        return
    
    if amount < MIN_BET:
        await update.message.reply_text(f"Минимум: {MIN_BET} ⭐")
        return
    
    user_id = update.effective_user.id
    await update_balance(user_id, amount)
    await add_transaction(user_id, "deposit", amount)
    
    new_balance = await get_balance(user_id)
    await update.message.reply_text(
        f"✅ Депозит: +{amount} ⭐\n"
        f"💰 Баланс: {new_balance} ⭐"
    )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /withdraw [сумма]\nПример: /withdraw 10")
        return
    
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Введите число!")
        return
    
    user_id = update.effective_user.id
    balance = await get_balance(user_id)
    
    if amount > balance:
        await update.message.reply_text(f"Недостаточно средств! Баланс: {balance} ⭐")
        return
    
    await update_balance(user_id, -amount)
    await add_transaction(user_id, "withdraw", amount)
    
    new_balance = await get_balance(user_id)
    await update.message.reply_text(
        f"✅ Вывод: -{amount} ⭐\n"
        f"💰 Баланс: {new_balance} ⭐\n\n"
        f"⭐ Звёзды отправлены!"
    )


async def rocket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        keyboard = [
            [InlineKeyboardButton("5 ⭐", callback_data="rocket_5"),
             InlineKeyboardButton("10 ⭐", callback_data="rocket_10"),
             InlineKeyboardButton("25 ⭐", callback_data="rocket_25")],
            [InlineKeyboardButton("50 ⭐", callback_data="rocket_50"),
             InlineKeyboardButton("100 ⭐", callback_data="rocket_100")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚀 Выбери ставку для ракеты:",
            reply_markup=reply_markup
        )
        return
    
    try:
        bet = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Введите число!")
        return
    
    if bet < MIN_BET or bet > MAX_BET:
        await update.message.reply_text(f"Ставка от {MIN_BET} до {MAX_BET} ⭐")
        return
    
    balance = await get_balance(user_id)
    if bet > balance:
        await update.message.reply_text(f"Недостаточно! Баланс: {balance} ⭐")
        return
    
    await start_rocket_game(update, context, user_id, bet)


async def start_rocket_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet: int):
    await update_balance(user_id, -bet)
    await add_transaction(user_id, "rocket_bet", bet)
    
    game_id, crash_point = await rocket_game.start_game(user_id, bet)
    
    keyboard = [[InlineKeyboardButton("💰 Забрать 1.00x", callback_data=f"cashout_{game_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = await update.message.reply_text(
        f"🚀 Ракета запущена!\n"
        f"💵 Ставка: {bet} ⭐\n"
        f"📈 Множитель: 1.00x\n"
        f"💵 Выигрыш: {bet} ⭐\n\n"
        f"Жми 'Забрать' пока ракета летит!",
        reply_markup=reply_markup
    )
    
    steps = await rocket_game.fly(game_id)
    
    for i, mult in enumerate(steps):
        if rocket_game.get_game(game_id)["status"] != "flying":
            break
        
        win = calculate_payout(bet, mult)
        keyboard = [[InlineKeyboardButton(f"💰 Забрать {mult:.2f}x ({win} ⭐)", callback_data=f"cashout_{game_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await msg.edit_text(
                f"🚀 Ракета летит!\n"
                f"💵 Ставка: {bet} ⭐\n"
                f"📈 Множитель: {mult:.2f}x\n"
                f"💵 Выигрыш: {win} ⭐\n\n"
                f"Жми 'Забрать' пока ракета летит!",
                reply_markup=reply_markup
            )
        except Exception:
            pass
        
        await asyncio.sleep(0.5)
    
    game = rocket_game.get_game(game_id)
    if game["status"] == "flying":
        game["status"] = "crashed"
    
    if game["status"] == "crashed":
        await update_stats(user_id, 0, bet)
        await msg.edit_text(
            f"💥 Ракета взорвалась!\n"
            f"💵 Ставка: {bet} ⭐\n"
            f"📉 Крах на: {crash_point:.2f}x\n\n"
            f"Вы проиграли {bet} ⭐ 😔"
        )
    elif game["status"] == "cashed_out":
        payout = calculate_payout(bet, game["cashout_multiplier"])
        profit = payout - bet
        await update_balance(user_id, payout)
        await update_stats(user_id, profit, 0)
        await add_transaction(user_id, "rocket_win", payout)
        await msg.edit_text(
            f"🎉 Вы забрали выигрыш!\n"
            f"💵 Ставка: {bet} ⭐\n"
            f"📈 Множитель: {game['cashout_multiplier']:.2f}x\n"
            f"💰 Выигрыш: {payout} ⭐\n"
            f"💵 Профит: +{profit} ⭐"
        )
    
    rocket_game.remove_game(game_id)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("rocket_"):
        bet = int(data.split("_")[1])
        user_id = query.from_user.id
        
        balance = await get_balance(user_id)
        if bet > balance:
            await query.edit_message_text(f"Недостаточно! Баланс: {balance} ⭐")
            return
        
        class FakeMessage:
            def __init__(self, msg):
                self._msg = msg
                self.chat = type('obj', (object,), {'id': query.message.chat_id})()
                self.message_id = query.message.message_id
            
            async def reply_text(self, text, reply_markup=None):
                return await query.edit_message_text(text, reply_markup=reply_markup)
        
        fake_msg = FakeMessage(query.message)
        fake_update = type('obj', (object,), {'message': fake_msg, 'effective_user': query.from_user})()
        
        await start_rocket_game(fake_update, context, user_id, bet)
    
    elif data.startswith("cashout_"):
        game_id = data.split("_", 1)[1]
        user_id = query.from_user.id
        
        game = rocket_game.get_game(game_id)
        if not game or game["user_id"] != user_id:
            await query.answer("Это не ваша игра!", show_alert=True)
            return
        
        payout = rocket_game.cashout(game_id)
        if payout is None:
            await query.answer("Невозможно забрать!", show_alert=True)
            return
        
        await query.answer(f"Вы забрали {payout} ⭐!")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update.effective_user.id)
    profit = user['total_won'] - user['total_lost']
    
    text = (
        f"📊 Статистика {update.effective_user.first_name}\n\n"
        f"💰 Баланс: {user['balance']} ⭐\n"
        f"🎮 Игр сыграно: {user['games_played']}\n"
        f"📈 Выиграно: {user['total_won']} ⭐\n"
        f"📉 Проиграно: {user['total_lost']} ⭐\n"
        f"💵 Профит: {'+' if profit >= 0 else ''}{profit} ⭐"
    )
    await update.message.reply_text(text)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = await get_leaderboard()
    
    if not leaders:
        await update.message.reply_text("Пока нет игроков!")
        return
    
    text = "🏆 Таблица лидеров\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (username, balance) in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = username or "Аноним"
        text += f"{medal} {name}: {balance} ⭐\n"
    
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎰 Команды казино:\n\n"
        "/start - Начало\n"
        "/balance - Баланс\n"
        "/deposit [сумма] - Депозит\n"
        "/withdraw [сумма] - Вывод\n"
        "/rocket [сумма] - Игра Ракета\n"
        "/stats - Статистика\n"
        "/leaderboard - Лидеры\n"
        "/help - Помощь"
    )
    await update.message.reply_text(text)


async def post_init(application: Application):
    await init_db()
    print("DB initialized")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("rocket", rocket))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("Casino Stars Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
