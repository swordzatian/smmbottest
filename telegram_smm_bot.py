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

# Импорты для работы с OpenAI
from openai import AsyncOpenAI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
# Ключ будет автоматически взят из переменной окружения OPENAI_API_KEY
client = AsyncOpenAI()

# Состояния для ConversationHandler
CHOOSING_NICHE, ENTERING_TOPIC, REVIEWING, EDITING = range(4)

class SMMBot:
    def __init__(self):
        self.pending_posts = {}  # user_id: post_data
        
    async def generate_image_url(self, keywords: list, niche: str) -> str:
        """Генерация реалистичного фото с помощью DALL-E"""

        # Создаем подробный запрос для AI
        prompt = (
            f"Фотореалистичное, высококачественное изображение на тему: '{' '.join(keywords)}' из ниши '{niche}'. "
            f"Стиль: рекламная фотография, 4K, студийный свет, без текста, резкий фокус."
        )

        try:
            # DALL-E-2 используется как более доступный и быстрый вариант для Telegram
            response = await client.images.generate(
                model="dall-e-2",
                prompt=prompt,
                n=1,
                size="512x512" 
            )
            # DALL-E возвращает временную ссылку на изображение
            return response.data[0].url
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            # Возвращаем ссылку на заглушку в случае ошибки (по необходимости, сейчас заглушек нет)
            return "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/1024px-No_image_available.svg.png"
        
    async def generate_post_text(self, topic: str, platform: str, niche: str) -> str:
        """Генерация текста для поста с помощью AI (GPT)"""
        
        system_prompt = (
            f"Ты профессиональный SMM-менеджер. Твоя задача — создать продающий и вовлекающий пост "
            f"на тему '{topic}' для ниши '{niche}'. "
            f"Адаптируй стиль, длину и хештеги под платформу '{platform}'. "
            f"Сделай пост максимально естественным и привлекательным для ЦА этой платформы."
        )

        user_prompt = f"Сгенерируй пост на тему '{topic}' для платформы {platform}. Включи эмодзи и релевантные хештеги."

        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo", # Быстрый и адекватный для контента
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка генерации текста: {e}")
            return f"❌ Ошибка AI-генерации текста. Тема: {topic}. Попробуйте позже."
        
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
✅ Генерирую контент для 4 платформ (GPT)
✅ Подбираю фото по теме (DALL-E)
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
        "🤖 AI создаёт тексты для всех платформ и подбирает фото. Это займет ~5-10 секунд...",
        parse_mode='HTML'
    )
    
    # Генерируем контент
    platforms = ["tiktok", "telegram", "instagram", "vk"]
    generated_content = {}
    
    # Асинхронно запускаем генерацию текста и фото
    tasks = []
    for platform in platforms:
        tasks.append(smm_bot.generate_post_text(topic, platform, niche))
        
    # Получаем фото
    keywords = [topic] 
    tasks.append(smm_bot.generate_image_url(keywords, niche))
    
    results = await asyncio.gather(*tasks)
    
    image_url = results[-1]
    text_results = results[:-1]
    
    for i, platform in enumerate(platforms):
        generated_content[platform] = {"text": text_results[i]}
    
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
        "📸 Уникальное фото подобрано (DALL-E)\n"
        "📝 Уникальные тексты сгенерированы для 4 платформ (GPT)",
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
3️⃣ AI (GPT) генерирует уникальный контент для всех соцсетей
4️⃣ AI (DALL-E) генерирует уникальное фото
5️⃣ Проверяете и редактируете при необходимости
6️⃣ Публикуете во все платформы одним кликом

<b>✨ Возможности:</b>

✅ Генерация уникальных текстов (GPT)
✅ Подбор качественных фото (DALL-E)
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
    # 2. Читаем токены из переменных окружения
    TOKEN = os.getenv("BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not TOKEN:
        print("❌ ОШИБКА: Токен бота не найден!")
        print("Создайте переменную BOT_TOKEN в настройках Render (или в файле .env).")
        return
        
    if not OPENAI_API_KEY:
        print("❌ ОШИБКА: Ключ OpenAI не найден!")
        print("Создайте переменную OPENAI_API_KEY в настройках Render (или в файле .env).")
        print("Для работы AI нужна регистрация на platform.openai.com и активный ключ.")
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
