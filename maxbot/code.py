import logging
import subprocess
import asyncio
from maxapi.types import NewMessageLink
from maxapi.enums.message_link_type import MessageLinkType


async def cmd_unmute(event, bot, args):
    if not args: return
    logging.info(f"Выполняю /unmute для: {args}")

async def trigger_keywords(event, bot, text):
    if "правила" in text.lower(): return True 
    return False

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
# 🌟 ГЛАВНАЯ ФУНКЦИЯ (ВЕРСИЯ 8 - ТЕРМИНАЛ)
# ==========================================
async def handler_v8(event, bot):
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
        admin_ids = []
        if not is_private:
            try:
                admins_response = await bot.get_list_admin_chat(chat_id=chat_id)
                members_list = getattr(admins_response, 'members', [])
                admin_ids = [a.user_id for a in members_list if hasattr(a, 'user_id')]
            except Exception:
                pass
        
        is_admin = is_private or (user_id in admin_ids)

        # ---------------------------------------------------------
        # КОМАНДЫ ДЛЯ АДМИНОВ
        # ---------------------------------------------------------
        if text.strip() == "/check":
            if is_admin:
                try:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text="✅ Я онлайн и работаю!", link=reply_link)
                except Exception:
                    pass
                return

        elif text.startswith("/sendcall"):
            if is_admin:
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text="Укажите команду: /sendcall <команда>", link=reply_link)
                    return
                
                command = parts[1]
                try:
                    # Запускаем команду (shell=True означает, что работаем как в cmd)
                    output = subprocess.check_output(
                        command, 
                        shell=True, 
                        text=True, 
                        encoding='cp866', 
                        errors='replace',
                        stderr=subprocess.STDOUT, # Захватываем текст ошибок
                        timeout=15                # Защита от зависания бота
                    )
                    
                    if not output.strip():
                        output = "[Команда выполнена успешно, вывода нет]"
                        
                    # Обрезаем вывод, если он слишком огромный
                    if len(output) > 3900:
                        output = output[:3900] + "\n...[ВЫВОД ОБРЕЗАН]..."
                        
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text=f"💻 Ответ сервера:\n```text\n{output}\n```", link=reply_link)
                    
                except subprocess.TimeoutExpired:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text="⏱ Ошибка: команда выполнялась дольше 15 секунд и была прервана.", link=reply_link)
                except subprocess.CalledProcessError as e:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text=f"❌ Команда завершилась с ошибкой (код {e.returncode}):\n```text\n{e.output}\n```", link=reply_link)
                except Exception as e:
                    reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=message_id)
                    await bot.send_message(chat_id=chat_id, text=f"⚠️ Системная ошибка: {e}", link=reply_link)
            return

        elif text.startswith("/unmute"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            await cmd_unmute(event, bot, args)
            return

        if not is_private:
            await filter_non_admins(event, bot)
        return

    if attachments:
        await handle_media(event, bot, attachments)
        return 
        
    if text:
        is_keyword = await trigger_keywords(event, bot, text)
        if is_keyword:
            return
            
    if text and not is_private:
        await filter_non_admins(event, bot)
