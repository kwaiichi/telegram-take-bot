import os
import logging
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

# Твой Telegram ID
MODERATOR_ID = 6708600693

# ID КФ пока можно оставить пустым.
# Позже добавим его в настройках хостинга.
CHAT_ID = os.environ.get("CHAT_ID", "")


# =========================================================
# ХЭШТЕГИ
# =========================================================

HASHTAGS = [
    "#резюме",
    "#вакансии",
    "#продажи",
    "#поиски",
    "#аукционы",
    "#арты",
    "#аккаунты",
    "#баннеры",
    "#сигны",
    "#нфт",
    "#адопты",
    "#эдиты",
    "#прокачки",
    "#игры",
    "#оформления",
    "#писательство",
    "#репетиторство",
    "#админство",
    "#учёба",
    "#одежда",
    "#рукоделие",
    "#пиар",
    "#бусты",
]


# =========================================================
# КЛЮЧЕВЫЕ СЛОВА ДЛЯ АВТОПОДБОРА
# =========================================================

TAG_WORDS = {
    "#резюме": [
        "резюме", "опыт работы", "ищу работу",
        "ищу подработку", "работал", "работала",
    ],

    "#вакансии": [
        "вакансия", "вакансии", "нанимаю",
        "требуется", "нужен сотрудник", "ищем сотрудника",
    ],

    "#продажи": [
        "продам", "продаю", "продажа", "продажи",
        "купить", "покупка", "цена", "отдам за",
    ],

    "#поиски": [
        "ищу", "нужен", "нужна", "нужны",
        "ищем", "поищу", "поиск", "разыскиваю",
    ],

    "#аукционы": [
        "аукцион", "аукционы", "ставка",
        "ставки", "кто больше", "аукук",
    ],

    "#арты": [
        "арт", "арты", "рисую", "рисование",
        "нарисую", "рисунок", "иллюстрация",
        "иллюстрации", "художник", "художники",
    ],

    "#аккаунты": [
        "аккаунт", "аккаунты", "учетка",
        "учётка", "профиль", "профили",
    ],

    "#баннеры": [
        "баннер", "баннеры", "шапка",
        "шапки", "реклама", "рекламный баннер",
    ],

    "#сигны": [
        "сигн", "сигны", "подпись",
        "подписи", "sign", "signs",
    ],

    "#нфт": [
        "nft", "нфт", "токен", "токены",
    ],

    "#адопты": [
        "адопт", "адопты", "adopt", "adopts",
        "персонаж на усыновление",
    ],

    "#эдиты": [
        "эдит", "эдиты", "edit", "edits",
        "монтаж", "монтажи", "видео монтаж",
    ],

    "#прокачки": [
        "прокачка", "прокачки", "прокачаю",
        "прокачать", "фарм", "фарма",
    ],

    "#игры": [
        "игра", "игры", "игровой",
        "игровые", "minecraft", "геншин",
        "genshin", "roblox",
    ],

    "#оформления": [
        "оформление", "оформления", "оформлю",
        "дизайн", "дизайны", "профильное оформление",
    ],

    "#писательство": [
        "писательство", "пишу", "напишу",
        "тексты", "текст", "статья",
        "статьи", "фанфик", "фанфики",
    ],

    "#репетиторство": [
        "репетитор", "репетиторство", "уроки",
        "занятия", "обучу", "обучение",
        "преподаю",
    ],

    "#админство": [
        "админ", "админы", "админство",
        "администратор", "администраторы",
        "модератор", "модераторы",
        "модерация",
    ],

    "#учёба": [
        "учёба", "учеба", "учусь",
        "домашка", "домашнее задание",
        "студент", "студенты",
    ],

    "#одежда": [
        "одежда", "одежду", "одежды",
        "футболка", "футболки", "худи",
        "худи", "штаны", "платье",
    ],

    "#рукоделие": [
        "рукоделие", "ручная работа",
        "сделаю руками", "вязание", "шитьё",
        "шитье", "вышивка", "лепка",
        "украшения ручной работы",
    ],

    "#пиар": [
        "пиар", "реклама", "рекламу",
        "продвижение", "продвину",
        "рекламировать", "раскрутка",
    ],

    "#бусты": [
        "буст", "бусты", "бустинг",
        "поднять уровень", "подниму уровень",
    ],
}


# =========================================================
# ВРЕМЕННОЕ ХРАНИЛИЩЕ ТЕЙКОВ
# =========================================================

takes = {}
take_counter = 0


# =========================================================
# ПОДБОР ХЭШТЕГОВ
# =========================================================

def suggest_hashtags(text):
    text_lower = text.lower()

    suggestions = []

    for tag, words in TAG_WORDS.items():
        for word in words:
            if word in text_lower:
                suggestions.append(tag)
                break

    # Если ничего подходящего не нашли,
    # предлагаем человеку выбрать самому.
    return suggestions


# =========================================================
# КЛАВИАТУРА ХЭШТЕГОВ
# =========================================================

def hashtag_keyboard(take_id):
    take = takes[take_id]
    selected = take["hashtags"]

    buttons = []
    row = []

    for tag in HASHTAGS:

        if tag in selected:
            text = f"☑️ {tag}"
        else:
            text = f"☐ {tag}"

        row.append(
            InlineKeyboardButton(
                text,
                callback_data=f"tag:{take_id}:{tag}"
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "✅ Готово",
            callback_data=f"done:{take_id}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================================================
# КНОПКИ ПРЕДПРОСМОТРА
# =========================================================

def preview_keyboard(take_id):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✏️ Изменить хэштеги",
                callback_data=f"edit:{take_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "📨 Отправить на модерацию",
                callback_data=f"send:{take_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Отменить",
                callback_data=f"cancel:{take_id}"
            )
        ]
    ])


# =========================================================
# ТЕКСТ ПРЕДПРОСМОТРА
# =========================================================

def make_preview(take_id):

    take = takes[take_id]

    text = html.escape(take["text"])
    hashtags = " ".join(take["hashtags"])

    if hashtags:
        return (
            "👀 <b>Предпросмотр тейка:</b>\n\n"
            f"{text}\n\n"
            f"{hashtags}"
        )

    return (
        "👀 <b>Предпросмотр тейка:</b>\n\n"
        f"{text}\n\n"
        "<i>Хэштеги не выбраны.</i>"
    )


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "Привет!\n\n"
        "Это бот для тейков. Сюда вы можете скинуть свой "
        "тейк, который сразу же рассмотрит модерация.\n\n"
        "Публикация осуществляется в течение 24 часов. "
        "Если прошло больше, пожалуйста, продублируйте тейк!\n\n"
        "Отправьте свой тейк следующим сообщением."
    )

    await update.message.reply_text(text)


# =========================================================
# ПОЛУЧЕНИЕ ТЕЙКА
# =========================================================

async def receive_take(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global take_counter

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if len(text) < 2:
        await update.message.reply_text(
            "Тейк слишком короткий 😭"
        )
        return

    if len(text) > 4000:
        await update.message.reply_text(
            "Тейк слишком длинный. Пожалуйста, сократите его "
            "до 4000 символов."
        )
        return

    take_counter += 1
    take_id = take_counter

    suggestions = suggest_hashtags(text)

    takes[take_id] = {
        "text": text,
        "hashtags": suggestions,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
    }

    if suggestions:
        message = (
            "Я подобрал несколько хэштегов автоматически.\n"
            "Вы можете убрать их или добавить другие:"
        )
    else:
        message = (
            "Выберите подходящие хэштеги для вашего тейка:"
        )

    await update.message.reply_text(
        message,
        reply_markup=hashtag_keyboard(take_id)
    )


# =========================================================
# ОБРАБОТКА INLINE-КНОПОК
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    data = query.data.split(":", 2)

    action = data[0]
    take_id = int(data[1])

    # Тейк уже удалён
    if take_id not in takes:
        await query.answer(
            "Этот тейк уже обработан.",
            show_alert=True
        )
        return

    take = takes[take_id]

    # =====================================================
    # ВЫБОР ХЭШТЕГА
    # =====================================================

    if action == "tag":

        # Выбирать хэштеги может только автор тейка
        if query.from_user.id != take["user_id"]:
            await query.answer(
                "Это не ваш тейк.",
                show_alert=True
            )
            return

        tag = data[2]

        if tag in take["hashtags"]:
            take["hashtags"].remove(tag)
        else:
            take["hashtags"].append(tag)

        await query.answer()

        await query.edit_message_reply_markup(
            reply_markup=hashtag_keyboard(take_id)
        )

        return

    # =====================================================
    # ГОТОВО
    # =====================================================

    if action == "done":

        if query.from_user.id != take["user_id"]:
            await query.answer(
                "Это не ваш тейк.",
                show_alert=True
            )
            return

        await query.answer()

        await query.edit_message_text(
            make_preview(take_id),
            parse_mode="HTML",
            reply_markup=preview_keyboard(take_id)
        )

        return

    # =====================================================
    # ИЗМЕНИТЬ ХЭШТЕГИ
    # =====================================================

    if action == "edit":

        if query.from_user.id != take["user_id"]:
            await query.answer(
                "Это не ваш тейк.",
                show_alert=True
            )
            return

        await query.answer()

        await query.edit_message_text(
            "Выберите подходящие хэштеги:",
            reply_markup=hashtag_keyboard(take_id)
        )

        return

    # =====================================================
    # ОТМЕНИТЬ
    # =====================================================

    if action == "cancel":

        if query.from_user.id != take["user_id"]:
            await query.answer(
                "Это не ваш тейк.",
                show_alert=True
            )
            return

        del takes[take_id]

        await query.answer()

        await query.edit_message_text(
            "❌ Тейк отменён."
        )

        return

    # =====================================================
    # ОТПРАВИТЬ МОДЕРАЦИИ
    # =====================================================

    if action == "send":

        if query.from_user.id != take["user_id"]:
            await query.answer(
                "Это не ваш тейк.",
                show_alert=True
            )
            return

        hashtags = " ".join(take["hashtags"])

        escaped_text = html.escape(take["text"])

        if hashtags:
            take_content = (
                f"{escaped_text}\n\n"
                f"{hashtags}"
            )
        else:
            take_content = escaped_text

        moderator_text = (
            f"📨 <b>Новый тейк #{take_id}</b>\n\n"
            f"{take_content}\n\n"
            f"👤 Автор: скрыт"
        )

        moderator_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ ОПУБЛИКОВАТЬ",
                    callback_data=f"approve:{take_id}"
                ),
                InlineKeyboardButton(
                    "❌ ОТКЛОНИТЬ",
                    callback_data=f"reject:{take_id}"
                )
            ]
        ])

        await context.bot.send_message(
            chat_id=MODERATOR_ID,
            text=moderator_text,
            parse_mode="HTML",
            reply_markup=moderator_keyboard
        )

        await query.answer()

        await query.edit_message_text(
            "📨 Тейк отправлен на модерацию!\n\n"
            "Если он пройдёт модерацию, его опубликуют "
            "в течение 24 часов."
        )

        return

    # =====================================================
    # ДАЛЬШЕ ТОЛЬКО МОДЕРАТОР
    # =====================================================

    if query.from_user.id != MODERATOR_ID:
        await query.answer(
            "У вас нет доступа к этой функции.",
            show_alert=True
        )
        return

    # =====================================================
    # ОПУБЛИКОВАТЬ
    # =====================================================

    if action == "approve":

        if not CHAT_ID:
            await query.answer(
                "CHAT_ID КФ ещё не настроен.",
                show_alert=True
            )
            return

        hashtags = " ".join(take["hashtags"])
        escaped_text = html.escape(take["text"])

        if hashtags:
            publication = (
                f"{escaped_text}\n\n"
                f"{hashtags}"
            )
        else:
            publication = escaped_text

        try:

            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=publication,
                parse_mode="HTML"
            )

            del takes[take_id]

            await query.answer("Опубликовано!")

            await query.edit_message_text(
                f"✅ <b>Тейк #{take_id} опубликован.</b>\n\n"
                f"{publication}",
                parse_mode="HTML"
            )

        except Exception as error:

            await query.answer(
                "Не удалось опубликовать.",
                show_alert=True
            )

            await query.message.reply_text(
                f"Ошибка публикации:\n{error}"
            )

        return

    # =====================================================
    # ОТКЛОНИТЬ
    # =====================================================

    if action == "reject":

        del takes[take_id]

        await query.answer("Отклонено.")

        await query.edit_message_text(
            f"❌ <b>Тейк #{take_id} отклонён.</b>",
            parse_mode="HTML"
        )

        return


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_take
        )
    )

    print("🤖 Бот запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
