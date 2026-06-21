import os
import json
import asyncio
import random

# إعداد حلقة الأحداث 
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from aiohttp import web
from pyrogram import Client, idle
from pyrogram.enums import ChatAction
from pyrogram.errors import FloodWait, UserPrivacyRestricted, PeerIdInvalid

# --- الإعدادات ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", 0))

channel_env = os.environ.get("CHANNEL_ID", "0")
try:
    CHANNEL_ID = int(channel_env)
except ValueError:
    CHANNEL_ID = channel_env 

FILE_TO_SEND = "baseta_interview.pdf" 
DB_FILE = "sent_messages.json"

# --- دوال قاعدة البيانات ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

# --- خادم الويب ---
async def handle_ping(request):
    return web.Response(text="النظام الآمن يعمل بنجاح!")

async def run_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', handle_ping)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- إعداد العملاء ---
app_user = Client("my_userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
app_bot = Client("my_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

async def send_report(message):
    try: await app_bot.send_message(chat_id=MY_CHAT_ID, text=message)
    except: pass

# --- نظام الفحص المستمر الآمن (كل 30 ثانية) ---
async def polling_task():
    await send_report(f"⏳ جاري تهيئة النظام ومسح الأعضاء الحاليين في ({CHANNEL_ID})...")
    
    known_members = set()
    try:
        async for member in app_user.get_chat_members(CHANNEL_ID):
            known_members.add(member.user.id)
        await send_report(f"✅ تم حفظ {len(known_members)} عضو سابق بنجاح.\n\n🔄 سيبدأ البوت الآن بفحص القناة كل 30 ثانية...")
    except Exception as e:
        await send_report(f"❌ حدث خطأ أثناء قراءة القناة.\nالخطأ: `{e}`")
        return

    while True:
        await asyncio.sleep(30) # الفحص كل نصف دقيقة
        try:
            current_members = set()
            async for member in app_user.get_chat_members(CHANNEL_ID):
                current_members.add(member.user.id)
            
            new_members = current_members - known_members
            left_members = known_members - current_members
            
            db = load_db()
            
            # 1. التعامل مع المنضمين الجدد ببطء ومحاكاة بشرية
            if new_members:
                await send_report(f"🔍 تم رصد {len(new_members)} أعضاء جدد! جاري الإرسال بوضع المحاكاة البشرية...")
                success_count = 0
                
                for uid in new_members:
                    try:
                        # --- الرسالة الأولى (ترحيب) ---
                        await app_user.send_chat_action(chat_id=uid, action=ChatAction.TYPING)
                        await asyncio.sleep(random.uniform(2.5, 4.0)) 
                        
                        msg1 = await app_user.send_message(
                            chat_id=uid,
                            text="يا هلا بك في عائلة \"بسيطة\" 💚👋\nأول شيء، خذ هديتك اللي وعدناك فيها.. ملف \"أسرار المقابلات الشخصية\" جاهز للتحميل الحين 👇"
                        )
                        await asyncio.sleep(random.uniform(1.5, 3.0)) 
                        
                        # --- الرسالة الثانية (الملف) ---
                        await app_user.send_chat_action(chat_id=uid, action=ChatAction.UPLOAD_DOCUMENT)
                        await asyncio.sleep(random.uniform(3.5, 5.0)) 
                        
                        msg2 = await app_user.send_document(
                            chat_id=uid,
                            document=FILE_TO_SEND
                        )
                        await asyncio.sleep(random.uniform(2.0, 3.5))
                        
                        # --- الرسالة الثالثة (من إحنا) ---
                        await app_user.send_chat_action(chat_id=uid, action=ChatAction.TYPING)
                        await asyncio.sleep(random.uniform(3.0, 5.5))
                        
                        msg3 = await app_user.send_message(
                            chat_id=uid,
                            text="من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
                        )
                        
                        db[str(uid)] = [msg1.id, msg2.id, msg3.id]
                        success_count += 1
                        
                        delay_between_users = random.uniform(15.0, 30.0)
                        await asyncio.sleep(delay_between_users)
                        
                    except FloodWait as e:
                        wait_time = e.value + 10
                        await send_report(f"🚨 تحذير أمني: تيليجرام يطلب التهدئة. سأتوقف عن الإرسال لمدة {wait_time} ثانية لحماية الحساب...")
                        await asyncio.sleep(wait_time)
                    except UserPrivacyRestricted:
                        await send_report(f"⚠️ العضو ذو الآيدي `{uid}` مقفل الخاص.")
                    except PeerIdInvalid:
                        await send_report(f"⚠️ لم أتمكن من بدء المحادثة مع `{uid}`.")
                    except Exception as e:
                        await send_report(f"❌ فشل الإرسال للعضو `{uid}`\nالسبب: `{e}`")
                    
                    known_members.add(uid)
                
                save_db(db)
                if success_count > 0:
                    await send_report(f"✅ اكتمل الإرسال! تم تسليم الجائزة لـ {success_count} أعضاء بأمان.")

            # 2. التعامل مع المغادرين 
            if left_members:
                removed_count = 0
                for uid in left_members:
                    if str(uid) in db:
                        try:
                            messages_to_delete = db[str(uid)]
                            if not isinstance(messages_to_delete, list):
                                messages_to_delete = [messages_to_delete]
                                
                            await app_user.delete_messages(chat_id=uid, message_ids=messages_to_delete, revoke=True)
                            del db[str(uid)]
                            removed_count += 1
                            await asyncio.sleep(1)
                        except: pass
                    known_members.remove(uid)
                
                save_db(db)
                if removed_count > 0:
                    await send_report(f"🗑️ تم رصد مغادرة أعضاء، وتم سحب جميع الرسائل من {removed_count} أشخاص.")
            
            # 3. إرسال تقرير الفحص الدوري (حتى لو مافي أحد جديد)
            if not new_members and not left_members:
                await send_report("🔄 تم الفحص (30 ثانية): لا يوجد أعضاء جدد أو مغادرين.")
                    
        except Exception as e:
            print(f"Polling loop error: {e}")

# --- دالة التشغيل الأساسية ---
async def start_all():
    await run_web_server()
    await app_user.start()
    await app_bot.start()
    asyncio.create_task(polling_task())
    await idle()
    await app_user.stop()
    await app_bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(start_all())
