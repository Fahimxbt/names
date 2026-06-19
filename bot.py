import logging
import requests
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ─── CONFIG ──────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN environment variable not set!")
    sys.exit(1)

if not API_BASE_URL:
    print("❌ API_BASE_URL environment variable not set!")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── HANDLERS ──────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mobile))
    application.add_error_handler(error_handler)
    
    print("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
