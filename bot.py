import os
import logging
import html
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
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

# ID чата модерации.
# Добавим его в Railway Variables после получения через /id.
MODERATION_CHAT_ID = os.environ.get("MODERATION_CHAT_ID", "").strip()

# Максимум фотографий на один тейк
MAX_PHOTOS = 10

# Подпись
BOT_SIGNATURE = "| @uslujestvokfbot"


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
# КЛЮЧЕВЫЕ СЛОВА
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
        "штаны", "платье",
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
# ХРАНИЛИЩЕ
# =========================================================

takes = {}
active_takes = {}
take_counter = 0

# Для сбора Telegram-альбомов
album_buffers = {}
album_tasks = {}


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def suggest_hashtags(text):
    text_lower = text.lower()
    suggestions = []

    for tag, words in TAG_WORDS.items():
        for word in words:
            if word in text_lower:
                suggestions.append(tag)
                break

    return suggestions


def make_author_link(take):
    name = html.escape(take["full_name"])

    return (
        f'<a href="tg://user?id={take["user_id"]}">'
        f'{name}'
        f'</a>'
    )


def make_publication_text(take):
    text = html.escape(take["text"].strip())
    hashtags = " ".join(take["hashtags"])

    parts = []

    if text:
        parts.append(text)

    # ВАЖНО:
    # подпись находится СРАЗУ ПОСЛЕ хэштегов
    if hashtags:
        parts.append(
            f"{hashtags} {html.escape(BOT_SIGNATURE)}"
        )
    else:
        parts.append(
            html.escape(BOT_SIGNATURE)
        )

    # Автор тоже будет виден в тейке
    parts.append(
        f"👤 Автор: {make_author_link(take)}"
    )

    return "\n\n".join(parts)


def make_take_id():
    global take_counter

    take_counter += 1
    return take_counter


def get_take(take_id):
    return takes.get(take_id)


def create_take(update, text="", photos=None):
    user = update.effective_user

    if photos is None:
        photos = []

    take_id = make_take_id()

    takes[take_id] = {
        "text": text.strip(),
        "hashtags": suggest_hashtags(text),
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "photos": photos[:MAX_PHOTOS],
        "state": "draft",
        "status": "draft",
    }

    active_takes[user.id] = take_id

    return take_id


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def photo_choice_keyboard(take_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📷 Добавить картинки",
                callback_data=f"addphotos:{take_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "➡️ Без картинок",
                callback_data=f"nophotos:{take_id}"
            )
        ]
    ])


def photo_actions_keyboard(take_id):
    take = get_take(take_id)

    buttons = []

    if take and len(take["photos"]) < MAX_PHOTOS:
        buttons.append([
            InlineKeyboardButton(
                "📷 Добавить ещё",
                callback_data=f"addmore:{take_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✏️ Добавить текст",
            callback_data=f"addtext:{take_id}"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "➡️ Без текста",
            callback_data=f"notext:{take_id}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def waiting_photos_keyboard(take_id):
    take = get_take(take_id)

    buttons = []

    if len(take["photos"]) < MAX_PHOTOS:
        buttons.append([
            InlineKeyboardButton(
                "📷 Добавить ещё",
                callback_data=f"addmore:{take_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ Готово",
            callback_data=f"photosdone:{take_id}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def hashtag_keyboard(take_id):
    take = get_take(take_id)

    if not take:
        return InlineKeyboardMarkup([])

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

    if len(take["photos"]) < MAX_PHOTOS:
        buttons.append([
            InlineKeyboardButton(
                "📷 Добавить фото",
                callback_data=f"addmore:{take_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ Готово",
            callback_data=f"done:{take_id}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


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
                "📷 Добавить фото",
                callback_data=f"addmore:{take_id}"
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


def moderation_keyboard(take_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ОДОБРИТЬ",
                callback_data=f"approve:{take_id}"
            ),
            InlineKeyboardButton(
                "❌ ОТКЛОНИТЬ",
                callback_data=f"reject:{take_id}"
            )
        ]
    ])


# =========================================================
# ПРЕДПРОСМОТР
# =========================================================

def make_preview(take_id):
    take = get_take(take_id)

    publication = make_publication_text(take)

    photo_count = len(take["photos"])

    return (
        "👀 <b>Предпросмотр тейка</b>\n\n"
        f"{publication}\n\n"
        f"📎 Фотографий: {photo_count}/{MAX_PHOTOS}"
    )


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "Привет!\n\n"
        "Отправь мне свой тейк текстом или "
        "фотографии с подписью.\n\n"
        "Можно добавить до 10 фотографий.\n"
        "После этого бот предложит хэштеги "
        "и отправит готовый тейк на модерацию."
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    take_id = active_takes.get(user_id)

    if take_id:
        takes.pop(take_id, None)
        active_takes.pop(user_id, None)

        await update.message.reply_text(
            "Текущий тейк отменён."
        )
    else:
        await update.message.reply_text(
            "У тебя сейчас нет активного тейка."
        )


# =========================================================
# ID ЧАТА
# =========================================================

async def chat_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat

    await update.effective_message.reply_text(
        f"ID этого чата:\n`{chat.id}`\n\n"
        f"Тип: `{chat.type}`",
        parse_mode="Markdown"
    )


# =========================================================
# ТЕКСТ
# =========================================================

async def receive_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    # Тейки принимаем только в личке с ботом.
    # Иначе сообщения модераторов в группе будут
    # случайно восприниматься как тейки.
    if update.effective_chat.type != "private":
        return

    text = update.message.text.strip()

    if len(text) < 2:
        await update.message.reply_text(
            "Тейк слишком короткий 😭"
        )
        return

    if len(text) > 4000:
        await update.message.reply_text(
            "Тейк слишком длинный. Максимум 4000 символов."
        )
        return

    user_id = update.effective_user.id
    active_id = active_takes.get(user_id)

    # Если бот уже ждёт текст для фото
    if active_id:
        take = get_take(active_id)

        if take and take["state"] == "waiting_text":
            take["text"] = text
            take["hashtags"] = suggest_hashtags(text)
            take["state"] = "hashtags"

            await update.message.reply_text(
                "Отлично! Теперь выбери хэштеги:",
                reply_markup=hashtag_keyboard(active_id)
            )
            return

        # Если уже есть активный незавершённый тейк
        if take and take["state"] not in (
            "submitted",
            "approved",
            "rejected",
        ):
            await update.message.reply_text(
                "У тебя уже есть незавершённый тейк 😭\n"
                "Закончи его или используй /cancel."
            )
            return

    take_id = create_take(
        update,
        text=text,
        photos=[]
    )

    await update.message.reply_text(
        "Хотите добавить картинку?",
        reply_markup=photo_choice_keyboard(take_id)
    )


# =========================================================
# ОБРАБОТКА ФОТО
# =========================================================

async def receive_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.photo:
        return

    if update.effective_chat.type != "private":
        return

    message = update.message
    user_id = update.effective_user.id

    # Telegram отправляет альбом как несколько отдельных сообщений
    # с одинаковым media_group_id.
    if message.media_group_id:

        key = (user_id, message.media_group_id)

        if key not in album_buffers:
            album_buffers[key] = []

        album_buffers[key].append(message)

        # Перезапускаем таймер сбора альбома
        old_task = album_tasks.get(key)

        if old_task:
            old_task.cancel()

        album_tasks[key] = asyncio.create_task(
            process_album_after_delay(
                key,
                context
            )
        )

        return

    # Одиночное фото
    await process_photo_batch(
        [message],
        context
    )


async def process_album_after_delay(
    key,
    context
):

    try:
        # Ждём, пока Telegram пришлёт остальные фотографии альбома.
        await asyncio.sleep(1.2)

        messages = album_buffers.pop(key, [])

        album_tasks.pop(key, None)

        if messages:
            messages.sort(key=lambda x: x.message_id)

            await process_photo_batch(
                messages,
                context
            )

    except asyncio.CancelledError:
        return


async def process_photo_batch(
    messages,
    context
):

    if not messages:
        return

    first_message = messages[0]
    user = first_message.from_user
    user_id = user.id

    # Собираем file_id фотографий
    photos = []

    for message in messages:
        if not message.photo:
            continue

        photos.append(
            message.photo[-1].file_id
        )

    # Берём подпись из первого сообщения альбома,
    # где она есть.
    caption = ""

    for message in messages:
        if message.caption:
            caption = message.caption.strip()
            break

    if len(caption) > 4000:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "Подпись слишком длинная. "
                "Максимум 4000 символов."
            )
        )
        return

    active_id = active_takes.get(user_id)
    take = get_take(active_id) if active_id else None

    # -----------------------------------------------------
    # НЕТ АКТИВНОГО ТЕЙКА
    # -----------------------------------------------------

    if not take:

        photos = photos[:MAX_PHOTOS]

        take_id = create_take(
            first_message,
            text=caption,
            photos=photos
        )

        take = get_take(take_id)

        # Фото + подпись -> сразу хэштеги
        if caption:
            take["state"] = "hashtags"

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Получил {len(photos)} "
                    f"фото.\n\n"
                    "Я автоматически подобрал хэштеги. "
                    "Можешь изменить их:"
                ),
                reply_markup=hashtag_keyboard(take_id)
            )

        # Только фото -> спрашиваем про текст
        else:
            take["state"] = "waiting_text_choice"

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Получил {len(photos)} "
                    f"фото.\n\n"
                    "Хотите добавить текст к тейку?"
                ),
                reply_markup=photo_actions_keyboard(take_id)
            )

        return

    # -----------------------------------------------------
    # ЕСТЬ АКТИВНЫЙ ТЕЙК
    # -----------------------------------------------------

    # Добавляем фотографии к существующему тейку
    current_count = len(take["photos"])
    available = MAX_PHOTOS - current_count

    if available <= 0:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ У тебя уже максимальные 10 фотографий."
        )
        return

    photos_to_add = photos[:available]

    take["photos"].extend(photos_to_add)

    # Если фотографий оказалось больше лимита
    if len(photos) > available:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Максимум 10 фотографий. Лишние фото не добавлены."
        )

    # Если подпись пришла вместе с фото и текста ещё нет,
    # используем её как текст.
    if caption and not take["text"]:
        take["text"] = caption
        take["hashtags"] = suggest_hashtags(caption)

    # Если ждём фотографии после текстового тейка
    if take["state"] in (
        "waiting_photos",
        "waiting_photo_choice",
        "waiting_text_choice",
        "draft",
    ):

        # Если уже есть текст -> просто продолжаем с фото
        if take["text"]:
            take["state"] = "waiting_photos"

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Добавлено фотографий: "
                    f"{len(take['photos'])}/{MAX_PHOTOS}\n\n"
                    "Когда закончишь, нажми «Готово»."
                ),
                reply_markup=waiting_photos_keyboard(active_id)
            )

        else:
            take["state"] = "waiting_text_choice"

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Добавлено фотографий: "
                    f"{len(take['photos'])}/{MAX_PHOTOS}\n\n"
                    "Хотите добавить текст?"
                ),
                reply_markup=photo_actions_keyboard(active_id)
            )

        return

    # Если пользователь добавляет фото уже на этапе хэштегов
    if take["state"] == "hashtags":

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"Добавлено фотографий: "
                f"{len(take['photos'])}/{MAX_PHOTOS}\n\n"
                "Хэштеги остаются прежними:"
            ),
            reply_markup=hashtag_keyboard(active_id)
        )

        return

    # Если добавляем фото из предпросмотра
    if take["state"] == "preview":

        await context.bot.send_message(
            chat_id=user_id,
            text=make_preview(active_id),
            parse_mode="HTML",
            reply_markup=preview_keyboard(active_id)
        )


# =========================================================
# CALLBACKS
# =========================================================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    try:
        action, take_id_str, *extra = data.split(":")
        take_id = int(take_id_str)
    except (ValueError, AttributeError):
        return

    take = get_take(take_id)

    if not take:
        await query.edit_message_text(
            "Этот тейк больше не существует."
        )
        return

    user_id = query.from_user.id

    # =====================================================
    # ДЕЙСТВИЯ АВТОРА
    # =====================================================

    if action not in ("approve", "reject"):

        if take["user_id"] != user_id:
            await query.answer(
                "Это не твой тейк.",
                show_alert=True
            )
            return

    # -----------------------------------------------------
    # ДОБАВИТЬ ФОТО
    # -----------------------------------------------------

    if action in ("addphotos", "addmore"):

        if len(take["photos"]) >= MAX_PHOTOS:
            await query.answer(
                "Уже добавлено 10 фотографий.",
                show_alert=True
            )
            return

        take["state"] = "waiting_photos"

        await query.edit_message_text(
            (
                f"Отправь фотографии.\n\n"
                f"Сейчас: {len(take['photos'])}/{MAX_PHOTOS}\n"
                "Можно отправить альбомом."
            ),
            reply_markup=waiting_photos_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # БЕЗ ФОТО
    # -----------------------------------------------------

    if action == "nophotos":

        take["state"] = "hashtags"

        await query.edit_message_text(
            "Хорошо. Теперь выбери хэштеги:",
            reply_markup=hashtag_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ДОБАВИТЬ ТЕКСТ
    # -----------------------------------------------------

    if action == "addtext":

        take["state"] = "waiting_text"

        await query.edit_message_text(
            "Напиши текст для тейка:"
        )
        return

    # -----------------------------------------------------
    # БЕЗ ТЕКСТА
    # -----------------------------------------------------

    if action == "notext":

        take["text"] = ""
        take["hashtags"] = []
        take["state"] = "hashtags"

        await query.edit_message_text(
            "Хорошо. Теперь выбери хэштеги:",
            reply_markup=hashtag_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ГОТОВО С ФОТО
    # -----------------------------------------------------

    if action == "photosdone":

        if not take["photos"]:
            await query.answer(
                "Добавь хотя бы одну фотографию.",
                show_alert=True
            )
            return

        take["state"] = "hashtags"

        await query.edit_message_text(
            "Теперь выбери хэштеги:",
            reply_markup=hashtag_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ХЭШТЕГ
    # -----------------------------------------------------

    if action == "tag":

        if not extra:
            return

        tag = extra[0]

        if tag in take["hashtags"]:
            take["hashtags"].remove(tag)
        else:
            take["hashtags"].append(tag)

        await query.edit_message_reply_markup(
            reply_markup=hashtag_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ГОТОВО С ХЭШТЕГАМИ
    # -----------------------------------------------------

    if action == "done":

        take["state"] = "preview"

        await query.edit_message_text(
            make_preview(take_id),
            parse_mode="HTML",
            reply_markup=preview_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ИЗМЕНИТЬ ХЭШТЕГИ
    # -----------------------------------------------------

    if action == "edit":

        take["state"] = "hashtags"

        await query.edit_message_text(
            "Измени хэштеги:",
            reply_markup=hashtag_keyboard(take_id)
        )
        return

    # -----------------------------------------------------
    # ОТМЕНИТЬ
    # -----------------------------------------------------

    if action == "cancel":

        takes.pop(take_id, None)

        if active_takes.get(user_id) == take_id:
            active_takes.pop(user_id, None)

        await query.edit_message_text(
            "Тейк отменён."
        )
        return

    # =====================================================
    # ОТПРАВКА НА МОДЕРАЦИЮ
    # =====================================================

    if action == "send":

        if not MODERATION_CHAT_ID:
            await query.answer(
                "MODERATION_CHAT_ID ещё не настроен.",
                show_alert=True
            )
            return

        take["state"] = "submitted"
        take["status"] = "pending"

        publication = make_publication_text(take)

        moderation_text = (
            "📨 <b>НОВЫЙ ТЕЙК</b>\n\n"
            f"{publication}\n\n"
            f"📎 Фотографий: {len(take['photos'])}/{MAX_PHOTOS}"
        )

        try:

            # Отправляем фотографии в чат модерации
            if take["photos"]:

                if len(take["photos"]) == 1:

                    await context.bot.send_photo(
                        chat_id=MODERATION_CHAT_ID,
                        photo=take["photos"][0]
                    )

                else:

                    media = [
                        InputMediaPhoto(
                            media=photo_id
                        )
                        for photo_id in take["photos"]
                    ]

                    await context.bot.send_media_group(
                        chat_id=MODERATION_CHAT_ID,
                        media=media
                    )

            # Отдельным сообщением отправляем текст
            # и кнопки модерации.
            await context.bot.send_message(
                chat_id=MODERATION_CHAT_ID,
                text=moderation_text,
                parse_mode="HTML",
                reply_markup=moderation_keyboard(take_id)
            )

            active_takes.pop(user_id, None)

            await query.edit_message_text(
                "✅ Тейк отправлен на модерацию!\n\n"
                "Теперь дождись решения модераторов."
            )

        except Exception as e:

            logging.exception(
                "Ошибка отправки в чат модерации"
            )

            take["state"] = "preview"
            take["status"] = "draft"

            await query.answer(
                "Не получилось отправить тейк в чат модерации.",
                show_alert=True
            )

        return

    # =====================================================
    # ПРОВЕРКА МОДЕРАТОРА
    # =====================================================

    if action in ("approve", "reject"):

        if not MODERATION_CHAT_ID:
            await query.answer(
                "MODERATION_CHAT_ID не настроен.",
                show_alert=True
            )
            return

        # Проверяем, является ли человек администратором
        # чата модерации.
        try:

            member = await context.bot.get_chat_member(
                chat_id=MODERATION_CHAT_ID,
                user_id=user_id
            )

            if member.status not in (
                "administrator",
                "creator",
            ):
                await query.answer(
                    "Только администраторы могут модерировать тейки.",
                    show_alert=True
                )
                return

        except Exception:

            await query.answer(
                "Не удалось проверить права модератора.",
                show_alert=True
            )
            return

        # -------------------------------------------------
        # ОДОБРЕНИЕ
        # -------------------------------------------------

        if action == "approve":

            take["status"] = "approved"
            take["state"] = "approved"

            publication = make_publication_text(take)

            await query.edit_message_text(
                "✅ <b>ОДОБРЕНО</b>\n\n"
                f"{publication}\n\n"
                "Можно вручную публиковать в канале.",
                parse_mode="HTML"
            )

            return

        # -------------------------------------------------
        # ОТКЛОНЕНИЕ
        # -------------------------------------------------

        if action == "reject":

            take["status"] = "rejected"
            take["state"] = "rejected"

            publication = make_publication_text(take)

            await query.edit_message_text(
                "❌ <b>ОТКЛОНЕНО</b>\n\n"
                f"{publication}",
                parse_mode="HTML"
            )

            return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logging.exception(
        "Ошибка во время обработки обновления:",
        exc_info=context.error
    )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("cancel", cancel_command)
    )

    # Команда для получения ID любого чата
    app.add_handler(
        CommandHandler("id", chat_id)
    )

    # Текст
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_text
        )
    )

    # Фотографии
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_photo
        )
    )

    # Кнопки
    app.add_handler(
        CallbackQueryHandler(callbacks)
    )

    # Ошибки
    app.add_error_handler(error_handler)

    print("🤖 Бот запущен!")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
