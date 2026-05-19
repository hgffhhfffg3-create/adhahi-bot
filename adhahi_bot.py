#!/usr/bin/env python3
"""
بوت تيليغرام للتسجيل التلقائي في منصة أضاحي adhahi.dz
"""

import asyncio
import json
import os
import logging
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

# ==================== الإعدادات ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ملف حفظ البيانات محلياً
DATA_FILE = "user_data.json"

# رابط المنصة
BASE_URL = "https://adhahi.dz"
REGISTER_URL = f"{BASE_URL}/register"
API_CHECK_URL = f"{BASE_URL}/api/wilayas"  # رابط للتحقق من الولايات المتاحة (يُعدَّل حسب API الفعلي)

# مراحل المحادثة
(
    MENU,
    ASK_NIN, ASK_CNIBE, ASK_PHONE, ASK_EMAIL,
    ASK_WILAYA, ASK_COMMUNE, ASK_PAYMENT,
    ASK_TARGET_WILAYA, ASK_OTP,
    CONFIRM_DATA
) = range(11)

# قائمة الولايات الجزائرية
WILAYAS = [
    "01-أدرار", "02-الشلف", "03-الأغواط", "04-أم البواقي", "05-باتنة",
    "06-بجاية", "07-بسكرة", "08-بشار", "09-البليدة", "10-البويرة",
    "11-تمنراست", "12-تبسة", "13-تلمسان", "14-تيارت", "15-تيزي وزو",
    "16-الجزائر", "17-الجلفة", "18-جيجل", "19-سطيف", "20-سعيدة",
    "21-سكيكدة", "22-سيدي بلعباس", "23-عنابة", "24-قالمة", "25-قسنطينة",
    "26-المدية", "27-مستغانم", "28-المسيلة", "29-معسكر", "30-ورقلة",
    "31-وهران", "32-البيض", "33-إليزي", "34-برج بوعريريج", "35-بومرداس",
    "36-الطارف", "37-تندوف", "38-تيسمسيلت", "39-الوادي", "40-خنشلة",
    "41-سوق أهراس", "42-تيبازة", "43-ميلة", "44-عين الدفلى", "45-النعامة",
    "46-عين تموشنت", "47-غرداية", "48-غليزان", "49-المغير", "50-المنيعة",
    "51-أولاد جلال", "52-برج باجي مختار", "53-بني عباس", "54-تيميمون",
    "55-تقرت", "56-جانت", "57-عين صالح", "58-عين قزام"
]

PAYMENT_METHODS = {
    "online": "💳 دفع إلكتروني (خصم خاص)",
    "tpe": "🏧 TPE (دفع بالبطاقة في نقطة البيع)",
    "cash": "💵 دفع نقدي"
}

# ==================== تحميل وحفظ البيانات ====================

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== فحص المنصة ====================

async def check_wilaya_availability(session: aiohttp.ClientSession, wilaya_code: str) -> bool:
    """
    تحقق إذا كانت الولاية متاحة للتسجيل.
    يجب تعديل هذه الدالة بعد فحص الـ API الحقيقي للمنصة.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ar,fr;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    }
    try:
        async with session.get(API_CHECK_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                # ⚙️ عدّل هذا المنطق حسب بنية الـ API الفعلية
                # مثال: إذا كانت البيانات قائمة من الولايات المتاحة
                available = data.get("available_wilayas", [])
                return wilaya_code in available
    except Exception as e:
        logger.error(f"خطأ في فحص المنصة: {e}")
    return False

async def submit_registration(session: aiohttp.ClientSession, user_info: dict) -> dict:
    """
    إرسال طلب التسجيل إلى المنصة.
    ⚙️ يجب تعديل الـ payload والـ endpoint بعد فحص الـ API الفعلي.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ar,fr;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Referer": REGISTER_URL,
        "Origin": BASE_URL,
    }

    # ⚙️ عدّل هذا الـ payload حسب الـ API الفعلي للمنصة
    payload = {
        "nin": user_info.get("nin"),
        "cnibe": user_info.get("cnibe"),
        "phone": user_info.get("phone"),
        "email": user_info.get("email"),
        "wilaya": user_info.get("wilaya_code"),
        "commune": user_info.get("commune"),
        "payment_method": user_info.get("payment"),
        "accept_terms": True
    }

    try:
        async with session.post(
            f"{BASE_URL}/api/register",  # ⚙️ عدّل الرابط
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            result = await resp.json()
            return {"success": resp.status == 200 or resp.status == 201, "data": result, "status": resp.status}
    except Exception as e:
        logger.error(f"خطأ في التسجيل: {e}")
        return {"success": False, "error": str(e)}

# ==================== أوامر البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("📝 إدخال / تعديل بياناتي", callback_data="enter_data")],
        [InlineKeyboardButton("👁️ عرض بياناتي المحفوظة", callback_data="view_data")],
        [InlineKeyboardButton("🎯 تحديد الولاية المستهدفة", callback_data="set_target")],
        [InlineKeyboardButton("🚀 بدء المراقبة التلقائية", callback_data="start_monitor")],
        [InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="stop_monitor")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "🐑 *مرحباً بك في بوت أضاحي الذكي*\n\n"
        "هذا البوت سيراقب منصة adhahi.dz ويسجلك تلقائياً فور فتح ولايتك!\n\n"
        "📌 *الخطوات:*\n"
        "1️⃣ أدخل بياناتك الشخصية\n"
        "2️⃣ حدد الولاية التي تريد الحجز فيها\n"
        "3️⃣ شغّل المراقبة التلقائية\n"
        "4️⃣ انتظر — سيُرسل لك البوت إشعاراً عند التسجيل ويطلب منك رمز OTP\n\n"
        "اختر من القائمة:"
    )
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MENU

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "enter_data":
        await query.edit_message_text("🪪 *الخطوة 1/7 — رقم NIN*\n\nأرسل رقم التعريف الوطني (NIN) الخاص بك:", parse_mode="Markdown")
        return ASK_NIN

    elif action == "view_data":
        data = load_data()
        uid = str(query.from_user.id)
        if uid in data:
            u = data[uid]
            text = (
                "📋 *بياناتك المحفوظة:*\n\n"
                f"🪪 NIN: `{u.get('nin', '—')}`\n"
                f"🪪 CNIBE: `{u.get('cnibe', '—')}`\n"
                f"📱 الهاتف: `{u.get('phone', '—')}`\n"
                f"📧 البريد: `{u.get('email', '—')}`\n"
                f"🗺️ الولاية: `{u.get('wilaya', '—')}`\n"
                f"🏘️ البلدية: `{u.get('commune', '—')}`\n"
                f"💳 الدفع: `{u.get('payment', '—')}`\n"
                f"🎯 الولاية المستهدفة: `{u.get('target_wilaya', '—')}`\n"
            )
        else:
            text = "❌ لا توجد بيانات محفوظة. أدخل بياناتك أولاً."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

    elif action == "set_target":
        # عرض قائمة الولايات
        buttons = []
        for i in range(0, len(WILAYAS), 2):
            row = [InlineKeyboardButton(WILAYAS[i], callback_data=f"target_{i+1:02d}")]
            if i+1 < len(WILAYAS):
                row.append(InlineKeyboardButton(WILAYAS[i+1], callback_data=f"target_{i+2:02d}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_menu")])
        await query.edit_message_text(
            "🎯 *اختر الولاية التي تريد الحجز فيها:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        return ASK_TARGET_WILAYA

    elif action == "start_monitor":
        data = load_data()
        uid = str(query.from_user.id)
        if uid not in data or not data[uid].get("nin"):
            await query.edit_message_text("❌ يجب إدخال بياناتك أولاً قبل بدء المراقبة!")
            return MENU
        if not data[uid].get("target_wilaya"):
            await query.edit_message_text("❌ يجب تحديد الولاية المستهدفة أولاً!")
            return MENU

        # بدء مهمة المراقبة في الخلفية
        if "monitor_task" not in context.bot_data:
            context.bot_data["monitor_task"] = {}

        if uid not in context.bot_data["monitor_task"]:
            task = asyncio.create_task(monitor_loop(context, uid, query.from_user.id))
            context.bot_data["monitor_task"][uid] = task
            await query.edit_message_text(
                "✅ *تم بدء المراقبة التلقائية!*\n\n"
                f"🔍 أراقب الآن منصة أضاحي كل 2 ثانية...\n"
                f"🎯 الولاية المستهدفة: *{data[uid].get('target_wilaya')}*\n\n"
                "سأُرسل لك إشعاراً فور فتح التسجيل وأبدأ التسجيل تلقائياً! 🚀",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ المراقبة تعمل بالفعل!")
        return MENU

    elif action == "stop_monitor":
        uid = str(query.from_user.id)
        if "monitor_task" in context.bot_data and uid in context.bot_data["monitor_task"]:
            context.bot_data["monitor_task"][uid].cancel()
            del context.bot_data["monitor_task"][uid]
            await query.edit_message_text("⏹️ تم إيقاف المراقبة.")
        else:
            await query.edit_message_text("ℹ️ لا توجد مراقبة نشطة حالياً.")
        return MENU

    elif action == "back_menu":
        return await show_main_menu(query)

    return MENU

async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("📝 إدخال / تعديل بياناتي", callback_data="enter_data")],
        [InlineKeyboardButton("👁️ عرض بياناتي المحفوظة", callback_data="view_data")],
        [InlineKeyboardButton("🎯 تحديد الولاية المستهدفة", callback_data="set_target")],
        [InlineKeyboardButton("🚀 بدء المراقبة التلقائية", callback_data="start_monitor")],
        [InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="stop_monitor")],
    ]
    await query.edit_message_text(
        "🐑 *القائمة الرئيسية — بوت أضاحي*\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MENU

# ==================== جمع البيانات خطوة بخطوة ====================

async def ask_nin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["nin"] = update.message.text.strip()
    await update.message.reply_text("🪪 *الخطوة 2/7 — رقم CNIBE*\n\nأرسل رقم بطاقة الهوية البيومترية:", parse_mode="Markdown")
    return ASK_CNIBE

async def ask_cnibe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["cnibe"] = update.message.text.strip()
    await update.message.reply_text("📱 *الخطوة 3/7 — رقم الهاتف*\n\nأرسل رقم هاتفك (مثال: 0551234567):", parse_mode="Markdown")
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("📧 *الخطوة 4/7 — البريد الإلكتروني*\n\nأرسل بريدك الإلكتروني:", parse_mode="Markdown")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["email"] = update.message.text.strip()
    # عرض قائمة الولايات
    buttons = []
    for i in range(0, len(WILAYAS), 2):
        row = [InlineKeyboardButton(WILAYAS[i], callback_data=f"wilaya_{i+1:02d}")]
        if i+1 < len(WILAYAS):
            row.append(InlineKeyboardButton(WILAYAS[i+1], callback_data=f"wilaya_{i+2:02d}"))
        buttons.append(row)
    await update.message.reply_text(
        "🗺️ *الخطوة 5/7 — الولاية*\n\nاختر ولايتك:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ASK_WILAYA

async def ask_wilaya_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    code = query.data.replace("wilaya_", "")
    wilaya_name = WILAYAS[int(code)-1]
    context.user_data["wilaya"] = wilaya_name
    context.user_data["wilaya_code"] = code
    await query.edit_message_text(
        f"✅ الولاية: *{wilaya_name}*\n\n🏘️ *الخطوة 6/7 — البلدية*\n\nأرسل اسم بلديتك:",
        parse_mode="Markdown"
    )
    return ASK_COMMUNE

async def ask_commune(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["commune"] = update.message.text.strip()
    buttons = [
        [InlineKeyboardButton(v, callback_data=f"pay_{k}")]
        for k, v in PAYMENT_METHODS.items()
    ]
    await update.message.reply_text(
        "💳 *الخطوة 7/7 — طريقة الدفع*\n\nاختر طريقة الدفع المفضلة:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ASK_PAYMENT

async def ask_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    payment = query.data.replace("pay_", "")
    context.user_data["payment"] = payment

    # حفظ البيانات
    data = load_data()
    uid = str(query.from_user.id)
    data[uid] = dict(context.user_data)
    save_data(data)

    text = (
        "✅ *تم حفظ بياناتك بنجاح!*\n\n"
        f"🪪 NIN: `{context.user_data['nin']}`\n"
        f"🪪 CNIBE: `{context.user_data['cnibe']}`\n"
        f"📱 الهاتف: `{context.user_data['phone']}`\n"
        f"📧 البريد: `{context.user_data['email']}`\n"
        f"🗺️ الولاية: `{context.user_data['wilaya']}`\n"
        f"🏘️ البلدية: `{context.user_data['commune']}`\n"
        f"💳 الدفع: `{PAYMENT_METHODS[payment]}`\n\n"
        "الآن حدد الولاية المستهدفة وابدأ المراقبة! 🚀"
    )
    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MENU

async def set_target_wilaya(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    code = query.data.replace("target_", "")
    wilaya_name = WILAYAS[int(code)-1]

    data = load_data()
    uid = str(query.from_user.id)
    if uid not in data:
        data[uid] = {}
    data[uid]["target_wilaya"] = wilaya_name
    data[uid]["target_wilaya_code"] = code
    save_data(data)

    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_menu")]]
    await query.edit_message_text(
        f"✅ *تم تحديد الولاية المستهدفة:*\n🎯 {wilaya_name}\n\nالآن ابدأ المراقبة من القائمة الرئيسية!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MENU

# ==================== حلقة المراقبة ====================

async def monitor_loop(context: ContextTypes.DEFAULT_TYPE, uid: str, chat_id: int):
    """حلقة المراقبة التلقائية — تفحص المنصة كل ثانيتين"""
    logger.info(f"بدء المراقبة للمستخدم {uid}")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                data = load_data()
                if uid not in data:
                    break
                user_info = data[uid]
                target_code = user_info.get("target_wilaya_code")

                is_available = await check_wilaya_availability(session, target_code)

                if is_available:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "🔥 *تنبيه عاجل!*\n\n"
                            f"✅ الولاية *{user_info.get('target_wilaya')}* أصبحت متاحة!\n"
                            "⚡ جاري التسجيل التلقائي الآن..."
                        ),
                        parse_mode="Markdown"
                    )

                    # محاولة التسجيل التلقائي
                    result = await submit_registration(session, user_info)

                    if result.get("success"):
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                "🎉 *تم إرسال طلب التسجيل بنجاح!*\n\n"
                                "📱 *انتظر رمز OTP على هاتفك*\n"
                                "أرسل الرمز هنا عبر الأمر:\n`/otp XXXXXX`\n\n"
                                "⚠️ لديك 30 دقيقة لتأكيد الطلب!"
                            ),
                            parse_mode="Markdown"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                "⚠️ *الولاية متاحة لكن فشل التسجيل التلقائي!*\n\n"
                                f"الخطأ: `{result.get('error', 'غير معروف')}`\n\n"
                                f"🏃 *افتح المنصة الآن وسجل يدوياً:*\n{REGISTER_URL}"
                            ),
                            parse_mode="Markdown"
                        )
                    break  # أوقف المراقبة بعد التسجيل

            except asyncio.CancelledError:
                logger.info(f"تم إيقاف المراقبة للمستخدم {uid}")
                break
            except Exception as e:
                logger.error(f"خطأ في حلقة المراقبة: {e}")

            await asyncio.sleep(2)  # انتظر ثانيتين قبل الفحص التالي

# ==================== معالجة OTP ====================

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رمز OTP الذي يرسله المستخدم"""
    if not context.args:
        await update.message.reply_text("❌ استخدم الأمر هكذا: `/otp 123456`", parse_mode="Markdown")
        return

    otp_code = context.args[0]
    data = load_data()
    uid = str(update.effective_user.id)

    await update.message.reply_text(f"⏳ جاري التحقق من رمز OTP: `{otp_code}`...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as session:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": REGISTER_URL,
        }
        # ⚙️ عدّل هذا حسب الـ API الفعلي
        payload = {
            "otp": otp_code,
            "phone": data.get(uid, {}).get("phone", "")
        }
        try:
            async with session.post(
                f"{BASE_URL}/api/verify-otp",  # ⚙️ عدّل الرابط
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await update.message.reply_text(
                        "🎉 *تهانينا! تم تأكيد تسجيلك بنجاح!*\n\n"
                        "✅ ستصلك رسالة SMS بموعد ونقطة الاستلام.\n"
                        "عيد أضحى مبارك! 🐑",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ رمز OTP غير صحيح أو منتهي الصلاحية.\n"
                        f"جرب مرة أخرى: `/otp XXXXXX`",
                        parse_mode="Markdown"
                    )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")

# ==================== تشغيل البوت ====================

def main():
    # ⚙️ ضع توكن البوت هنا
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8860768793:AAEUqmtEWOUWXYMDtI6Ju0612tzUPEn9JB8")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(menu_callback)],
            ASK_NIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nin)],
            ASK_CNIBE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cnibe)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASK_WILAYA: [CallbackQueryHandler(ask_wilaya_callback, pattern=r"^wilaya_")],
            ASK_COMMUNE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_commune)],
            ASK_PAYMENT: [CallbackQueryHandler(ask_payment_callback, pattern=r"^pay_")],
            ASK_TARGET_WILAYA: [CallbackQueryHandler(set_target_wilaya, pattern=r"^target_")],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("otp", handle_otp))
    # معالجة أزرار القائمة الرئيسية خارج ConversationHandler
    app.add_handler(CallbackQueryHandler(menu_callback))

    logger.info("🚀 البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
