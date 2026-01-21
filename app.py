import os
import asyncio
import logging
import sys
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting Telegram Signal Forwarder")
    
    # Get credentials
    API_ID = int(os.getenv('API_ID', 0))
    API_HASH = os.getenv('API_HASH', '')
    SESSION_STRING = os.getenv('TELETHON_SESSION', '')
    
    # Get group URLs
    SOURCE_GROUP = os.getenv('SOURCE_GROUP_URL', 'https://t.me/iosassembly')
    TARGET_GROUP = os.getenv('TARGET_GROUP_URL', 'https://t.me/acctdeveloperselling')
    SOURCE_USER = os.getenv('SOURCE_USERNAME', '@Systembadgetickverify02')
    
    # Validate
    if not all([API_ID, API_HASH, SESSION_STRING]):
        logger.error("❌ Missing API_ID, API_HASH, or TELETHON_SESSION")
        return
    
    logger.info("✅ Config loaded")
    
    try:
        # Create client with session string (NO PHONE VERIFICATION)
        client = TelegramClient(
            session=StringSession(SESSION_STRING),
            api_id=API_ID,
            api_hash=API_HASH
        )
        
        # Connect
        await client.connect()
        logger.info("✅ Connected to Telegram")
        
        # Check if session is valid
        if not await client.is_user_authorized():
            logger.error("❌ Session string is invalid or expired")
            logger.info("💡 Run get_session.py on your computer to get new session")
            return
        
        # Get user info
        me = await client.get_me()
        logger.info(f"✅ Logged in as: {me.first_name}")
        
        # Get groups
        def get_username(url):
            return url.split('t.me/')[-1].replace('@', '').strip('/')
        
        source = await client.get_entity(get_username(SOURCE_GROUP))
        target = await client.get_entity(get_username(TARGET_GROUP))
        
        logger.info(f"✅ Source: {source.title}")
        logger.info(f"✅ Target: {target.title}")
        
        # Get specific user if configured
        source_user = None
        if SOURCE_USER:
            try:
                source_user = await client.get_entity(SOURCE_USER)
                logger.info(f"✅ Monitoring user: @{source_user.username}")
            except:
                logger.info("⚠️ Will forward from any user")
        
        # Message handler
        @client.on(events.NewMessage(chats=source))
        async def handler(event):
            try:
                # Check specific user
                if source_user:
                    sender = await event.get_sender()
                    if sender.id != source_user.id:
                        return
                
                # Check for signal
                text = event.message.text or ''
                if '🔔 NEW SIGNAL!' in text:
                    logger.info("🎯 Signal found! Forwarding...")
                    
                    # Add timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    formatted = f"📡 Signal Forwarded\n🕒 {timestamp}\n\n{text}"
                    
                    # Forward
                    await client.send_message(target, formatted)
                    logger.info(f"✅ Forwarded to {target.title}")
                    
            except Exception as e:
                logger.error(f"Error: {e}")
        
        logger.info("📡 Listening for signals...")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
