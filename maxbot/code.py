import logging
import subprocess # <-- Добавили для работы с консолью Windows
from maxapi.types import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType


async def filter_non_admins(event, bot):
    message = event.message
    user_id = message.sender.user_id
    chat_id = message.recipient.chat_id
    message_id = message.body.mid

    if chat_id > 0: return

    try:
        admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
        members_list = getattr(admins_response, 'members', [])
        admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
        
        if not admin_ids: return
        if user_id not in admin_ids:
            await bot.delete_message(message_id=message_id)
    except Exception as e:
        logging.error(f"Ошибка модерации: {e}")

async def handle_media(event, bot, attachments):
    await filter_non_admins(event, bot)

# ==========================================
# 🌟 ГЛАВНАЯ ФУНКЦИЯ (ВЕРСИЯ 5)
# ==========================================
async def handler_v5(event, bot):
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

    if text.startswith("/"):
        
        # Проверяем, админ ли это (чтобы обычные юзеры не могли убить сервер)
        admin_ids = []
        if not is_private:
            try:
                admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
                members_list = getattr(admins_response, 'members', [])
                admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
            except Exception:
                pass
        
        is_admin = is_private or (user_id in admin_ids)

        if text.strip() == "/check":
            if is_admin:
                try:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text="✅ Я онлайн и работаю!", link=reply_link)
                except Exception:
                    pass
                return

        # ---------------------------------------------------------
        # НОВЫЕ СЕКРЕТНЫЕ КОМАНДЫ ДЛЯ АДМИНИСТРИРОВАНИЯ СЕРВЕРА
        # ---------------------------------------------------------
        elif text.strip() == "/ps":
            if is_admin:
                try:
                    # Запрашиваем у Windows список процессов python. Используем cp866 для русской винды
                    cmd_output = subprocess.check_output('tasklist | findstr python', shell=True, text=True, encoding='cp866', errors='replace')
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text=f"🖥 Процессы Python на сервере:\n```\n{cmd_output}\n```", link=reply_link)
                except Exception as e:
                    await bot.send_message(chat_id=chat_id, text=f"Ошибка выполнения /ps: {e}")
                return

        elif text.strip() == "/killall":
            if is_admin:
                reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                await bot.send_message(chat_id=chat_id, text="💀 Запускаю очистку клонов. Ухожу в рестарт, вернусь через 5 секунд...", link=reply_link)
                # Команда убивает ВСЕ процессы python.exe мгновенно
                subprocess.Popen('taskkill /F /IM python.exe', shell=True)
                return
        # ---------------------------------------------------------

        if not is_private:
            await filter_non_admins(event, bot)
        return

    if attachments:
        await handle_media(event, bot, attachments)
        return 

            
    if text and not is_private:
        await filter_non_admins(event, bot)
