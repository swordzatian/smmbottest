import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional
import random

# Импорт для работы с токеном из .env файла
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHOOSING_NICHE, ENTERING_TOPIC, REVIEWING, EDITING = range(4)

class SMMBot:
    def __init__(self):
        self.pending_posts = {}  # user_id: post_data
        
    async def generate_image_url(self, keywords: list, niche: str) -> str:
        """Получаем красивое фото (имитация)"""
        demo_images = {
            "автомобили": [
                "https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2",
                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738",
                "https://images.unsplash.com/photo-1549399542-7e3f8b79c341"
            ],
            "недвижимость": [
                "https://images.unsplash.com/photo-1512917774080-9991f1c4c750",
                "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9",
                "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c"
            ]
        }
        
        images = demo_images.get(niche, demo_images["автомобили"])
        # Выбираем случайное фото
        return random.choice(images)
        
    def generate_post_text(self, topic: str, platform: str, niche: str) -> str:
        """Генерация текста для поста (имитация)"""
        
        if niche == "автомобили":
            templates = {
                "tiktok": f"🔥 {topic}\n\nЭто просто космос! Смотри возможности 🚀\n\n#авто #новинки #cars",
                "telegram": f"🚗 {topic}\n\nНовое поколение автомобилей впечатляет!\n\n🔹 Инновационные технологии\n🔹 Премиум комфорт\n🔹 Невероятная мощность\n\n💬 Ваше мнение?",
                "instagram": f"✨ {topic} ✨\n\nКогда стиль встречается с технологиями 🔥\n\nСохрани! 📌\n\n#авто #cars #luxury #новинки #автоновости",
                "vk": f"🚘 {topic}\n\nНовинка, которая меняет правила игры!\n\n👍 Лайк, если впечатлён!\n💬 Твоя машина мечты?"
            }
        else:  # недвижимость
            templates = {
                "tiktok": f"✨ {topic}\n\nМечта или реальность? 🏠 Листай!\n\n#недвижимость #дом #квартира",
                "telegram": f"🏡 {topic}\n\nНовый объект в портфолио! Это стиль жизни.\n\n✅ Премиум локация\n✅ Продуманная планировка\n✅ Инфраструктура рядом\n\n📞 Подробности в директе!",
                "instagram": f"🏠 {topic}\n\nДом вашей мечты существует 💫\n\nВсё что нужно - в карусели ➡️\n\n#недвижимость #дом #realestate #квартира #новостройка",
                "vk": f"🏡 {topic}\n\nЭта недвижимость заслуживает внимания!\n\n❤️ Нравится? Сохраняй!\n💭 Какой район предпочитаешь?"
            }
        
        return templates.get(platform, f"📢 {topic}")
        
    def format_post_preview(self, post_data: Dict) -> str:
        """Красивый превью поста"""
        text = f"📋 <b>ПРЕВЬЮ ПОСТА</b>\n\n"
        text += f"🎯 <b>Тема:</b> {post_data['topic']}\n"
        text += f"📂 <b>Ниша:</b> {post_data['niche'].capitalize()}\n"
        text += f"🖼 <b>Фото:</b> ✅ Готово\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        icons = {"tiktok": "🎵", "telegram": "✈️", "instagram": "📸", "vk": "🌐"}
        
        for platform, content in post_data['platforms'].items():
            icon = icons.get(platform, "📱")
            text += f"{icon} <b>{platform.upper()}</b>\n"
            text += f"{content['text']}\n\n"
        
        return text

# Инициализация бота
smm_bot = SMMBot()

# ========== КОМАНДЫ БОТА ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🚀 Создать пост", callback_data="create_post")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
👋 <b>Привет, {user.first_name}!</b>

🤖 Я бот для автоматизации SMM
Помогу создать посты для всех соцсетей за секунды!

<b>Что умею:</b>
✅ Генерирую контент для 4 платформ
✅ Подбираю фото по теме
✅ Адаптирую под каждую соцсеть
✅ Автоматизирую публикацию

<b>Тематики:</b>
🚗 Автомобили
🏡 Недвижимость

Нажми "Создать пост" чтобы начать! 👇
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return CHOOSING_NICHE

async def choose_niche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор ниши"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🚗 Автомобили", callback_data="niche_auto")],
        [InlineKeyboardButton("🏡 Недвижимость", callback_data="niche_realestate")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
<b>📂 Выберите тематику контента:</b>

🚗 <b>Автомобили</b>
    Премиум авто, новинки, тест-драйвы

🏡 <b>Недвижимость</b>
    Элитное жильё, новостройки, инвестиции

Выберите нишу для создания поста:
    """
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return ENTERING_TOPIC

async def handle_niche_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора ниши"""
    query = update.callback_query
    await query.answer()
    
    niche_map = {
        "niche_auto": "автомобили",
        "niche_realestate": "недвижимость"
    }
    
    niche = niche_map.get(query.data)
    context.user_data['niche'] = niche
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="create_post")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    examples = {
        "автомобили": "Например:\n• BMW X5 2025: новая эра комфорта\n• Tesla Model Y для семьи\n• Электрокары будущего",
        "недвижимость": "Например:\n• Пентхаус с панорамным видом\n• Квартира у моря в Сочи\n• Таунхаус в закрытом поселке"
    }
    
    text = f"""
<b>✍️ Введите тему поста</b>

<b>Выбрана ниша:</b> {niche.capitalize()} ✅

{examples[niche]}

<i>Напишите тему своего поста:</i>
    """
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return ENTERING_TOPIC

async def handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка темы и генерация контента"""
    topic = update.message.text
    niche = context.user_data.get('niche', 'автомобили')
    
    # Показываем процесс генерации
    status_msg = await update.message.reply_text(
        "⏳ <b>Генерирую контент...</b>\n\n"
        "🤖 AI создаёт тексты для всех платформ...",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(1.5)
    
    # Генерируем контент
    platforms = ["tiktok", "telegram", "instagram", "vk"]
    generated_content = {}
    
    for platform in platforms:
        text = smm_bot.generate_post_text(topic, platform, niche)
        generated_content[platform] = {"text": text}
    
    # Получаем фото
    keywords = ["luxury", "car"] if niche == "автомобили" else ["house", "apartment"]
    image_url = await smm_bot.generate_image_url(keywords, niche)
    
    # Сохраняем пост
    post_data = {
        "id": f"post_{int(datetime.now().timestamp())}",
        "topic": topic,
        "niche": niche,
        "platforms": generated_content,
        "image_url": image_url,
        "status": "draft"
    }
    
    user_id = update.effective_user.id
    smm_bot.pending_posts[user_id] = post_data
    
    await status_msg.edit_text(
        "✅ <b>Контент готов!</b>\n\n"
        "📸 Фото подобрано\n"
        "📝 Тексты сгенерированы для 4 платформ",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(1)
    
    # Показываем превью
    preview_text = smm_bot.format_post_preview(post_data)
    
    keyboard = [
        [InlineKeyboardButton("✅ Одобрить и опубликовать", callback_data="approve")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("🖼 Показать фото", callback_data="show_image")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        preview_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return REVIEWING

async def show_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать фото поста"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    post_data = smm_bot.pending_posts.get(user_id)
    
    if not post_data:
        await query.edit_message_text("❌ Пост не найден. Создайте новый.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к посту", callback_data="back_to_review")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_photo(
        photo=post_data['image_url'],
        caption=f"🖼 <b>Фото для поста:</b>\n{post_data['topic']}",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return REVIEWING

async def back_to_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к превью"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    post_data = smm_bot.pending_posts.get(user_id)
    
    if query.message.text:
         # Если сообщение - это превью, просто его редактируем
        edit_func = query.edit_message_text
    else:
        # Если это ответ на фото, нужно отправить новое сообщение
        edit_func = query.message.reply_text
        
    preview_text = smm_bot.format_post_preview(post_data)
    
    keyboard = [
        [InlineKeyboardButton("✅ Одобрить и опубликовать", callback_data="approve")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("🖼 Показать фото", callback_data="show_image")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_func(
        preview_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return REVIEWING

async def edit_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование поста"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎵 TikTok", callback_data="edit_tiktok")],
        [InlineKeyboardButton("✈️ Telegram", callback_data="edit_telegram")],
        [InlineKeyboardButton("📸 Instagram", callback_data="edit_instagram")],
        [InlineKeyboardButton("🌐 VK", callback_data="edit_vk")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_review")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
<b>✏️ РЕДАКТИРОВАНИЕ ПОСТА</b>

Выберите платформу для редактирования:

После выбора напишите новый текст для этой платформы.
    """
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return EDITING

async def select_platform_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор платформы для редактирования"""
    query = update.callback_query
    await query.answer()
    
    platform_map = {
        "edit_tiktok": "tiktok",
        "edit_telegram": "telegram",
        "edit_instagram": "instagram",
        "edit_vk": "vk"
    }
    
    platform = platform_map.get(query.data)
    context.user_data['editing_platform'] = platform
    
    user_id = update.effective_user.id
    post_data = smm_bot.pending_posts.get(user_id)
    current_text = post_data['platforms'][platform]['text']
    
    keyboard = [
        [InlineKeyboardButton("◀️ Отмена", callback_data="edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    platform_names = {
        "tiktok": "TikTok 🎵",
        "telegram": "Telegram ✈️",
        "instagram": "Instagram 📸",
        "vk": "VK 🌐"
    }
    
    text = f"""
<b>✏️ Редактирование: {platform_names[platform]}</b>

<b>Текущий текст:</b>
{current_text}

━━━━━━━━━━━━━━━━━━━━

<i>Напишите новый текст для этой платформы:</i>
    """
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return EDITING

async def save_edited_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение отредактированного текста"""
    new_text = update.message.text
    platform = context.user_data.get('editing_platform')
    
    user_id = update.effective_user.id
    post_data = smm_bot.pending_posts.get(user_id)
    
    if not platform or not post_data:
        await update.message.reply_text("❌ Произошла ошибка. Пожалуйста, начните сначала (/start).")
        return ConversationHandler.END

    # Обновляем текст
    post_data['platforms'][platform]['text'] = new_text
    
    platform_names = {
        "tiktok": "TikTok 🎵",
        "telegram": "Telegram ✈️",
        "instagram": "Instagram 📸",
        "vk": "VK 🌐"
    }
    
    await update.message.reply_text(
        f"✅ Текст для <b>{platform_names[platform]}</b> обновлён!",
        parse_mode='HTML'
    )
    
    # Возвращаемся к превью
    preview_text = smm_bot.format_post_preview(post_data)
    
    keyboard = [
        [InlineKeyboardButton("✅ Одобрить и опубликовать", callback_data="approve")],
        [InlineKeyboardButton("✏️ Редактировать ещё", callback_data="edit")],
        [InlineKeyboardButton("🖼 Показать фото", callback_data="show_image")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        preview_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    # Сбрасываем платформу редактирования
    context.user_data['editing_platform'] = None

    return REVIEWING

async def approve_and_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация поста"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    post_data = smm_bot.pending_posts.get(user_id)
    
    # Анимация публикации
    status_msg = await query.message.reply_text(
        "🚀 <b>ПУБЛИКАЦИЯ...</b>\n\n"
        "⏳ Подключаемся к платформам...",
        parse_mode='HTML'
    )
    
    platforms = ["TikTok 🎵", "Telegram ✈️", "Instagram 📸", "VK 🌐"]
    
    for i, platform in enumerate(platforms, 1):
        await asyncio.sleep(1)
        await status_msg.edit_text(
            f"🚀 <b>ПУБЛИКАЦИЯ...</b>\n\n"
            f"{'✅ ' * i}{'⏳ ' * (4-i)}\n\n"
            f"Публикуем в {platform}...",
            parse_mode='HTML'
        )
    
    await asyncio.sleep(1)
    
    # Финальное сообщение
    success_text = f"""
✅ <b>ПОСТ УСПЕШНО ОПУБЛИКОВАН!</b>

📊 <b>Результаты:</b>

🎵 TikTok: ✅ Опубликовано
✈️ Telegram: ✅ Опубликовано  
📸 Instagram: ✅ Опубликовано
🌐 VK: ✅ Опубликовано

🎯 <b>Тема:</b> {post_data['topic']}
⏰ <b>Время:</b> {datetime.now().strftime("%H:%M")}

━━━━━━━━━━━━━━━━━━━━

💬 <b>Автоответы на комментарии:</b> Включены ✅

Бот будет автоматически отвечать на вопросы подписчиков!
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 Создать ещё пост", callback_data="create_post")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await status_msg.edit_text(
        success_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    # Очищаем временные данные
    if user_id in smm_bot.pending_posts:
        del smm_bot.pending_posts[user_id]
    
    return CHOOSING_NICHE

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    stats_text = """
📊 <b>СТАТИСТИКА РАБОТЫ БОТА</b>

<b>За сегодня:</b>
✅ Создано постов: 5
🚀 Опубликовано: 5
💬 Автоответов: 23

<b>По платформам:</b>
🎵 TikTok: 5 постов
✈️ Telegram: 5 постов
📸 Instagram: 5 постов
🌐 VK: 5 постов

<b>Охват:</b>
👁 Просмотры: ~12,500
❤️ Реакции: 847
💬 Комментарии: 156

<b>Экономия времени:</b>
⏱ Сэкономлено: ~3.5 часа
💰 Стоимость работы SMM: $150/мес

━━━━━━━━━━━━━━━━━━━━

🤖 Автоматизация работает отлично!
    """
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return CHOOSING_NICHE

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать помощь"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
ℹ️ <b>ПОМОЩЬ И ВОЗМОЖНОСТИ</b>

<b>🎯 Как работает бот:</b>

1️⃣ Выбираете нишу (Авто/Недвижимость)
2️⃣ Пишете тему поста
3️⃣ AI генерирует контент для всех соцсетей
4️⃣ Проверяете и редактируете при необходимости
5️⃣ Публикуете во все платформы одним кликом

<b>✨ Возможности:</b>

✅ Генерация уникальных текстов
✅ Подбор качественных фото
✅ Адаптация под каждую платформу
✅ Автоматическая публикация
✅ Умные автоответы на комментарии
✅ Статистика и аналитика

<b>📱 Поддержка платформ:</b>

🎵 TikTok
✈️ Telegram
📸 Instagram
🌐 VK

<b>🤖 Автоответы:</b>

Бот автоматически отвечает на типовые вопросы:
• О цене
• О характеристиках
• О заказе/просмотре
• На комплименты

━━━━━━━━━━━━━━━━━━━━

📞 <b>Поддержка:</b> @your_support
    """
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    return CHOOSING_NICHE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания поста"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id in smm_bot.pending_posts:
        del smm_bot.pending_posts[user_id]
    
    keyboard = [
        [InlineKeyboardButton("🚀 Создать пост", callback_data="create_post")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "❌ Создание поста отменено.\n\nЧто хотите сделать?",
        reply_markup=reply_markup
    )
    
    return CHOOSING_NICHE

def main():
    """Запуск бота"""
    
    # 1. Загружаем переменные окружения из .env
    load_dotenv()
    # 2. Читаем токен из переменной окружения
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ ОШИБКА: Токен бота не найден!")
        print("Создайте файл .env в папке с ботом и добавьте туда строку: BOT_TOKEN=ВАШ_ТОКЕН")
        print("Получите токен у @BotFather в Telegram.")
        return
    
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для управления диалогом
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_NICHE: [
                CallbackQueryHandler(choose_niche, pattern="^create_post$"),
                CallbackQueryHandler(show_stats, pattern="^stats$"),
                CallbackQueryHandler(show_help, pattern="^help$"),
                CallbackQueryHandler(start, pattern="^back_to_start$"),
            ],
            ENTERING_TOPIC: [
                CallbackQueryHandler(handle_niche_selection, pattern="^niche_"),
                CallbackQueryHandler(choose_niche, pattern="^create_post$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_input),
            ],
            REVIEWING: [
                CallbackQueryHandler(approve_and_publish, pattern="^approve$"),
                CallbackQueryHandler(edit_post, pattern="^edit$"),
                CallbackQueryHandler(show_image, pattern="^show_image$"),
                CallbackQueryHandler(back_to_review, pattern="^back_to_review$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            EDITING: [
                CallbackQueryHandler(select_platform_to_edit, pattern="^edit_"),
                CallbackQueryHandler(edit_post, pattern="^edit$"),
                CallbackQueryHandler(back_to_review, pattern="^back_to_review$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_text),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    print("Найди его в Telegram и напиши /start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
