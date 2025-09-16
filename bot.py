import os
import json
import html
import time
import asyncio
import traceback
from threading import Thread
from flask import Flask, jsonify
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import telebot

from gate import check_card, lookup_bin
from admin_commands import register_admin_commands, is_authorized, load_auth
import batch_processor
from start_cmd import register_start_command

with open('config.json') as f:
    config = json.load(f)

BOT_TOKEN = config['BOT_TOKEN']
PROXY = config['PROXY']
DEFAULT_SITE = config['DEFAULT_SITE']
AUTHORIZED_GROUPS = set(config.get('AUTHORIZED_GROUPS', []))

bot = telebot.TeleBot(BOT_TOKEN)
CHANNEL_USERNAME = "@privatecoree"
CHANNEL_JOIN_URL = "https://t.me/privatecoree"  # Adjust as needed

def check_authorization(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    data = load_auth()
    authorized_groups = set(data.get("groups", [])) | AUTHORIZED_GROUPS
    is_auth = (user_id in data.get("users", [])) or (chat_id in authorized_groups)
    if not is_auth:
        bot.reply_to(message, "❌ Unauthorized user or not in authorized group.")
    return is_auth

def load_default_sites():
    sites = []
    try:
        with open("SITES.txt", "r") as f:
            for line in f:
                s = line.strip()
                if s:
                    sites.append(s)
    except:
        pass
    return sites if sites else [DEFAULT_SITE]

async def forward_resp(fullcc, gateway_label, response):
    print(f"[FORWARD] {gateway_label} | {fullcc} | {response}")

async def refundcredit(user_id):
    print(f"[REFUND] Credit refunded for user ID {user_id}")

async def get_charge_resp(result, user_id, fullcc):
    try:
        try:
            res_json = json.loads(result) if result.strip().startswith("{") else None
            resp_text = res_json.get("Response", "") if res_json else result
            price = res_json.get("Price", "") if res_json else ""
        except Exception:
            resp_text = result
            price = ""

        sanitized_resp = resp_text.replace('<br>', '\n').replace('<br />', '\n').replace('<br/>', '\n')
        sanitized_resp = html.unescape(sanitized_resp)

        upper_resp = sanitized_resp.upper()

        special_approved_tokens = ["3D CC", "INVALID_CVC", "INSUFFICIENT_FUNDS", "INCORRECT_CVC"]
        generic_approved_tokens = [
            "THANK YOU", "THANKYOU", "THANK YOU FOR YOUR PURCHASE", "ORDER IS CONFIRMED", "SUCCESS"
        ]
        if any(token in upper_resp for token in special_approved_tokens):
            status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
            response = sanitized_resp
            hits = "YES"
            await forward_resp(fullcc, "Auto Shopify 💎", response)
        elif any(token in upper_resp for token in generic_approved_tokens):
            status = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
            response = f"Thank You For Your donation of ${price}" if price else "Thank You"
            hits = "YES"
            await forward_resp(fullcc, "Auto Shopify 💎", response)
        elif "PROXYERROR" in upper_resp:
            status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
            response = "Proxy Connection Refused"
            hits = "NO"
            await refundcredit(user_id)
        else:
            status = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌"
            response = sanitized_resp if sanitized_resp else "Card was declined"
            hits = "NO"
        return {"status": status, "response": response, "hits": hits, "price": price, "fullz": fullcc}
    except Exception as e:
        traceback.print_exc()
        return {"status": "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌", "response": f"{str(e)} ❌", "hits": "NO", "price": "", "fullz": fullcc}

def build_card_message(card, status, status_str, gateway, bin_info, time_taken, proxy_status, price):
    owner_link = '<a href="tg://user?id=6622603977">𝑵𝒂𝒊𝒓𝒐𝒃𝒊𝒂𝒏𝒈𝒐𝒐𝒏</a>'
    return f"""{status}
━━━━━━━━━━━━━
[ϟ] 𝗖𝗖 - <code>{html.escape(card)}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀 : {html.escape(status_str)}
[ϟ] 𝗚𝗮𝘁𝗲 - {gateway}
[ϟ] Price - {price}$
━━━━━━━━━━━━━
[ϟ] B𝗶𝗻 : {bin_info.get("bin", "N/A")}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 : {bin_info.get("country_name", "Unknown")} {bin_info.get("country_flag", "")}
[ϟ] 𝗜𝘀𝘀𝘂𝗿 : {bin_info.get("bank", "Unknown")}
[ϟ] 𝗧𝘆𝗽𝗲 : {bin_info.get("brand", "Unknown")} | {bin_info.get("type", "Unknown")}
━━━━━━━━━━━━━
[ϟ] T/t : {time_taken}s | Proxy : {proxy_status}
[ϟ] 𝗢𝘄𝗻𝗲𝗿: {owner_link}
╚━━━━━━「𝐀𝐏𝐏𝐑𝐎𝐕𝐄𝐃 𝐂𝐇𝐄𝐂𝐊𝐄𝐑」━━━━━━╝
"""

def pin_message(chat_id, message_id):
    try:
        bot.pin_chat_message(chat_id, message_id, disable_notification=False)
    except Exception as e:
        print(f"Failed to pin message: {e}")

# Register start command with join button URL
register_start_command(bot, CHANNEL_USERNAME, CHANNEL_JOIN_URL)

@bot.message_handler(commands=['help'])
def help_msg(message):
    if not check_authorization(message):
        return
    help_text = """📚 *Help - Auto Shopify Checker*

Commands:
/start - Welcome message
/sh <card> - Check a single credit card
/msh <cards> - Mass check cards line by line
Upload a TXT file - Batch check cards from file

Usage:
/sh 4111111111111111|12|24|123
/msh
4111111111111111|12|24|123
5500000000000004|11|23|321

Contact support if needed.
"""
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['sh'])
def single_check(message):
    if not check_authorization(message):
        return
    try:
        card = message.text.split(None, 1)[1].strip()
    except IndexError:
        bot.reply_to(message, "Usage:\n/sh <card>")
        return

    cooking_msg = bot.send_message(message.chat.id, "Your order is cooking 🍳")

    user_site = DEFAULT_SITE
    start_time = time.time()
    raw_resp = check_card(card, user_site, PROXY)
    elapsed = round(time.time() - start_time, 2)

    async def send_single():
        charge_resp = await get_charge_resp(raw_resp, message.from_user.id, card)
        bin_info = lookup_bin(card.split("|")[0])
        msg = build_card_message(
            card,
            charge_resp['status'],
            charge_resp['response'],
            "Auto Shopify 💎",
            bin_info,
            elapsed,
            "Live ✨",
            charge_resp.get("price", "0")
        )
        try:
            sent_msg = bot.edit_message_text(msg, message.chat.id, cooking_msg.message_id, parse_mode="HTML", disable_web_page_preview=True)
            if charge_resp['status'] == "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" and message.chat.type in ['group', 'supergroup']:
                pin_message(message.chat.id, sent_msg.message_id)
        except Exception as e:
            print(f"Edit message failed: {e}")

    asyncio.run(send_single())

@bot.message_handler(commands=['msh'])
def mass_check_command(message):
    if not check_authorization(message):
        return
    try:
        card_lines_text = message.text.split(None, 1)[1]
        lines = [line.strip() for line in card_lines_text.split('\n') if line.strip()]
    except IndexError:
        bot.reply_to(message, "Usage:\n/msh <card1>\n<card2>\n... Send cards line by line after the command.")
        return

    valid_lines, invalid_count = batch_processor.validate_card_lines(lines)
    if invalid_count > 0:
        asyncio.run(batch_processor.send_cleaning_warning(bot, message, invalid_count))
        return
    if not valid_lines:
        bot.reply_to(message, "No valid card lines found.")
        return

    bot.reply_to(message, f"Received {len(valid_lines)} valid cards, starting mass checking...")

    approved_cards = []
    declined_cards = []
    error_cards = []

    async def process_and_handle_buttons():
        last_sent = None
        sites = load_default_sites()
        sites_count = len(sites)

        for idx, card_line in enumerate(valid_lines):
            site = sites[idx % sites_count]
            start_time = time.time()
            raw_resp = check_card(card_line, site, PROXY)
            elapsed = round(time.time() - start_time, 2)

            charge_resp = await get_charge_resp(raw_resp, message.from_user.id, card_line)
            bin_info = lookup_bin(card_line.split("|")[0])

            record = f"{card_line} | Response: {charge_resp['response']}"

            if charge_resp['status'] == "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                approved_cards.append(record)
            elif charge_resp['status'] == "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌":
                declined_cards.append(record)
            else:
                error_cards.append(record)

            msg = build_card_message(
                card_line,
                charge_resp['status'],
                charge_resp['response'],
                "Auto Shopify 💎",
                bin_info,
                elapsed,
                "Live ✨",
                charge_resp.get("price", "0")
            )
            sent_msg = bot.send_message(message.chat.id, msg, parse_mode="HTML", disable_web_page_preview=True)

            if charge_resp['status'] == "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" and message.chat.type in ['group', 'supergroup']:
                pin_message(message.chat.id, sent_msg.message_id)

            if last_sent and last_sent.status != "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                await asyncio.sleep(3)
                try:
                    bot.delete_message(message.chat.id, last_sent.message_id)
                except Exception:
                    pass

            sent_msg.status = charge_resp['status']
            last_sent = sent_msg

        if last_sent:
            await asyncio.sleep(6)
            try:
                if last_sent.status != "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                    bot.delete_message(message.chat.id, last_sent.message_id)
            except Exception:
                pass

        bot.send_message(message.chat.id, "Your Cards Are ready 🍾")

        keyboard = batch_processor.build_summary_buttons(
            len(approved_cards), len(declined_cards), len(error_cards), message.message_id
        )
        bot.send_message(message.chat.id, f"Mass checking complete for {len(valid_lines)} cards.\nSelect a button below to view detailed results.", reply_markup=keyboard)

        base_path = f"temp_files/cardlist_{message.message_id}"
        os.makedirs(base_path, exist_ok=True)

        with open(f"{base_path}/approved.txt", "w", encoding="utf-8") as f_approved:
            f_approved.write(" || ".join(approved_cards) if approved_cards else "No approved cards.")
        with open(f"{base_path}/declined.txt", "w", encoding="utf-8") as f_declined:
            f_declined.write(" || ".join(declined_cards) if declined_cards else "No declined cards.")
        with open(f"{base_path}/error.txt", "w", encoding="utf-8") as f_error:
            f_error.write(" || ".join(error_cards) if error_cards else "No error cards.")

    asyncio.run(process_and_handle_buttons())

@bot.message_handler(content_types=['document'])
def handle_file(message):
    if not check_authorization(message):
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    os.makedirs("temp_files", exist_ok=True)
    path = os.path.join("temp_files", message.document.file_name)
    with open(path, "wb") as f:
        f.write(downloaded)

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    valid_lines, invalid_count = batch_processor.validate_card_lines(lines)

    if invalid_count > 0:
        asyncio.run(batch_processor.send_cleaning_warning(bot, message, invalid_count))
        return

    bot.reply_to(message, f"File received, {len(valid_lines)} valid cards detected, starting batch checking...")

    approved_cards = []
    declined_cards = []
    error_cards = []

    async def process_and_handle_buttons():
        last_sent = None
        sites = load_default_sites()
        sites_count = len(sites)
        for idx, card_line in enumerate(valid_lines):
            site = sites[idx % sites_count]
            start_time = time.time()
            raw_resp = check_card(card_line, site, PROXY)
            elapsed = round(time.time() - start_time, 2)

            charge_resp = await get_charge_resp(raw_resp, message.from_user.id, card_line)
            bin_info = lookup_bin(card_line.split("|")[0])

            record = f"{card_line} | Response: {charge_resp['response']}"

            if charge_resp['status'] == "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                approved_cards.append(record)
            elif charge_resp['status'] == "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌":
                declined_cards.append(record)
            else:
                error_cards.append(record)

            msg = build_card_message(
                card_line,
                charge_resp['status'],
                charge_resp['response'],
                "Auto Shopify 💎",
                bin_info,
                elapsed,
                "Live ✨",
                charge_resp.get("price", "0")
            )
            sent_msg = bot.send_message(message.chat.id, msg, parse_mode="HTML", disable_web_page_preview=True)

            if charge_resp['status'] == "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" and message.chat.type in ['group', 'supergroup']:
                pin_message(message.chat.id, sent_msg.message_id)

            if last_sent and last_sent.status != "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                await asyncio.sleep(3)
                try:
                    bot.delete_message(message.chat.id, last_sent.message_id)
                except Exception:
                    pass

            sent_msg.status = charge_resp['status']
            last_sent = sent_msg

        if last_sent:
            await asyncio.sleep(6)
            try:
                if last_sent.status != "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅":
                    bot.delete_message(message.chat.id, last_sent.message_id)
            except Exception:
                pass

        bot.send_message(message.chat.id, "Your Cards Are ready 🍾")

        keyboard = batch_processor.build_summary_buttons(
            len(approved_cards), len(declined_cards), len(error_cards), message.message_id
        )
        bot.send_message(message.chat.id, f"Batch processing complete for {len(valid_lines)} cards.\nSelect a button below to view detailed results.", reply_markup=keyboard)

        base_path = f"temp_files/cardlist_{message.message_id}"
        os.makedirs(base_path, exist_ok=True)

        with open(f"{base_path}/approved.txt", "w", encoding="utf-8") as f_approved:
            f_approved.write(" || ".join(approved_cards) if approved_cards else "No approved cards.")
        with open(f"{base_path}/declined.txt", "w", encoding="utf-8") as f_declined:
            f_declined.write(" || ".join(declined_cards) if declined_cards else "No declined cards.")
        with open(f"{base_path}/error.txt", "w", encoding="utf-8") as f_error:
            f_error.write(" || ".join(error_cards) if error_cards else "No error cards.")

    asyncio.run(process_and_handle_buttons())

@bot.callback_query_handler(func=lambda call: call.data.startswith("cardlist_"))
def callback_cardlist(call):
    parts = call.data.split('_')
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "Invalid callback data.")
        return

    msg_id = parts[1]
    list_type = parts[2]
    base_path = os.path.join("temp_files", f"cardlist_{msg_id}")
    file_map = {
        "approved": "approved.txt",
        "declined": "declined.txt",
        "error": "error.txt"
    }

    filename = file_map.get(list_type)
    if not filename:
        bot.answer_callback_query(call.id, "Unknown list type.")
        return

    filepath = os.path.join(base_path, filename)
    if not os.path.exists(filepath):
        bot.answer_callback_query(call.id, "No data file found.")
        return

    with open(filepath, "rb") as file:
        bot.answer_callback_query(call.id, f"Sending {list_type} cards...")
        bot.send_document(call.message.chat.id, file, caption=f"{list_type.capitalize()} cards from batch #{msg_id}")

register_admin_commands(bot)

app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>Telegram Shopify Bot is running</h2>"

@app.route("/status")
def status():
    data = load_auth()
    return jsonify({
        "status": "running",
        "authorized_users": data.get("users", []),
        "authorized_groups": list(AUTHORIZED_GROUPS | set(data.get("groups", []))),
        "admins": data.get("admins", [])
    })

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.infinity_polling()
