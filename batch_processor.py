import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def clean_line(line):
    parts = line.strip().split('|')
    return len(parts) >= 4 and all(parts)

def validate_card_lines(lines):
    valid_lines = [line for line in lines if clean_line(line)]
    invalid_count = len(lines) - len(valid_lines)
    return valid_lines, invalid_count

def build_summary_buttons(approved, declined, error, message_id):
    keyboard = InlineKeyboardMarkup(row_width=3)
    base_call = f"cardlist_{message_id}"

    def button_text(label, count):
        return f"{label} ({count})"

    keyboard.add(
        InlineKeyboardButton(button_text("✅ Approved", approved), callback_data=f"{base_call}_approved"),
        InlineKeyboardButton(button_text("❌ Declined", declined), callback_data=f"{base_call}_declined"),
        InlineKeyboardButton(button_text("⚠️ Error", error), callback_data=f"{base_call}_error"),
    )
    return keyboard

async def send_cleaning_warning(bot, message, invalid_count):
    await bot.send_message(
        message.chat.id,
        f"⚠️ The uploaded file contains {invalid_count} incorrectly formatted lines.\n"
        "Please clean your file and use the format:\n"
        "`card|month|year|cvv` for each line.",
        parse_mode="Markdown"
    )
