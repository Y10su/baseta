import os
import json
import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from aiohttp import web
from pyrogram import Client, idle
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", 0)) 

FILE_TO_SEND = "prize_file.pdf" 
DB_FILE = "sent_messages.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

async def handle_ping(request):
    return web.Response(text="يعمل بنجاح!")

async def run_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', handle_ping)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

app_user = Client("my_userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
app_bot = Client("my_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

async def send_report(message):
    try: await app_bot.send_message(chat_id=MY_CHAT_ID, text=message)
    except: pass

# أزلنا الفلتر الخاص بالقناة لكي يراقب أي قناة هو أدمن فيها
@app_bot.on_chat_member_updated()
async def handle_channel_changes(client: Client, chat_member_updated: ChatMemberUpdated):
    new_member = chat_member_updated.new_chat_member
    old_member = chat_member_updated.old_chat_member
    
    user_id = chat_member_updated.from_user.id
    user_name = chat_member_updated.from_user.first_name or "مستخدم"
    chat_title = chat_member_updated.chat.title
    actual_chat_id = chat_member_updated.chat.id
    
    db = load_db()

    # الانضمام
    if new_member and new_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not old_member or old_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            # رسالة الفحص (ستخبرنا إذا رصد الدخول والآيدي الصحيح)
            await send_report(f"🔍 **تم رصد دخول!**\nالقناة: {chat_title}\nأيدي القناة الفعلي: `{actual_chat_id}`\nالعضو: {user_name}")
            
            await asyncio.sleep(4) 
            try:
                # محاولة الإرسال باستخدام اليوزر بوت
                msg = await app_user.send_document(
                    chat_id=user_id,
                    document=FILE_TO_SEND,
                    caption="🎁 أهلاً بك في القناة! إليك ملف الجائزة الخاص بك.\n⚠️ تنبيه: في حال مغادرتك سيتم سحب الملف تلقائياً!"
                )
                db[str(user_id)] = msg.id
                save_db(db)
                await send_report(f"✅ تم إرسال الملف بنجاح لـ: {user_name}")
            except Exception as e:
                # إذا رصد الدخول لكن فشل في الإرسال سيخبرنا بالسبب
                await send_report(f"❌ فشل إرسال الملف لـ {user_name}\nالسبب: `{e}`")

    # المغادرة
    elif old_member and old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not new_member or new_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            if str(user_id) in db:
                msg_id = db[str(user_id)]
                try:
                    await app_user.delete_messages(chat_id=user_id, message_ids=msg_id, revoke=True)
                    await send_report(f"🗑️ العضو غادر وتم سحب الملف بنجاح: {user_name}")
                    del db[str(user_id)]
                    save_db(db)
                except: pass

async def start_all():
    await run_web_server()
    await app_user.start()
    await app_bot.start()
    await send_report("🚀 تم تشغيل كود الفحص بنجاح! جرب الانضمام الآن...")
    await idle()
    await app_user.stop()
    await app_bot.stop()

if __name__ == "__main__":
    loop.run_until_complete(start_all())
