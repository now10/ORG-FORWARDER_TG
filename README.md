# Telegram Signal Forwarder

Forwards specific trading signals from one Telegram group to another.

## Features
- ✅ Only forwards messages with "🔔 NEW SIGNAL!" header
- ✅ Can filter by specific user
- ✅ Adds timestamps to forwarded messages
- ✅ Optional confirmation messages
- ✅ Render.com optimized

## Setup Instructions

### 1. Get Credentials
1. Go to https://my.telegram.org
2. Create app and save `api_id` and `api_hash`

### 2. Find User Information
To forward from a specific user:
1. In Telegram, open the user's profile
2. Note their username (e.g., @trader_john)
3. Or find their user ID using a bot like @userinfobot

### 3. Configure Environment Variables

In Render dashboard → Environment → Add:

```env
# Required
API_ID=12345678
API_HASH=your_api_hash
PHONE_NUMBER=+1234567890
SOURCE_GROUP_URL=https://t.me/your_source_group
TARGET_GROUP_URL=https://t.me/your_target_group

# Optional - User filter (use one)
SOURCE_USERNAME=@specific_trader
# OR
# SOURCE_USER_ID=123456789

# Optional - Signal header
SIGNAL_HEADER=🔔 NEW SIGNAL!

# Optional settings
ADD_TIMESTAMP=true
SEND_CONFIRMATION=true
FORWARD_DELAY=0