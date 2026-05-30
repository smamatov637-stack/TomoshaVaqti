#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 TOMOSHA VAQTI BOT - @TomoshaVaqti_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dasturchi: @salohiddinWebDev
Versiya: 4.0 PREMIUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Yangiliklar v4.0:
  ✅ Har yangi kino qo'shilganda avtomatik DB nusxa adminга
  ✅ Ombor guruhiga har 1 soatda DB fayl yuboriladi
  ✅ Admin o'chirish - tugma orqali (matn pastida)
  ✅ Kino qo'shishda tavsif so'rash + Skip tugma
  ✅ Tavsif ombordagi film captioniga yoziladi
  ✅ DB da tavsif maydoni saqlanadi
  ✅ v3.0 barcha funksiyalari saqlab qolindi
"""

import logging
import time
import asyncio
import json
import io
from datetime import datetime
from collections import defaultdict
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.error import TelegramError, Forbidden

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️  SOZLAMALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = "8838342197:AAHxbtIOrG_6JaTH8zLMbgk5pKTmYNTxm5Y"
BOT_USERNAME = "TomoshaVaqti_bot"
DEVELOPER_USERNAME = "@salohiddinWebDev"
DEVELOPER_ID = 8505118420  # Super-ega: hech kim uni adminlikdan chiqara olmaydi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 LOGGING (minimal - CPU tejash)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💾 MA'LUMOTLAR BAZASI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🎬 Kinolar: {raqam: {message_id, chat_id, nomi, tavsif, qoshilgan}}
movies_db = {}

# 👥 Foydalanuvchilar
users_db = {}

# 🚫 Bloklangan foydalanuvchilar
blocked_users = {}

# ⏱️ Spam bloklash
spam_tracker = defaultdict(lambda: {"hisoblagich": 0, "birinchi_vaqt": 0, "blok_vaqti": 0})

# 📢 Majburiy kanallar
required_channels = {}

# 🏪 Ombor guruhlar
storage_groups = {}

# 👑 Adminlar
admins_db = {DEVELOPER_ID: {"ism": "Super-Ega", "qoshilgan": datetime.now().strftime("%d.%m.%Y")}}

# 📈 Statistika
stats = {
    "jami_foydalanuvchilar": 0,
    "bugungi_foydalanuvchilar": set(),
    "jami_sorovlar": 0,
    "bugungi_sorovlar": 0,
    "bugungi_sana": datetime.now().strftime("%d.%m.%Y"),
    "kanal_statistika": defaultdict(int),
    "botni_bloklaganlar": set(),
}

# 🔄 Admin holatlari
admin_state = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛠️  YORDAMCHI FUNKSIYALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_admin(user_id: int) -> bool:
    return user_id in admins_db or user_id == DEVELOPER_ID

def is_super_owner(user_id: int) -> bool:
    return user_id == DEVELOPER_ID

def check_spam(user_id: int) -> bool:
    if is_admin(user_id):
        return False
    tracker = spam_tracker[user_id]
    current_time = time.time()
    if tracker["blok_vaqti"] > 0:
        if current_time - tracker["blok_vaqti"] < 60:
            return True
        spam_tracker[user_id] = {"hisoblagich": 0, "birinchi_vaqt": 0, "blok_vaqti": 0}
    if tracker["hisoblagich"] == 0 or current_time - tracker["birinchi_vaqt"] > 10:
        spam_tracker[user_id] = {"hisoblagich": 1, "birinchi_vaqt": current_time, "blok_vaqti": 0}
        return False
    tracker["hisoblagich"] += 1
    if tracker["hisoblagich"] >= 6:
        tracker["blok_vaqti"] = current_time
        return True
    return False

def remaining_block_time(user_id: int) -> int:
    tracker = spam_tracker[user_id]
    if tracker["blok_vaqti"] > 0:
        return max(0, int(60 - (time.time() - tracker["blok_vaqti"])))
    return 0

def update_stats_day():
    today = datetime.now().strftime("%d.%m.%Y")
    if stats["bugungi_sana"] != today:
        stats["bugungi_sana"] = today
        stats["bugungi_foydalanuvchilar"] = set()
        stats["bugungi_sorovlar"] = 0

def register_user(user):
    update_stats_day()
    user_id = user.id
    if user_id not in users_db:
        users_db[user_id] = {
            "ism": user.first_name or "Noma'lum",
            "username": f"@{user.username}" if user.username else "Yo'q",
            "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "faol": True,
        }
        stats["jami_foydalanuvchilar"] += 1
    else:
        users_db[user_id]["faol"] = True
        users_db[user_id]["ism"] = user.first_name or users_db[user_id]["ism"]
        if user.username:
            users_db[user_id]["username"] = f"@{user.username}"
    stats["bugungi_foydalanuvchilar"].add(user_id)

async def check_channels_membership(bot, user_id: int):
    if not required_channels:
        return True, []
    not_subscribed = []
    for channel_id, channel_info in required_channels.items():
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked', 'banned']:
                not_subscribed.append(channel_info)
        except TelegramError:
            not_subscribed.append(channel_info)
    return len(not_subscribed) == 0, not_subscribed

def get_subscription_keyboard(channels):
    kb = [[InlineKeyboardButton(f"📢 {ch['nomi']}", url=ch['link'])] for ch in channels]
    kb.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(kb)

def get_main_keyboard(user_id: int):
    return get_admin_keyboard(user_id) if is_admin(user_id) else get_user_keyboard()

def get_user_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 Kino Qidirish")],
        [KeyboardButton("💬 Xabar Yuborish")],
    ], resize_keyboard=True)

def get_admin_keyboard(user_id: int = 0):
    rows = [
        [KeyboardButton("🎬 Kino Qo'shish"),      KeyboardButton("🗑️ Kino O'chirish")],
        [KeyboardButton("📢 Kanal Qo'shish"),      KeyboardButton("📛 Kanal O'chirish")],
        [KeyboardButton("🏪 Ombor Qo'shish"),      KeyboardButton("🗂️ Ombor Ko'rish")],
        [KeyboardButton("💾 DB Nusxalash"),         KeyboardButton("📥 DB Qo'shish")],
        [KeyboardButton("📊 Statistika"),           KeyboardButton("📅 Kunlik Statistika")],
        [KeyboardButton("📣 Reklama Yuborish"),     KeyboardButton("👥 Foydalanuvchilar")],
        [KeyboardButton("🚫 Foydalanuvchi Bloklash"), KeyboardButton("✅ Blokni Ochish")],
        [KeyboardButton("👑 Admin Qo'shish"),       KeyboardButton("👑 Admin O'chirish")],
        [KeyboardButton("🎬 Kino Qidirish"),        KeyboardButton("⚙️ Bot Sozlamalari")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💾 DB EXPORT / IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def export_database() -> dict:
    return {
        "version": "4.0",
        "export_vaqt": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "jami_kinolar": len(movies_db),
        "kinolar": movies_db,
    }

def make_db_file() -> io.BytesIO:
    """DB ni BytesIO ga chiqaradi (yuborish uchun)"""
    data = export_database()
    bio = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    bio.name = f"database_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.json"
    return bio

def import_database(data: dict):
    qoshildi = 0
    xato = 0
    xatolar = []
    for raqam, info in data.get("kinolar", {}).items():
        try:
            if "message_id" not in info or "chat_id" not in info:
                xatolar.append(f"#{raqam}: maydon yetishmaydi")
                xato += 1
                continue
            if raqam not in movies_db:
                movies_db[raqam] = {
                    "message_id": int(info["message_id"]),
                    "chat_id":    int(info["chat_id"]),
                    "nomi":       info.get("nomi", f"Kino_{raqam}"),
                    "tavsif":     info.get("tavsif", ""),
                    "qoshilgan":  info.get("qoshilgan", datetime.now().strftime("%d.%m.%Y %H:%M")),
                }
                qoshildi += 1
        except Exception as e:
            xatolar.append(f"#{raqam}: {e}")
            xato += 1
    return qoshildi, xato, xatolar

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📤 OMBOR VA ADMINGA DB YUBORISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def send_db_to_admin(bot, raqam: str):
    """Yangi kino qo'shilganda darhol adminga DB yuboradi"""
    if not movies_db:
        return
    try:
        bio = make_db_file()
        caption = (
            f"💾 <b>Avtomatik DB Nusxa</b>\n\n"
            f"🆕 Yangi kino qo'shildi: <code>{raqam}</code>\n"
            f"📊 Jami kinolar: <b>{len(movies_db)}</b> ta\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        for admin_id in list(admins_db.keys()):
            bio.seek(0)
            try:
                await bot.send_document(admin_id, document=bio, caption=caption, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"DB admin yuborish xatosi: {e}")

async def send_db_to_storage(context: ContextTypes.DEFAULT_TYPE):
    """Har 1 soatda ombor guruhlariga DB yuboradi"""
    if not storage_groups or not movies_db:
        return
    try:
        bio = make_db_file()
        caption = (
            f"🔄 <b>Ombor DB Yangilash</b>\n\n"
            f"📊 Jami kinolar: <b>{len(movies_db)}</b> ta\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        for gid in list(storage_groups.keys()):
            bio.seek(0)
            try:
                await context.bot.send_document(gid, document=bio, caption=caption, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"DB ombor yuborish xatosi: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📅 KUNLIK BROADCAST (08:00 va 20:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def hourly_job(context: ContextTypes.DEFAULT_TYPE):
    """Har soat ishlaydigan job: broadcast + DB ombor"""
    now = datetime.now()
    soat = now.hour

    # 1. Ombor guruhlariga DB yuborish (har soat)
    await send_db_to_storage(context)

    # 2. Kunlik broadcast faqat 08:00 va 20:00 da
    if soat not in [8, 20]:
        return

    broadcast_text = (
        "🎬 <b>/start /start /start /start /start</b>\n\n"
        "╔══════════════════════════╗\n"
        "║   🍿 <b>Tomosha Vaqti Bot</b> 🍿   ║\n"
        "╚══════════════════════════╝\n\n"
        "👋 Kino ko'rish vaqti keldi!\n"
        "🔢 Kino raqamini yuboring va tomosha qiling!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 /start bosing yoki raqam yuboring!"
    )

    sent = failed = blocked = 0
    yuborilganlar = []

    for uid in list(users_db.keys()):
        if uid in blocked_users or is_admin(uid):
            continue
        try:
            await context.bot.send_message(uid, broadcast_text, parse_mode="HTML")
            sent += 1
            yuborilganlar.append(uid)
            await asyncio.sleep(0.1)
        except Forbidden:
            blocked += 1
            stats["botni_bloklaganlar"].add(uid)
            users_db[uid]["faol"] = False
        except TelegramError:
            failed += 1

    idlar_text = ", ".join(str(i) for i in yuborilganlar[:50])
    if len(yuborilganlar) > 50:
        idlar_text += "..."

    natija = (
        f"📣 <b>Kunlik Broadcast Natijasi</b>\n\n"
        f"🕐 <b>Vaqt:</b> {now.strftime('%d.%m.%Y %H:%M')}\n"
        f"{'🌅 Ertalabgi' if soat == 8 else '🌆 Kechqurungi'} broadcast\n\n"
        f"✅ <b>Muvaffaqiyatli:</b> {sent} ta\n"
        f"🚫 <b>Bot bloklagan:</b> {blocked} ta\n"
        f"❌ <b>Xatolik:</b> {failed} ta\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Yuborilgan IDlar:</b>\n"
        f"<code>{idlar_text}</code>\n\n"
        f"📈 Jami: {sent + blocked + failed} ta urinish"
    )
    for admin_id in list(admins_db.keys()):
        try:
            await context.bot.send_message(admin_id, natija, parse_mode="HTML")
        except Exception:
            pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📜 MATNLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WELCOME_TEXT = (
    "🎬 <b>TOMOSHA VAQTI'ga xush kelibsiz!</b>\n\n"
    "╔══════════════════════════╗\n"
    "║   🍿 <b>Tomosha Vaqti Bot</b> 🍿   ║\n"
    "╚══════════════════════════╝\n\n"
    "Salom, <b>{ism}</b>! 👋\n\n"
    "🌟 Bu bot orqali siz:\n"
    "   ✦ Minglab kinolarni topishingiz\n"
    "   ✦ Eng sara filmlarni yuklab olishingiz mumkin!\n\n"
    "🔢 <b>Misol:</b> <code>1001</code> → Film yuboriladi\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💫 <i>Tomosha Vaqti — eng yaxshi kinolar bir joyda!</i>"
)

SUB_REQUIRED = (
    "🔐 <b>Diqqat! Obuna talab qilinadi</b>\n\n"
    "╔══════════════════════════╗\n"
    "║  📢 <b>MAJBURIY OBUNA</b> 📢    ║\n"
    "╚══════════════════════════╝\n\n"
    "Salom, <b>{ism}</b>! 👋\n\n"
    "Botdan foydalanish uchun obuna bo'ling:\n\n"
    "{kanallar}\n\n"
    "✅ Obuna bo'lganingizdan so'ng \"Tekshirish\" bosing!"
)

SPAM_TEXT = (
    "🚫 <b>Vaqtincha bloklangansiz!</b>\n\n"
    "⏳ <b>Blok muddati:</b> <code>{vaqt}</code> soniya\n\n"
    "⏱️ <i>Sabr qiling, tez orada ochiladi!</i>"
)

ADMIN_BLOCKED_TEXT = (
    "🚫 <b>Sizga kirish taqiqlangan!</b>\n\n"
    "Siz adminlar tomonidan bloklangansiz.\n\n"
    "📞 Murojaat: {developer}"
)

NOT_FOUND_TEXT = (
    "❌ <b>Kino topilmadi!</b>\n\n"
    "Siz kiritgan raqam: <code>{raqam}</code>\n\n"
    "💡 Kino so'rash: \"💬 Xabar Yuborish\" tugmasi"
)

SUGGEST_TEXT = (
    "💬 <b>Adminga Xabar Yuborish</b>\n\n"
    "╔══════════════════════════╗\n"
    "║  📨 <b>XABAR YUBORISH</b> 📨    ║\n"
    "╚══════════════════════════╝\n\n"
    "⚠️ <b>Bu xabaringiz to'g'ridan-to'g'ri adminga boradi!</b>\n\n"
    "📝 Xabaringizni yuboring (matn, rasm, video):"
)

SENT_TEXT = (
    "✅ <b>Xabaringiz adminga yuborildi!</b>\n\n"
    "🎉 Rahmat, <b>{ism}</b>!\n\n"
    "Tez orada ko'rib chiqiladi. 🙏"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 START VA CALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    register_user(user)

    if user_id in blocked_users and not is_admin(user_id):
        all_ok, not_sub = await check_channels_membership(context.bot, user_id)
        if not all_ok:
            await update.message.reply_text(
                SUB_REQUIRED.format(ism=user.first_name,
                    kanallar="\n".join(f"   📌 <b>{c['nomi']}</b>" for c in not_sub)),
                reply_markup=get_subscription_keyboard(not_sub), parse_mode="HTML")
            return
        await update.message.reply_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
        return

    all_ok, not_sub = await check_channels_membership(context.bot, user_id)
    if not all_ok and not is_admin(user_id):
        await update.message.reply_text(
            SUB_REQUIRED.format(ism=user.first_name,
                kanallar="\n".join(f"   📌 <b>{c['nomi']}</b>" for c in not_sub)),
            reply_markup=get_subscription_keyboard(not_sub), parse_mode="HTML")
        return

    await update.message.reply_text(
        WELCOME_TEXT.format(ism=user.first_name),
        reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    data = query.data
    await query.answer()

    # ━━━ OBUNA TEKSHIRISH ━━━
    if data == "check_subscription":
        all_ok, not_sub = await check_channels_membership(context.bot, user_id)
        if all_ok:
            if user_id in blocked_users and not is_admin(user_id):
                await query.edit_message_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
                return
            await query.edit_message_text(
                f"✅ <b>Obuna tasdiqlandi!</b>\n\nSalom, <b>{user.first_name}</b>! 🎬\nEndi botdan foydalana olasiz!",
                parse_mode="HTML")
            await context.bot.send_message(user_id, WELCOME_TEXT.format(ism=user.first_name),
                reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
        else:
            await query.edit_message_text(
                SUB_REQUIRED.format(ism=user.first_name,
                    kanallar="\n".join(f"   📌 <b>{c['nomi']}</b>" for c in not_sub)),
                reply_markup=get_subscription_keyboard(not_sub), parse_mode="HTML")
        return

    if not is_admin(user_id):
        return

    # ━━━ KINO O'CHIRISH TASDIQLASH ━━━
    if data.startswith("confirm_delete_movie_"):
        movie_id = data[len("confirm_delete_movie_"):]
        if movie_id in movies_db:
            name = movies_db[movie_id]["nomi"]
            del movies_db[movie_id]
            await query.edit_message_text(
                f"✅ <b>Kino o'chirildi!</b>\n\n🔢 <code>{movie_id}</code> — {name}\n📊 Jami: <b>{len(movies_db)}</b> ta",
                parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Kino topilmadi!")
        return

    if data == "cancel_delete_movie":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    # ━━━ KANAL O'CHIRISH ━━━
    if data.startswith("confirm_delete_channel_"):
        ch_id = int(data[len("confirm_delete_channel_"):])
        if ch_id in required_channels:
            name = required_channels[ch_id]["nomi"]
            del required_channels[ch_id]
            await query.edit_message_text(f"✅ <b>Kanal o'chirildi!</b>\n📛 {name}\n📢 Jami: {len(required_channels)} ta", parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Topilmadi!")
        return

    if data == "cancel_delete_channel":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    # ━━━ FOYDALANUVCHI BLOKLASH ━━━
    if data.startswith("confirm_block_user_"):
        uid = int(data[len("confirm_block_user_"):])
        if uid not in blocked_users:
            blocked_users[uid] = {"sabab": "Admin blokladi", "vaqt": datetime.now().strftime("%d.%m.%Y %H:%M")}
            ui = users_db.get(uid, {})
            await query.edit_message_text(
                f"🚫 <b>Bloklandi!</b>\n\n👤 ID: <code>{uid}</code>\n👤 Ism: {ui.get('ism', 'Noma_lum')}",
                parse_mode="HTML")
        else:
            await query.edit_message_text("⚠️ Allaqachon bloklangan!")
        return

    if data.startswith("cancel_block_user"):
        await query.edit_message_text("❌ Bloklash bekor qilindi.")
        return

    # ━━━ ADMIN O'CHIRISH (faqat super-ega) ━━━
    if data.startswith("confirm_remove_admin_"):
        if not is_super_owner(user_id):
            await query.edit_message_text("❌ Faqat super-ega admin o'chira oladi!")
            return
        target_id = int(data[len("confirm_remove_admin_"):])
        if target_id == DEVELOPER_ID:
            await query.edit_message_text("❌ Super-egani o'chirib bo'lmaydi!")
            return
        if target_id in admins_db:
            del admins_db[target_id]
            await query.edit_message_text(
                f"✅ <b>Admin o'chirildi!</b>\n\n🆔 <code>{target_id}</code>\n👑 Qolgan: {len(admins_db)} ta",
                parse_mode="HTML")
        return

    if data == "cancel_remove_admin":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    # ━━━ TAVSIF SKIP ━━━
    if data == "skip_tavsif":
        state = admin_state.get(user_id, {})
        if state.get("holat") == "kino_tavsif_kutish":
            raqam = state["raqam"]
            # Tavsif yo'q - saqlash
            movies_db[raqam]["tavsif"] = ""
            del admin_state[user_id]
            await query.edit_message_text(
                f"✅ <b>Tavsif o'tkazib yuborildi.</b>\n\n"
                f"🔢 Raqam: <code>{raqam}</code>\n"
                f"🎬 Nomi: {movies_db[raqam]['nomi']}\n\n"
                f"📊 Jami kinolar: <b>{len(movies_db)}</b> ta",
                parse_mode="HTML")
            # DB yuborish
            await send_db_to_admin(context.bot, raqam)
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📨 ASOSIY XABAR HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    user_id = user.id
    message = update.message
    text = message.text or ""

    register_user(user)

    # Spam tekshiruvi
    if check_spam(user_id) and not is_admin(user_id):
        await message.reply_text(SPAM_TEXT.format(vaqt=remaining_block_time(user_id)), parse_mode="HTML")
        return

    stats["jami_sorovlar"] += 1
    stats["bugungi_sorovlar"] += 1

    # Admin holat
    if is_admin(user_id) and user_id in admin_state:
        await handle_admin_state(update, context, text)
        return

    # Bloklangan
    if user_id in blocked_users and not is_admin(user_id):
        all_ok, not_sub = await check_channels_membership(context.bot, user_id)
        if not all_ok:
            await message.reply_text(
                SUB_REQUIRED.format(ism=user.first_name,
                    kanallar="\n".join(f"   📌 <b>{c['nomi']}</b>" for c in not_sub)),
                reply_markup=get_subscription_keyboard(not_sub), parse_mode="HTML")
            return
        await message.reply_text(ADMIN_BLOCKED_TEXT.format(developer=DEVELOPER_USERNAME), parse_mode="HTML")
        return

    # Kanal obuna
    if not is_admin(user_id):
        all_ok, not_sub = await check_channels_membership(context.bot, user_id)
        if not all_ok:
            await message.reply_text(
                SUB_REQUIRED.format(ism=user.first_name,
                    kanallar="\n".join(f"   📌 <b>{c['nomi']}</b>" for c in not_sub)),
                reply_markup=get_subscription_keyboard(not_sub), parse_mode="HTML")
            return

    # ━━━━━━━━━━━━━━━━ TUGMALAR ━━━━━━━━━━━━━━━━

    if text == "🎬 Kino Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "kino_raqam_kutish"}
        await message.reply_text(
            "🎬 <b>Kino Qo'shish</b>\n\n"
            "📋 Jarayon: Raqam → Fayl → Tavsif\n\n"
            "🔢 <b>Kino raqamini yuboring:</b>\n"
            "(Masalan: <code>1001</code>)\n\n"
            "❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "🗑️ Kino O'chirish" and is_admin(user_id):
        if not movies_db:
            await message.reply_text("❌ <b>Bazada kino yo'q!</b>", parse_mode="HTML")
            return
        admin_state[user_id] = {"holat": "kino_ochirish_raqam"}
        movie_list = "\n".join(f"   🎬 <code>{k}</code> — {v['nomi'][:25]}" for k, v in list(movies_db.items())[-20:])
        await message.reply_text(
            f"🗑️ <b>Kino O'chirish</b>\n\n"
            f"📋 <b>Kinolar (oxirgi 20):</b>\n{movie_list}\n\n"
            f"🔢 <b>O'chiriladigan kino raqamini yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "📢 Kanal Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "kanal_qoshish_id"}
        await message.reply_text(
            "📢 <b>Majburiy Kanal Qo'shish</b>\n\n"
            "ℹ️ Botni kanalga <b>admin</b> qiling — avtomatik qo'shiladi.\n\n"
            "📌 <b>Kanal ID yuboring:</b>\n<code>-1001234567890</code>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "📛 Kanal O'chirish" and is_admin(user_id):
        if not required_channels:
            await message.reply_text("❌ <b>Majburiy kanal yo'q!</b>", parse_mode="HTML")
            return
        admin_state[user_id] = {"holat": "kanal_ochirish_id"}
        ch_list = "\n".join(f"   📢 <code>{k}</code> — {v['nomi']}" for k, v in required_channels.items())
        await message.reply_text(
            f"📛 <b>Kanal O'chirish</b>\n\n📋 <b>Kanallar:</b>\n{ch_list}\n\n"
            f"📌 <b>O'chirish uchun ID yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "🏪 Ombor Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "ombor_qoshish"}
        await message.reply_text(
            "🏪 <b>Ombor Guruh Qo'shish</b>\n\n"
            "Kinolar saqlanadigan guruh yoki kanal.\n\n"
            "⚠️ <b>Avval:</b> Botni guruhga admin qiling!\n\n"
            "📌 <b>Link yoki ID yuboring:</b>\n"
            "<code>https://t.me/guruhim</code>\n"
            "yoki <code>-1001234567890</code>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "🗂️ Ombor Ko'rish" and is_admin(user_id):
        if not storage_groups:
            await message.reply_text("ℹ️ <b>Ombor yo'q!</b>\n\"🏪 Ombor Qo'shish\" bosing.", parse_mode="HTML")
            return
        grp_list = "\n".join(
            f"   🏪 <code>{gid}</code>\n      📛 {gi['nomi']}\n      🔗 {gi['link']}"
            for gid, gi in storage_groups.items()
        )
        await message.reply_text(
            f"🗂️ <b>Ombor Guruhlar</b>\n\n📊 Jami: <b>{len(storage_groups)}</b> ta\n\n{grp_list}",
            parse_mode="HTML")
        return

    if text == "💾 DB Nusxalash" and is_admin(user_id):
        if not movies_db:
            await message.reply_text("❌ <b>Bazada kino yo'q!</b>", parse_mode="HTML")
            return
        try:
            bio = make_db_file()
            await message.reply_document(
                document=bio,
                caption=f"💾 <b>Database Nusxasi</b>\n\n📊 Jami: <b>{len(movies_db)}</b> ta kino\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML")
        except Exception as e:
            await message.reply_text(f"❌ Xatolik: {e}", parse_mode="HTML")
        return

    if text == "📥 DB Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "db_import_kutish"}
        await message.reply_text(
            f"📥 <b>Database Import</b>\n\n"
            f"📎 JSON faylni yuboring.\n"
            f"Joriy bazada: <b>{len(movies_db)}</b> ta kino\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "📊 Statistika" and is_admin(user_id):
        update_stats_day()
        faol = sum(1 for u in users_db.values() if u.get("faol"))
        await message.reply_text(
            f"📊 <b>Bot Statistikasi</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['jami_foydalanuvchilar']}</b>\n"
            f"👥 Faol: <b>{faol}</b>\n"
            f"🚫 Bloklangan: <b>{len(blocked_users)}</b>\n"
            f"🎬 Kinolar: <b>{len(movies_db)}</b>\n"
            f"📨 Jami so'rovlar: <b>{stats['jami_sorovlar']}</b>\n"
            f"📨 Bugungi: <b>{stats['bugungi_sorovlar']}</b>\n"
            f"🏪 Ombor: <b>{len(storage_groups)}</b>\n"
            f"📢 Kanallar: <b>{len(required_channels)}</b>\n"
            f"👑 Adminlar: <b>{len(admins_db)}</b>\n\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML")
        return

    if text == "📅 Kunlik Statistika" and is_admin(user_id):
        update_stats_day()
        await message.reply_text(
            f"📅 <b>Kunlik Statistika</b>\n\n"
            f"📅 Sana: {stats['bugungi_sana']}\n"
            f"👥 Yangi: <b>{len(stats['bugungi_foydalanuvchilar'])}</b>\n"
            f"📨 Bugungi so'rovlar: <b>{stats['bugungi_sorovlar']}</b>\n"
            f"📈 Jami: <b>{stats['jami_foydalanuvchilar']}</b>\n"
            f"🎬 Kinolar: <b>{len(movies_db)}</b>\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="HTML")
        return

    if text == "📣 Reklama Yuborish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "reklama_kutish"}
        await message.reply_text(
            "📣 <b>Reklama Yuborish</b>\n\n"
            "Matn, rasm, video — barchasi mumkin.\n"
            "Barcha foydalanuvchilarga yuboriladi.\n\n"
            "📨 <b>Reklama xabarini yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "👥 Foydalanuvchilar" and is_admin(user_id):
        users_list = list(users_db.items())[-15:]
        utext = "\n".join(
            f"{'🚫' if uid in blocked_users else '✅'} <code>{uid}</code> | {ui['ism'][:12]} | {ui['username']}"
            for uid, ui in users_list
        )
        await message.reply_text(
            f"👥 <b>Foydalanuvchilar</b>\n\n"
            f"📊 Jami: <b>{len(users_db)}</b> ta\n"
            f"🚫 Bloklangan: <b>{len(blocked_users)}</b> ta\n\n"
            f"<b>Oxirgi 15:</b>\n{utext}\n\n"
            f"✅=Faol  🚫=Bloklangan",
            parse_mode="HTML")
        return

    if text == "🚫 Foydalanuvchi Bloklash" and is_admin(user_id):
        admin_state[user_id] = {"holat": "bloklash_id"}
        await message.reply_text(
            "🚫 <b>Foydalanuvchi Bloklash</b>\n\n"
            "🔢 <b>Foydalanuvchi ID sini yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "✅ Blokni Ochish" and is_admin(user_id):
        if not blocked_users:
            await message.reply_text("ℹ️ <b>Bloklangan foydalanuvchi yo'q!</b>", parse_mode="HTML")
            return
        bl_list = "\n".join(
            f"   🚫 <code>{uid}</code> — {users_db.get(uid, {}).get('ism', 'Noma_lum')}"
            for uid in list(blocked_users.keys())[:20]
        )
        admin_state[user_id] = {"holat": "blok_ochish_id"}
        await message.reply_text(
            f"✅ <b>Blokni Ochish</b>\n\n📋 Bloklangan:\n{bl_list}\n\n"
            f"🔢 <b>ID yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    if text == "👑 Admin Qo'shish" and is_admin(user_id):
        admin_state[user_id] = {"holat": "admin_qoshish_id"}
        await message.reply_text(
            "👑 <b>Admin Qo'shish</b>\n\n"
            "🔢 <b>Yangi admin Telegram ID sini yuboring:</b>\n\n❌ Bekor: /cancel",
            parse_mode="HTML")
        return

    # ━━━ ADMIN O'CHIRISH (yangi tugma bilan) ━━━
    if text == "👑 Admin O'chirish" and is_admin(user_id):
        if not is_super_owner(user_id):
            await message.reply_text("❌ Faqat super-ega admin o'chira oladi!")
            return
        # Super-egani chiqarib qolgan adminlarni ko'rsat
        boshqa_adminlar = {aid: ainfo for aid, ainfo in admins_db.items() if aid != DEVELOPER_ID}
        if not boshqa_adminlar:
            await message.reply_text("ℹ️ <b>O'chiriladigan admin yo'q!</b>\n\nFaqat siz — super-ega adminsiz.", parse_mode="HTML")
            return

        # Har bir admin uchun inline tugma
        kb = []
        for aid, ainfo in boshqa_adminlar.items():
            label = f"❌ {ainfo['ism'][:15]} | {aid}"
            kb.append([InlineKeyboardButton(label, callback_data=f"confirm_remove_admin_{aid}")])
        kb.append([InlineKeyboardButton("🚫 Yopish", callback_data="cancel_remove_admin")])

        await message.reply_text(
            f"👑 <b>Admin O'chirish</b>\n\n"
            f"╔══════════════════════════╗\n"
            f"║  🗑️ <b>ADMINLAR RO'YXATI</b>  ║\n"
            f"╚══════════════════════════╝\n\n"
            f"O'chirmoqchi bo'lgan adminni bosing:\n\n"
            f"🔒 Super-ega (<code>{DEVELOPER_ID}</code>) o'chira olmaysiz.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML")
        return

    if text == "⚙️ Bot Sozlamalari" and is_admin(user_id):
        admins_list = "\n".join(
            f"   {'🔒 SUPER-EGA' if aid == DEVELOPER_ID else '🔑'} <code>{aid}</code> — {ai['ism']}"
            for aid, ai in admins_db.items()
        )
        await message.reply_text(
            f"⚙️ <b>Bot Sozlamalari</b>\n\n"
            f"🤖 Bot: @{BOT_USERNAME}\n"
            f"👨‍💻 Dasturchi: {DEVELOPER_USERNAME}\n\n"
            f"👑 <b>Adminlar:</b>\n{admins_list}\n\n"
            f"📢 Kanallar: {len(required_channels)} ta\n"
            f"🏪 Ombor: {len(storage_groups)} ta\n"
            f"🎬 Kinolar: {len(movies_db)} ta\n"
            f"👥 Foydalanuvchilar: {len(users_db)} ta\n\n"
            f"🔄 <i>Version: 4.0 PREMIUM</i>",
            parse_mode="HTML")
        return

    if text == "💬 Xabar Yuborish":
        admin_state[user_id] = {"holat": "user_xabar_yuborish"}
        await message.reply_text(SUGGEST_TEXT, parse_mode="HTML")
        return

    if text == "🎬 Kino Qidirish":
        await message.reply_text(
            "🔍 <b>Kino Qidirish</b>\n\n"
            "🔢 Kino raqamini yuboring!\n"
            "📌 Misol: <code>1001</code>",
            parse_mode="HTML")
        return

    # ━━━ RAQAM → KINO ━━━
    if text and text.strip().isdigit():
        movie_id = text.strip()
        if movie_id in movies_db:
            movie = movies_db[movie_id]
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=movie["chat_id"],
                    message_id=movie["message_id"],
                )
            except TelegramError as e:
                await message.reply_text("⚠️ <b>Kino yuborishda xatolik!</b>\nAdmin bilan bog'laning.", parse_mode="HTML")
        else:
            await message.reply_text(NOT_FOUND_TEXT.format(raqam=movie_id), parse_mode="HTML")
        return

    if not is_admin(user_id):
        await message.reply_text(
            "❓ <b>Tushunmadim!</b>\n\n"
            "📌 Kino olish uchun raqam yuboring: <code>1001</code>\n"
            "📌 Pastdagi tugmalardan foydalaning!",
            parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔧 ADMIN HOLAT HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def handle_admin_state(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user = update.effective_user
    user_id = user.id
    message = update.message
    state = admin_state.get(user_id, {})
    holat = state.get("holat", "")

    # ━━━ 1. KINO RAQAM ━━━
    if holat == "kino_raqam_kutish":
        if text and text.strip().isdigit():
            raqam = text.strip()
            if raqam in movies_db:
                await message.reply_text(
                    f"⚠️ <b>Bu raqam band!</b>\n🔢 <code>{raqam}</code> — {movies_db[raqam]['nomi']}\n\nBoshqa raqam yoki /cancel",
                    parse_mode="HTML")
                return
            admin_state[user_id] = {"holat": "kino_fayl_kutish", "raqam": raqam}
            await message.reply_text(
                f"✅ <b>Raqam qabul qilindi: <code>{raqam}</code></b>\n\n"
                f"🎬 <b>Endi film faylini yuboring:</b>\n(Video, rasm, hujjat — istalgan format)\n\n❌ Bekor: /cancel",
                parse_mode="HTML")
        else:
            await message.reply_text("❌ Faqat raqam yuboring! Masalan: <code>1001</code>", parse_mode="HTML")
        return

    # ━━━ 2. KINO FAYL ━━━
    if holat == "kino_fayl_kutish":
        raqam = state["raqam"]
        if message.video:
            movie_name = message.video.file_name or f"Video_{raqam}"
        elif message.document:
            movie_name = message.document.file_name or f"Fayl_{raqam}"
        elif message.photo:
            movie_name = f"Rasm_{raqam}"
        elif message.text:
            movie_name = message.text[:50]
        elif message.audio:
            movie_name = message.audio.file_name or f"Audio_{raqam}"
        else:
            movie_name = f"Kino_{raqam}"

        # Vaqtincha saqlash (tavsif so'rash uchun)
        movies_db[raqam] = {
            "message_id": message.message_id,
            "chat_id": message.chat_id,
            "nomi": movie_name,
            "tavsif": "",
            "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }

        admin_state[user_id] = {"holat": "kino_tavsif_kutish", "raqam": raqam}

        skip_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Skip (tavsif o'tkazish)", callback_data="skip_tavsif")
        ]])

        await message.reply_text(
            f"✅ <b>Fayl qabul qilindi!</b>\n\n"
            f"🔢 Raqam: <code>{raqam}</code>\n"
            f"🎬 Nomi: {movie_name}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Kino tavsifini yuboring:</b>\n"
            f"(Yil, janr, rejissyor va boshqalar)\n\n"
            f"💡 Misol:\n"
            f"<i>🎬 Avengers: Endgame (2019)\n"
            f"🎭 Janr: Fantastika, Harakat\n"
            f"⭐ IMDB: 8.4/10</i>\n\n"
            f"yoki ⏭️ Skip bosing",
            reply_markup=skip_kb,
            parse_mode="HTML")
        return

    # ━━━ 3. KINO TAVSIF ━━━
    if holat == "kino_tavsif_kutish":
        raqam = state["raqam"]
        tavsif = text.strip() if text else ""

        if raqam not in movies_db:
            await message.reply_text("❌ Xatolik: kino bazada topilmadi. Qaytadan qo'shing.", parse_mode="HTML")
            del admin_state[user_id]
            return

        # Tavsifni saqlash
        movies_db[raqam]["tavsif"] = tavsif

        del admin_state[user_id]

        # Ombordagi film captionini yangilash (agar ombor bo'lsa)
        movie = movies_db[raqam]
        if tavsif and storage_groups:
            caption_text = (
                f"🎬 <b>Raqam: {raqam}</b>\n\n"
                f"{tavsif}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Qo'shilgan: {movie['qoshilgan']}"
            )
            try:
                await context.bot.edit_message_caption(
                    chat_id=movie["chat_id"],
                    message_id=movie["message_id"],
                    caption=caption_text,
                    parse_mode="HTML"
                )
            except Exception:
                # Caption bo'lmasa yoki xatolik bo'lsa — oddiy xabar yuboramiz
                pass

        await message.reply_text(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"╔══════════════════════════╗\n"
            f"║  🎬 <b>QO'SHILDI</b> 🎬         ║\n"
            f"╚══════════════════════════╝\n\n"
            f"🔢 <b>Raqam:</b> <code>{raqam}</code>\n"
            f"🎥 <b>Nomi:</b> {movie['nomi']}\n"
            f"📝 <b>Tavsif:</b> {'✅ Qoshildi' if tavsif else 'Yoq'}\n"
            f"📅 <b>Vaqt:</b> {movie['qoshilgan']}\n\n"
            f"📊 Jami kinolar: <b>{len(movies_db)}</b> ta\n\n"
            f"💾 <i>DB nusxasi adminga yuborilmoqda...</i>",
            parse_mode="HTML")

        # Adminga avtomatik DB yuborish
        await send_db_to_admin(context.bot, raqam)
        return

    # ━━━ KINO O'CHIRISH ━━━
    if holat == "kino_ochirish_raqam":
        if text and text.strip().isdigit():
            raqam = text.strip()
            if raqam in movies_db:
                movie = movies_db[raqam]
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_movie_{raqam}"),
                    InlineKeyboardButton("❌ Bekor", callback_data="cancel_delete_movie"),
                ]])
                await message.reply_text(
                    f"🗑️ <b>Tasdiqlang!</b>\n\n"
                    f"🔢 <code>{raqam}</code> — {movie['nomi']}\n"
                    f"📅 {movie['qoshilgan']}\n\n"
                    f"⚠️ Qaytarib bo'lmaydi!",
                    reply_markup=kb, parse_mode="HTML")
                del admin_state[user_id]
            else:
                await message.reply_text(f"❌ <code>{raqam}</code> topilmadi!", parse_mode="HTML")
        else:
            await message.reply_text("❌ Faqat raqam yuboring!", parse_mode="HTML")
        return

    # ━━━ KANAL QO'SHISH ━━━
    if holat == "kanal_qoshish_id":
        try:
            channel_id = int(text.strip())
            try:
                chat = await context.bot.get_chat(channel_id)
                ch_name = chat.title or chat.username or str(channel_id)
                ch_link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(channel_id).replace('-100', '')}"
                required_channels[channel_id] = {"nomi": ch_name, "link": ch_link, "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M")}
                del admin_state[user_id]
                await message.reply_text(
                    f"✅ <b>Kanal qo'shildi!</b>\n\n📛 {ch_name}\n🆔 <code>{channel_id}</code>\n📢 Jami: {len(required_channels)} ta",
                    parse_mode="HTML")
            except TelegramError as e:
                await message.reply_text(f"❌ Xatolik: {e}\n\nBot kanalda admin qilinganmi?", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ To'g'ri ID yuboring! Masalan: <code>-1001234567890</code>", parse_mode="HTML")
        return

    # ━━━ KANAL O'CHIRISH ━━━
    if holat == "kanal_ochirish_id":
        try:
            channel_id = int(text.strip())
            if channel_id in required_channels:
                ch = required_channels[channel_id]
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ O'chir", callback_data=f"confirm_delete_channel_{channel_id}"),
                    InlineKeyboardButton("❌ Bekor", callback_data="cancel_delete_channel"),
                ]])
                await message.reply_text(
                    f"🗑️ <b>Tasdiqlang!</b>\n\n📢 {ch['nomi']}\n🆔 <code>{channel_id}</code>",
                    reply_markup=kb, parse_mode="HTML")
                del admin_state[user_id]
            else:
                await message.reply_text("❌ Bu ID ro'yxatda yo'q!", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ To'g'ri ID yuboring!", parse_mode="HTML")
        return

    # ━━━ OMBOR QO'SHISH ━━━
    if holat == "ombor_qoshish":
        inp = text.strip()
        try:
            if inp.startswith("https://t.me/") or inp.startswith("@"):
                username = inp.replace("https://t.me/", "").replace("@", "").strip().split("/")[0]
                chat_obj = await context.bot.get_chat(f"@{username}")
            else:
                chat_obj = await context.bot.get_chat(int(inp))

            gid = chat_obj.id
            gname = chat_obj.title or chat_obj.username or str(gid)
            glink = f"https://t.me/{chat_obj.username}" if chat_obj.username else f"https://t.me/c/{str(gid).replace('-100','')}"

            storage_groups[gid] = {"nomi": gname, "link": glink, "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M")}
            del admin_state[user_id]

            for admin_id in list(admins_db.keys()):
                try:
                    await context.bot.send_message(admin_id,
                        f"🎉 <b>Yangi Ombor Qo'shildi!</b>\n\n"
                        f"📛 {gname}\n🆔 <code>{gid}</code>\n🔗 {glink}\n\n"
                        f"🏪 Jami ombor: <b>{len(storage_groups)}</b> ta",
                        parse_mode="HTML")
                except Exception:
                    pass

        except TelegramError as e:
            await message.reply_text(f"❌ Guruh topilmadi: {e}\n\nBot admin qilinganmi?", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ Noto'g'ri format! Link yoki ID yuboring.", parse_mode="HTML")
        return

    # ━━━ DB IMPORT ━━━
    if holat == "db_import_kutish":
        if message.document:
            doc = message.document
            if not doc.file_name.endswith(".json"):
                await message.reply_text("❌ Faqat <b>.json</b> fayl!", parse_mode="HTML")
                return
            try:
                file = await context.bot.get_file(doc.file_id)
                file_bytes = await file.download_as_bytearray()
                data = json.loads(file_bytes.decode("utf-8"))
                qoshildi, xato, xatolar = import_database(data)
                xato_text = ""
                if xatolar:
                    xato_text = "\n\n⚠️ Xatolar:\n" + "\n".join(xatolar[:5])
                del admin_state[user_id]
                await message.reply_text(
                    f"✅ <b>Import yakunlandi!</b>\n\n"
                    f"✅ Qo'shildi: <b>{qoshildi}</b> ta\n"
                    f"❌ Xatolik: <b>{xato}</b> ta\n\n"
                    f"📊 Jami bazada: <b>{len(movies_db)}</b> ta{xato_text}",
                    parse_mode="HTML")
            except json.JSONDecodeError:
                await message.reply_text("❌ JSON fayl buzilgan!", parse_mode="HTML")
            except Exception as e:
                await message.reply_text(f"❌ Xatolik: {e}", parse_mode="HTML")
        else:
            await message.reply_text("❌ Fayl yuboring yoki /cancel bosing!", parse_mode="HTML")
        return

    # ━━━ REKLAMA ━━━
    if holat == "reklama_kutish":
        del admin_state[user_id]
        sent = failed = blocked = 0
        await message.reply_text(f"📣 Yuborilmoqda... ({len(users_db)} ta)", parse_mode="HTML")
        for uid in list(users_db.keys()):
            if uid in blocked_users:
                continue
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=message.chat_id, message_id=message.message_id)
                sent += 1
                await asyncio.sleep(0.05)
            except Forbidden:
                blocked += 1
                stats["botni_bloklaganlar"].add(uid)
                users_db[uid]["faol"] = False
            except TelegramError:
                failed += 1
        await message.reply_text(
            f"✅ <b>Yuborildi!</b>\n\n✅ {sent} ta\n🚫 {blocked} ta\n❌ {failed} ta",
            parse_mode="HTML")
        return

    # ━━━ FOYDALANUVCHI BLOKLASH ━━━
    if holat == "bloklash_id":
        try:
            target_id = int(text.strip())
            if target_id == user_id:
                await message.reply_text("❌ O'zingizni bloklashingiz mumkin emas!")
                return
            if target_id == DEVELOPER_ID:
                await message.reply_text("❌ Super-egani bloklashingiz mumkin emas!")
                return
            if is_admin(target_id):
                await message.reply_text("❌ Adminni bloklashingiz mumkin emas!")
                return
            ui = users_db.get(target_id, {"ism": "Noma'lum", "username": "Yo'q"})
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Blokla", callback_data=f"confirm_block_user_{target_id}"),
                InlineKeyboardButton("❌ Bekor", callback_data="cancel_block_user"),
            ]])
            await message.reply_text(
                f"🚫 <b>Bloklashni tasdiqlang!</b>\n\n"
                f"👤 ID: <code>{target_id}</code>\n"
                f"👤 Ism: {ui.get('ism','?')}\n"
                f"📱 Username: {ui.get('username','?')}",
                reply_markup=kb, parse_mode="HTML")
            del admin_state[user_id]
        except ValueError:
            await message.reply_text("❌ To'g'ri ID yuboring!", parse_mode="HTML")
        return

    # ━━━ BLOK OCHISH ━━━
    if holat == "blok_ochish_id":
        try:
            target_id = int(text.strip())
            if target_id in blocked_users:
                del blocked_users[target_id]
                del admin_state[user_id]
                ui = users_db.get(target_id, {"ism": "Noma'lum"})
                await message.reply_text(
                    f"✅ <b>Blok ochildi!</b>\n\n👤 ID: <code>{target_id}</code>\n👤 {ui.get('ism','?')}",
                    parse_mode="HTML")
                try:
                    await context.bot.send_message(target_id,
                        "🎉 <b>Blokilganingiz ochildi!</b>\n\nEndi botdan to'liq foydalana olasiz!\n🎬 Kino raqamini yuboring!",
                        parse_mode="HTML")
                except Exception:
                    pass
            else:
                await message.reply_text(f"❌ <code>{target_id}</code> bloklangan ro'yxatda yo'q!", parse_mode="HTML")
        except ValueError:
            await message.reply_text("❌ To'g'ri ID yuboring!", parse_mode="HTML")
        return

    # ━━━ ADMIN QO'SHISH ━━━
    if holat == "admin_qoshish_id":
        try:
            new_id = int(text.strip())
            if new_id in admins_db:
                await message.reply_text(f"⚠️ <code>{new_id}</code> allaqachon admin!", parse_mode="HTML")
                del admin_state[user_id]
                return
            ai = users_db.get(new_id, {"ism": "Noma'lum"})
            admins_db[new_id] = {"ism": ai.get("ism", "Noma'lum"), "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M")}
            del admin_state[user_id]
            await message.reply_text(
                f"✅ <b>Admin qo'shildi!</b>\n\n🆔 <code>{new_id}</code>\n👤 {ai.get('ism','?')}\n👑 Jami: {len(admins_db)} ta",
                parse_mode="HTML")
            try:
                await context.bot.send_message(new_id,
                    f"👑 <b>Siz admin qilindingiz!</b>\n\n@{BOT_USERNAME} botining admini bo'ldingiz!\n/start bosing.",
                    parse_mode="HTML")
            except Exception:
                pass
        except ValueError:
            await message.reply_text("❌ To'g'ri ID yuboring!", parse_mode="HTML")
        return

    # ━━━ USER XABAR YUBORISH ━━━
    if holat == "user_xabar_yuborish":
        del admin_state[user_id]
        await message.reply_text(SENT_TEXT.format(ism=user.first_name), parse_mode="HTML")

        ui = users_db.get(user_id, {"ism": "Noma'lum", "username": "Yo'q"})
        kimdan = (
            f"💬 <b>Yangi Xabar!</b>\n\n"
            f"╔══════════════════════════╗\n"
            f"║  📨 <b>FOYDALANUVCHI XABARI</b> ║\n"
            f"╚══════════════════════════╝\n\n"
            f"👤 <b>Kimdan:</b> {ui.get('ism','?')}\n"
            f"📱 <b>Username:</b> {ui.get('username','Yoq')}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📅 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Xabar:</b>"
        )
        for admin_id in list(admins_db.keys()):
            try:
                await context.bot.send_message(admin_id, kimdan, parse_mode="HTML")
                await context.bot.copy_message(chat_id=admin_id, from_chat_id=message.chat_id, message_id=message.message_id)
            except Exception:
                pass
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🏗️ KANAL/GURUH ADMIN BO'LGANDA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_chat_member = update.my_chat_member
    if not my_chat_member:
        return

    chat = my_chat_member.chat
    new_status = my_chat_member.new_chat_member.status
    old_status = my_chat_member.old_chat_member.status

    if chat.type not in ["channel", "supergroup", "group"]:
        return

    cid = chat.id
    cname = chat.title or str(cid)
    clink = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(cid).replace('-100','')}"

    if new_status == "administrator" and old_status != "administrator":
        # Kanal → majburiy + ombor
        if chat.type == "channel" and cid not in required_channels:
            required_channels[cid] = {"nomi": cname, "link": clink, "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M")}
        # Har qanday tur → ombor
        if cid not in storage_groups:
            storage_groups[cid] = {"nomi": cname, "link": clink, "qoshilgan": datetime.now().strftime("%d.%m.%Y %H:%M")}

        for admin_id in list(admins_db.keys()):
            try:
                await context.bot.send_message(admin_id,
                    f"🎉 <b>Bot admin qilindi!</b>\n\n📛 {cname}\n🆔 <code>{cid}</code>\n🔗 {clink}\n📋 {chat.type}\n\n"
                    "✅ Majburiy kanalga qo'shildi!\n" * (1 if chat.type == 'channel' else 0) + "✅ Ombor guruhiga qo'shildi!",
                    parse_mode="HTML")
            except Exception:
                pass

    elif new_status in ["member", "left", "kicked", "restricted"] and old_status == "administrator":
        removed = []
        if cid in required_channels:
            del required_channels[cid]
            removed.append("📢 Majburiy kanaldan o'chirildi")
        if cid in storage_groups:
            del storage_groups[cid]
            removed.append("🏪 Ombor guruhidan o'chirildi")
        if removed:
            for admin_id in list(admins_db.keys()):
                try:
                    await context.bot.send_message(admin_id,
                        f"⚠️ <b>Bot adminlikdan olindi!</b>\n\n🆔 <code>{cid}</code>\n\n" + "\n".join(removed),
                        parse_mode="HTML")
                except Exception:
                    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /cancel KOMANDASI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_state:
        del admin_state[user_id]
        await update.message.reply_text("❌ <b>Bekor qilindi!</b>", reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
    else:
        await update.message.reply_text("ℹ️ Bekor qilinadigan narsa yo'q.", reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    logger.warning("🎬 Tomosha Vaqti Bot v4.0 ishga tushmoqda...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (
            filters.TEXT | filters.VIDEO | filters.Document.ALL |
            filters.PHOTO | filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE
        ),
        handle_message
    ))

    from telegram.ext import ChatMemberHandler
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Har soat: DB → ombor + 08:00/20:00 broadcast
    app.job_queue.run_repeating(
        hourly_job,
        interval=3600,
        first=30,
        name="hourly_job"
    )

    logger.warning(f"✅ Bot ishga tushdi! @{BOT_USERNAME}")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "my_chat_member"]
    )

if __name__ == "__main__":
    main()
