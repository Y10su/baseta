import os
import asyncio
import json
import re
from aiohttp import web
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- الإعدادات الأساسية ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# إعدادات المدراء
try:
    PRIMARY_ADMIN = int(os.environ.get("MY_CHAT_ID", 0))
except ValueError:
    PRIMARY_ADMIN = 0

SECONDARY_ADMIN = 1209459374

# قائمة بكل المدراء لسهولة التوجيه
ADMIN_IDS = [SECONDARY_ADMIN]
if PRIMARY_ADMIN != 0 and PRIMARY_ADMIN not in ADMIN_IDS:
    ADMIN_IDS.append(PRIMARY_ADMIN)

CHANNEL_USERNAME = os.environ.get("CHANNEL_ID", "@bassetaSa") 
FILE_TO_SEND = "baseta_interview.pdf"
USERS_DB = "users_db.json" 
BANNED_DB = "banned_db.json" 

bot = AsyncTeleBot(BOT_TOKEN)
admin_state = {}

# --- دوال قواعد البيانات ---
def load_db(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f: return json.load(f)
        except: pass
    return []

def save_to_db(filename, data_list):
    with open(filename, "w") as f: json.dump(data_list, f)

def save_user(user_id):
    users = load_db(USERS_DB)
    if user_id not in users:
        users.append(user_id)
        save_to_db(USERS_DB, users)

def is_banned(user_id):
    return user_id in load_db(BANNED_DB)

# --- خادم الويب (ريندر) ---
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

# --- دالة النبض (تصل للمدير الأساسي فقط) ---
async def keep_alive_ping():
    while True:
        await asyncio.sleep(300) 
        if PRIMARY_ADMIN != 0:
            users_count = len(load_db(USERS_DB))
            try:
                await bot.send_message(
                    PRIMARY_ADMIN, 
                    f"🔄 **نبض النظام:** البوت يعمل بكفاءة.\n👥 إجمالي من ضغطوا البداية: **{users_count}**",
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
        except: pass
            
        await bot.send_message(
            user_id, 
            "من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
        )
    except: pass

# 🌟 2. لوحة تحكم الإدارة (تعمل لكل المدراء) 🌟
@bot.message_handler(commands=['admin'], func=lambda message: message.chat.id in ADMIN_IDS)
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

@bot.callback_query_handler(func=lambda call: call.message.chat.id in ADMIN_IDS)
async def admin_callbacks(call):
    admin_id = call.message.chat.id
    if call.data == "stats":
        users = load_db(USERS_DB)
        banned = load_db(BANNED_DB)
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            admin_id, 
            f"📊 **إحصائيات منصة بسيطة:**\n\n👥 إجمالي المسجلين: **{len(users)}** عضو.\n🚫 الحسابات المحظورة: **{len(banned)}**.", 
            parse_mode="Markdown"
        )
    elif call.data == "broadcast":
        admin_state[admin_id] = "waiting_for_broadcast"
        await bot.answer_callback_query(call.id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ إلغاء الإذاعة", callback_data="cancel_broadcast"))
        
        await bot.send_message(
            admin_id, 
            "📢 **وضع الإذاعة نشط:**\n\nأرسل الآن الرسالة (نص، صورة، أو ملف) التي ترغب في نشرها للجميع.\n\n⚠️ *تنبيه: سيتم الإرسال فوراً لجميع المستخدمين.*", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    elif call.data == "cancel_broadcast":
        admin_state.pop(admin_id, None)
        await bot.answer_callback_query(call.id, "تم الإلغاء")
        await bot.edit_message_text(
            "❌ **تم إلغاء الإذاعة.**", 
            chat_id=admin_id, 
            message_id=call.message.message_id, 
            parse_mode="Markdown"
        )

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice'], func=lambda message: message.chat.id in ADMIN_IDS and admin_state.get(message.chat.id) == "waiting_for_broadcast")
async def execute_broadcast(message):
    admin_id = message.chat.id
    admin_state.pop(admin_id, None)
    users = load_db(USERS_DB)
    
    if not users:
        await bot.send_message(admin_id, "❌ لا يوجد مستخدمين.")
        return
    
    await bot.send_message(admin_id, f"🚀 جاري بدء النشر لـ {len(users)} مستخدم... الرجاء الانتظار.")
    
    success, failed = 0, 0
    for uid in users:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=admin_id, message_id=message.message_id)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
            
    await bot.send_message(
        admin_id, 
        f"✅ **انتهت الإذاعة بنجاح!**\n\n🟢 المستلمين: {success}\n🔴 فشل لـ: {failed}", 
        parse_mode="Markdown"
    )

# 🌟 3. معالجة أمر /start 🌟
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS and admin_state.get(user_id) == "waiting_for_broadcast":
        return

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
        except: pass
            
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
            f"أهلاً بك يا {name} ✋\n\nعشان تستلم هديتك، لازم تكون فرد من عائلة بسيطة أولاً 💚.\n\nاشترك في القناة من الزر بالأسفل، وبعدها ارجع هنا واضغط /start مرة ثانية عشان أرسل لك الملف فوراً 👇",
            reply_markup=markup
        )

# 🌟 4. نظام التواصل: توجيه رسائل الأعضاء للمدراء 🌟
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice'], func=lambda message: message.chat.id not in ADMIN_IDS and not str(message.text).startswith('/'))
async def forward_to_admins(message):
    user_id = message.from_user.id
    if is_banned(user_id): return 
    
    name = message.from_user.first_name or "عضو"
    save_user(user_id) 
    
    for admin_id in ADMIN_IDS:
        try:
            if message.content_type == 'text':
                # أضفنا (MSG) عشان البوت يقدر يقتبس الرسالة لاحقاً
                admin_msg = f"📨 **رسالة من:** {name}\n🆔 ID: `{user_id}`\n🔖 MSG: `{message.message_id}`\n➖➖➖➖➖➖\n{message.text}"
                await bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
            else:
                # للمرفقات، نرسل المرفق أولاً ثم بياناته تحته ليرد الإداري عليها
                await bot.forward_message(admin_id, message.chat.id, message.message_id)
                await bot.send_message(admin_id, f"☝️ **المرفق أعلاه من:** {name}\n🆔 ID: `{user_id}`\n🔖 MSG: `{message.message_id}`\n*(للرد، اضغط 'رد' على هذه الرسالة)*", parse_mode="Markdown")
        except: pass

# 🌟 5. نظام التواصل: رد المدراء والحظر وإشعار الزملاء 🌟
@bot.message_handler(func=lambda message: message.chat.id in ADMIN_IDS and message.reply_to_message is not None)
async def admin_reply_action(message):
    try:
        target_user_id = None
        target_msg_id = None
        original_msg = message.reply_to_message
        admin_id = message.chat.id
        admin_name = message.from_user.first_name or "إداري"
        
        # استخراج الآيدي ورقم الرسالة
        if original_msg.text:
            match_id = re.search(r"ID:\s*(\d+)", original_msg.text)
            match_msg = re.search(r"MSG:\s*(\d+)", original_msg.text)
            if match_id: target_user_id = int(match_id.group(1))
            if match_msg: target_msg_id = int(match_msg.group(1))
            
        if target_user_id:
            text_command = message.text.strip().lower() if message.text else ""
            if text_command == '/ban':
                banned = load_db(BANNED_DB)
                if target_user_id not in banned:
                    banned.append(target_user_id)
                    save_to_db(BANNED_DB, banned)
                await bot.send_message(admin_id, "🚫 **تم حظر هذا العضو.**")
                return
            elif text_command == '/unban':
                banned = load_db(BANNED_DB)
                if target_user_id in banned:
                    banned.remove(target_user_id)
                    save_to_db(BANNED_DB, banned)
                await bot.send_message(admin_id, "✅ **تم فك الحظر عن هذا العضو.**")
                return

            # إرسال الرد للمستخدم (مع اقتباس رسالته الأصلية إذا كانت موجودة)
            try:
                await bot.copy_message(chat_id=target_user_id, from_chat_id=admin_id, message_id=message.message_id, reply_to_message_id=target_msg_id)
            except Exception:
                # إذا مسح العضو رسالته وما قدرنا نقتبسها، نرسلها كرسالة عادية
                await bot.copy_message(chat_id=target_user_id, from_chat_id=admin_id, message_id=message.message_id)

            await bot.send_message(admin_id, "✅ تم الإرسال للمستخدم بنجاح.")

            # إشعار باقي الإداريين بأنك رديت
            for other_admin in ADMIN_IDS:
                if other_admin != admin_id:
                    try:
                        await bot.send_message(other_admin, f"👤 **الإداري {admin_name}** قام بالرد على العضو (ID: `{target_user_id}`):\n👇", parse_mode="Markdown")
                        await bot.copy_message(chat_id=other_admin, from_chat_id=admin_id, message_id=message.message_id)
                    except: pass
        else:
            await bot.send_message(admin_id, "⚠️ لم أتمكن من تحديد العضو! تأكد من الرد على الرسالة اللي فيها الـ ID.")
    except Exception as e:
        await bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# --- دالة التشغيل الأساسية ---
async def start_all():
    asyncio.create_task(run_web_server())
    asyncio.create_task(keep_alive_ping())
    print("Bot is running...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(start_all())
