#!/usr/bin/env python3
import os
import logging
import time
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    CallbackContext, CallbackQueryHandler
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '5359404414:AAF7frhK0wwEDjT8ggNmeQKWdgqCL6FjDdA')
OWNER_CHAT_ID = os.environ.get('OWNER_CHAT_ID', '907307421')

# Channel links
CHANNELS = [
    {"name": "🔥 CHANNEL 1", "url": "https://t.me/IOS_ANDROID_NPVT"},
    {"name": "🔥 CHANNEL 2", "url": "https://t.me/ACHANNELWITHHELLAPLUGS00"},
    {"name": "🔥 CHANNEL 3", "url": "https://t.me/unlimtedwxrld"},
    {"name": "🔥 CHANNEL 4", "url": "https://t.me/The_Easy_Plugs"},
    {"name": "🔥 PRIVATE CHANNEL ", "url": "https://t.me/+yUFDl0Qu6VE2OGRk"},
]

# Store user conversations and message tracking
user_conversations = {}
pending_messages = {}
MESSAGE_EXPIRY_TIME = 3 * 24 * 60 * 60  # 3 days

class MessageExpiryManager:
    def __init__(self):
        self.running = True
        self.cleanup_interval = 3600
    
    def start_cleanup_thread(self, application):
        def cleanup_loop():
            while self.running:
                try:
                    self.cleanup_expired_messages(application)
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    logging.error(f"Error in cleanup thread: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        logging.info("Message expiry cleanup thread started")
    
    def cleanup_expired_messages(self, application):
        current_time = time.time()
        expired_messages = []
        
        for msg_id, msg_data in list(pending_messages.items()):
            if current_time - msg_data["timestamp"] > MESSAGE_EXPIRY_TIME:
                expired_messages.append((msg_id, msg_data))
        
        for msg_id, msg_data in expired_messages:
            try:
                user_info = user_conversations.get(msg_data["user_id"], {})
                user_display = user_info.get('first_name', 'Unknown User')
                
                expiry_notice = f"⏰ Message from {user_display} has expired (3 days old)."
                
                application.bot.edit_message_text(
                    chat_id=OWNER_CHAT_ID,
                    message_id=msg_data["owner_message_id"],
                    text=expiry_notice
                )
                
                del pending_messages[msg_id]
                
            except Exception as e:
                if msg_id in pending_messages:
                    del pending_messages[msg_id]
        
        if expired_messages:
            logging.info(f"Cleaned up {len(expired_messages)} expired messages")

expiry_manager = MessageExpiryManager()

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📢 Our Channels", callback_data="channels")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"),
         InlineKeyboardButton("🆘 Help", callback_data="help")],
        [InlineKeyboardButton("💬 Contact Owner", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"👋 Welcome {user.first_name}!\n\nI'm an advanced messaging bot."
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🤖 **Bot Help**\n\n"
        "**Features:**\n• Message forwarding\n• 3-day message expiry\n• Privacy protection\n\n"
        "**Commands:**\n/start - Start bot\n/help - Show help\n/channels - Show channels"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def show_channels(update: Update, context: CallbackContext) -> None:
    channels_text = "📢 **Join Our Channels**\n\n"
    for channel in CHANNELS:
        channels_text += f"• {channel['name']}\n"
    
    keyboard = []
    for channel in CHANNELS:
        keyboard.append([InlineKeyboardButton(channel["name"], url=channel["url"])])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(channels_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "channels":
        await show_channels(update, context)
    elif query.data == "help":
        await help_command(update, context)
    elif query.data == "contact":
        await start_contact(update, context)
    elif query.data.startswith('reply_'):
        await handle_owner_reply(update, context)

async def start_contact(update: Update, context: CallbackContext) -> None:
    contact_text = "💬 **Contact Owner**\n\nSend any message, photo, video, etc.\n⏰ Unreplied messages expire after 3 days."
    await update.message.reply_text(contact_text, parse_mode='Markdown')

async def forward_to_owner(update: Update, context: CallbackContext) -> None:
    try:
        user = update.effective_user
        if update.effective_chat.type != "private":
            return
            
        user_identifier = f"User_{hash(user.id) % 10000:04d}"
        user_info = f"👤 From: {user.first_name or 'Unknown'}"
        if user.username:
            user_info += f" (@{user.username})"
        user_info += f"\n🔒 ID: {user_identifier}"
        user_info += f"\n⏰ Expires: {(datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M')}"
        
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("📨 Reply", callback_data=f"reply_{user.id}_{update.message.message_id}"),
            InlineKeyboardButton("👤 Info", callback_data=f"info_{user.id}")
        ]])
        
        user_conversations[user.id] = {
            'first_name': user.first_name,
            'username': user.username,
            'identifier': user_identifier
        }
        
        if update.message.text:
            message_text = f"💬 New Message\n{user_info}\n\n{update.message.text}"
            sent_message = await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=message_text,
                reply_markup=reply_markup
            )
        # Add other media types here as needed...
        
        pending_messages[update.message.message_id] = {
            "user_id": user.id,
            "timestamp": time.time(),
            "owner_message_id": sent_message.message_id
        }
        
        await update.message.reply_text("✅ Your message has been sent to the owner!")
        
    except Exception as e:
        logging.error(f"Error forwarding message: {e}")
        await update.message.reply_text("❌ Sorry, there was an error.")

async def handle_owner_reply(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('reply_'):
        parts = query.data.split('_')
        user_id = int(parts[1])
        original_message_id = int(parts[2])
        
        if original_message_id not in pending_messages:
            await query.answer("❌ This message has expired (3 days old).", show_alert=True)
            return
        
        msg_data = pending_messages[original_message_id]
        current_time = time.time()
        
        if current_time - msg_data["timestamp"] > MESSAGE_EXPIRY_TIME:
            await query.answer("❌ This message has expired.", show_alert=True)
            del pending_messages[original_message_id]
            return
        
        context.user_data['replying_to'] = user_id
        context.user_data['original_message_id'] = original_message_id
        
        user_info = user_conversations.get(user_id, {})
        user_display = user_info.get('first_name', 'Unknown User')
        
        time_remaining = MESSAGE_EXPIRY_TIME - (current_time - msg_data["timestamp"])
        hours_remaining = int(time_remaining / 3600)
        
        await query.edit_message_text(
            text=f"🔄 Replying to {user_display}\n⏰ Time remaining: {hours_remaining}h"
        )

async def forward_reply_to_user(update: Update, context: CallbackContext) -> None:
    if 'replying_to' in context.user_data:
        try:
            user_id = context.user_data['replying_to']
            original_message_id = context.user_data.get('original_message_id')
            
            if original_message_id and original_message_id in pending_messages:
                del pending_messages[original_message_id]
            
            if update.message.text:
                reply_text = f"📩 Reply from Bot Owner:\n\n{update.message.text}"
                await context.bot.send_message(chat_id=user_id, text=reply_text)
            
            del context.user_data['replying_to']
            if 'original_message_id' in context.user_data:
                del context.user_data['original_message_id']
                
            await update.message.reply_text("✅ Reply sent successfully!")
            
        except Exception as e:
            await update.message.reply_text("❌ Error sending reply.")

async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(f"Update {update} caused error {context.error}")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("channels", show_channels))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.add_handler(MessageHandler(
        filters.Chat(OWNER_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
        forward_reply_to_user
    ))
    
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, 
        forward_to_owner
    ))

    application.add_error_handler(error_handler)

    expiry_manager.start_cleanup_thread(application)

    print("🤖 Bot is running on Koyeb...")
    print("⏰ 3-day message expiry: Active")
    application.run_polling()

if __name__ == '__main__':
    main()