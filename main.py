import os
import re
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv

# .env फाइल लोड करें
load_dotenv()

# आपके स्क्रीनशॉट के अनुसार Exact Variables
API_ID = int(os.getenv("API_ID").strip())
API_HASH = os.getenv("API_HASH").strip()
STRING_SESSION = os.getenv("STRING_SESSION").strip().replace("\n", "").replace(" ", "")

OFFICIAL_SOURCE_ID = int(os.getenv("OFFICIAL_SOURCE_ID").strip())
TEST_SOURCE_ID = int(os.getenv("TEST_SOURCE_ID").strip())
DEST_CHANNEL_ID = int(os.getenv("DEST_CHANNEL_ID").strip())

SOURCE_CHANNELS = [OFFICIAL_SOURCE_ID, TEST_SOURCE_ID]

# अल्ट्रा-फास्ट क्लाइंट सेटअप
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    receive_updates=True,
    sequential_updates=False
)

# कैलकुलेशन पकड़ने वाला फास्ट Regex (जैसे: 25 + 30 = ?, 10 * 5, 100 / 2)
CALC_PATTERN = re.compile(r'(\d+(?:\.\d+)?(?:\s*[\+\-\*\/xX×÷]\s*\d+(?:\.\d+)?)+)')

def solve_expression(text: str):
    if not text:
        return None
    
    # अलग-अलग गुणा/भाग के चिन्हों को नॉर्मल ऑपरेटर में बदलना
    cleaned_text = text.replace('×', '*').replace('x', '*').replace('X', '*').replace('÷', '/')
    
    match = CALC_PATTERN.search(cleaned_text)
    if not match:
        return None
        
    expr = match.group(1)
    clean_expr = re.sub(r'[^\d\+\-\*\/\.]+', '', expr)
    
    try:
        result = eval(clean_expr)
        # अगर पॉइंट के बाद 0 है (जैसे 15.0) तो सिर्फ 15 रिटर्न करे
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 4))
    except Exception:
        return None

# मैसेज आते ही तुरंत पकड़ने वाला हैंडलर (Main + Test दोनों के लिए)
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def fast_calc_handler(event):
    caption_text = event.raw_text
    if not caption_text:
        return

    answer = solve_expression(caption_text)
    if answer:
        # 4 लाइन, बिना किसी स्पेस के, मोनो फॉर्मेटिंग में
        formatted_msg = f"`{answer}`\n`{answer}`\n`{answer}`\n`{answer}`"
        
        # तुरंत आपके DEST_CHANNEL_ID में भेज देगा
        await client.send_message(
            DEST_CHANNEL_ID, 
            formatted_msg, 
            parse_mode='md'
        )

async def keep_updates_alive():
    """
    बिना चैनल खोले (Unseen रहने पर भी) तुरंत मैसेज पकड़ने के लिए 
    हर 20 सेकंड में दोनों सोर्स चैनल्स को पिंग करेगा।
    """
    while True:
        try:
            for chat_id in SOURCE_CHANNELS:
                await client.get_messages(chat_id, limit=1)
        except Exception:
            pass
        await asyncio.sleep(20)

async def main():
    print("Starting Bot...")
    await client.start()
    
    # चैनल्स को मेमोरी में सिंक करना ताकि 'Unseen' की दिक्कत कभी न आए
    print("Syncing channels...")
    await client.get_dialogs(limit=None)
    await client.catch_up()
    
    asyncio.create_task(keep_updates_alive())
    
    print(f"Bot is LIVE! Listening on: {SOURCE_CHANNELS}")
    print(f"Sending answers to: {DEST_CHANNEL_ID}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
    
