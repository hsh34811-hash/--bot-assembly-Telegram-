# =============================================
# Developer : ✘ 𝙍𝘼𝙑𝙀𝙉
# Telegram  : @P_X_24
# =============================================

import logging
import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telethon import TelegramClient, errors


from config import API_ID, API_HASH, SUDO_ID, RUNNING_PROCESSES, WHAT_NEED_TO_DO_ECHO, POINTS_DATA
from data import INFO, save_info
from client import (
    start_background_task, stop_background_task, stop_all_background_tasks,
    delall_sessions, copynum_sessions,
    join_channel_sync, start_bot_via_link, join_via_invite, leave_a_channel_sync,
    boost_post_vote, boost_post_views, boost_poll_vote, spam_messages,
    process_account_action_sync,
    run_mahdaweon_collector_for_all_accounts, run_damkom_collector_for_all_accounts,
    run_asiasell_collector_for_all_accounts, run_billion_collector_for_all_accounts,
    run_cr7_collector_for_all_accounts, run_joker_collector_for_all_accounts
)

logger = logging.getLogger(__name__)

def check_access(user_id):
    """Checks if a user has access rights (sudo, admin, vip, or trial)."""
    user_id_str = str(user_id)

    if user_id_str == str(INFO.get("sudo")):
        return True
    if user_id_str in INFO.get("admins", {}):
        return True
    if INFO.get("bot_mode") == "free":
        return True

    now_ts = datetime.now().timestamp()
    
    
    if user_id_str in INFO.get("vips", {}):
        expiration = INFO["vips"][user_id_str]
        if now_ts < expiration:
            return True
        else:
            del INFO["vips"][user_id_str]
            save_info(INFO)
            
    
    if user_id_str in INFO.get("trial_users", {}):
        expiration = INFO["trial_users"][user_id_str]
        if now_ts < expiration:
            return True
        else:
            del INFO["trial_users"][user_id_str]
            save_info(INFO)
            return False

    return False

def contact_validate(text):
    """Simple validation for Telegram phone number format."""
    text = str(text)
    return len(text) > 0 and text[0] == '+' and text[1:].isdigit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, shows main menu, checks access/trial."""
    if not update.message or update.message.chat.type != "private":
        return

    chat_id = update.message.chat.id
    chat_id_str = str(chat_id)

    if not check_access(chat_id):
        trial_settings = INFO.get("trial_settings", {})
        if trial_settings.get("enabled") and chat_id_str not in INFO.get("trial_users", {}):
            duration_hours = trial_settings.get("duration_hours", 2)
            expiration_time = datetime.now() + timedelta(hours=duration_hours)
            INFO["trial_users"][chat_id_str] = expiration_time.timestamp()
            save_info(INFO)
            await update.message.reply_text(f"مرحباً بك! لقد حصلت على فترة تجريبية لمدة {duration_hours} ساعة لاستخدام البوت.")
        else:
            await update.message.reply_text("عذراً، ليس لديك صلاحية لاستخدام هذا البوت.")
            return

    if not os.path.isdir(f"echo_ac/{chat_id_str}"):
        os.makedirs(f"echo_ac/{chat_id_str}")

    WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""

    user_name = update.message.from_user.first_name
    directory_path = Path(f"echo_ac/{chat_id_str}")
    num_accounts = len(list(directory_path.glob('*.session'))) if directory_path.is_dir() else 0
    
    user_points_for_display = POINTS_DATA.get(chat_id_str, {})
    total_points = sum(user_points_for_display.values())
    speed = INFO.get('sleeptime', 20)

    reply_text = (
        f"أهلاً بك، {user_name}!\n\n"
        f"سرعة التجميع: {speed} ثانية\n"
        f"عدد الأرقام: {num_accounts}\n"
        f"النقاط المجمعة: {total_points}"
    )

    is_sudo = chat_id_str == str(INFO["sudo"])
    
    keyboard = [
        [InlineKeyboardButton("اضافه رقم", callback_data="addecho"), InlineKeyboardButton("مسح رقم", callback_data="delecho")],
        [InlineKeyboardButton("الارقام الخاصه بك", callback_data="myecho"), InlineKeyboardButton("عدد نقاطك", callback_data="mypoints")],
        [InlineKeyboardButton("رشق قناة", callback_data="joinchn"), InlineKeyboardButton("دخول رابط دعوة", callback_data="join_invite_link")],
        [InlineKeyboardButton("رشق تصويت", callback_data="boost_vote"), InlineKeyboardButton("رشق مشاهدات", callback_data="boost_views")],
        [InlineKeyboardButton("رشق استفسار", callback_data="boost_poll"), InlineKeyboardButton("إرسال سبام", callback_data="spam_message")],
        [InlineKeyboardButton("مغادرة قناة", callback_data="leave_specific_chn"), InlineKeyboardButton("مسح كل القنوات", callback_data="leavechn")],
        [InlineKeyboardButton("مسح قنوات (+7 ايام)", callback_data="leave_7d_collection"), InlineKeyboardButton("سرعه التجميع", callback_data="sleeptime")],
        [InlineKeyboardButton("تحويل تمبلر", callback_data="templer"), InlineKeyboardButton("تجميع النقاط", callback_data="custom_collect")],
        [InlineKeyboardButton("إيقاف كل التجميع", callback_data="stop_all_collection")],
    ]

    if is_sudo:
        keyboard.append([InlineKeyboardButton("اضافه ادمن", callback_data="addadminecho"), InlineKeyboardButton("مسح ادمن", callback_data="deladminecho")])
        keyboard.append([InlineKeyboardButton("ملف ارقام", callback_data="copynum"), InlineKeyboardButton("مسح جميع الحسابات", callback_data="delall")])
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم المطور", callback_data="admin_panel_home")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply_text, reply_markup=reply_markup)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sudo panel entry point."""
    chat_id_str = str(update.message.chat.id)
    if chat_id_str != str(INFO["sudo"]):
        return

    mode_text = "مجاني للكل" if INFO.get("bot_mode") == "free" else "مدفوع (للمشتركين فقط)"
    trial_text = "مفعلة" if INFO.get("trial_settings", {}).get("enabled") else "معطلة"
    trial_duration = INFO.get("trial_settings", {}).get("duration_hours", 2)

    keyboard = [
        [InlineKeyboardButton(f"وضع البوت: {mode_text}", callback_data="toggle_mode")],
        [InlineKeyboardButton("إدارة عضوية VIP", callback_data="manage_vip")],
        [InlineKeyboardButton(f"الفترة التجريبية: {trial_text}", callback_data="toggle_trial")],
        [InlineKeyboardButton(f"مدة التجربة: {trial_duration} ساعات", callback_data="set_trial_duration")],
        [InlineKeyboardButton("إدارة الأدمنية", callback_data="myadminsecho")],
        [InlineKeyboardButton("رجوع للقائمة الرئيسية", callback_data="sudohome")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ لوحة تحكم المطور", reply_markup=reply_markup)

async def echoMaker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles conversational state messages for Telethon actions."""
    if not update.message or update.message.chat.type != "private":
        return

    chat_id_str = str(update.message.chat.id)
    if not check_access(chat_id_str):
        return

 
    if chat_id_str in WHAT_NEED_TO_DO_ECHO and WHAT_NEED_TO_DO_ECHO[chat_id_str] == "get_spam_message":
        spam_info = {"text": None, "file_path": None}
        message = update.message

        media_file_id = None
        if message.photo:
            media_file_id = message.photo[-1].file_id
        elif message.document:
            media_file_id = message.document.file_id
        elif message.video:
            media_file_id = message.video.file_id
        elif message.audio:
            media_file_id = message.audio.file_id
        elif message.voice:
            media_file_id = message.voice.file_id

        spam_info["text"] = message.text or message.caption

        if media_file_id:
            try:
                new_file = await context.bot.get_file(media_file_id)
                temp_dir = Path("temp_spam")
                temp_dir.mkdir(exist_ok=True)
                file_ext = Path(new_file.file_path).suffix if new_file.file_path else '.dat'
                file_path = temp_dir / f"{chat_id_str}_{datetime.now().timestamp()}{file_ext}"
                await new_file.download_to_drive(custom_path=file_path)
                spam_info["file_path"] = str(file_path)
            except Exception as e:
                await update.message.reply_text(f"حدث خطأ أثناء معالجة الملف: {e}")
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                return

        if not spam_info["text"] and not spam_info["file_path"]:
            await update.message.reply_text("لا يمكن إرسال هذه الرسالة (فارغة أو نوع غير مدعوم).")
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            return

        WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}_spam_details"] = spam_info
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_spam_count"
        await update.message.reply_text("تم حفظ الرسالة. الآن أرسل عدد المرات التي تريد تكرارها:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        return
    
    text = update.message.text
    if not text:
        return

    if chat_id_str in WHAT_NEED_TO_DO_ECHO and WHAT_NEED_TO_DO_ECHO[chat_id_str]:
        action = WHAT_NEED_TO_DO_ECHO[chat_id_str]

        
        if action == "addecho":
            if not contact_validate(text):
                await update.message.reply_text("ارسل رقم صحيح", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                return
            
            client = TelegramClient(f"echo_ac/{chat_id_str}/{text}", API_ID, API_HASH, device_model="iPhone 15 Pro Max")
            try:
                await client.connect()
                WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}:phone"] = text
                sent_code = await client.send_code_request(text)
                WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}:phone_code_hash"] = sent_code.phone_code_hash
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = "echocode"
                await update.message.reply_text("ارسل رمز تسجيل الدخول:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except Exception as e:
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                await update.message.reply_text(f"حدث خطأ: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            finally:
                if client.is_connected():
                    await client.disconnect()

        elif action == "echocode":
            WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}code"] = text
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = "anthercode"
            await update.message.reply_text("ارسل رمز التحقق بخطوتين (اذا لم يكن هناك رمز ارسل اي شيء):")

        elif action == "anthercode":
            phone = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}:phone", None)
            code = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}code", None)
            phone_code_hash = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}:phone_code_hash", None)
            
            if not (phone and code and phone_code_hash):
                await update.message.reply_text("خطأ في البيانات. يرجى البدء من جديد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                return

            client = TelegramClient(f"echo_ac/{chat_id_str}/{phone}", API_ID, API_HASH, device_model="iPhone 15 Pro Max")
            try:
                await client.connect()
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                await update.message.reply_text(f"تم تسجيل الدخول بنجاح: {phone}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except errors.SessionPasswordNeededError:
                await client.sign_in(password=text)
                await update.message.reply_text(f"تم تسجيل الدخول بنجاح: {phone}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except Exception as e:
                await update.message.reply_text(f"حدث خطأ أثناء تسجيل الدخول: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            finally:
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                if client.is_connected():
                    await client.disconnect()

        
        elif action.startswith("collect_bot_user:"):
            parts = action.split(":")
            target = parts[1]
            duration = parts[2]
            bot_user = text.lstrip('@')
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = f"collect_send_to:{target}:{duration}:{bot_user}"
            await update.message.reply_text(
                "ارسل ايدي الحساب الذي تريد التجميع له نقاط:\n\n"
                "- ارسل 'انا' لارسال النقاط لحسابك\n"
                "- ارسل 'حساب' لارسال النقاط لنفس الحساب",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="myecho")]]))

        elif action.startswith("collect_send_to:"):
            parts = action.split(":")
            target = parts[1]
            duration_seconds = int(parts[2])
            bot_user = parts[3]
            send_to = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            
            if target == "all":
                await update.message.reply_text(f"تم بدء التجميع لجميع الحسابات من {bot_user} لمدة محددة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                directory_path = Path(f"echo_ac/{chat_id_str}")
                if directory_path.is_dir():
                    file_list = [file.stem for file in directory_path.glob('*.session')]
                    for filename in file_list:
                        start_background_task(filename, bot_user, chat_id_str, send_to, duration_seconds)
            else:
                filename = target
                await update.message.reply_text(f"تم بدء التجميع للحساب {filename} من {bot_user} لمدة محددة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                start_background_task(filename, bot_user, chat_id_str, send_to, duration_seconds)

        elif action.startswith("custom_collect_send_to:"):
            parts = action.split(":")
            bot_type = parts[1]
            duration_seconds = int(parts[2])
            send_to = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""

            BOT_MAP = {
                "mahdaweon": ("المهدويون", run_mahdaweon_collector_for_all_accounts),
                "damkom": ("دعمكم", run_damkom_collector_for_all_accounts),
                "asiasell": ("اساسيل", run_asiasell_collector_for_all_accounts),
                "billion": ("المليار", run_billion_collector_for_all_accounts),
                "cr7": ("كرستيانو", run_cr7_collector_for_all_accounts),
                "joker": ("الجوكر", run_joker_collector_for_all_accounts),
            }
            
            bot_name, collector_func = BOT_MAP.get(bot_type, (None, None))
            
            if collector_func:
                await update.message.reply_text(f"✅ تم بدء التجميع من بوت {bot_name} لمدة محددة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

                task_key = f'custom_{bot_type}'
                if chat_id_str not in RUNNING_PROCESSES: RUNNING_PROCESSES[chat_id_str] = {}

                collection_task = asyncio.create_task(collector_func(chat_id_str, send_to))
                RUNNING_PROCESSES[chat_id_str][task_key] = collection_task

                async def stop_after_delay(task, delay, user_id, bot_name_text, t_key):
                    if delay == 0: return # 
                    await asyncio.sleep(delay)
                    if user_id in RUNNING_PROCESSES and t_key in RUNNING_PROCESSES[user_id]:
                        if not task.done(): task.cancel()
                        RUNNING_PROCESSES[user_id].pop(t_key, None)

                asyncio.create_task(stop_after_delay(collection_task, duration_seconds, chat_id_str, bot_name, task_key))
            else:
                await update.message.reply_text("خطأ: نوع البوت المخصص غير معروف.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))


        
        elif action == "get_invite_link":
            link = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            if re.search(r"t\\.me/([^?]+)\\?start=", link):
                await update.message.reply_text("تم التعرف على رابط بدء بوت. جاري بدء إرسال الأوامر...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                asyncio.create_task(start_bot_via_link(chat_id_str, link))
            elif "t.me/+" in link or "telegram.me/+" in link or "joinchat/" in link:
                await update.message.reply_text("تم التعرف على رابط دعوة. جاري بدء عملية الانضمام...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                asyncio.create_task(join_via_invite(chat_id_str, link))
            else:
                await update.message.reply_text("الرابط الذي أرسلته غير مدعوم أو غير صالح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "joinchn_getuser":
            chn = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            await update.message.reply_text("انتظر جاري الانضمام...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            asyncio.create_task(join_channel_sync(chat_id_str, chn))

        elif action == "leavechn_getuser":
            chn = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            await update.message.reply_text("انتظر جاري المغادرة...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            asyncio.create_task(leave_a_channel_sync(chat_id_str, chn))

        elif action == "get_vote_link":
            link = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            if "t.me" in link and "/" in link:
                await update.message.reply_text("تم استلام الرابط. جاري بدء عملية التصويت...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                asyncio.create_task(boost_post_vote(chat_id_str, link))
            else:
                await update.message.reply_text("الرابط غير صالح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "get_views_link":
            link = text.strip()
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            if "t.me" in link and "/" in link:
                await update.message.reply_text("تم استلام الرابط. جاري بدء عملية زيادة المشاهدات...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                asyncio.create_task(boost_post_views(chat_id_str, link))
            else:
                await update.message.reply_text("الرابط غير صالح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "get_poll_link":
            link = text.strip()
            if "t.me" in link and "/" in link:
                WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}_poll_link"] = link
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_poll_option"
                await update.message.reply_text("تم استلام الرابط. الآن أرسل رقم الخيار الذي تريد التصويت له (مثال: 1):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            else:
                await update.message.reply_text("الرابط غير صالح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "get_poll_option":
            try:
                option = int(text)
                link = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}_poll_link", None)
                if link:
                    WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                    await update.message.reply_text(f"تم استلام رقم الخيار ({option}). جاري بدء عملية التصويت...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                    asyncio.create_task(boost_poll_vote(chat_id_str, link, option))
                else:
                    await update.message.reply_text("حدث خطأ ما، لم يتم العثور على الرابط.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح للخيار.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "get_spam_count":
            try:
                count = int(text)
                if count <= 0:
                    await update.message.reply_text("الرجاء إدخال عدد أكبر من صفر.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                    return
                WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}_spam_count"] = count
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_spam_target"
                await update.message.reply_text(f"سيتم تكرار الرسالة {count} مرة.\n\nالآن أرسل يوزر المجموعة أو الشخص المستهدف (مثال: @username):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

        elif action == "get_spam_target":
            target_username = text.strip()
            spam_details = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}_spam_details", None)
            count = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}_spam_count", None)

            if not all([spam_details, count]):
                await update.message.reply_text("حدث خطأ ما، يرجى البدء من جديد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                return

            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            await update.message.reply_text("جاري بدء عملية الإرسال...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            asyncio.create_task(spam_messages(chat_id_str, spam_details, count, target_username))

        
        elif action == "sleeptime":
            try:
                INFO["sleeptime"] = int(text)
                save_info(INFO)
                await update.message.reply_text("تم الحفظ بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            finally:
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""

        elif action == "deladminecho":
            admin_id_to_del = text.strip()
            if admin_id_to_del in INFO.get("admins", {}):
                del INFO["admins"][admin_id_to_del]
                save_info(INFO)
                stop_all_background_tasks(admin_id_to_del)
                await update.message.reply_text("تم مسح الادمن بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            else:
                await update.message.reply_text("لا يوجد هكذا ادمن.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""

        elif action == "addadminecho":
            admin_id_to_add = text.strip()
            if not os.path.isdir(f"echo_ac/{admin_id_to_add}"):
                os.makedirs(f"echo_ac/{admin_id_to_add}")
            INFO["admins"][admin_id_to_add] = "5"
            save_info(INFO)
            await update.message.reply_text("تم اضافه ادمن جديد بنجاح.\n\n- يمكن للادمن اضافه 5 حسابات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
            
        elif action.startswith("setlimt:"):
            admin = action.split(":")[1]
            try:
                limit = int(text)
                INFO["admins"][admin] = str(limit)
                save_info(INFO)
                await update.message.reply_text(f"تم تعيين عدد الحسابات المسموحة للادمن {admin} إلى {limit}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="myadminsecho")]]))
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="myadminsecho")]]))
            finally:
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""

        elif action == "add_vip_get_id":
            try:
                vip_id = int(text)
                WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}_vip_id"] = vip_id
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                keyboard = [
                    [InlineKeyboardButton("بالساعات", callback_data="add_vip_hours"), InlineKeyboardButton("بالأيام", callback_data="add_vip_days")],
                    [InlineKeyboardButton("رجوع", callback_data="manage_vip")]
                ]
                await update.message.reply_text("اختر وحدة الوقت لتفعيل العضوية:", reply_markup=InlineKeyboardMarkup(keyboard))
            except ValueError:
                await update.message.reply_text("الرجاء إدخال ID صحيح (رقم).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="manage_vip")]]))

        elif action == "add_vip_get_duration":
            try:
                duration = int(text)
                vip_id = str(WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}_vip_id"))
                unit = WHAT_NEED_TO_DO_ECHO.pop(f"{chat_id_str}_vip_unit")

                if unit == 'hours':
                    delta = timedelta(hours=duration)
                    unit_text = "ساعة"
                else:
                    delta = timedelta(days=duration)
                    unit_text = "يوم"

                expiration_time = datetime.now() + delta
                INFO["vips"][vip_id] = expiration_time.timestamp()
                save_info(INFO)
                WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                await update.message.reply_text(f"✅ تم تفعيل عضوية VIP للمستخدم {vip_id} لمدة {duration} {unit_text}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="manage_vip")]]))

            except ValueError:
                await update.message.reply_text("الرجاء إدخال مدة صحيحة (رقم).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="manage_vip")]]))
        
        elif action == "set_trial_duration_get_hours":
            try:
                duration_hours = int(text)
                if duration_hours > 0:
                    INFO["trial_settings"]["duration_hours"] = duration_hours
                    save_info(INFO)
                    WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
                    await update.message.reply_text(f"✅ تم تحديد مدة الفترة التجريبية إلى {duration_hours} ساعة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للوحة التحكم", callback_data="admin_panel_home")]]))
                else:
                    await update.message.reply_text("الرجاء إدخال عدد ساعات أكبر من صفر.")
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all Inline Keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    if not query.message or query.message.chat.type != "private":
        return

    chat_id_str = str(query.message.chat.id)
    if not check_access(chat_id_str):
        return

    data = query.data

    async def go_home():
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = ""
        await query.delete_message()
        await start(query, context)

    if data != "stop_all_collection" and data != "sudohome":
        custom_task_active = any(key.startswith('custom_') for key in RUNNING_PROCESSES.get(chat_id_str, {}))
        
        allowed_actions = ["myecho", "delecho", "mypoints", "run:", "stop:", "del:", "addadminecho", "deladminecho", "admin_panel_home", "toggle_mode", "manage_vip", "toggle_trial", "set_trial_duration", "add_vip", "add_vip_hours", "add_vip_days", "myadminsecho", "setlimt:"]
        if custom_task_active and not any(data.startswith(a) for a in allowed_actions):
             await query.answer(text="هذا الزر معطل حالياً لأن هناك عملية تجميع مخصصة قيد التشغيل. يرجى إيقافها أولاً.", show_alert=True)
             return

    if data == "sudohome":
        await go_home()
        return

    

    if data == "addecho":
        limit = float('inf')
        if chat_id_str != str(INFO["sudo"]):
            limit = int(INFO["admins"].get(chat_id_str, 0))

        directory_path = Path(f"echo_ac/{chat_id_str}")
        count = len(list(directory_path.glob('*.session'))) if directory_path.is_dir() else 0

        if count < limit:
            WHAT_NEED_TO_DO_ECHO[chat_id_str] = data
            await query.edit_message_text(text="ارسل رقم الحساب الان:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        else:
            await query.edit_message_text(text=f"لا يمكنك اضافه المزيد من الحسابات! (حدك: {limit})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data in ["leavechn", "templer", "leave_7d_collection"]:
        await query.edit_message_text(text="حسناً، جاري بدأ العملية، قد تستغرق بعض الوقت...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        asyncio.create_task(process_account_action_sync(chat_id_str, data))
        
    elif data == "stop_all_collection":
        stop_all_background_tasks(chat_id_str)
        await query.edit_message_text(
            text="✅ تم إرسال طلب إيقاف لجميع عمليات التجميع النشطة.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع للقائمة الرئيسية", callback_data="sudohome")]]))

    

    elif data == "admin_panel_home":
        await query.delete_message()
        await admin_panel(query, context)

    elif data == "toggle_mode":
        INFO["bot_mode"] = "free" if INFO.get("bot_mode") == "paid" else "paid"
        save_info(INFO)
        await query.delete_message()
        await admin_panel(query, context)

    elif data == "toggle_trial":
        INFO["trial_settings"]["enabled"] = not INFO["trial_settings"].get("enabled", False)
        save_info(INFO)
        await query.delete_message()
        await admin_panel(query, context)

    elif data == "set_trial_duration":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "set_trial_duration_get_hours"
        await query.edit_message_text(text="أرسل مدة الفترة التجريبية بالساعات:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel_home")]]))

    elif data == "manage_vip":
        keyboard = [
            [InlineKeyboardButton("إضافة عضو VIP", callback_data="add_vip")],
            [InlineKeyboardButton("رجوع", callback_data="admin_panel_home")]]
        await query.edit_message_text("إدارة العضوية المميزة (VIP):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_vip":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "add_vip_get_id"
        await query.edit_message_text("أرسل ID المستخدم الذي تريد تفعيل عضويته:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="manage_vip")]]))

    elif data == "add_vip_hours" or data == "add_vip_days":
        unit = 'hours' if data == 'add_vip_hours' else 'days'
        unit_text = "بالساعات" if unit == 'hours' else "بالأيام"
        WHAT_NEED_TO_DO_ECHO[f"{chat_id_str}_vip_unit"] = unit
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "add_vip_get_duration"
        await query.edit_message_text(f"أرسل مدة التفعيل {unit_text}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="manage_vip")]]))

    elif data == "deladminecho":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = data
        await query.edit_message_text(text="ارسل ايدي الادمن الان:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "addadminecho":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = data
        await query.edit_message_text(text="ارسل ايدي الادمن الان:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        
    elif data == "myadminsecho":
        keyboard = [[InlineKeyboardButton(f"{key}", callback_data=f"setlimt:{key}"), InlineKeyboardButton(str(value), callback_data=f"setlimt:{key}")] for key, value in INFO.get("admins", {}).items()]
        keyboard.append([InlineKeyboardButton("رجوع", callback_data="admin_panel_home")])
        await query.edit_message_text("الادمنيه في البوت:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("setlimt:"):
        admin = data.split(":")[1]
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = data
        await query.edit_message_text(f"ارسل عدد الحسابات المسموحة للادمن {admin}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="myadminsecho")]]))

    elif data == "delall":
        await query.edit_message_text(text="جاري مسح جميع الحسابات وإيقاف المهام...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        asyncio.create_task(delall_sessions(chat_id_str))

    elif data == "copynum":
        await query.edit_message_text(text="جاري إرسال نسخ احتياطية...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        asyncio.create_task(copynum_sessions(chat_id_str))

    
    
    elif data == "join_invite_link":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_invite_link"
        await query.edit_message_text(text="أرسل الرابط (رابط دعوة خاص أو رابط بدء بوت):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "joinchn":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "joinchn_getuser"
        await query.edit_message_text(text="ارسل يوزر القناة للانضمام اليها:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "boost_vote":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_vote_link"
        await query.edit_message_text(text="أرسل رابط المنشور الذي تريد التصويت عليه:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "boost_views":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_views_link"
        await query.edit_message_text(text="أرسل رابط المنشور الذي تريد زيادة مشاهداته:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "boost_poll":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_poll_link"
        await query.edit_message_text(text="أرسل رابط منشور الاستفتاء:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "spam_message":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "get_spam_message"
        await query.edit_message_text(text="الآن، أرسل الرسالة (نص، صورة، فيديو، إلخ) التي تريد تكرارها.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "leave_specific_chn":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = "leavechn_getuser"
        await query.edit_message_text(text="ارسل يوزر القناة للمغادرة منها:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    elif data == "sleeptime":
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = data
        await query.edit_message_text(text="يرجى إرسال العدد الذي ترغب فيه من الثواني:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    

    elif data == "delecho":
        directory_path = Path(f"echo_ac/{chat_id_str}")
        file_list = [file.stem for file in directory_path.glob('*.session')] if directory_path.is_dir() else []
        keyboard = [[InlineKeyboardButton(f"{filename}", callback_data=f"del:{filename}"), InlineKeyboardButton("❌", callback_data=f"del:{filename}")] for filename in file_list]
        keyboard.append([InlineKeyboardButton("رجوع", callback_data="sudohome")])
        await query.edit_message_text("الحسابات الخاصة بك:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del:"):
        filename = data.split(":")[1]
        stop_background_task(filename, chat_id_str)
        session_file = f"echo_ac/{chat_id_str}/{filename}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
            await query.edit_message_text(f"تم حذف الرقم: {filename}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="delecho")]]))
        else:
            await query.edit_message_text(f"لا يوجد هكذا رقم: {filename}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="delecho")]]))

    elif data == "mypoints":
        user_points = POINTS_DATA.get(chat_id_str, {})
        if not user_points:
            await query.edit_message_text(text="لا توجد بيانات عن النقاط بعد. يرجى بدء التجميع أولاً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
            return

        message_text = "📊 عدد النقاط الحالي لحساباتك:\n\n"
        for phone, points in user_points.items():
            message_text += f"- الحساب `{phone}`: {points} نقطة\n"

        await query.edit_message_text(text=message_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))
        
    elif data == "myecho":
        directory_path = Path(f"echo_ac/{chat_id_str}")
        file_list = [file.stem for file in directory_path.glob('*.session')] if directory_path.is_dir() else []
        running_tasks = RUNNING_PROCESSES.get(chat_id_str, {})

        custom_task_active = any(key.startswith('custom_') for key in running_tasks)

        keyboard = []

        if custom_task_active:
            keyboard.append([InlineKeyboardButton("⚠️ جاري تجميع مخصص", callback_data="noop")])
            
        for filename in file_list:
            if filename in running_tasks and not custom_task_active:
                button = InlineKeyboardButton(f"{filename}", callback_data=f"stop:{filename}")
                button2 = InlineKeyboardButton("✅ | اضغط للايقاف", callback_data=f"stop:{filename}")
            elif custom_task_active:
                button = InlineKeyboardButton(f"{filename}", callback_data="noop")
                button2 = InlineKeyboardButton("⚙️ (مهام مخصصة)", callback_data="noop")
            else:
                button = InlineKeyboardButton(f"{filename}", callback_data=f"run:{filename}")
                button2 = InlineKeyboardButton("❌ | اضغط للتشغيل", callback_data=f"run:{filename}")
            keyboard.append([button, button2])

        keyboard.append([InlineKeyboardButton("رجوع", callback_data="sudohome")])
        await query.edit_message_text("الحسابات الخاصة بك:\n\n- ✅ = يعمل | ❌ = متوقف", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("run:"):
        target = data.split(":")[1]
        msg_text = f"اختر مدة التجميع للحساب {target}:"

        duration_keyboard = [
            [
                InlineKeyboardButton("يوم", callback_data=f"start_collect:{target}:86400"),
                InlineKeyboardButton("أسبوع", callback_data=f"start_collect:{target}:604800"),
                InlineKeyboardButton("شهر", callback_data=f"start_collect:{target}:2592000")
            ],
            [InlineKeyboardButton("بدون إيقاف محدد", callback_data=f"start_collect:{target}:0")],
            [InlineKeyboardButton("رجوع", callback_data="myecho")]
        ]
        reply_markup = InlineKeyboardMarkup(duration_keyboard)
        await query.edit_message_text(text=msg_text, reply_markup=reply_markup)
        
    elif data.startswith("start_collect:"):
        parts = data.split(":")
        target = parts[1]
        duration = parts[2]
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = f"collect_bot_user:{target}:{duration}"
        await query.edit_message_text(text="ارسل معرف البوت الذي تريد التجميع منه:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="myecho")]]))

    elif data.startswith("stop:"):
        filename = data.split(":")[1]
        stop_background_task(filename, chat_id_str)
        await query.edit_message_text(f"تم ايقاف عمل الرقم: {filename}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="sudohome")]]))

    

    elif data == "custom_collect":
        keyboard = [
            [InlineKeyboardButton("بوت المهدويون", callback_data="collect_mahdaweon")],
            [InlineKeyboardButton("بوت دعمكم", callback_data="collect_damkom")],
            [InlineKeyboardButton("بوت اساسيل", callback_data="collect_asiasell")],
            [InlineKeyboardButton("بوت المليار", callback_data="collect_billion")],
            [InlineKeyboardButton("بوت كرستيانو", callback_data="collect_cr7")],
            [InlineKeyboardButton("بوت الجوكر", callback_data="collect_joker")],
            [InlineKeyboardButton("رجوع", callback_data="sudohome")]]
        await query.edit_message_text("اختر البوت الذي تريد التجميع منه:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("collect_"):
        bot_type = data.split("_")[1]
        bot_name = ""
        if "mahdaweon" in data: bot_name = "المهدويون"
        elif "damkom" in data: bot_name = "دعمكم"
        elif "asiasell" in data: bot_name = "اساسيل"
        elif "billion" in data: bot_name = "المليار"
        elif "cr7" in data: bot_name = "كرستيانو"
        elif "joker" in data: bot_name = "الجوكر"

        duration_keyboard = [
            [
                InlineKeyboardButton("يوم", callback_data=f"start_custom_collect:{bot_type}:86400"),
                InlineKeyboardButton("أسبوع", callback_data=f"start_custom_collect:{bot_type}:604800"),
                InlineKeyboardButton("شهر", callback_data=f"start_custom_collect:{bot_type}:2592000")]
            ,
            [InlineKeyboardButton("بدون إيقاف محدد", callback_data=f"start_custom_collect:{bot_type}:0")],
            [InlineKeyboardButton("رجوع", callback_data="custom_collect")]
        ]
        await query.edit_message_text(text=f"اختر مدة التجميع من بوت {bot_name}:", reply_markup=InlineKeyboardMarkup(duration_keyboard))

    elif data.startswith("start_custom_collect:"):
        parts = data.split(":")
        bot_type = parts[1]
        duration_seconds = parts[2]
        WHAT_NEED_TO_DO_ECHO[chat_id_str] = f"custom_collect_send_to:{bot_type}:{duration_seconds}"
        await query.edit_message_text(
            text="ارسل ايدي الحساب الذي تريد التجميع له نقاط:\n\n"
                 "- ارسل 'انا' لارسال النقاط لحسابك\n"
                 "- ارسل 'حساب' لارسال النقاط لنفس الحساب",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="custom_collect")]]))