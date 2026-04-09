# =============================================
# Developer : ✘ 𝙍𝘼𝙑𝙀𝙉
# Telegram  : @P_X_24
# =============================================

import asyncio
import random
import re
import os
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path


from telethon import TelegramClient, sync, functions, errors, events, types
from telethon.tl.functions.account import UpdateStatusRequest, UpdateProfileRequest
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, SendReactionRequest, GetHistoryRequest, SendVoteRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.types import MessageMediaPoll


from config import (
    API_ID, API_HASH, BOT_TOKEN,
    RUNNING_PROCESSES, CLIENTS, POINTS_DATA
)
from data import INFO, save_info



def send_message_via_http(chat_id, text):
    """Utility to send simple messages using the Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

async def send_file(bot_token, chat_id, file_name, file_data):
    """Sends a document via Bot API."""
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data={
            "chat_id": chat_id,
            "caption": f"الرقم : {file_name.replace('.session', '')}"
        },
        files={
            "document": (file_name, file_data)
        }
    )

def stop_background_task(phone, chat_id):
    """Stops a specific background task and disconnects the client."""
    chat_id = str(chat_id)
    phone = str(phone)
    client_key = f"{phone}-{chat_id}"

    if client_key in CLIENTS:
        client = CLIENTS[client_key]
        try:
            if client.is_connected():
                asyncio.create_task(client.disconnect())
        except Exception as e:
            print(f"Error disconnecting client {client_key}: {e}")
        del CLIENTS[client_key]

    if chat_id in RUNNING_PROCESSES and phone in RUNNING_PROCESSES[chat_id]:
        task = RUNNING_PROCESSES[chat_id][phone]
        if not task.done():
            task.cancel()
            print(f"Stopped background task for phone {phone} and chat_id {chat_id}")
        RUNNING_PROCESSES[chat_id].pop(phone, None)

def stop_all_background_tasks(chat_id):
    """Stops all running tasks associated with a chat ID."""
    chat_id = str(chat_id)
    if chat_id in RUNNING_PROCESSES:
        # Iterate over a copy of keys to allow modification of the dict during iteration
        for phone in list(RUNNING_PROCESSES[chat_id].keys()):
            stop_background_task(phone, chat_id)
        
        # Cancel custom tasks (keys starting with 'custom_')
        custom_keys = [k for k in list(RUNNING_PROCESSES[chat_id].keys()) if k.startswith('custom_')]
        for k in custom_keys:
            task = RUNNING_PROCESSES[chat_id].pop(k, None)
            if task and not task.done():
                task.cancel()

        if not RUNNING_PROCESSES[chat_id]:
             RUNNING_PROCESSES.pop(chat_id, None)

        send_message_via_http(chat_id, "✅ تم إيقاف جميع عمليات التجميع والمهام المخصصة المرتبطة بحساباتك.")



async def background_task(phonex, bot_username, sudo, send_to):
    """The main loop for Keko/Echo points collection."""
    sudo = str(sudo)
    client_key = f"{phonex}-{sudo}"
    send_message_via_http(sudo, f"جاري الاتصال : {phonex}")

    CLIENTS[client_key] = TelegramClient(f"echo_ac/{sudo}/{phonex}", API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    clientx = CLIENTS[client_key]

    try:
        @clientx.on(events.NewMessage)
        async def handle_new_message(event):
            if event.is_channel and not event.mentioned:
                await clientx(GetMessagesViewsRequest(
                    peer=event.chat_id,
                    id=[event.message.id],
                    increment=True
                ))

        await clientx.connect()
        await clientx(UpdateStatusRequest(offline=False))
        if not await clientx.is_user_authorized():
            send_message_via_http(sudo, f"الحساب غير مسجل بالبوت : {phonex}")
            await clientx.disconnect()
            stop_background_task(phonex, sudo)
            return

        me = await clientx.get_me()
        user_id = me.id
        
        target_send_to = user_id if send_to == "حساب" else (sudo if send_to == "انا" else send_to)

        try:
            bot_entity = await clientx.get_entity(bot_username)
            bot_id = bot_entity.id
        except Exception as e:
            send_message_via_http(sudo, f"- لا يمكن العثور على البوت بالمعرف '{bot_username}'. يرجى التحقق منه.\n- خطأ: {e}\n\n- {phonex}")
            await clientx.disconnect()
            stop_background_task(phonex, sudo)
            return

        await clientx.send_message(bot_username, '/start')
        await asyncio.sleep(5)
        
        response = requests.get(f"https://bot.keko.dev/api/?login={user_id}&bot_id={bot_id}")
        response_json = response.json()
        
        if response_json.get("ok", False):
            echo_token = response_json.get("token", "")
            send_message_via_http(sudo, f"- تم تسجيل الدخول بنجاح, توكن حسابك : {echo_token} \n\n- سيتم ارسال النقاط الى : {target_send_to} \n\n- {phonex}")

            while client_key in CLIENTS:
                try:
                    response = requests.get(f"https://bot.keko.dev/api/?token={echo_token}")
                    response_json = response.json()
                    
                    if not response_json.get("ok", False):
                        msg = response_json.get('msg', 'خطأ غير معروف')
                        send_message_via_http(sudo, f"- {msg} \n\n- {phonex}")
                        if 'تسجيل الدخول' in msg or 'انتهت مدة' in msg: break
                        await asyncio.sleep(INFO.get("sleeptime", 20))
                        continue
                    
                    if response_json.get("canleave", False):
                        for chat in response_json["canleave"]:
                            try:
                                await clientx.delete_dialog(chat)
                                send_message_via_http(sudo, f"- تم مغادرة : {chat} -> بسبب انتهاء مده الاشتراك\n\n- {phonex}")
                                await asyncio.sleep(random.randint(3, 10))
                            except Exception as e:
                                print(f"Error leaving chat: {str(e)}")
                        continue
                    
                    task_type = response_json.get("type", "")
                    task_return = response_json.get("return", "")
                    
                    if task_return:
                        try:
                            if task_type == "link":
                                await clientx(ImportChatInviteRequest(task_return))
                                peer_entity = int(task_return)
                            else:
                                await clientx(JoinChannelRequest(task_return))
                                peer_entity = await clientx.get_entity(task_return)

                            await asyncio.sleep(random.randint(2, 5))
                            messages = await clientx.get_messages(peer_entity, limit=20 if task_type == "link" else 10)
                            if messages:
                                MSG_IDS = [message.id for message in messages]
                                
                                await clientx(GetMessagesViewsRequest(
                                    peer=peer_entity,
                                    id=MSG_IDS,
                                    increment=True
                                ))

                                try:
                                    await clientx(SendReactionRequest(
                                        peer=peer_entity,
                                        msg_id=messages[0].id,
                                        big=True,
                                        add_to_recent=True,
                                        reaction=[types.ReactionEmoji(emoticon='👍')]
                                    ))
                                except Exception as e:
                                    print(f"Error sending reaction: {str(e)}")

                        except errors.FloodWaitError as e:
                            timeoutt = e.seconds + random.randint(5, 15)
                            send_message_via_http(sudo, f"- تم حظر الرقم مؤقتًا: انتظار {timeoutt} ثانية \n\n- {phonex}")
                            
                            await clientx(UpdateStatusRequest(offline=True))
                            await clientx.disconnect()
                            await asyncio.sleep(timeoutt)
                            
                            if client_key not in CLIENTS: break
                            await clientx.connect()
                            await clientx(UpdateStatusRequest(offline=False))
                            continue

                        except Exception as e:
                            send_message_via_http(sudo, f"- خطا، سيتم تخطي المهمة الحالية: \n\n{str(e)}\n\n- {phonex}")
                            await asyncio.sleep(10)
                            continue
                    
                    report_response = requests.get(f"https://bot.keko.dev/api/?token={echo_token}&to_id={target_send_to}&done={task_return}")
                    report_json = report_response.json()
                    
                    if not report_json.get("ok", False):
                        msg = report_json.get('msg', 'خطأ غير معروف في الإبلاغ')
                        send_message_via_http(sudo, f"- {msg} \n\n- {phonex}")
                        if 'تسجيل الدخول' in msg: break
                    else:
                        points_val = report_json.get('c')
                        if points_val is not None:
                            POINTS_DATA.setdefault(sudo, {})[phonex] = points_val

                        points_text = f"- اصبح عدد نقاطك: {points_val}\n\n" if points_val is not None and points_val != 0 else ""
                        timeout_val = report_json.get('timeout')
                        leave_after_text = f"{timeout_val} ثانية" if timeout_val is not None and str(timeout_val).lower() != 'none' else "غير محدد"
                        
                        timeoutt = random.randint(INFO.get("sleeptime", 20), int(INFO.get("sleeptime", 20) * 1.3))
                        
                        send_message_via_http(sudo, 
                            f"{points_text}"
                            f"يمكنك المغادرة بعد: {leave_after_text}\n\n"
                            f"- {phonex}\n\n"
                            f"- انتظار: {timeoutt}"
                        )
                        
                        await clientx(UpdateStatusRequest(offline=True))
                        await clientx.disconnect()
                        await asyncio.sleep(timeoutt)
                        
                        if client_key not in CLIENTS: break
                        await clientx.connect()
                        await clientx(UpdateStatusRequest(offline=False))

                except Exception as e:
                    send_message_via_http(sudo, f"حدث خطا فادح في الحلقة الرئيسية للحساب : {phonex}. الخطأ: {e}")
                    break
        
        await clientx.disconnect()
        send_message_via_http(sudo, f"- تم ايقاف عمل الرقم : {phonex}")
        stop_background_task(phonex, sudo)

    except Exception as e:
        send_message_via_http(sudo, f"حدث خطا في الحساب (الاتصال الأولي): {phonex}. الخطأ: {e}")
        if clientx.is_connected():
            await clientx.disconnect()
        stop_background_task(phonex, sudo)

# --- Task Management Utilities ---

def start_background_task(phone, bot_username, chat_id, send_to, duration_seconds=None):
    """Initializes and tracks a new background task."""
    chat_id = str(chat_id)
    phone = str(phone)
    
    stop_background_task(phone, chat_id)
    
    if chat_id not in RUNNING_PROCESSES:
        RUNNING_PROCESSES[chat_id] = {}
        
    task = asyncio.create_task(background_task(phone, bot_username, chat_id, send_to))
    RUNNING_PROCESSES[chat_id][phone] = task

    if duration_seconds and duration_seconds > 0:
        async def stop_after_delay(delay, p, c):
            await asyncio.sleep(delay)
            if c in RUNNING_PROCESSES and p in RUNNING_PROCESSES[c]:
                stop_background_task(p, c)
                send_message_via_http(c, f"⏰ انتهت مدة التجميع المحددة للحساب: {p}\nتم إيقافه تلقائياً.")

        asyncio.create_task(stop_after_delay(duration_seconds, phone, chat_id))

# --- Telethon Action Handlers ---

async def delall_sessions(chat_id):
    """Deletes all session files for a given user and stops related tasks."""
    directory = f'echo_ac/{chat_id}'
    stop_all_background_tasks(chat_id)
    if os.path.isdir(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) and filename.endswith('.session'):
                    os.unlink(file_path)
                    send_message_via_http(chat_id, f"الرقم : {filename.replace('.session', '')}\n تم حذفه")
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

async def copynum_sessions(chat_id):
    """Sends session files to the user."""
    directory = f'echo_ac/{chat_id}'
    if os.path.isdir(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and filename.endswith('.session'):
                with open(file_path, 'rb') as f:
                    await send_file(BOT_TOKEN, chat_id, filename, f)

async def join_channel_sync(user_id, chn):
    """Makes all user accounts join a specific channel/chat."""
    directory_path = Path(f"echo_ac/{user_id}")
    if not directory_path.is_dir(): return
    file_list = [file.stem for file in directory_path.glob('*.session')]
    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                await client(JoinChannelRequest(chn))
                send_message_via_http(user_id, f"الرقم : {file_stem}\nتم الانضمام في {chn}")
            except Exception as e:
                send_message_via_http(user_id, f"الرقم : {file_stem}\nفشل في الانضمام: {e}")

async def start_bot_via_link(user_id, bot_link):
    """Sends /start command with payload to a bot via user accounts."""
    match = re.search(r"t\\.me/([^?]+)(?:\\?start=(.+))?", bot_link)
    if not match:
        send_message_via_http(user_id, "⚠️ رابط البوت غير صالح.")
        return

    bot_username = match.group(1)
    start_payload = match.group(2)
    command = f"/start {start_payload}" if start_payload else "/start"

    directory_path = Path(f"echo_ac/{user_id}")
    file_list = [file.stem for file in directory_path.glob('*.session')]
    send_message_via_http(user_id, f"✅ تم استلام الرابط. ستقوم {len(file_list)} حسابات بإرسال الأمر `{command}` إلى @{bot_username}...")

    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                await client.send_message(bot_username, command)
                send_message_via_http(user_id, f"الحساب: {file_stem}\n✅ تم إرسال أمر البدء بنجاح.")
            except Exception as e:
                error_message = str(e).replace('<', '').replace('>', '')
                send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل: {error_message}")
        await asyncio.sleep(random.randint(2, 5))
    send_message_via_http(user_id, "🏁 انتهت العملية.")

async def join_via_invite(user_id, invite_link):
    """Joins a private chat/channel using an invite link hash."""
    try:
        if "t.me/+" in invite_link or "telegram.me/+" in invite_link:
            invite_hash = invite_link.split('+')[1].strip().split('/')[0]
        elif "joinchat/" in invite_link:
            invite_hash = invite_link.split('joinchat/')[1].strip().split('/')[0]
        else:
            send_message_via_http(user_id, "⚠️ رابط الدعوة غير صالح.")
            return
    except IndexError:
        send_message_via_http(user_id, "⚠️ فشل في تحليل رابط الدعوة.")
        return

    directory_path = Path(f"echo_ac/{user_id}")
    file_list = [file.stem for file in directory_path.glob('*.session')]
    send_message_via_http(user_id, f"✅ تم استلام الرابط. ستقوم {len(file_list)} حسابات بالانضمام...")

    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                await client(ImportChatInviteRequest(invite_hash))
                send_message_via_http(user_id, f"الحساب: {file_stem}\n✅ تم الانضمام بنجاح.")
            except errors.UserAlreadyParticipantError:
                send_message_via_http(user_id, f"الحساب: {file_stem}\nℹ️ الحساب عضو بالفعل.")
            except Exception as e:
                error_message = str(e).replace('<', '').replace('>', '')
                send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل في الانضمام: {error_message}")
        await asyncio.sleep(random.randint(3, 7))
    send_message_via_http(user_id, "🏁 انتهت عملية الانضمام.")

async def leave_a_channel_sync(id, chn):
    """Makes all user accounts leave a specific channel/chat."""
    directory_path = Path(f"echo_ac/{id}")
    if not directory_path.is_dir(): return
    file_list = [file.stem for file in directory_path.glob('*.session')]
    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                await client(LeaveChannelRequest(chn))
                send_message_via_http(id, f"الرقم : {file_stem}\nتمت المغادرة من {chn}")
            except Exception as e:
                send_message_via_http(id, f"الرقم : {file_stem}\nفشل في المغادرة: {e}")

async def boost_post_vote(user_id, post_link):
    """Sends a 'like' reaction to a post using user accounts."""
    try:
        parts = post_link.strip().split('/')
        channel_username = parts[-2]
        msg_id = int(parts[-1])
    except (IndexError, ValueError):
        send_message_via_http(user_id, "فشل تحليل الرابط.")
        return

    directory_path = Path(f"echo_ac/{user_id}")
    file_list = [file.stem for file in directory_path.glob('*.session')]
    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                channel_entity = await client.get_entity(channel_username)
                await client(SendReactionRequest(
                    peer=channel_entity,
                    msg_id=msg_id,
                    big=True,
                    add_to_recent=True,
                    reaction=[types.ReactionEmoji(emoticon='👍')]
                ))
                send_message_via_http(user_id, f"الحساب: {file_stem}\n✅ تم التصويت بنجاح.")
            except errors.UserNotParticipantError:
                send_message_via_http(user_id, f"الحساب: {file_stem}\n⚠️ فشل: الحساب ليس عضواً في القناة.")
            except Exception as e:
                error_message = str(e).replace('<', '').replace('>', '')
                send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل التصويت: {error_message}")
            await asyncio.sleep(random.randint(2, 5))

async def boost_post_views(user_id, post_link):
    """Increments views on a post using user accounts."""
    try:
        parts = post_link.strip().split('/')
        channel_username = parts[-2]
        msg_id = int(parts[-1])
    except (IndexError, ValueError):
        send_message_via_http(user_id, "فشل تحليل الرابط.")
        return

    directory_path = Path(f"echo_ac/{user_id}")
    file_list = [file.stem for file in directory_path.glob('*.session')]
    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                peer = await client.get_entity(channel_username)
                await client(GetMessagesViewsRequest(
                    peer=peer,
                    id=[msg_id],
                    increment=True
                ))
                send_message_via_http(user_id, f"الحساب: {file_stem}\n✅ تمت المشاهدة بنجاح.")
            except errors.UserNotParticipantError:
                 send_message_via_http(user_id, f"الحساب: {file_stem}\n⚠️ فشل: الحساب ليس عضواً في القناة. يجب الانضمام أولاً.")
            except Exception as e:
                error_message = str(e).replace('<', '').replace('>', '')
                send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل زيادة المشاهدات: {error_message}")
            await asyncio.sleep(random.randint(1, 3))

async def boost_poll_vote(user_id, post_link, option_index):
    """Casts a vote in a poll using user accounts."""
    try:
        option_index_0_based = option_index - 1
        if option_index_0_based < 0:
            send_message_via_http(user_id, "رقم الخيار يجب أن يكون 1 أو أكبر.")
            return

        parts = post_link.strip().split('/')
        channel_username = parts[-2]
        msg_id = int(parts[-1])
    except (IndexError, ValueError):
        send_message_via_http(user_id, "فشل تحليل الرابط.")
        return

    directory_path = Path(f"echo_ac/{user_id}")
    file_list = [file.stem for file in directory_path.glob('*.session')]
    for file_stem in file_list:
        async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
            try:
                peer = await client.get_entity(channel_username)
                message = await client.get_messages(peer, ids=msg_id)
                if not message or not message.media or not isinstance(message.media, MessageMediaPoll):
                    send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل: المنشور المحدد ليس استفتاءً.")
                    continue

                poll = message.media.poll
                if option_index_0_based >= len(poll.answers):
                     send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل: رقم الخيار ({option_index}) غير موجود.")
                     continue

                option_to_vote = poll.answers[option_index_0_based].option

                await client(SendVoteRequest(
                    peer=peer,
                    msg_id=msg_id,
                    options=[option_to_vote]
                ))
                send_message_via_http(user_id, f"الحساب: {file_stem}\n✅ تم التصويت على الخيار {option_index} بنجاح.")
            except errors.UserNotParticipantError:
                send_message_via_http(user_id, f"الحساب: {file_stem}\n⚠️ فشل: الحساب ليس عضواً في القناة.")
            except errors.PollVoteRequiredError:
                send_message_via_http(user_id, f"الحساب: {file_stem}\n⚠️ فشل: لا يمكنك التصويت في هذا الاستفتاء.")
            except Exception as e:
                error_message = str(e).replace('<', '').replace('>', '')
                send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل التصويت: {error_message}")
            await asyncio.sleep(random.randint(2, 5))

async def spam_messages(user_id, spam_details, count, target_username):
    """Sends a specified message multiple times to a target chat/user."""
    directory_path = Path(f"echo_ac/{user_id}")
    file_path = spam_details.get("file_path")
    spam_text = spam_details.get("text")

    if not directory_path.is_dir():
        send_message_via_http(user_id, "لم يتم العثور على حسابات.")
        return

    file_list = [file.stem for file in directory_path.glob('*.session')]
    if not file_list:
        send_message_via_http(user_id, "لا يوجد حسابات مسجلة لبدء الإرسال.")
        return

    num_accounts = len(file_list)
    count_per_account = (count + num_accounts - 1) // num_accounts
    total_sent = 0

    send_message_via_http(user_id, f"✅ تم استلام المعلومات. سيبدأ الإرسال إلى {target_username}.\n- إجمالي الرسائل: {count}")

    try:
        for file_stem in file_list:
            if total_sent >= count:
                break

            async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
                try:
                    target_entity = await client.get_entity(target_username)
                    send_message_via_http(user_id, f"الحساب: {file_stem}\n- بدأ الإرسال...")

                    sent_by_this_account = 0
                    for i in range(count_per_account):
                        if total_sent >= count: break

                        try:
                            if file_path:
                                await client.send_file(target_entity, file=file_path, caption=spam_text or "")
                            elif spam_text:
                                await client.send_message(target_entity, message=spam_text)
                            else: continue

                            total_sent += 1
                            sent_by_this_account += 1
                            await asyncio.sleep(random.uniform(1.5, 3.0))
                        except errors.FloodWaitError as e:
                            send_message_via_http(user_id, f"الحساب: {file_stem}\n- تم حظره مؤقتًا. الانتظار لمدة {e.seconds} ثانية.")
                            await asyncio.sleep(e.seconds + 5)
                        except Exception as inner_e:
                            send_message_via_http(user_id, f"الحساب: {file_stem}\n- فشل في إرسال الرسالة: {inner_e}")
                            break

                    send_message_via_http(user_id, f"الحساب: {file_stem}\n- اكتمل إرسال {sent_by_this_account} رسالة.")
                except Exception as e:
                    error_message = str(e).replace('<', '').replace('>', '')
                    send_message_via_http(user_id, f"الحساب: {file_stem}\n❌ فشل الإرسال: {error_message}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    send_message_via_http(user_id, f"🏁 انتهت عملية السبام. تم إرسال {total_sent}/{count} رسالة.")

async def temp_account(client):
    """Changes account profile picture and bio to random 'templer' content."""
    try:
        channel_username = 'Zqqqk'
        channel = await client.get_entity(channel_username)
        posts = await client(GetHistoryRequest(peer=channel, limit=100, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        photo_posts = [post for post in posts.messages if post.media and hasattr(post.media, 'photo')]
        if not photo_posts: return
        
        random_photo_post = random.choice(photo_posts)
        photo_path = await client.download_media(random_photo_post.media.photo)
        if not photo_path: return
        
        pfile = await client.upload_file(photo_path)
        await client(UploadProfilePhotoRequest(file=pfile))
        
        if random_photo_post.message:
            caption_parts = random_photo_post.message.split('\n', 1)
            first_name = caption_parts[0]
            bio = caption_parts[1] if len(caption_parts) > 1 else ""
            await client(UpdateProfileRequest(first_name=first_name, about=bio))
            
        os.remove(photo_path)
    except Exception as e:
        print(f"Error in temp function: {e}")

async def process_account_action_sync(chat_id, action_type):
    """Handles synchronous actions (leave all, temp, leave 7d) across all user accounts."""
    directory_path = Path(f"echo_ac/{chat_id}")
    if not directory_path.is_dir(): return
    file_list = [file.stem for file in directory_path.glob('*.session')]
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for file_stem in file_list:
        client = TelegramClient(f"echo_ac/{chat_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max")
        try:
            await client.connect()
            if not await client.is_user_authorized():
                send_message_via_http(chat_id, f"الرقم: {file_stem} غير صالح")
                continue

            if action_type == "leavechn":
                dialogs = await client.get_dialogs()
                count = 0
                for dialog in dialogs:
                    if dialog.is_channel:
                        await client(LeaveChannelRequest(dialog.entity))
                        count += 1
                send_message_via_http(chat_id, f"الرقم: {file_stem}\nتم مغادرة {count} قناة")

            elif action_type == "templer":
                await temp_account(client)
                send_message_via_http(chat_id, f"الرقم: {file_stem}\nتم تحويله تمبلر")

            elif action_type == "leave_7d_collection":
                dialogs = await client.get_dialogs()
                count = 0
                for dialog in dialogs:
                    if dialog.is_channel:
                        try:
                            participant_info = await client(functions.channels.GetParticipantRequest(channel=dialog.entity, participant='me'))
                            join_date = participant_info.participant.date

                            if join_date < seven_days_ago:
                                await client(LeaveChannelRequest(dialog.entity))
                                count += 1
                                await asyncio.sleep(random.randint(2, 4))
                        except (errors.UserNotParticipantError, Exception):
                            continue
                send_message_via_http(chat_id, f"الرقم: {file_stem}\nتم مغادرة {count} قناة منضمة منذ أكثر من 7 أيام.")

        except Exception as e:
            send_message_via_http(chat_id, f"حدث خطأ عام مع الحساب {file_stem}: {e}")
        finally:
            if client.is_connected():
                await client.disconnect()



async def run_custom_collector(user_id, send_to, bot_username, bot_name):
    """Generic function to run custom collection bots."""
    user_id_str = str(user_id)
    directory_path = Path(f"echo_ac/{user_id_str}")
    if not directory_path.is_dir(): return
    active_accounts = [file.stem for file in directory_path.glob('*.session')]

    if not active_accounts:
        send_message_via_http(user_id, "لا توجد حسابات قيد التشغيل لبدء التجميع.")
        return

    send_message_via_http(user_id, f"سيتم بدء التجميع من {bot_name} ({bot_username}) باستخدام {len(active_accounts)} حساب مفعل.")

    for file_stem in active_accounts:
        try:
            # Ensure the task is still running (not cancelled externally)
            task_key = f'custom_{bot_name.split()[0].lower()}' if ' ' in bot_name else f'custom_{bot_name.lower()}'
            if user_id_str not in RUNNING_PROCESSES or task_key not in RUNNING_PROCESSES[user_id_str]:
                 break

            async with TelegramClient(f"echo_ac/{user_id}/{file_stem}", API_ID, API_HASH, device_model="iPhone 15 Pro Max") as client:
                me = await client.get_me()
                if not me:
                    send_message_via_http(user_id, f"الحساب {file_stem} لا يعمل، جاري التخطي.")
                    continue

                my_user_id = me.id
                destination_id = send_to
                if send_to.lower() == "انا":
                    destination_id = user_id
                elif send_to.lower() == "حساب":
                    destination_id = my_user_id

                send_message_via_http(user_id, f"الحساب: {file_stem}\n- بدء التجميع من بوت {bot_name} (إرسال إلى {destination_id}).")

                channel_entity = await client.get_entity(bot_username)
                
                await client.send_message(bot_username, f'/start {destination_id}')
                await asyncio.sleep(4)

                msg0 = await client.get_messages(bot_username, limit=1)
                if msg0 and hasattr(msg0[0], 'click') and len(msg0[0].reply_markup.rows) > 2: # Ensure it has enough buttons
                    await msg0[0].click(2)
                    await asyncio.sleep(4)
                
                msg1 = await client.get_messages(bot_username, limit=1)
                if msg1 and hasattr(msg1[0], 'click'):
                    await msg1[0].click(0)
                
                chs = 0
                for i in range(100):
                    if user_id_str not in RUNNING_PROCESSES or task_key not in RUNNING_PROCESSES[user_id_str]: break

                    await asyncio.sleep(4)
                    
                    list_hist = await client(GetHistoryRequest(peer=channel_entity, limit=1, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
                    msgs = list_hist.messages[0]

                    if msgs.message and 'لا يوجد قنوات' in msgs.message:
                        send_message_via_http(user_id, f"الحساب: {file_stem}\n- انتهى التجميع، لا يوجد قنوات.")
                        break

                    if not hasattr(msgs, 'reply_markup') or not msgs.reply_markup:
                        await asyncio.sleep(2)
                        continue

                    url = None
                    try:
                        if msgs.reply_markup.rows[0].buttons[0].url:
                            url = msgs.reply_markup.rows[0].buttons[0].url
                    except (IndexError, AttributeError):
                        pass

                    try:
                        is_damkom_join_request = (bot_username == '@DamKombot' and msgs.message and "اشترك فالقناة @" in msgs.message)

                        if url or is_damkom_join_request:
                            if is_damkom_join_request:
                                channel_to_join = msgs.message.split('@')[1].split()[0]
                                entity = await client.get_entity(channel_to_join)
                                if entity: await client(JoinChannelRequest(entity.id))
                            else:
                                try:
                                    await client(JoinChannelRequest(url))
                                except:
                                    bott = url.split('/')[-1]
                                    await client(ImportChatInviteRequest(bott))
                            
                            await asyncio.sleep(4)
                            
                            if bot_username == '@MHDN313bot':
                                await msgs.click(text='التالي')
                            elif bot_username == '@DamKombot':
                                await msgs.click(text='اشتركت ✅')
                            else: 
                                msg_after_join = await client.get_messages(bot_username, limit=1)
                                if msg_after_join and hasattr(msg_after_join[0], 'click'):
                                    await msg_after_join[0].click(text='تحقق')
                            
                            chs += 1
                            send_message_via_http(user_id, f"الحساب: {file_stem}\n- ✅ تم الاشتراك بقناة/تحقق. (القناة #{chs})")
                        
                        else:
                            try:
                                await msgs.click(text='التالي')
                            except Exception:
                                pass
                            send_message_via_http(user_id, f"الحساب: {file_stem}\n- تم التخطي/الضغط على التالي.")

                    except Exception as e:
                        send_message_via_http(user_id, f"الحساب: {file_stem}\n- تخطي القناة الحالية بسبب خطأ: {e}")
                        try:
                            await msgs.click(text='التالي')
                        except Exception:
                            pass
                        continue
                        
                send_message_via_http(user_id, f"الحساب: {file_stem}\n- تم الانتهاء من التجميع (Total: {chs} joins).")
        
        except asyncio.CancelledError:
            send_message_via_http(user_id, f"الحساب: {file_stem}\n- تم إيقاف التجميع.")
            break
        except Exception as e:
            send_message_via_http(user_id, f"الحساب: {file_stem}\n- حدث خطأ فادح: {str(e)}")

    send_message_via_http(user_id, f"اكتملت عملية التجميع المخصصة من {bot_name}.")


async def run_mahdaweon_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@MHDN313bot', "المهدويون")

async def run_damkom_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@DamKombot', "دعمكم")

async def run_asiasell_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@yynnurybot', "اساسيل")

async def run_billion_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@EEObot', "المليار")

async def run_cr7_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@PPAHSBOT', "كرستيانو")

async def run_joker_collector_for_all_accounts(user_id, send_to):
    await run_custom_collector(user_id, send_to, '@A_MAN9300BOT', "الجوكر")