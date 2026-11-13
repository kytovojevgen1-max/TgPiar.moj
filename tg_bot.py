import os
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# ================= НАСТРОЙКИ БОТА =================
BOT_TOKEN = "9145730808:AAFE7XcNeJc1RWlYN51g7pPQ6ZJFlZnYOhE"
INITIAL_OWNER_ID = 8736945672  # Твой ID владельца
CLIENT_NAME = "nebula_tg_bot"
DATA_FILE = f"data_{CLIENT_NAME}.json"

DEFAULT_PIAR_TEXT = (
    "💎 NEBULA STUDIO — ЭКСКЛЮЗИВНЫЕ ПРОЕКТЫ И ПРЕМИУМ-СЛИВЫ ДЛЯ CRMP MOBILE\n\n"
    "Мы не делаем дёшево и наспех — мы создаём качественный фундамент для серьёзных проектов. 🚀\n\n"
    "👑 Что мы предлагаем:\n"
    "• 📱 Моды Mobile (Black Russia, Матрёшка РП)\n"
    "• 💻 ПК Сборки (Radmir RP 8.4)\n"
    "• 💬 Форумы XenForo под ключ\n"
    "• 🌐 Сайты и лендинги\n\n"
    "🔗 Telegram: https://t.me/NEBULASTUDIO"
)

DEFAULT_PRICE_TEXT = (
    "🛒 ПРАЙС-ЛИСТ И ТОВАРЫ:\n\n"
    "1️⃣ Моды Mobile (Black Russia / Матрёшка РП)\n"
    "2️⃣ ПК Сборки (Radmir RP 8.4)\n"
    "3️⃣ Форумы XenForo под ключ\n"
    "4️⃣ Сайты, лендинги и боты\n\n"
    "⚠️ Работаем строго по 100% предоплате!\n"
    "👇 Нажми «📩 Вызвать администратора», чтобы сделать заказ:"
)

DEFAULT_WELCOME_TEXT = "🌌 Добро пожаловать! Выбери нужный раздел в меню ниже:"
DEFAULT_HELPER_TEXT = "📘 ПРАВИЛА ПОКУПКИ:\n1️⃣ Выбери товар.\n2️⃣ Нажми «Вызвать администратора».\n3️⃣ Оплата строго 100% перед началом работы."

# ================= БАЗА ДАННЫХ =================
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "owner": INITIAL_OWNER_ID,
            "admins": [INITIAL_OWNER_ID],
            "piar_text": DEFAULT_PIAR_TEXT,
            "price_text": DEFAULT_PRICE_TEXT,
            "welcome_text": DEFAULT_WELCOME_TEXT,
            "helper_text": DEFAULT_HELPER_TEXT,
            "is_active": True,
            "users": [],
            "chats": []
        }
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if data.get("owner") != INITIAL_OWNER_ID:
            data["owner"] = INITIAL_OWNER_ID
        if INITIAL_OWNER_ID not in data["admins"]:
            data["admins"].append(INITIAL_OWNER_ID)
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# FSM Состояния для редактирования
class AdminStates(StatesGroup):
    edit_piar = State()
    edit_price = State()
    edit_welcome = State()
    edit_helper = State()
    broadcast = State()
    add_admin = State()
    remove_admin = State()
    transfer_owner = State()

# ================= КЛАВИАТУРЫ =================
def get_admin_keyboard(is_active: bool, is_owner: bool):
    status_text = "🔴 Остановить автопиар" if is_active else "🟢 Запустить автопиар"
    kb = [
        [KeyboardButton(text=status_text)],
        [KeyboardButton(text="✏️ Текст автопиара"), KeyboardButton(text="✏️ Изменить прайс-лист")],
        [KeyboardButton(text="✏️ Автоответ в ЛС"), KeyboardButton(text="✏️ Текст хелпера")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📢 Рассылка в ЛС")]
    ]
    if is_owner:
        kb.append([KeyboardButton(text="➕ Выдать админа"), KeyboardButton(text="➖ Снять админа")])
        kb.append([KeyboardButton(text="👑 Передать владельца"), KeyboardButton(text="👥 Список админов")])
    kb.append([KeyboardButton(text="🛒 Меню покупателя")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_user_keyboard(is_admin: bool):
    kb = [
        [KeyboardButton(text="🛒 Прайс-лист / Товары")],
        [KeyboardButton(text="❓ Как купить / Правила")],
        [KeyboardButton(text="📩 Вызвать администратора")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ================= ОСНОВНОЙ ЛОГИКА БОТА =================
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type != "private":
        # Если бота добавили в группу/чат
        db = load_data()
        if message.chat.id not in db["chats"]:
            db["chats"].append(message.chat.id)
            save_data(db)
        return

    db = load_data()
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"].append(user_id)
        save_data(db)

    is_admin = (user_id == db["owner"]) or (user_id in db["admins"])
    await message.answer(db["welcome_text"], reply_markup=get_user_keyboard(is_admin))

# Обработка текстовых кнопок в ЛС
@router.message(F.chat.type == "private")
async def handle_messages(message: Message, state: FSMContext):
    db = load_data()
    user_id = message.from_user.id
    text = message.text

    # Регистрация пользователя в базе
    if user_id not in db["users"]:
        db["users"].append(user_id)
        save_data(db)

    is_owner = (user_id == db["owner"])
    is_admin = is_owner or (user_id in db["admins"])

    # Проверка состояний FSM (ввод текста/админов)
    current_state = await state.get_state()
    if current_state and is_admin:
        if text.lower() == "отмена":
            await state.clear()
            await message.answer("❌ Действие отменено.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return

        if current_state == AdminStates.edit_piar.state:
            db["piar_text"] = text
            save_data(db)
            await state.clear()
            await message.answer("✅ Текст автопиара обновлён!", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif current_state == AdminStates.edit_price.state:
            db["price_text"] = text
            save_data(db)
            await state.clear()
            await message.answer("✅ Прайс-лист обновлён!", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif current_state == AdminStates.edit_welcome.state:
            db["welcome_text"] = text
            save_data(db)
            await state.clear()
            await message.answer("✅ Автоответ обновлён!", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif current_state == AdminStates.edit_helper.state:
            db["helper_text"] = text
            save_data(db)
            await state.clear()
            await message.answer("✅ Правила обновлены!", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif current_state == AdminStates.broadcast.state:
            count = 0
            for uid in db["users"]:
                try:
                    await message.bot.send_message(uid, text)
                    count += 1
                    await asyncio.sleep(0.1)
                except:
                    pass
            await state.clear()
            await message.answer(f"✅ Рассылка отправлена {count} пользователям.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif current_state == AdminStates.add_admin.state and is_owner:
            target_id = text.strip().replace("@", "")
            # Поддержка ввода ID или юзернейма
            try:
                tid = int(target_id)
            except ValueError:
                tid = target_id # Если ввели юзернейм (в Телеграме лучше передавать числовой ID)
            
            if tid not in db["admins"]:
                db["admins"].append(tid)
                save_data(db)
                await message.answer(f"✅ Администратор {tid} успешно добавлен!", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            else:
                await message.answer("❌ Пользователь уже в списке админов.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            await state.clear()
            return
        elif current_state == AdminStates.remove_admin.state and is_owner:
            try:
                tid = int(text.strip())
                if tid in db["admins"] and tid != db["owner"]:
                    db["admins"].remove(tid)
                    save_data(db)
                    await message.answer(f"✅ Администратор {tid} снят.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
                else:
                    await message.answer("❌ Нельзя снять владельца или неверный ID.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            except:
                await message.answer("❌ Ошибка. Введи числовой Telegram ID.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            await state.clear()
            return
        elif current_state == AdminStates.transfer_owner.state and is_owner:
            try:
                tid = int(text.strip())
                db["owner"] = tid
                if tid not in db["admins"]:
                    db["admins"].append(tid)
                save_data(db)
                new_owner = (user_id == tid)
                await message.answer(f"👑 Права владельца переданы пользователю ID: {tid}!", reply_markup=get_admin_keyboard(db["is_active"], new_owner))
            except:
                await message.answer("❌ Неверный ID.", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            await state.clear()
            return

    # Обработка обычных кнопок админ-панели
    if is_admin:
        if text in ["⚙️ Админ-панель", "админ", "меню"]:
            await message.answer(f"⚙️ ТЕЛЕГРАМ АДМИН-ПАНЕЛЬ\n\n💬 Чатов с пиаром: {len(db['chats'])}\n👥 Юзеров в ЛС: {len(db['users'])}\n⚡ Статус пиара: {'🟢 Вкл' if db['is_active'] else '🔴 Выкл'}", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif text == "🔴 Остановить автопиар":
            db["is_active"] = False
            save_data(db)
            await message.answer("🔴 Автопиар остановлен.", reply_markup=get_admin_keyboard(False, is_owner))
            return
        elif text == "🟢 Запустить автопиар":
            db["is_active"] = True
            save_data(db)
            await message.answer("🟢 Автопиар запущен!", reply_markup=get_admin_keyboard(True, is_owner))
            return
        elif text == "📊 Статистика":
            await message.answer(f"📊 Статистика:\n• Владелец ID: {db['owner']}\n• Чатов: {len(db['chats'])}\n• Юзеров в ЛС: {len(db['users'])}", reply_markup=get_admin_keyboard(db["is_active"], is_owner))
            return
        elif text == "✏️ Текст автопиара":
            await state.set_state(AdminStates.edit_piar)
            await message.answer("✍️ Отправь новый текст автопиара для групп (или 'Отмена'):")
            return
        elif text == "✏️ Изменить прайс-лист":
            await state.set_state(AdminStates.edit_price)
            await message.answer("✍️ Отправь новый прайс-лист для ЛС (или 'Отмена'):")
            return
        elif text == "✏️ Автоответ в ЛС":
            await state.set_state(AdminStates.edit_welcome)
            await message.answer("✍️ Отправь новый приветственный текст (или 'Отмена'):")
            return
        elif text == "✏️ Текст хелпера":
            await state.set_state(AdminStates.edit_helper)
            await message.answer("✍️ Отправь новые правила покупки (или 'Отмена'):")
            return
        elif text == "📢 Рассылка в ЛС":
            await state.set_state(AdminStates.broadcast)
            await message.answer("📣 Напиши текст для массовой рассылки (или 'Отмена'):")
            return
        elif text == "🛒 Меню покупателя":
            await message.answer(db["welcome_text"], reply_markup=get_user_keyboard(True))
            return
        
        if is_owner:
            if text == "➕ Выдать админа":
                await state.set_state(AdminStates.add_admin)
                await message.answer("👤 Отправь Telegram ID нового администратора (или 'Отмена'):")
                return
            elif text == "➖ Снять админа":
                await state.set_state(AdminStates.remove_admin)
                await message.answer("👤 Отправь Telegram ID админа для снятия (или 'Отмена'):")
                return
            elif text == "👑 Передать владельца":
                await state.set_state(AdminStates.transfer_owner)
                await message.answer("👑 ВНИМАНИЕ! Отправь Telegram ID нового ВЛАДЕЛЬЦА (или 'Отмена'):")
                return
            elif text == "👥 Список админов":
                lst = "\n".join([f"• ID: `{a}`" for a in db["admins"]])
                await message.answer(f"👑 Владелец ID: {db['owner']}\n\n🛡 Администраторы:\n{lst}", reply_markup=get_admin_keyboard(db["is_active"], is_owner), parse_mode="Markdown")
                return

    # Кнопки покупателя
    if text == "🛒 Прайс-лист / Товары":
        await message.answer(db["price_text"], reply_markup=get_user_keyboard(is_admin))
    elif text == "❓ Как купить / Правила":
        await message.answer(db["helper_text"], reply_markup=get_user_keyboard(is_admin))
    elif text == "📩 Вызвать администратора":
        await message.answer("📩 Запрос отправлен администраторам! Ожидайте ответа.\n⚠️ Работаем строго по 100% предоплате.", reply_markup=get_user_keyboard(is_admin))
        for aid in db["admins"]:
            try:
                username_info = f" (@{message.from_user.username})" if message.from_user.username else ""
                await message.bot.send_message(aid, f"🚨 ВЫЗОВ АДМИНА!\nПокупатель: tg://user?id={user_id}{username_info} (ID: {user_id})")
            except:
                pass
    else:
        await message.answer(db["welcome_text"], reply_markup=get_user_keyboard(is_admin))

# ================= ФОНОВЫЙ АВТОПИАР ДЛЯ ТГ =================
async def background_autopyar(bot: Bot):
    while True:
        await asyncio.sleep(30)
        try:
            db = load_data()
            if not db.get("is_active", True) or not db.get("chats"):
                continue
            
            active_chats = []
            for chat_id in db["chats"]:
                try:
                    await bot.send_message(chat_id, db["piar_text"])
                    active_chats.append(chat_id)
                    await asyncio.sleep(0.3)
                except Exception:
                    # Если бота кикнули из чата
                    pass
            
            if len(active_chats) != len(db["chats"]):
                db["chats"] = active_chats
                save_data(db)
        except Exception as e:
            logging.error(f"Ошибка автопиара: {e}")

# Веб-сервер для Render (чтобы хостинг не усыплял бота)
async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="Telegram Bot is running 24/7!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Запускаем веб-сервер для Render и фоновый автопиар параллельно с ботом
    asyncio.create_task(web_server())
    asyncio.create_task(background_autopyar(bot))

    print("🤖 Telegram бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
