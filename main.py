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

# اسم الملف 
FILE_TO_SEND = "baseta_interview.pdf" 
BROADCAST_DB = "broadcast_db.json"

# --- دوال قاعدة بيانات الإرسال ---
def load_broadcast_db():
    if os.path.exists(BROADCAST_DB):
        try:
            with open(BROADCAST_DB, "r") as f: return json.load(f)
        except: pass
    return []

def save_broadcast_db(data):
    with open(BROADCAST_DB, "w") as f: json.dump(data, f)

# --- خادم الويب ---
async def handle_ping(request):
    return web.Response(text="نظام الإرسال البطيء يعمل!")

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

# --- مهمة الإرسال البطيء ---
async def slow_broadcast_task():
    await send_report("⏳ جاري جلب قائمة الأعضاء الحاليين من القناة...")
    
    sent_users = load_broadcast_db()
    members_to_message = [] 

    try:
        async for member in app_user.get_chat_members(CHANNEL_ID):
            user = member.user
            if not user.is_bot and not user.is_deleted:
                if str(user.id) not in sent_users:
                    name = user.first_name or "عضو"
                    members_to_message.append((user.id, name))
                    
        total_targets = len(members_to_message)
        await send_report(f"📊 الإحصائيات:\n- إجمالي المستهدفين المتبقين: {total_targets} عضو.\n\n🚀 ستبدأ حملة الإرسال الآن...")
    except Exception as e:
        await send_report(f"❌ حدث خطأ أثناء قراءة القناة.\nالخطأ: `{e}`")
        return

    success_count = 0
    for uid, name in members_to_message:
        try:
            # --- الرسالة الأولى (ترحيب مع ذكر الاسم لكسر تطابق الرسائل) ---
            await app_user.send_chat_action(chat_id=uid, action=ChatAction.TYPING)
            await asyncio.sleep(random.uniform(3.0, 5.0)) 
            
            await app_user.send_message(
                chat_id=uid,
                text=f"يا هلا بك يا {name} في عائلة \"بسيطة\" 💚👋\nأول شيء، خذ هديتك اللي وعدناك فيها.. ملف \"أسرار المقابلات الشخصية\" جاهز للتحميل الحين 👇"
            )
            await asyncio.sleep(random.uniform(2.0, 4.0)) 
            
            # --- الرسالة الثانية (الملف) ---
            await app_user.send_chat_action(chat_id=uid, action=ChatAction.UPLOAD_DOCUMENT)
            await asyncio.sleep(random.uniform(4.0, 6.0)) 
            
            await app_user.send_document(
                chat_id=uid,
                document=FILE_TO_SEND
            )
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # --- الرسالة الثالثة (من إحنا) ---
            await app_user.send_chat_action(chat_id=uid, action=ChatAction.TYPING)
            await asyncio.sleep(random.uniform(4.0, 7.0))
            
            await app_user.send_message(
                chat_id=uid,
                text="من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
            )
            
            sent_users.append(str(uid))
            save_broadcast_db(sent_users)
            success_count += 1
            
            delay = random.uniform(45.0, 75.0)
            
            report_msg = (
                f"✅ **تم الإرسال بنجاح!**\n"
                f"👤 العضو: [{name}](tg://user?id={uid})\n"
                f"📈 العدد المنجز: {success_count} من أصل {total_targets}\n"
                f"⏳ سآخذ فترة راحة لمدة **{int(delay)} ثانية**..."
            )
            await send_report(report_msg)
            
            await asyncio.sleep(delay)
            
        except FloodWait as e:
            wait_time = e.value + 10
            await send_report(f"🚨 تحذير: تيليجرام يطلب التهدئة. سأتوقف عن الإرسال لمدة {wait_time} ثانية...")
            await asyncio.sleep(wait_time)
        except UserPrivacyRestricted:
            await send_report(f"⚠️ تجاوزت العضو [{name}](tg://user?id={uid}) لأنه مقفل الخاص.")
            sent_users.append(str(uid))
            save_broadcast_db(sent_users)
        except PeerIdInvalid:
            await send_report(f"⚠️ تجاوزت العضو [{name}](tg://user?id={uid}) (حساب محذوف).")
            sent_users.append(str(uid))
            save_broadcast_db(sent_users)
        except Exception as e:
            # هنا التعديل الأهم: سيتم إرسال الخطأ بالتفصيل لبوت الأحداث
            error_text = str(e)
            if "PEER_FLOOD" in error_text:
                await send_report(f"❌ فشل الإرسال للعضو [{name}](tg://user?id={uid})\nالسبب: 🚨 حظر `PEER_FLOOD` (حسابك مقيد من إرسال رسائل جديدة).")
            else:
                await send_report(f"❌ فشل الإرسال للعضو [{name}](tg://user?id={uid})\nالسبب: `{error_text}`")
            
            await asyncio.sleep(15) # انتظار أطول قليلاً بعد الخطأ

    if total_targets > 0:
        await send_report(f"🏁 انتهت حملة الإرسال!\nتم توصيل الجائزة لـ {success_count} من أصل {total_targets}.")
    else:
        await send_report("✅ لا يوجد أشخاص للإرسال لهم.")

async def start_all():
    await run_web_server()
    await app_user.start()
    await app_bot.start()
    asyncio.create_task(slow_broadcast_task())
    await idle()
    await app_user.stop()
    await app_bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(start_all())
