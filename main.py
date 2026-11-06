import os
import re
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv

# लोकल टेस्टिंग के लिए .env लोड करें (Railway अपने आप वेरिएबल ले लेता है)
load_dotenv()

# Environment Variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

# चैनल IDs (इन्हें -100 के साथ डालें, जैसे: -100123456789)
MAIN_SOURCE_ID = int(os.getenv("MAIN_SOURCE_ID"))
TEST_SOURCE_ID = int(os.getenv("TEST_SOURCE_ID"))
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

SOURCE_CHANNELS = [MAIN_SOURCE_ID, TEST_SOURCE_ID]

# फास्ट रिस्पॉन्स के लिए ऑप्टिमाइज्ड क्लाइंट
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    receive_updates=True,
     sequential_updates=False # पैरेलल और अल्ट्रा-फास्ट प्रोसेसिंग के लिए
)

# कैलकुलेशन ढूंढने के लिए प्री-कंपाइल्ड Regex (सबसे तेज तरीका)
# यह "12 + 5 = ?", "50 * 2", "100 / 4 =" आदि को तुरंत पकड़ लेगा
CALC_PATTERN = re.compile(r'(\d+(?:\.\d+)?(?:\s*[\+\-\*\/xX×÷]\s*\d+(?:\.\d+)?)+)')

def solve_expression(text: str):
    if not text:
        return None
    
    # ब्रैकेट या अजीब चिन्हों को स्टैंडर्ड मैथ ऑपरेटर में बदलें
    cleaned_text = text.replace('×', '*').replace('x', '*').replace('X', '*').replace('÷', '/')
    
    match = CALC_PATTERN.search(cleaned_text)
    if not match:
        return None
        
    expr = match.group(1)
    # सुरक्षा के लिए सिर्फ नंबर और ऑपरेटर ही रखें
    clean_expr = re.sub(r'[^\d\+\-\*\/\.]+', '', expr)
    
    try:
        result = eval(clean_expr)
        # अगर आंसर 25.0 जैसा है तो उसे 25 (इंटीजर) बनाएं, वरना डेसिमल रखें
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 4))
    except Exception:
        return None

# दोनों सोर्स चैनल (Main + Testing) पर नजर रखने वाला हैंडलर
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def fast_calc_handler(event):
    # raw_text फोटो के कैप्शन और नॉर्मल मैसेज दोनों को बिना देरी के पढ़ता है
    caption_text = event.raw_text
    if not caption_text:
        return

    answer = solve_expression(caption_text)
    if answer:
        # 4 बार मोनो फॉर्मेटिंग में, एक लाइन में एक आंसर, बिना किसी एक्स्ट्रा स्पेस के
        formatted_msg = f"`{answer}`\n`{answer}`\n`{answer}`\n`{answer}`"
        
        # बिना किसी डिले के सीधा टारगेट चैनल में सेंड
        await client.send_message(
            TARGET_CHANNEL_ID, 
            formatted_msg, 
            parse_mode='md'
        )

async def keep_updates_alive():
    """
    यह फंक्शन 'Unseen Message' वाली समस्या को खत्म करता है।
    हर 25 सेकंड में दोनों चैनल्स को बैकग्राउंड में पिंग करता है ताकि 
    Telegram सर्वर कभी भी अपडेट्स भेजना बंद न करे।
    """
    while True:
        try:
            for chat_id in SOURCE_CHANNELS:
                await client.get_messages(chat_id, limit=1)
        except Exception:
            pass
        await asyncio.sleep(25)

async def main():
    print("Starting Fast Calculation Userbot...")
    await client.start()
    
    # सबसे जरूरी स्टेप: सारे चैनल्स की Access Hash मेमोरी में लोड करना
    print("Syncing channels to prevent 'Unseen' issue...")
    await client.get_dialogs(limit=None)
    await client.catch_up()
    
    # बैकग्राउंड में कीप-अलाइव टास्क शुरू करें
    asyncio.create_task(keep_updates_alive())
    
    print(f"Bot is LIVE and listening to: {SOURCE_CHANNELS}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
  
