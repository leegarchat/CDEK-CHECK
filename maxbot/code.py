import logging


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

    try:
        admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
        members_list = getattr(admins_response, 'members', [])
        admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
        
        if not admin_ids: return
            
        if user_id not in admin_ids:
            await bot.delete_message(message_id=message_id)
            logging.info(f"v2: Удалено сообщение от не-админа {user_id}")
    except Exception as e:
        logging.error(f"v2: Ошибка модерации: {e}")




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

async def handler_v3(event, bot):
    message = event.message
    
    try:
        chat_id = message.recipient.chat_id
        if not chat_id or chat_id > 0: return 
    except AttributeError:
        return
    try:
        text = message.body.text or ""
    except AttributeError:
        text = ""
    try:
        attachments = message.body.attachments or []
    except AttributeError:
        attachments = []
    if text.startswith("/"):
        if text.startswith("/unmute"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            await cmd_unmute(event, bot, args)
        return

    if attachments:
        await handle_media(event, bot, attachments)
        return 
    if text:
        is_keyword = await trigger_keywords(event, bot, text)
        if is_keyword:
            return
    if text:
        await filter_non_admins(event, bot)
