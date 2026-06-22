import os
import asyncio
import json
import re
from aiohttp import web
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- الإعدادات ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
try:
    MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", 0))
except ValueError:
    MY_CHAT_ID = 0

CHANNEL_USERNAME = os.environ.get("CHANNEL_ID", "@bassetaSa") 
FILE_TO_SEND = "baseta_interview.pdf"
USERS_DB = "users_db.json" 

bot = AsyncTeleBot(BOT_TOKEN)

# متغير لتتبع حالة الأدمن (عشان نعرف متى يرسل رسالة الإذاعة)
admin_state = {}

# --- دوال قاعدة بيانات الأعضاء ---
def load_users():
    if os.path.exists(USERS_DB):
        try:
            with open(USERS_DB, "r") as f: return json.load(f)
        except: pass
    return []

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_DB, "w") as f: json.dump(users, f)

# --- خادم الويب ---
async def handle_ping(request):
    return web.Response(text="النظام الشامل يعمل بنجاح!")

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- دالة النبض (كل 5 دقائق) ---
async def keep_alive_ping():
    while True:
        await asyncio.sleep(300) 
        if MY_CHAT_ID != 0:
            users_count = len(load_users())
            try:
                await bot.send_message(
                    MY_CHAT_ID, 
                    f"🔄 **نبض النظام:** البوت يعمل بكفاءة.\n👥 عدد الأعضاء المسجلين: **{users_count}**",
                    parse_mode="Markdown"
                )
            except: pass

# --- دالة التحقق من الاشتراك ---
async def check_membership(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

# 🌟 1. معالجة طلبات الانضمام 🌟
@bot.chat_join_request_handler()
async def handle_join_request(request):
    user_id = request.from_user.id
    name = request.from_user.first_name or "عضو"
    chat_id = request.chat.id

    save_user(user_id)

    try:
        await bot.approve_chat_join_request(chat_id, user_id)
        
        await bot.send_message(
            user_id, 
            f"يا هلا بك يا {name} في عائلة \"بسيطة\" 💚👋\nأول شيء، خذ هديتك اللي وعدناك فيها.. ملف \"أسرار المقابلات الشخصية\" جاهز للتحميل الحين 👇"
        )
        
        try:
            with open(FILE_TO_SEND, 'rb') as pdf_file:
                await bot.send_document(user_id, pdf_file)
        except:
            await bot.send_message(user_id, "عذراً، هناك مشكلة في قراءة الملف، تواصل مع الإدارة.")
            
        await bot.send_message(
            user_id, 
            "من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
        )
        
        if MY_CHAT_ID != 0:
            await bot.send_message(MY_CHAT_ID, f"✅ **تم قبول عضو جديد آلياً:** {name}")

    except Exception as e:
        if MY_CHAT_ID != 0:
            await bot.send_message(MY_CHAT_ID, f"❌ حدث خطأ في قبول {name}: {e}")

# 🌟 2. لوحة تحكم الإدارة (أمر /admin) 🌟
@bot.message_handler(commands=['admin'], func=lambda message: message.chat.id == MY_CHAT_ID)
async def admin_panel(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 إحصائيات البوت", callback_data="stats"))
    markup.add(InlineKeyboardButton("📢 إذاعة رسالة (نشر)", callback_data="broadcast"))
    
    await bot.send_message(
        message.chat.id, 
        "⚙️ **لوحة تحكم الإدارة - منصة بسيطة**\n\nاختر الإجراء المطلوب من الأزرار بالأسفل:", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

# استجابة أزرار لوحة التحكم
@bot.callback_query_handler(func=lambda call: call.message.chat.id == MY_CHAT_ID)
async def admin_callbacks(call):
    if call.data == "stats":
        users = load_users()
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id, 
            f"📊 **إحصائيات منصة بسيطة:**\n\n👥 إجمالي عدد المستخدمين في قاعدة البيانات: **{len(users)}** عضو.", 
            parse_mode="Markdown"
        )
    elif call.data == "broadcast":
        admin_state[call.from_user.id] = "waiting_for_broadcast"
        await bot.answer_callback_query(call.id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ إلغاء الإذاعة", callback_data="cancel_broadcast"))
        
        await bot.send_message(
            call.message.chat.id, 
            "📢 **وضع الإذاعة نشط:**\n\nأرسل الآن الرسالة (نص، صورة، أو ملف) التي ترغب في نشرها للجميع.\n\n⚠️ *تنبيه: سيتم الإرسال فوراً لجميع المستخدمين.*", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    elif call.data == "cancel_broadcast":
        admin_state.pop(call.from_user.id, None)
        await bot.answer_callback_query(call.id, "تم الإلغاء")
        await bot.edit_message_text(
            "❌ **تم إلغاء الإذاعة.**", 
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            parse_mode="Markdown"
        )

# تنفيذ النشر (يستقبل الرسالة وينسخها للجميع)
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice'], func=lambda message: message.chat.id == MY_CHAT_ID and admin_state.get(message.from_user.id) == "waiting_for_broadcast")
async def execute_broadcast(message):
    admin_state.pop(message.from_user.id, None) # إنهاء وضع الإذاعة
    users = load_users()
    
    if not users:
        await bot.send_message(MY_CHAT_ID, "❌ لا يوجد مستخدمين في قاعدة البيانات.")
        return
    
    await bot.send_message(MY_CHAT_ID, f"🚀 جاري بدء النشر لـ {len(users)} مستخدم... الرجاء الانتظار.")
    
    success = 0
    failed = 0
    for uid in users:
        try:
            # نسخ الرسالة بالضبط كما أرسلتها (سواء صورة، ملف، نص)
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            await asyncio.sleep(0.05) # تأخير بسيط جداً لحماية السيرفر من الضغط
        except:
            failed += 1
            
    await bot.send_message(
        MY_CHAT_ID, 
        f"✅ **انتهت الإذاعة بنجاح!**\n\n🟢 المستلمين: {success}\n🔴 فشل لـ: {failed} (حظروا البوت أو حساب محذوف)", 
        parse_mode="Markdown"
    )

# 🌟 3. معالجة أمر /start 🌟
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    # لا نستجيب لك في أمر ستارت إذا كنت أنت في وضع الإدارة عشان ما يصير تعارض
    if message.chat.id == MY_CHAT_ID and admin_state.get(message.from_user.id) == "waiting_for_broadcast":
        return

    user_id = message.from_user.id
    name = message.from_user.first_name or "عضو"
    
    save_user(user_id)
    
    checking_msg = await bot.send_message(user_id, "⏳ جاري التحقق من اشتراكك...")
    is_member = await check_membership(user_id)
    await bot.delete_message(user_id, checking_msg.message_id)
    
    if is_member:
        await bot.send_message(
            user_id, 
            f"يا هلا بك يا {name} في عائلة \"بسيطة\" 💚👋\nأول شيء، خذ هديتك اللي وعدناك فيها.. ملف \"أسرار المقابلات الشخصية\" جاهز للتحميل الحين 👇"
        )
        
        try:
            with open(FILE_TO_SEND, 'rb') as pdf_file:
                await bot.send_document(user_id, pdf_file)
        except:
            await bot.send_message(user_id, "عذراً، هناك مشكلة في قراءة الملف، تواصل مع الإدارة.")
            
        await bot.send_message(
            user_id, 
            "من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
        )
    else:
        markup = InlineKeyboardMarkup()
        clean_username = CHANNEL_USERNAME.replace('@', '')
        channel_url = f"https://t.me/{clean_username}"
        markup.add(InlineKeyboardButton("📢 اضغط هنا للاشتراك في القناة", url=channel_url))
        
        await bot.send_message(
            user_id, 
            f"أهلاً بك يا {name} ✋\n\nعشان تستلم هديتك (ملف أسرار المقابلات الشخصية)، لازم تكون فرد من عائلة بسيطة أولاً 💚.\n\nاشترك في القناة من الزر بالأسفل، وبعدها ارجع هنا واضغط /start مرة ثانية عشان أرسل لك الملف فوراً 👇",
            reply_markup=markup
        )

# 🌟 4. نظام التواصل: توجيه رسائل الأعضاء لك 🌟
@bot.message_handler(func=lambda message: message.chat.id != MY_CHAT_ID and not message.text.startswith('/'))
async def forward_to_admin(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "عضو"
    save_user(user_id) 
    
    if MY_CHAT_ID != 0:
        admin_msg = (
            f"📨 **رسالة من عضو:** {name}\n"
            f"🆔 ID: {user_id}\n"
            f"➖➖➖➖➖➖\n"
            f"{message.text}"
        )
        await bot.send_message(MY_CHAT_ID, admin_msg)

@bot.message_handler(content_types=['photo', 'video', 'document', 'audio', 'voice'], func=lambda message: message.chat.id != MY_CHAT_ID)
async def forward_media_to_admin(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "عضو"
    if MY_CHAT_ID != 0:
        await bot.send_message(MY_CHAT_ID, f"📎 **مرفق من:** {name}\n🆔 ID: {user_id}")
        await bot.forward_message(MY_CHAT_ID, message.chat.id, message.message_id)

# 🌟 5. نظام التواصل: ردك كإدارة 🌟
@bot.message_handler(func=lambda message: message.chat.id == MY_CHAT_ID and message.reply_to_message is not None)
async def reply_to_user(message):
    try:
        target_user_id = None
        original_msg = message.reply_to_message
        
        if original_msg.text:
            match = re.search(r"ID:\s*(\d+)", original_msg.text)
            if match:
                target_user_id = int(match.group(1))
        
        if not target_user_id and original_msg.forward_from:
            target_user_id = original_msg.forward_from.id
            
        if target_user_id:
            # ننسخ ردك للعضو عشان لو رديت بصورة توصل له صورة، ولو نص يوصل نص
            await bot.send_message(target_user_id, "📩 **رد من منصة بسيطة:**")
            await bot.copy_message(chat_id=target_user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            await bot.send_message(MY_CHAT_ID, "✅ تم إرسال ردك للعضو بنجاح.")
        else:
            await bot.send_message(MY_CHAT_ID, "⚠️ لم أتمكن من تحديد العضو! تأكد أنك تسوي (رد / Reply) على الرسالة اللي فيها رقم الـ ID.")
    except Exception as e:
        await bot.send_message(MY_CHAT_ID, f"❌ حدث خطأ أثناء إرسال الرد: {e}")

# --- دالة التشغيل الأساسية ---
async def start_all():
    asyncio.create_task(run_web_server())
    asyncio.create_task(keep_alive_ping())
    print("Bot is running...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(start_all())
