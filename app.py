import os
import asyncio
import logging
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Message, User, Channel

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
SOURCE_GROUP_URL = os.getenv('SOURCE_GROUP_URL', '')
TARGET_GROUP_URL = os.getenv('TARGET_GROUP_URL', '')

# Signal configuration
SOURCE_USERNAME = os.getenv('SOURCE_USERNAME', '').strip()
SOURCE_USER_ID = int(os.getenv('SOURCE_USER_ID', 0))
SIGNAL_HEADER = os.getenv('SIGNAL_HEADER', '🔔 NEW SIGNAL!')
ADD_TIMESTAMP = os.getenv('ADD_TIMESTAMP', 'true').lower() == 'true'
SEND_CONFIRMATION = os.getenv('SEND_CONFIRMATION', 'true').lower() == 'true'
FORWARD_DELAY = int(os.getenv('FORWARD_DELAY', 0))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SignalForwarder:
    def __init__(self):
        self.client = None
        self.source_group = None
        self.target_group = None
        self.source_user = None
        self.is_running = False
        
    def extract_username(self, url):
        """Extract username from Telegram URL."""
        if not url:
            return ""
        
        # Remove protocol
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        
        # Remove domain and get username
        if url.startswith('t.me/'):
            url = url[5:]
        elif url.startswith('@'):
            url = url[1:]
        
        # Remove query params and trailing slash
        url = url.split('?')[0].rstrip('/')
        
        return url
    
    async def initialize(self):
        """Initialize Telegram client and get groups/user."""
        logger.info("🚀 Initializing Signal Forwarder...")
        
        try:
            # Create Telegram client
            self.client = TelegramClient(
                'signal_forwarder_session',
                API_ID,
                API_HASH,
                device_model="Signal Forwarder",
                system_version="Render Cloud",
                app_version="2.0.0",
                connection_retries=5,
                auto_reconnect=True
            )
            
            # Connect to Telegram
            await self.client.connect()
            
            # Check if already authorized
            if not await self.client.is_user_authorized():
                logger.info("🔐 First time setup - phone verification required")
                await self.client.send_code_request(PHONE_NUMBER)
                
                # Get verification code from environment
                code = os.getenv('TELEGRAM_CODE')
                if not code:
                    logger.info("="*50)
                    logger.info("📱 VERIFICATION REQUIRED")
                    logger.info("="*50)
                    logger.info("1. Check Telegram for verification code")
                    logger.info("2. Add TELEGRAM_CODE environment variable")
                    logger.info("3. Service will auto-restart")
                    logger.info("="*50)
                    
                    # Wait for code
                    for i in range(300):
                        await asyncio.sleep(1)
                        code = os.getenv('TELEGRAM_CODE')
                        if code:
                            break
                    
                    if not code:
                        logger.error("❌ No verification code provided")
                        return False
                
                await self.client.sign_in(PHONE_NUMBER, code)
                logger.info("✅ Successfully logged in")
            else:
                logger.info("✅ Using existing session")
            
            # Get user info
            me = await self.client.get_me()
            logger.info(f"👤 Logged in as: {me.first_name} (@{me.username})")
            
            # Get source group
            source_username = self.extract_username(SOURCE_GROUP_URL)
            logger.info(f"🔍 Looking for source group: {source_username}")
            self.source_group = await self.client.get_entity(source_username)
            logger.info(f"✅ Source group: {self.source_group.title}")
            
            # Get target group
            target_username = self.extract_username(TARGET_GROUP_URL)
            logger.info(f"🔍 Looking for target group: {target_username}")
            self.target_group = await self.client.get_entity(target_username)
            logger.info(f"✅ Target group: {self.target_group.title}")
            
            # Get source user (specific user to forward from)
            if SOURCE_USERNAME:
                logger.info(f"🔍 Looking for source user: {SOURCE_USERNAME}")
                try:
                    self.source_user = await self.client.get_entity(SOURCE_USERNAME)
                except Exception as e:
                    logger.error(f"❌ Could not find user {SOURCE_USERNAME}: {e}")
                    # Try to extract from group participants
                    participants = await self.client.get_participants(self.source_group)
                    for participant in participants:
                        if participant.username and participant.username.lower() == SOURCE_USERNAME.replace('@', '').lower():
                            self.source_user = participant
                            break
            elif SOURCE_USER_ID:
                logger.info(f"🔍 Looking for source user ID: {SOURCE_USER_ID}")
                try:
                    self.source_user = await self.client.get_entity(SOURCE_USER_ID)
                except Exception as e:
                    logger.error(f"❌ Could not find user ID {SOURCE_USER_ID}: {e}")
            
            if self.source_user:
                user_name = self.source_user.username or self.source_user.first_name or f"User {self.source_user.id}"
                logger.info(f"✅ Source user: {user_name}")
            else:
                logger.warning("⚠️ No specific user configured - will forward from any user")
            
            # Verify access to groups
            logger.info("🔑 Verifying group access...")
            try:
                await self.client.get_participants(self.source_group, limit=1)
                logger.info("✅ Can read from source group")
            except Exception as e:
                logger.warning(f"⚠️ Limited access to source group: {e}")
            
            logger.info("✅ Initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    def is_signal_message(self, message_text):
        """Check if message is a signal message with the required header."""
        if not message_text:
            return False
        
        # Check for the exact signal header at the beginning
        if message_text.strip().startswith(SIGNAL_HEADER):
            return True
        
        # Also check for the header anywhere in the message (case-insensitive)
        if SIGNAL_HEADER.lower() in message_text.lower():
            return True
        
        return False
    
    def extract_signal_details(self, message_text):
        """Extract signal details from message."""
        if not message_text:
            return {}
        
        details = {
            'currency_pair': None,
            'direction': None,
            'entry_time': None,
            'martingale_levels': []
        }
        
        try:
            # Extract currency pair (look for pattern like EUR/CAD)
            currency_pattern = r'🇪🇺\s*EUR/CAD\s*🇨🇦|EUR/CAD'
            currency_match = re.search(currency_pattern, message_text, re.IGNORECASE)
            if currency_match:
                details['currency_pair'] = 'EUR/CAD'
            
            # Extract direction (SELL/BUY)
            direction_pattern = r'Direction:\s*(SELL|BUY)'
            direction_match = re.search(direction_pattern, message_text, re.IGNORECASE)
            if direction_match:
                details['direction'] = direction_match.group(1)
            
            # Extract entry time
            entry_pattern = r'Entry:\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)'
            entry_match = re.search(entry_pattern, message_text, re.IGNORECASE)
            if entry_match:
                details['entry_time'] = entry_match.group(1)
            
            # Extract martingale levels
            martingale_pattern = r'Level\s*(\d+)\s*→\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)'
            martingale_matches = re.findall(martingale_pattern, message_text, re.IGNORECASE)
            for level, time in martingale_matches:
                details['martingale_levels'].append(f"Level {level} → {time}")
            
        except Exception as e:
            logger.error(f"Error extracting signal details: {e}")
        
        return details
    
    def format_forward_message(self, original_text, signal_details, sender_name):
        """Format the message for forwarding."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create header
        if ADD_TIMESTAMP:
            header = f"📡 **SIGNAL FORWARDED**\n"
            header += f"🕒 {timestamp}\n"
            header += f"👤 From: {sender_name}\n"
            header += f"📊 Source: {self.source_group.title}\n"
            header += "━━━━━━━━━━━━━━━━━━\n\n"
        else:
            header = ""
        
        # Add signal summary if we extracted details
        summary = ""
        if signal_details.get('currency_pair'):
            summary += f"**Pair:** {signal_details['currency_pair']}\n"
        if signal_details.get('direction'):
            emoji = "🔴" if signal_details['direction'].upper() == 'SELL' else "🟢"
            summary += f"**Direction:** {emoji} {signal_details['direction']}\n"
        if signal_details.get('entry_time'):
            summary += f"**Entry:** {signal_details['entry_time']}\n"
        
        if summary:
            header += "📈 **Signal Summary:**\n" + summary + "\n"
            header += "━━━━━━━━━━━━━━━━━━\n\n"
        
        return header + original_text
    
    async def forward_signal(self, event):
        """Forward a signal message."""
        try:
            message = event.message
            
            # Skip edited messages
            if message.edit_date:
                return
            
            # Get sender
            sender = await message.get_sender()
            if not sender:
                logger.warning("Could not get sender information")
                return
            
            # Check if message is from the specific user
            if self.source_user:
                if sender.id != self.source_user.id:
                    return  # Not from the specified user
            
            # Get message text
            message_text = message.text or message.message or ""
            if not message_text:
                return  # Skip media-only messages
            
            # Check if it's a signal message
            if not self.is_signal_message(message_text):
                return
            
            logger.info("🎯 Found signal message!")
            
            # Get sender name for logging
            sender_name = "Unknown"
            if hasattr(sender, 'username') and sender.username:
                sender_name = f"@{sender.username}"
            elif hasattr(sender, 'first_name') and sender.first_name:
                sender_name = sender.first_name
                if hasattr(sender, 'last_name') and sender.last_name:
                    sender_name += f" {sender.last_name}"
            
            logger.info(f"📨 Signal from: {sender_name}")
            logger.info(f"📝 Preview: {message_text[:100]}...")
            
            # Extract signal details
            signal_details = self.extract_signal_details(message_text)
            
            # Apply delay if configured
            if FORWARD_DELAY > 0:
                logger.info(f"⏳ Waiting {FORWARD_DELAY} seconds before forwarding...")
                await asyncio.sleep(FORWARD_DELAY)
            
            # Format the message
            formatted_message = self.format_forward_message(
                message_text,
                signal_details,
                sender_name
            )
            
            # Forward the message
            await self.client.send_message(
                entity=self.target_group,
                message=formatted_message
            )
            
            logger.info(f"✅ Signal forwarded to {self.target_group.title}")
            
            # Send confirmation if enabled
            if SEND_CONFIRMATION:
                try:
                    await self.client.send_message(
                        entity=self.source_group,
                        message=f"✅ Signal forwarded successfully to {self.target_group.title}",
                        reply_to=message.id
                    )
                    logger.info("✅ Sent confirmation message")
                except Exception as e:
                    logger.warning(f"Could not send confirmation: {e}")
            
            # Log details
            if signal_details.get('currency_pair'):
                logger.info(f"📊 Signal details: {signal_details['currency_pair']} {signal_details.get('direction', '')}")
            
        except Exception as e:
            logger.error(f"❌ Error forwarding signal: {e}")
    
    async def start(self):
        """Start the signal forwarder."""
        logger.info("="*50)
        logger.info("🎯 TELEGRAM SIGNAL FORWARDER")
        logger.info("="*50)
        
        # Validate configuration
        if not all([API_ID, API_HASH, PHONE_NUMBER, SOURCE_GROUP_URL, TARGET_GROUP_URL]):
            logger.error("❌ Missing required environment variables")
            logger.info("Please check: API_ID, API_HASH, PHONE_NUMBER, SOURCE_GROUP_URL, TARGET_GROUP_URL")
            return
        
        # Initialize
        if not await self.initialize():
            logger.error("❌ Failed to initialize")
            return
        
        self.is_running = True
        
        # Setup event handler
        @self.client.on(events.NewMessage(chats=self.source_group))
        async def message_handler(event):
            await self.forward_signal(event)
        
        # Log configuration
        logger.info("="*50)
        logger.info("⚙️ CONFIGURATION")
        logger.info(f"Source Group: {self.source_group.title}")
        logger.info(f"Target Group: {self.target_group.title}")
        if self.source_user:
            user_name = self.source_user.username or self.source_user.first_name or f"ID: {self.source_user.id}"
            logger.info(f"Source User: {user_name}")
        else:
            logger.info("Source User: Any user")
        logger.info(f"Signal Header: '{SIGNAL_HEADER}'")
        logger.info(f"Add Timestamp: {ADD_TIMESTAMP}")
        logger.info(f"Send Confirmation: {SEND_CONFIRMATION}")
        logger.info(f"Forward Delay: {FORWARD_DELAY}s")
        logger.info("="*50)
        logger.info("📡 LISTENING FOR SIGNALS...")
        logger.info("="*50)
        
        # Send startup notification
        try:
            startup_msg = f"✅ Signal Forwarder Started\n" \
                         f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                         f"📊 Listening for: '{SIGNAL_HEADER}'\n" \
                         f"👤 From: {self.source_user.username if self.source_user else 'Any user'}\n" \
                         f"📨 To: {self.target_group.title}"
            
            await self.client.send_message(
                entity=self.target_group,
                message=startup_msg
            )
            logger.info("✅ Sent startup notification")
        except Exception as e:
            logger.warning(f"Could not send startup notification: {e}")
        
        # Keep running
        try:
            await self.client.run_until_disconnected()
        except asyncio.CancelledError:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the forwarder gracefully."""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping signal forwarder...")
        self.is_running = False
        
        if self.client:
            await self.client.disconnect()
            logger.info("✅ Disconnected from Telegram")
        
        logger.info("👋 Signal forwarder stopped")

async def main():
    forwarder = SignalForwarder()
    
    try:
        await forwarder.start()
    except KeyboardInterrupt:
        logger.info("\nReceived keyboard interrupt")
        await forwarder.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await forwarder.stop()

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 7):
        logger.error("❌ Python 3.7 or higher is required")
        sys.exit(1)
    
    # Run the application
    asyncio.run(main())