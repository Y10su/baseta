# --- استدعاء المكتبات الأساسية أولاً ---
import os
import json
import asyncio

# إعداد حلقة الأحداث (مهم جداً لريندر)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from aiohttp import web
from pyrogram import Client, idle, filters
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus

# --- قراءة الإعدادات من متغيرات بيئة ريندر ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", 0)) # تأكد أن هذا المتغير في ريندر يحتوي على رقمك فقط

# اسم ملف الجائزة 
FILE_TO_SEND = "prize_file.pdf" 
DB_FILE = "sent_messages.json"

# --- دوال قاعدة البيانات ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# --- خادم الويب الوهمي لـ Render ---
async def handle_ping(request):
    return web.Response(text="النظام المزدوج (البوت + اليوزر بوت) يعمل بنجاح!")

async def run_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', handle_ping)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"تم تشغيل خادم الويب على البورت {port}")

# ====================================================
# --- إعداد العميلين (البوت الرسمي واليوزر بوت) ---
# ====================================================
# العميل الأول: اليوزر بوت (اليد التي ترسل الملفات)
app_user = Client("my_userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# العميل الثاني: البوت الرسمي (العين التي تراقب وترسل لك الإشعارات)
app_bot = Client("my_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# دالة إرسال التقارير لحسابك
async def send_report(message):
    try:
        await app_bot.send_message(chat_id=MY_CHAT_ID, text=message)
    except Exception as e:
        print(f"فشل إرسال التقرير: {e}")

# نربط "مستمع الأحداث" بالـ (البوت الرسمي) لأنه هو من يملك صلاحية رؤية القناة
@app_bot.on_chat_member_updated(filters.chat(CHANNEL_ID))
async def handle_channel_changes(client: Client, chat_member_updated: ChatMemberUpdated):
    new_member = chat_member_updated.new_chat_member
    old_member = chat_member_updated.old_chat_member
    
    user_id = chat_member_updated.from_user.id
    user_name = chat_member_updated.from_user.first_name or "مستخدم"
    
    db = load_db()

    # أولاً: حالة الانضمام للقناة
    if new_member and new_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not old_member or old_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await asyncio.sleep(4) 
            try:
                # نستخدم (اليوزر بوت) لإرسال الملف في الخاص
                msg = await app_user.send_document(
                    chat_id=user_id,
                    document=FILE_TO_SEND,
                    caption="🎁 أهلاً بك في القناة! إليك ملف الجائزة الخاص بك.\n⚠️ تنبيه: في حال مغادرتك للقناة سيتم سحب الملف وحذفه تلقائياً!"
                )
                db[str(user_id)] = msg.id
                save_db(db)
                await send_report(f"✅ تم إرسال الملف بنجاح لـ: {user_name}")
            except Exception as e:
                await send_report(f"❌ فشل إرسال الملف لـ {user_name}\nالسبب: {e}")

    # ثانياً: حالة المغادرة من القناة
    elif old_member and old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not new_member or new_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            if str(user_id) in db:
                msg_id = db[str(user_id)]
                try:
                    # نستخدم (اليوزر بوت) لحذف الملف من الخاص
                    await app_user.delete_messages(chat_id=user_id, message_ids=msg_id, revoke=True)
                    await send_report(f"🗑️ العضو غادر وتم سحب الملف بنجاح: {user_name}")
                    del db[str(user_id)]
                    save_db(db)
                except Exception as e:
                    pass

# --- دالة التشغيل الأساسية ---
async def start_all():
    await run_web_server()
    
    # تشغيل العميلين معاً في نفس الوقت
    await app_user.start()
    await app_bot.start()
    
    await send_report("🚀 تم تشغيل النظام المزدوج بنجاح!\n(البوت الرسمي يراقب القناة 👀، واليوزر بوت مستعد لإرسال الملفات 🤝)")
    
    await idle()
    
    await app_user.stop()
    await app_bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(start_all())
