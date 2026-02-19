import logging
# Новые импорты добавляем прямо сюда! Ядро их скушает без проблем.
from maxapi.types import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType


async def cmd_unmute(event, bot, args):
    chat_id = event.message.recipient.chat_id
    if not args:
        logging.info("Вызвана команда /unmute без параметров")
        return
    logging.info(f"Выполняю /unmute для: {args}")


async def trigger_keywords(event, bot, text):
    chat_id = event.message.recipient.chat_id
    if "правила" in text.lower():
        logging.info("Сработало ключевое слово 'правила'")
        return True 
    return False


async def filter_non_admins(event, bot):
    message = event.message
    user_id = message.sender.user_id
    chat_id = message.recipient.chat_id
    message_id = message.body.mid

    # Защита: модератор работает только в группах (chat_id < 0)
    if chat_id > 0: 
        return

    try:
        admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
        members_list = getattr(admins_response, 'members', [])
        admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
        
        if not admin_ids: return
            
        if user_id not in admin_ids:
            await bot.delete_message(message_id=message_id)
            logging.info(f"v4: Удалено сообщение от не-админа {user_id}")
    except Exception as e:
        logging.error(f"v4: Ошибка модерации: {e}")


async def handle_media(event, bot, attachments):
    message = event.message
    chat_id = message.recipient.chat_id
    for att in attachments:
        att_type = getattr(att, 'type', 'unknown')
        if att_type == 'image':
            logging.info(f"Получена картинка! Обрабатываем...")
        elif att_type == 'video':
            logging.info(f"Получено видео!")
        elif att_type == 'file':
            logging.info(f"Получен документ!")
            
    await filter_non_admins(event, bot)


# ==========================================
# 🌟 ГЛАВНАЯ ФУНКЦИЯ (ВЕРСИЯ 4)
# ==========================================
async def handler_v4(event, bot):
    message = event.message
    
    # 1. Извлекаем ID
    try:
        user_id = message.sender.user_id
        chat_id = message.recipient.chat_id
        message_id = message.body.mid
        if not chat_id: return 
    except AttributeError:
        return

    is_private = (chat_id > 0) # True = Личка, False = Группа

    # 2. Безопасно извлекаем текст и вложения
    try:
        text = message.body.text or ""
    except AttributeError:
        text = ""
    try:
        attachments = message.body.attachments or []
    except AttributeError:
        attachments = []

    # 3. МАРШРУТИЗАЦИЯ КОМАНД
    if text.startswith("/"):
        
        # --- Команда /check ---
        if text.strip() == "/check":
            admin_ids = []
            
            if not is_private:
                try:
                    admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
                    members_list = getattr(admins_response, 'members', [])
                    admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
                except Exception as e:
                    logging.error(f"Ошибка получения админов для /check: {e}")
                    return

            if is_private or user_id in admin_ids:
                try:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(
                        chat_id=chat_id, 
                        text="✅ Я онлайн и работаю!", 
                        link=reply_link
                    )
                    logging.info("✅ Ответил РЕПЛАЕМ на /check")
                except Exception as e:
                    logging.error(f"Ошибка при отправке /check: {e}")
                return # Выходим, чтобы команду не удалило
            else:
                pass # Если написал не админ в группе — пропускаем код дальше, к фильтру удаления

        # --- Команда /unmute ---
        elif text.startswith("/unmute"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            await cmd_unmute(event, bot, args)
            return

        # Если это какая-то другая неизвестная команда от не-админа в группе, пусть её удалит фильтр
        if not is_private:
            await filter_non_admins(event, bot)
        return

    # 4. ОБРАБОТКА МЕДИА
    if attachments:
        await handle_media(event, bot, attachments)
        return 
        
    # 5. КЛЮЧЕВЫЕ СЛОВА
    if text:
        is_keyword = await trigger_keywords(event, bot, text)
        if is_keyword:
            return
            
    # 6. ДЕЙСТВИЕ ПО УМОЛЧАНИЮ (Фильтр спама в группах)
    if text and not is_private:
        await filter_non_admins(event, bot)
