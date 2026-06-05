import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8980445619:AAEb8n0EouEBTqyzvjYTewhsCgkqWCo77UE"
ADMIN_GROUP_ID = -5116572321
SPONSOR_LINK = "https://t.me/patrickstarsrobot?start=6322254286"

# ===== БАЗА ДАННЫХ (в памяти, для постоянства нужна БД) =====
users = {}  # user_id: {stars, throws, referred_by, subscribed}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "stars": 0,
            "throws": 1,  # 1 бесплатный бросок при старте
            "subscribed": False,
            "referred_by": None,
            "username": ""
        }
    return users[user_id]

# ===== КЛАВИАТУРЫ =====
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏀 Бросок", callback_data="throw_6"),
         InlineKeyboardButton("🎁 Получить бросок", callback_data="get_throw")],
        [InlineKeyboardButton("🛒 Магазин бросков", callback_data="shop"),
         InlineKeyboardButton("💰 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("5 мячей 🏀🏀🏀🏀🏀", callback_data="throw_5"),
         InlineKeyboardButton("4 мяча 🏀🏀🏀🏀", callback_data="throw_4")],
        [InlineKeyboardButton("3 мяча 🏀🏀🏀", callback_data="throw_3")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])

def after_throw_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
         InlineKeyboardButton("🏀 Бросить ещё", callback_data="throw_6")],
        [InlineKeyboardButton("💰 Мой баланс", callback_data="balance")]
    ])

# ===== СТАРТ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["username"] = update.effective_user.username or str(user_id)

    # Реферал
    args = context.args
    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != user_id and user["referred_by"] is None:
            user["referred_by"] = ref_id
            ref_user = get_user(ref_id)
            ref_user["throws"] += 1
            try:
                await context.bot.send_message(
                    ref_id,
                    "🎉 Твой друг присоединился! Ты получил +1 бросок!"
                )
            except:
                pass

    if user["subscribed"]:
        await update.message.reply_text(
            "🏀 Добро пожаловать обратно!",
            reply_markup=main_menu_keyboard()
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на спонсора", url=SPONSOR_LINK)],
        [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]
    ])
    await update.message.reply_text(
        "👋 Привет!\n\nЧтобы продолжить, подпишись на нашего спонсора 👇",
        reply_markup=keyboard
    )

# ===== ПРОВЕРКА ПОДПИСКИ =====
async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    # В реальности тут можно проверить через API, пока просто доверяем
    user["subscribed"] = True
    await query.edit_message_text(
        "✅ Подписка подтверждена! Добро пожаловать!\n\nУ тебя есть 1 бесплатный бросок 🏀",
        reply_markup=main_menu_keyboard()
    )

# ===== ГЛАВНОЕ МЕНЮ =====
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    await query.edit_message_text(
        f"🏠 Главное меню\n⭐ Звёзды: {user['stars']} | 🏀 Броски: {user['throws']}",
        reply_markup=main_menu_keyboard()
    )

# ===== БРОСОК =====
async def throw_ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    data = query.data  # throw_6, throw_5, throw_4, throw_3
    count = int(data.split("_")[1])

    # Проверка стоимости
    costs = {6: 0, 5: 15, 4: 25, 3: 40}  # в звёздах
    cost = costs[count]

    if count == 6:
        if user["throws"] < 1:
            await query.edit_message_text(
                "❌ У тебя нет бросков!\n\nКупи в магазине или пригласи друга.",
                reply_markup=main_menu_keyboard()
            )
            return
        user["throws"] -= 1
    else:
        if user["stars"] < cost:
            await query.edit_message_text(
                f"❌ Недостаточно звёзд!\n\nНужно {cost}⭐, у тебя {user['stars']}⭐",
                reply_markup=main_menu_keyboard()
            )
            return
        user["stars"] -= cost

    # Анимация бросков
    balls = ["🏀"] * count
    await query.edit_message_text("🏀 Бросаю мячи...\n\n" + " ".join(balls))
    await asyncio.sleep(1.5)

    # Результаты
    results = [random.choice([True, False]) for _ in range(count)]
    result_text = ""
    for i, hit in enumerate(results):
        result_text += f"Мяч {i+1}: {'✅' if hit else '❌'}\n"

    all_hit = all(results)
    reward = 50

    if all_hit:
        user["stars"] += reward
        final_text = (
            f"{'🏀 ' * count}\n\n{result_text}\n"
            f"🎉 ВСЕ ПОПАЛИ! Ты получаешь {reward}⭐!"
        )
    else:
        hits = sum(results)
        final_text = (
            f"{'🏀 ' * count}\n\n{result_text}\n"
            f"😔 Не повезло! Попало {hits}/{count} мячей."
        )

    await query.edit_message_text(final_text, reply_markup=after_throw_keyboard())

# ===== ПОЛУЧИТЬ БРОСОК (реферал) =====
async def get_throw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    ref_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await query.edit_message_text(
        f"🎁 Пригласи друга и получи бросок!\n\n"
        f"Твоя ссылка:\n{ref_link}\n\n"
        f"Когда друг зайдёт по ней — ты получишь +1 бросок 🏀",
        reply_markup=back_keyboard()
    )

# ===== МАГАЗИН =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 бросок — 3⭐", callback_data="buy_1")],
        [InlineKeyboardButton("3 броска — 8⭐", callback_data="buy_3")],
        [InlineKeyboardButton("5 бросков — 13⭐", callback_data="buy_5")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])
    await query.edit_message_text(
        "🛒 Магазин бросков\n\nВыбери пакет:",
        reply_markup=keyboard
    )

async def buy_throws(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    data = query.data  # buy_1, buy_3, buy_5
    amount = int(data.split("_")[1])
    prices = {1: 3, 3: 8, 5: 13}
    cost = prices[amount]

    if user["stars"] < cost:
        await query.edit_message_text(
            f"❌ Недостаточно звёзд!\n\nНужно {cost}⭐, у тебя {user['stars']}⭐",
            reply_markup=back_keyboard()
        )
        return

    user["stars"] -= cost
    user["throws"] += amount
    await query.edit_message_text(
        f"✅ Куплено {amount} бросков за {cost}⭐!\n\n"
        f"Теперь у тебя {user['throws']} бросков и {user['stars']}⭐",
        reply_markup=main_menu_keyboard()
    )

# ===== БАЛАНС =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])
    await query.edit_message_text(
        f"💰 Твой баланс\n\n⭐ Звёзды: {user['stars']}\n🏀 Броски: {user['throws']}",
        reply_markup=keyboard
    )

# ===== ВЫВОД =====
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    stars = user["stars"]
    buttons = []
    for amount in [15, 25, 50, 100]:
        if stars >= amount:
            buttons.append(InlineKeyboardButton(f"{amount}✅", callback_data=f"wd_{amount}"))
        else:
            buttons.append(InlineKeyboardButton(f"{amount}❌", callback_data="no_stars"))

    keyboard = InlineKeyboardMarkup([buttons[:2], buttons[2:], 
                                     [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
    await query.edit_message_text(
        f"💸 Сколько хотите вывести?\n\nВаш баланс: {stars}⭐",
        reply_markup=keyboard
    )

async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)

    if query.data == "no_stars":
        await query.answer("❌ Недостаточно звёзд!", show_alert=True)
        return

    amount = int(query.data.split("_")[1])
    if user["stars"] < amount:
        await query.answer("❌ Недостаточно звёзд!", show_alert=True)
        return

    user["stars"] -= amount
    username = user.get("username") or str(user_id)

    # Отправка заявки в группу админа
    try:
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"💸 Заявка на вывод\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"⭐ Сумма: {amount} звёзд"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки в группу: {e}")

    await query.edit_message_text(
        f"✅ Заявка на вывод {amount}⭐ принята!\n\nЭто может занять некоторое время.",
        reply_markup=back_keyboard()
    )

# ===== ЗАПУСК =====
def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(throw_ball, pattern="^throw_"))
    app.add_handler(CallbackQueryHandler(get_throw, pattern="get_throw"))
    app.add_handler(CallbackQueryHandler(shop, pattern="shop"))
    app.add_handler(CallbackQueryHandler(buy_throws, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(process_withdraw, pattern="^wd_|no_stars"))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
