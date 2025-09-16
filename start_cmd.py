from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from admin_commands import is_authorized

def register_start_command(bot, channel_username, join_url):
    @bot.message_handler(commands=['start'])
    def start_msg(message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        if not is_authorized(user_id, chat_id):
            markup = InlineKeyboardMarkup()
            join_button = InlineKeyboardButton("Join Free Access Channel", url=join_url)
            markup.add(join_button)
            bot.send_message(
                message.chat.id,
                f"❌ Unauthorized user or please join the channel {channel_username} to use the bot.",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        welcome_text = f"""👋 *Welcome to Auto Shopify Checker!*

I check cards on Shopify sites with proxy support.

You can:
• Send /sh (card details) to check a single card
• Upload a TXT file with combos for batch checking
• Use /msh followed by cards for mass inline checking

Powered by 𝑵𝒂𝒊𝒓𝒐𝒃𝒊𝒂𝒏𝒈𝒐𝒐𝒏 - Reliable & Fast ✅
"""
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("/sh", "/msh", "/help")
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)
