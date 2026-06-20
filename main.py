import os
import json
import asyncio
import requests
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
MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")

FILE_TO_SEND = "prize_file.pdf" # تأكد من رفع هذا الملف إلى GitHub مع الكود
DB_FILE = "sent_messages.json"

# --- دوال قاعدة البيانات والإشعارات ---
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

def send_report(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": MY_CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

# --- خادم الويب الوهمي (إجباري لـ Render) ---
async def handle_ping(request):
    return web.Response(text="اليوزر بوت يعمل بنجاح!")

async def run_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', handle_ping)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"تم تشغيل خادم الويب على البورت {port}")

# --- إعداد اليوزر بوت ---
app = Client("my_userbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

@app.on_chat_member_updated(filters.chat(CHANNEL_ID))
async def handle_channel_changes(client: Client, chat_member_updated: ChatMemberUpdated):
    new_member = chat_member_updated.new_chat_member
    old_member = chat_member_updated.old_chat_member
    
    user_id = chat_member_updated.from_user.id
    user_name = chat_member_updated.from_user.first_name or "مستخدم"
    
    db = load_db()

    # الانضمام
    if new_member and new_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not old_member or old_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await asyncio.sleep(4)
            try:
                msg = await client.send_document(
                    chat_id=user_id,
                    document=FILE_TO_SEND,
                    caption="🎁 أهلاً بك في القناة! إليك ملف الجائزة الخاص بك.\n⚠️ تنبيه: في حال مغادرتك للقناة سيتم سحب الملف وحذفه تلقائياً!"
                )
                db[str(user_id)] = msg.id
                save_db(db)
                send_report(f"✅ *تم إرسال الملف بنجاح*\n👤 العضو: {user_name}")
            except Exception as e:
                send_report(f"❌ *فشل إرسال الملف لـ {user_name}*\nالسبب: `{e}`")

    # المغادرة
    elif old_member and old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.SUBSCRIBER]:
        if not new_member or new_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            if str(user_id) in db:
                msg_id = db[str(user_id)]
                try:
                    await client.delete_messages(chat_id=user_id, message_ids=msg_id, revoke=True)
                    send_report(f"🗑️ *العضو غادر وتم سحب الملف بنجاح!*\n👤 العضو: {user_name}")
                    del db[str(user_id)]
                    save_db(db)
                except Exception as e:
                    pass

# --- التشغيل الأساسي ---
async def start_all():
    await run_web_server()
    await app.start()
    send_report("🚀 *تم تشغيل اليوزر بوت على Render بنجاح!*")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_all())
