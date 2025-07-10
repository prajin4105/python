import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue,
)
import asyncio

# 🔐 Telegram Bot Token
TOKEN = ""  # replace with actual bot token
API_URL = "https://gagstock.gleeze.com/grow-a-garden"

# 🛠️ Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 📦 Fetch stock data
async def fetch_stock():
    try:
        response = requests.get(API_URL)
        data = response.json()

        if data["status"] != "success":
            return "❌ API returned error status."

        stock = data["data"]
        message = "🌱 *Grow A Garden - Live Stock*\n\n"

        for category_name, category_data in stock.items():
            if category_name in ["updated_at", "items"]:
                continue

            items = category_data.get("items", [])
            countdown = category_data.get("countdown")
            appear_in = category_data.get("appearIn")

            if not isinstance(items, list):
                continue

            message += f"📦 *{category_name.title()}*"
            if countdown:
                message += f" ⏳ {countdown}"
            elif appear_in:
                message += f" ⏱️ Appears in {appear_in}"
            message += "\n"

            if items:
                for item in items:
                    emoji = item.get("emoji", "")
                    name = item.get("name", "Unknown")
                    qty = item.get("quantity", 0)
                    message += f"  • {emoji} {name} × {qty}\n"
            else:
                message += "  • (empty)\n"

            message += "\n"

        return message.strip()

    except Exception as e:
        logging.error("❌ Unexpected error: %s", e)
        return "❌ Failed to fetch or parse data."


# 🔁 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await fetch_stock()
    await update.message.reply_text(msg, parse_mode="Markdown")

    # Schedule auto updates for this chat
    chat_id = update.effective_chat.id
    job_removed = remove_existing_job(str(chat_id), context)
    context.job_queue.run_repeating(
        send_stock_auto,
        interval=300,  # every 5 mins
        first=0,
        chat_id=chat_id,
        name=str(chat_id)
    )
    if job_removed:
        await update.message.reply_text("🔁 Auto-updates restarted.")
    else:
        await update.message.reply_text("✅ Auto-updates started every 5 minutes.")


# ♻️ Remove existing job
def remove_existing_job(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


# 🕒 Scheduled job to send stock
async def send_stock_auto(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    msg = await fetch_stock()
    await context.bot.send_message(chat_id=job.chat_id, text=msg, parse_mode="Markdown")


# 🚀 Start bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # No need for async or post_init setup
    app.run_polling()


if __name__ == "__main__":
    main()
