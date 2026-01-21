"""
TELEGRAM SIGNAL FORWARDER - OPTIMIZED FOR RENDER.COM
Handles verification codes properly - NOT in .env file
"""

import os
import asyncio
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID', ''))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
SOURCE_GROUP_URL = os.getenv('SOURCE_GROUP_URL', 'https://t.me/iosassembly')
TARGET_GROUP_URL = os.getenv('TARGET_GROUP_URL', 'https://t.me/acctdeveloperselling')
SOURCE_USERNAME = os.getenv('SOURCE_USERNAME', '@Systembadgetickverify02')
SIGNAL_HEADER = os.getenv('SIGNAL_HEADER', '🔔 NEW SIGNAL!')
ADD_TIMESTAMP = os.getenv('ADD_TIMESTAMP', 'true').lower() == 'true'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class TelegramSignalForwarder:
    def __init__(self):
        self.client = None
        self.source_group = None
        self.target_group = None
        self.source_user = None
        
    def extract_username(self, url):
        """Extract username from Telegram URL."""
        if not url:
            return ""
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        if url.startswith('t.me/'):
            url = url[5:]
        elif url.startswith('@'):
            url = url[1:]
        return url.split('?')[0].rstrip('/')
    
    async def initialize(self):
        """Initialize Telegram client with proper verification handling."""
        logger.info("🚀 INITIALIZING SIGNAL FORWARDER")
        logger.info("=" * 60)
        
        try:
            # Create client
            self.client = TelegramClient(
                'render_session',
                API_ID,
                API_HASH,
                device_model="Signal Forwarder",
                system_version="Render Cloud",
                app_version="3.0.0"
            )
            
            await self.client.connect()
            
            # Check if already logged in
            if await self.client.is_user_authorized():
                logger.info("✅ Using existing session (already logged in)")
            else:
                # FIRST-TIME SETUP - Phone verification required
                logger.info("🔐 FIRST-TIME SETUP DETECTED")
                logger.info("📱 Sending verification code request...")
                
                # Send code request
                await self.client.send_code_request(PHONE_NUMBER)
                
                # Get code from RENDER ENVIRONMENT (NOT .env file)
                verification_code = os.getenv('TELEGRAM_CODE')
                
                if verification_code:
                    # Clean and validate code
                    code = str(verification_code).strip()
                    code = code.replace('-', '').replace(' ', '')
                    
                    if len(code) >= 5:
                        logger.info(f"🔑 Using verification code: {code}")
                        logger.info("⏳ Signing in...")
                        
                        try:
                            await self.client.sign_in(PHONE_NUMBER, code)
                            logger.info("✅ Successfully logged in!")
                        except SessionPasswordNeededError:
                            # Handle 2FA password if needed
                            password = os.getenv('TELEGRAM_PASSWORD')
                            if password:
                                await self.client.sign_in(password=password)
                                logger.info("✅ Logged in with 2FA password")
                            else:
                                logger.error("❌ 2FA password required but not provided")
                                logger.info("💡 Add TELEGRAM_PASSWORD environment variable")
                                return False
                        except Exception as e:
                            logger.error(f"❌ Login failed: {e}")
                            logger.info("💡 The verification code might be:")
                            logger.info("   - Expired (get a new one from Telegram)")
                            logger.info("   - Already used")
                            logger.info("   - Incorrect")
                            logger.info("💡 Solution:")
                            logger.info("   1. Get NEW code from Telegram")
                            logger.info("   2. Update TELEGRAM_CODE in Render Environment")
                            logger.info("   3. Service will auto-restart")
                            return False
                    else:
                        logger.error(f"❌ Invalid code length: {len(code)} (minimum 5)")
                        return False
                else:
                    # No code provided - show instructions
                    logger.info("=" * 60)
                    logger.info("📱 PHONE VERIFICATION REQUIRED")
                    logger.info("=" * 60)
                    logger.info("INSTRUCTIONS:")
                    logger.info("1. Check Telegram app for verification code (5-6 digits)")
                    logger.info("2. Go to Render.com dashboard")
                    logger.info("3. Find 'telegram-signal-forwarder' service")
                    logger.info("4. Click 'Environment' tab")
                    logger.info("5. Add NEW environment variable:")
                    logger.info("   - Name: TELEGRAM_CODE")
                    logger.info("   - Value: [code from Telegram]")
                    logger.info("   Example: If Telegram shows '123-456', enter '123456'")
                    logger.info("6. Click 'Save Changes'")
                    logger.info("7. Wait 30 seconds for auto-restart")
                    logger.info("=" * 60)
                    
                    # Wait for user to add code (Render will restart)
                    logger.info("⏳ Waiting for verification code...")
                    for i in range(180):  # Wait 3 minutes
                        await asyncio.sleep(1)
                        if os.getenv('TELEGRAM_CODE'):
                            logger.info("✅ Code detected! Service will restart automatically.")
                            break
                        if i % 30 == 0:
                            logger.info(f"⏱️ Still waiting... ({i+1}/180 seconds)")
                    
                    return False  # Will restart with new code
            
            # Get user info
            me = await self.client.get_me()
            logger.info(f"👤 Logged in as: {me.first_name}")
            
            # Get groups
            source_id = self.extract_username(SOURCE_GROUP_URL)
            target_id = self.extract_username(TARGET_GROUP_URL)
            
            self.source_group = await self.client.get_entity(source_id)
            self.target_group = await self.client.get_entity(target_id)
            
            logger.info(f"✅ Source group: {self.source_group.title}")
            logger.info(f"✅ Target group: {self.target_group.title}")
            
            # Get specific user if configured
            if SOURCE_USERNAME:
                try:
                    self.source_user = await self.client.get_entity(SOURCE_USERNAME)
                    logger.info(f"✅ Monitoring user: @{self.source_user.username}")
                except:
                    logger.info("⚠️ Could not find specific user, will forward from any user")
            
            logger.info("=" * 60)
            logger.info("✅ INITIALIZATION COMPLETE!")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def forward_signal(self, event):
        """Forward signal messages."""
        try:
            # Check if from specific user
            if self.source_user:
                sender = await event.get_sender()
                if sender.id != self.source_user.id:
                    return
            
            message_text = event.message.text or ""
            
            # Check for signal header
            if SIGNAL_HEADER in message_text:
                logger.info("🎯 Signal detected! Forwarding...")
                
                # Format message
                if ADD_TIMESTAMP:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                    formatted = f"📡 **Signal Forwarded**\n🕒 {timestamp}\n\n{message_text}"
                else:
                    formatted = message_text
                
                # Forward
                await self.client.send_message(self.target_group, formatted)
                logger.info(f"✅ Forwarded to {self.target_group.title}")
                
        except Exception as e:
            logger.error(f"❌ Error forwarding: {e}")
    
    async def start(self):
        """Start the forwarder."""
        logger.info("🤖 TELEGRAM SIGNAL FORWARDER")
        logger.info("=" * 60)
        
        # Initialize
        if not await self.initialize():
            logger.error("❌ Initialization failed")
            return
        
        # Setup handler
        @self.client.on(events.NewMessage(chats=self.source_group))
        async def handler(event):
            await self.forward_signal(event)
        
        # Send startup message
        startup_msg = (
            f"✅ **Signal Forwarder Started**\n\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"🎯 Monitoring: {self.source_group.title}\n"
            f"📨 Forwarding to: {self.target_group.title}\n"
            f"🔔 Looking for: '{SIGNAL_HEADER}'"
        )
        
        await self.client.send_message(self.target_group, startup_msg)
        
        logger.info("📡 LISTENING FOR SIGNALS...")
        logger.info("=" * 60)
        
        # Keep running
        await self.client.run_until_disconnected()

async def main():
    forwarder = TelegramSignalForwarder()
    await forwarder.start()

if __name__ == "__main__":
    asyncio.run(main())
