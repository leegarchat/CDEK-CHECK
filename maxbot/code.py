import logging

async def handler_v1(event, bot):
    message = event.message
    try:
        user_id = message.sender.user_id
        chat_id = message.recipient.chat_id
        message_id = message.body.mid
    except AttributeError:
        return

    if not chat_id or chat_id > 0:
        return

    try:
        admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
        members_list = getattr(admins_response, 'members', [])
        admin_ids = []
        for admin in members_list:
            if hasattr(admin, 'user_id'):
                admin_ids.append(admin.user_id)
        
        if not admin_ids:
            logging.warning("Не удалось собрать ID админов.")
            return
            
        if user_id not in admin_ids:
            await bot.delete_message(message_id=message_id)
            logging.info(f"v1: Удалено сообщение от не-админа {user_id} в группе {chat_id}")
        else:
            logging.info(f"v1: Сообщение от администратора {user_id} пропущено.")

    except Exception as e:
        logging.error(f"v1: Ошибка при обработке сообщения: {e}")
