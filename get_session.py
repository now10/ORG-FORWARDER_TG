from telethon import TelegramClient
import asyncio

async def main():
    API_ID = 12345678  # YOUR API ID
    API_HASH = "your_api_hash_here"  # YOUR API HASH
    PHONE = "+1234567890"  # YOUR PHONE
    
    print("Getting session string...")
    
    client = TelegramClient('my_session', API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("Please check Telegram for verification code...")
            await client.send_code_request(PHONE)
            code = input("Enter code: ").strip()
            await client.sign_in(PHONE, code)
        
        # Get session string
        session_string = client.session.save()
        
        print("\n" + "="*60)
        print("✅ SESSION STRING (Copy this):")
        print("="*60)
        print(session_string)
        print("="*60)
        
        await client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
