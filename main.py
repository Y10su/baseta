import os
import asyncio
from aiohttp import web
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- الإعدادات ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "") # تأكد إن هذا المتغير موجود في ريندر برقم الآيدي حقك
CHANNEL_USERNAME = os.environ.get("CHANNEL_ID", "@bassetaSa") 
FILE_TO_SEND = "baseta_interview.pdf"

bot = AsyncTeleBot(BOT_TOKEN)

# --- خادم الويب (لاستقبال زيارات UptimeRobot) ---
async def handle_ping(request):
    return web.Response(text="بوت التوزيع والاشتراك الإجباري يعمل بنجاح!")

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- دالة إرسال تقرير كل 5 دقائق (النبض) ---
async def keep_alive_ping():
    while True:
        await asyncio.sleep(300) # 300 ثانية = 5 دقائق
        if MY_CHAT_ID:
            try:
                await bot.send_message(
                    MY_CHAT_ID, 
                    "🔄 **نبض النظام:** البوت يعمل بنجاح ومستعد لاستقبال المشتركين الجدد.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"فشل إرسال تقرير النبض: {e}")

# --- دالة التحقق من الاشتراك ---
async def check_membership(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

# --- معالجة أمر /start ---
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "عضو"
    
    checking_msg = await bot.send_message(user_id, "⏳ جاري التحقق من اشتراكك في القناة...")
    is_member = await check_membership(user_id)
    await bot.delete_message(user_id, checking_msg.message_id)
    
    if is_member:
        # 1. الرسالة الترحيبية
        await bot.send_chat_action(user_id, 'typing')
        await asyncio.sleep(1.5)
        await bot.send_message(
            user_id, 
            f"يا هلا بك يا {name} في عائلة \"بسيطة\" 💚👋\nأول شيء، خذ هديتك اللي وعدناك فيها.. ملف \"أسرار المقابلات الشخصية\" جاهز للتحميل الحين 👇"
        )
        
        # 2. ملف الجائزة
        await bot.send_chat_action(user_id, 'upload_document')
        await asyncio.sleep(2)
        try:
            with open(FILE_TO_SEND, 'rb') as pdf_file:
                await bot.send_document(user_id, pdf_file)
        except Exception as e:
            await bot.send_message(user_id, "عذراً، يبدو أن هناك مشكلة في قراءة الملف حالياً، يرجى إبلاغ الإدارة.")
            
        # 3. رسالة من إحنا؟
        await bot.send_chat_action(user_id, 'typing')
        await asyncio.sleep(2.5)
        await bot.send_message(
            user_id, 
            "من إحنا؟\nإحنا منصة سعودية متخصصة في تمكين الباحثين عن عمل، ومعانا خبراء موارد بشرية (HR) يصيغون سيرتك بالملّي لتتخطى فلاتر الـ ATS. يعني من اليوم أنت مو لوحدك، إحنا مستشارك وسندك خطوة بخطوة لين تبشرنا بقبولك 🤝🚀.\n\n💡 تنبيه غالي: ثبّت القناة وفعّل التنبيهات 🔔 عشان ما تفوتك الفرص والوظائف اليومية.\n\nفالك التوفيق والوظيفة اللي تطمح لها يا رب! 🟢🫡"
        )
        
    else:
        # طلب الاشتراك الإجباري
        markup = InlineKeyboardMarkup()
        clean_username = CHANNEL_USERNAME.replace('@', '')
        channel_url = f"https://t.me/{clean_username}"
        markup.add(InlineKeyboardButton("📢 اضغط هنا للاشتراك في القناة", url=channel_url))
        
        await bot.send_message(
            user_id, 
            f"أهلاً بك يا {name} ✋\n\nعشان تستلم هديتك (ملف أسرار المقابلات الشخصية)، لازم تكون فرد من عائلة بسيطة أولاً 💚.\n\nاشترك في القناة من الزر بالأسفل، وبعدها ارجع هنا واضغط /start مرة ثانية عشان أرسل لك الملف فوراً 👇",
            reply_markup=markup
        )

# --- دالة التشغيل الأساسية ---
async def start_all():
    # تشغيل خادم الويب
    asyncio.create_task(run_web_server())
    
    # تشغيل مهمة النبض (إرسال رسالة كل 5 دقائق)
    asyncio.create_task(keep_alive_ping())
    
    print("Bot is running...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(start_all())
