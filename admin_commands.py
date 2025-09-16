import json

AUTH_FILE = "authorized.json"

def load_auth():
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": [], "groups": [], "admins": []}

def save_auth(data):
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(user_id):
    data = load_auth()
    return user_id in data.get("admins", [])

def is_authorized(user_id, chat_id):
    data = load_auth()
    return (user_id in data.get("users", [])) or (chat_id in data.get("groups", []))

def register_admin_commands(bot):

    @bot.message_handler(commands=['add'])
    def add_handler(message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "❌ Only admins can add authorized users or groups.")
            return
        try:
            _, entity = message.text.split(maxsplit=1)
            entity = entity.strip()
            data = load_auth()

            try:
                e_id = int(entity)
            except:
                bot.reply_to(message, "❌ Please provide a valid numerical Telegram user or group ID.")
                return

            if e_id < 0:
                if e_id not in data['groups']:
                    data['groups'].append(e_id)
                    save_auth(data)
                    bot.reply_to(message, f"✅ Group ID {e_id} authorized.")
                else:
                    bot.reply_to(message, f"ℹ️ Group ID {e_id} is already authorized.")
            else:
                if e_id not in data['users']:
                    data['users'].append(e_id)
                    save_auth(data)
                    bot.reply_to(message, f"✅ User ID {e_id} authorized.")
                else:
                    bot.reply_to(message, f"ℹ️ User ID {e_id} is already authorized.")
        except Exception:
            bot.reply_to(message, "Usage:\n/add <user_id> or /add <group_id>")

    @bot.message_handler(commands=['remove'])
    def remove_handler(message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "❌ Only admins can remove authorized users or groups.")
            return
        try:
            _, entity = message.text.split(maxsplit=1)
            entity = entity.strip()
            data = load_auth()

            try:
                e_id = int(entity)
            except:
                bot.reply_to(message, "❌ Please provide a valid numerical Telegram user or group ID.")
                return

            if e_id in data.get('users', []):
                data['users'].remove(e_id)
                save_auth(data)
                bot.reply_to(message, f"✅ User ID {e_id} removed from authorized users.")
            elif e_id in data.get('groups', []):
                data['groups'].remove(e_id)
                save_auth(data)
                bot.reply_to(message, f"✅ Group ID {e_id} removed from authorized groups.")
            else:
                bot.reply_to(message, "ℹ️ ID not found in authorized lists.")
        except Exception:
            bot.reply_to(message, "Usage:\n/remove <user_id> or /remove <group_id>")
