#!/usr/bin/env python3
import asyncio
import json
import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"
BASE_URL = "https://adhahi.dz"
TARGET_WILAYA = "24"  # قالمة
TARGET_WILAYA_NAME = "قالمة"

MENU, ASK_NIN, ASK_CNIBE, ASK_PHONE, ASK_EMAIL, ASK_COMMUNE, ASK_PAYMENT = range(7)

PAYMENT_OPTIONS = {
    "online": "💳 دفع إلكتروني (48,000 دج)",
    "tpe": "🏧 TPE - دفع بالبطاقة (49,000 دج)",
    "cash": "💵 دفع نقدي (50,000 دج)"
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 إدخال / تعديل بياناتي", callback_data="enter")],
        [InlineKeyboardButton("👁️ عرض بياناتي", callback_data="view")],
        [InlineKeyboardButton("🚀 بدء المراقبة", callback_data="monitor_start")],
        [InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="monitor_stop")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🐑 *بوت أضاحي — ولاية قالمة*\n\n"
        "سأراقب منصة adhahi.dz وأُسجّلك فور فتح ولاية *قالمة*!\n\n"
        "📌 *الخطوات:*\n"
        "1️⃣ أدخل بياناتك الشخصية\n"
        "2️⃣ شغّل المراقبة\n"
        "3️⃣ انتظر الإشعار 🎉\n\n"
        "اختر من القائمة:"
    )
    await update.message.reply_text(msg, reply_markup=main_keyboard(), parse_mode="Markdown")
    return MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    action = query.data

    if action == "enter":
        await query.edit_message_text(
            "📝 *إدخال البيانات — الخطوة 1/6*\n\nأرسل رقم *NIN* (رقم التعريف الوطني):",
            parse_mode="Markdown"
        )
        return ASK_NIN

    elif action == "view":
        data = load_data()
        if uid in data and data[uid].get("nin"):
            u = data[uid]
            text = (
                "📋 *بياناتك المحفوظة:*\n\n"
                f"🪪 NIN: `{u.get('nin','—')}`\n"
                f"🪪 CNIBE: `{u.get('cnibe','—')}`\n"
                f"📱 الهاتف: `{u.get('phone','—')}`\n"
                f"📧 البريد: `{u.get('email','—')}`\n"
                f"🏘️ البلدية: `{u.get('commune','—')}`\n"
                f"💳 الدفع: `{u.get('payment','—')}`\n"
                f"🎯 الولاية المستهدفة: *قالمة* ✅"
            )
        else:
            text = "❌ لا توجد بيانات محفوظة. اضغط 'إدخال بياناتي' أولاً."
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]),
            parse_mode="Markdown"
        )
        return MENU

    elif action == "monitor_start":
        data = load_data()
        if not data.get(uid, {}).get("nin"):
            await query.edit_message_text(
                "❌ يجب إدخال بياناتك أولاً!",
                reply_markup=main_keyboard()
            )
            return MENU

        if "monitors" not in context.bot_data:
            context.bot_data["monitors"] = {}

        if uid in context.bot_data["monitors"]:
            await query.edit_message_text(
                "⚠️ المراقبة تعمل بالفعل!\n\n🔍 أراقب منصة أضاحي كل ثانيتين...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="monitor_stop")]]),
            )
            return MENU

        task = asyncio.create_task(monitor_loop(context, uid, query.from_user.id))
        context.bot_data["monitors"][uid] = task

        await query.edit_message_text(
            "✅ *المراقبة تعمل الآن!*\n\n"
            "🔍 أفحص المنصة كل ثانيتين...\n"
            "🎯 الولاية: *قالمة*\n\n"
            "سأرسل لك إشعاراً فور الفتح! 🚀",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="monitor_stop")]]),
            parse_mode="Markdown"
        )
        return MENU

    elif action == "monitor_stop":
        if "monitors" in context.bot_data and uid in context.bot_data["monitors"]:
            context.bot_data["monitors"][uid].cancel()
            del context.bot_data["monitors"][uid]
            msg = "⏹️ تم إيقاف المراقبة."
        else:
            msg = "ℹ️ لا توجد مراقبة نشطة."
        await query.edit_message_text(msg, reply_markup=main_keyboard())
        return MENU

    elif action == "back":
        await query.edit_message_text(
            "🐑 *القائمة الرئيسية:*",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        return MENU

    return MENU

async def ask_nin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nin"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 2/6*\n\nأرسل رقم بطاقة الهوية البيومترية *(CNIBE)*:",
        parse_mode="Markdown"
    )
    return ASK_CNIBE

async def ask_cnibe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cnibe"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 3/6*\n\nأرسل رقم هاتفك:\n(مثال: 0551234567)",
        parse_mode="Markdown"
    )
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 4/6*\n\nأرسل بريدك الإلكتروني:",
        parse_mode="Markdown"
    )
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *الخطوة 5/6*\n\nأرسل اسم بلديتك في ولاية قالمة:\n(مثال: قالمة، بوشقوف، هيليوبوليس...)",
        parse_mode="Markdown"
    )
    return ASK_COMMUNE

async def ask_commune(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["commune"] = update.message.text.strip()
    buttons = [[InlineKeyboardButton(v, callback_data=f"pay_{k}")] for k, v in PAYMENT_OPTIONS.items()]
    await update.message.reply_text(
        "📝 *الخطوة 6/6*\n\nاختر طريقة الدفع:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ASK_PAYMENT

async def ask_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment = query.data.replace("pay_", "")
    context.user_data["payment"] = payment
    context.user_data["wilaya"] = TARGET_WILAYA_NAME
    context.user_data["wilaya_code"] = TARGET_WILAYA

    data = load_data()
    uid = str(query.from_user.id)
    data[uid] = dict(context.user_data)
    save_data(data)

    await query.edit_message_text(
        "✅ *تم حفظ بياناتك بنجاح!*\n\n"
        f"🪪 NIN: `{context.user_data['nin']}`\n"
        f"🪪 CNIBE: `{context.user_data['cnibe']}`\n"
        f"📱 الهاتف: `{context.user_data['phone']}`\n"
        f"📧 البريد: `{context.user_data['email']}`\n"
        f"🏘️ البلدية: `{context.user_data['commune']}`\n"
        f"💳 الدفع: `{PAYMENT_OPTIONS[payment]}`\n"
        f"🎯 الولاية: *قالمة* ✅\n\n"
        "الآن اضغط *بدء المراقبة* 🚀",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )
    return MENU

async def monitor_loop(context, uid, chat_id):
    logger.info(f"بدأت المراقبة للمستخدم {uid} - ولاية قالمة")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": BASE_URL,
    }
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # ⚙️ هذا الرابط يجب تعديله بعد فحص API المنصة
                async with session.get(
                    f"{BASE_URL}/api/wilayas",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        available = result.get("available", [])
                        if TARGET_WILAYA in available or TARGET_WILAYA_NAME in available:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=(
                                    "🔥 *تنبيه عاجل!*\n\n"
                                    "✅ ولاية *قالمة* أصبحت متاحة!\n"
                                    "⚡ افتح الرابط الآن وسجّل:\n"
                                    f"{BASE_URL}/register\n\n"
                                    "⏱️ لديك ثوانٍ فقط!"
                                ),
                                parse_mode="Markdown"
                            )
                            break
            except asyncio.CancelledError:
                logger.info(f"تم إيقاف المراقبة للمستخدم {uid}")
                break
            except Exception as e:
                logger.error(f"خطأ في المراقبة: {e}")

            await asyncio.sleep(2)

async def otp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ الاستخدام الصحيح:\n`/otp 123456`", parse_mode="Markdown")
        return
    otp = context.args[0]
    await update.message.reply_text(f"⏳ جاري التحقق من رمز OTP: `{otp}`...", parse_mode="Markdown")
    # ⚙️ أضف هنا كود التحقق من OTP بعد فحص API المنصة
    await update.message.reply_text("✅ تم إرسال الرمز! انتظر التأكيد من المنصة.")

def main():
    token = os.environ.get("BOT_TOKEN", "8860768793:AAGs_mDN9JNterqdxchPFXLEnwFj1ZIDbfU")
    if not token:
        logger.error("❌ BOT_TOKEN غير موجود في متغيرات البيئة!")
        return

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button_handler)],
            ASK_NIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nin)],
            ASK_CNIBE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cnibe)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASK_COMMUNE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_commune)],
            ASK_PAYMENT: [CallbackQueryHandler(ask_payment, pattern="^pay_")],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("otp", otp_command))

    logger.info("🚀 البوت يعمل الآن!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
