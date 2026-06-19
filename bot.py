import logging
import requests
import os
import sys
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ─── CONFIG ──────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not set!")
    sys.exit(1)
if not API_BASE_URL:
    print("❌ API_BASE_URL not set!")
    sys.exit(1)

# 10 ONE-TIME ACCESS CODES (6 digits)
ACCESS_CODES = {
    "284739": False,
    "561902": False,
    "837461": False,
    "192847": False,
    "645831": False,
    "308275": False,
    "974162": False,
    "453098": False,
    "716254": False,
    "829013": False,
}

VERIFIED_USERS = set()
WAITING_CODE = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── HANDLERS ──────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in VERIFIED_USERS:
        await show_welcome(update)
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔒 *Access Required*\n\n"
        "This bot is private. Please enter your 6-digit access code.",
        parse_mode="Markdown"
    )
    return WAITING_CODE

async def check_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip()
    
    if code in ACCESS_CODES and not ACCESS_CODES[code]:
        ACCESS_CODES[code] = True
        VERIFIED_USERS.add(user_id)
        
        await update.message.reply_text(
            "✅ *Access Granted!*\n\n"
            "Your code has been redeemed successfully.",
            parse_mode="Markdown"
        )
        await show_welcome(update)
        return ConversationHandler.END
    
    elif code in ACCESS_CODES and ACCESS_CODES[code]:
        await update.message.reply_text(
            "❌ This code has already been used.\n"
            "Each code is valid for one user only.",
            parse_mode="Markdown"
        )
        return WAITING_CODE
    
    else:
        await update.message.reply_text(
            "❌ Invalid access code.\n"
            "Please enter a valid 6-digit code.",
            parse_mode="Markdown"
        )
        return WAITING_CODE

async def show_welcome(update: Update):
    welcome = (
        "👋 *Welcome to the Search Bot!*\n\n"
        "Send me a mobile number and I'll search for you.\n"
        "Example: `9999999891`"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def search_api(mobile: str):
    try:
        response = requests.get(
            f"{API_BASE_URL}?mobile={mobile}",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "⏱ API is taking too long. Try again in a moment."}
    except requests.exceptions.ConnectionError:
        return {"error": "🔌 Cannot connect to API. Is the space running?"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"❌ API returned error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"⚠️ Unexpected error: {str(e)}"}

async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in VERIFIED_USERS:
        await update.message.reply_text(
            "🔒 *Access Denied*\n\n"
            "Please use /start to enter your access code first.",
            parse_mode="Markdown"
        )
        return

    mobile = update.message.text.strip()
    
    if not mobile.isdigit() or len(mobile) != 10:
        await update.message.reply_text(
            "❌ Please send a valid 10-digit mobile number.\nExample: `9999999891`",
            parse_mode="Markdown"
        )
        return

    wait_msg = await update.message.reply_text(
        "🔍 *Searching...*\nPlease wait while I fetch the data.",
        parse_mode="Markdown"
    )
    
    result = await search_api(mobile)
    await wait_msg.delete()
    
    if "error" in result:
        await update.message.reply_text(result["error"])
        return
    
    formatted = format_response(result, mobile)
    await update.message.reply_text(formatted, parse_mode="Markdown", disable_web_page_preview=True)

def format_response(data: dict, mobile: str) -> str:
    text = f"📱 *Search Results for:* `{mobile}`\n\n"
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                text += f"\n🔹 *{key.title()}:*\n"
                for k, v in value.items():
                    text += f"  • {k}: `{v}`\n"
            elif isinstance(value, list):
                text += f"\n🔹 *{key.title()}:*\n"
                for item in value:
                    text += f"  • `{item}`\n"
            else:
                text += f"🔹 *{key.title()}:* `{value}`\n"
    else:
        text += f"```\n{str(data)}\n```"
    
    return text

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("😕 Something went wrong. Please try again.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Use /start to try again.")
    return ConversationHandler.END

# ─── MAIN ──────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mobile))
    app.add_error_handler(error_handler)
    
    print("🤖 Bot is running...")
    
    while True:
        try:
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
