import os
import re

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
client = OpenAI(api_key=api_key) if api_key else None


STORE_INSTRUCTIONS = """
You are the concise, friendly, professional multilingual customer support
assistant for WIJESINGHE TEXTILES.

IMPORTANT LANGUAGE RULE:
- The response language is explicitly specified in the instruction
  accompanying each request.
- Respond ONLY in that specified language.
- Do not switch to English unless English is explicitly requested.
- Do not mix languages unnecessarily.
- Use natural, customer-friendly Sinhala or Tamil when requested.
- Conversation history does not override the specified response language.

RESPONSE RULES:
- Answer only the customer's question.
- Normally use 1-3 short sentences.
- Begin each answer with the store welcome greeting in the requested language.
- Do not add unrelated departments, policies, promotions, branch details,
  tips, suggestions or closing questions.
- Never invent stock, prices, exact addresses or opening hours.
- Say briefly when information cannot be verified.
- Do not claim an item is in stock without confirmation.

CONFIRMED FLOOR GUIDE:

1st Floor:
Accessories including handbags/bags, perfumes, teddy bears/soft toys,
wallets/purses, sunglasses, watches, hair accessories, gift items and
fashion jewellery. Cashier counter is on this floor.

2nd Floor:
Kids' section, including shirts, frocks, skinny jeans, trousers, shorts,
T-shirts, tops, skirts, party wear and children's clothing.

3rd Floor:
Women's section, including sarees, dresses/frocks, blouses, tops, shirts,
trousers, jeans, skirts, underwear and other women's clothing.

4th Floor:
Men's section, including shirts, T-shirts, denim/jeans, trousers, shorts,
formal and casual clothing.

5th Floor:
Sports section, including sportswear, gym/fitness clothing, sports T-shirts,
shorts, trousers and sports accessories.

OTHER STORE INFORMATION:

Branches: Kandy, Colombo, Gampaha and Hanguranketha.

Exchange:
Underwear cannot be exchanged under any circumstances.
Other items may be exchanged within 15 days of purchase only if their
tags are still attached.

Promotions:
Selected items may have 20% or 50% discounts.
Customers spending over LKR 20,000 may be eligible for a promotional
coupon associated with an iPhone 18 Pro Max prize.
Exact details are not confirmed.

Limitations:
No real-time stock, price or transaction access.
"""


CATEGORY_ANSWERS = {
    "women": {
        "en": "We offer sarees, dresses, frocks, blouses, tops, trousers, jeans, skirts, underwear and other women's clothing. Our Women's section is on the 3rd floor.",
        "si": "අපගේ කාන්තා ඇඳුම් අංශයේ සාරි, dresses, frocks, blouses, tops, trousers, jeans, skirts සහ වෙනත් කාන්තා ඇඳුම් තිබෙනවා. එය 3 වන මහලේ තිබෙනවා.",
        "ta": "எங்கள் பெண்கள் ஆடைப் பிரிவில் சேலைகள், dresses, frocks, blouses, tops, trousers, jeans, skirts மற்றும் பிற பெண்கள் ஆடைகள் உள்ளன. இது 3ஆம் மாடியில் உள்ளது."
    },

    "men": {
        "en": "We offer shirts, T-shirts, denim, trousers, shorts, formal and casual wear. Our Men's section is on the 4th floor.",
        "si": "අපගේ පිරිමි ඇඳුම් අංශයේ shirts, T-shirts, denim, trousers, shorts, formal සහ casual ඇඳුම් තිබෙනවා. එය 4 වන මහලේ තිබෙනවා.",
        "ta": "எங்கள் ஆண்கள் பிரிவில் shirts, T-shirts, denim, trousers, shorts, formal மற்றும் casual ஆடைகள் உள்ளன. இது 4ஆம் மாடியில் உள்ளது."
    },

    "children": {
        "en": "Our Kids' section has shirts, frocks, skinny jeans, trousers, shorts, T-shirts, tops, skirts and children's clothing. It's on the 2nd floor.",
        "si": "අපගේ ළමා අංශයේ shirts, frocks, skinny jeans, trousers, shorts, T-shirts, tops, skirts සහ ළමා ඇඳුම් තිබෙනවා. එය 2 වන මහලේ තිබෙනවා.",
        "ta": "எங்கள் குழந்தைகள் பிரிவில் shirts, frocks, skinny jeans, trousers, shorts, T-shirts, tops, skirts மற்றும் குழந்தைகள் ஆடைகள் உள்ளன. இது 2ஆம் மாடியில் உள்ளது."
    },

    "accessories": {
        "en": "Our 1st floor has accessories such as handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items and fashion jewellery.",
        "si": "අපගේ 1 වන මහලේ handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items සහ fashion jewellery වැනි accessories තිබෙනවා.",
        "ta": "எங்கள் 1ஆம் மாடியில் handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items மற்றும் fashion jewellery போன்ற accessories உள்ளன."
    },

    "sports": {
        "en": "Our Sports section includes sportswear, gym and fitness clothing, sports T-shirts, shorts, trousers and sports accessories. It's on the 5th floor.",
        "si": "අපගේ Sports අංශයේ sportswear, gym සහ fitness ඇඳුම්, sports T-shirts, shorts, trousers සහ sports accessories තිබෙනවා. එය 5 වන මහලේ තිබෙනවා.",
        "ta": "எங்கள் Sports பிரிவில் sportswear, gym மற்றும் fitness ஆடைகள், sports T-shirts, shorts, trousers மற்றும் sports accessories உள்ளன. இது 5ஆம் மாடியில் உள்ளது."
    },

    "cashier": {
        "en": "The cashier counter is on the 1st floor.",
        "si": "Cashier counter එක 1 වන මහලේ තිබෙනවා.",
        "ta": "Cashier counter 1ஆம் மாடியில் உள்ளது."
    },

    "floor1": {
        "en": "The 1st floor has our accessories section and cashier counter. You can find handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items and fashion jewellery.",
        "si": "1 වන මහලේ අපගේ accessories අංශය සහ cashier counter එක තිබෙනවා. එම අංශයේ handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items සහ fashion jewellery තිබෙනවා.",
        "ta": "1ஆம் மாடியில் எங்கள் accessories பிரிவும் cashier counter-மும் உள்ளன. அந்தப் பிரிவில் handbags, bags, perfumes, teddy bears, wallets, purses, sunglasses, watches, hair accessories, gift items மற்றும் fashion jewellery உள்ளன."
    },

    "floor2": {
        "en": "The 2nd floor is our Kids' section. It includes children's clothing such as shirts, frocks, jeans, trousers, shorts, T-shirts, tops, skirts and party wear.",
        "si": "2 වන මහලේ අපගේ ළමා ඇඳුම් අංශය තිබෙනවා. එහි shirts, frocks, jeans, trousers, shorts, T-shirts, tops, skirts සහ party wear ඇතුළු ළමා ඇඳුම් තිබෙනවා.",
        "ta": "2ஆம் மாடியில் எங்கள் குழந்தைகள் ஆடைப் பிரிவு உள்ளது. அங்கு shirts, frocks, jeans, trousers, shorts, T-shirts, tops, skirts மற்றும் party wear உள்ளிட்ட குழந்தைகள் ஆடைகள் உள்ளன."
    },

    "floor3": {
        "en": "The 3rd floor is our Women's section. It includes sarees, dresses, frocks, blouses, tops, trousers, jeans, skirts and other women's clothing.",
        "si": "3 වන මහලේ අපගේ කාන්තා ඇඳුම් අංශය තිබෙනවා. එහි සාරි, dresses, frocks, blouses, tops, trousers, jeans, skirts සහ වෙනත් කාන්තා ඇඳුම් තිබෙනවා.",
        "ta": "3ஆம் மாடியில் எங்கள் பெண்கள் ஆடைப் பிரிவு உள்ளது. அங்கு சேலைகள், dresses, frocks, blouses, tops, trousers, jeans, skirts மற்றும் பிற பெண்கள் ஆடைகள் உள்ளன."
    },

    "floor4": {
        "en": "The 4th floor is our Men's section. It includes shirts, T-shirts, denim, trousers, shorts, formal and casual wear.",
        "si": "4 වන මහලේ අපගේ පිරිමි ඇඳුම් අංශය තිබෙනවා. එහි shirts, T-shirts, denim, trousers, shorts, formal සහ casual ඇඳුම් තිබෙනවා.",
        "ta": "4ஆம் மாடியில் எங்கள் ஆண்கள் ஆடைப் பிரிவு உள்ளது. அங்கு shirts, T-shirts, denim, trousers, shorts, formal மற்றும் casual ஆடைகள் உள்ளன."
    },

    "floor5": {
        "en": "The 5th floor is our Sports section. It includes sportswear, gym and fitness clothing, sports T-shirts, shorts, trousers and sports accessories.",
        "si": "5 වන මහලේ අපගේ Sports අංශය තිබෙනවා. එහි sportswear, gym සහ fitness ඇඳුම්, sports T-shirts, shorts, trousers සහ sports accessories තිබෙනවා.",
        "ta": "5ஆம் மாடியில் எங்கள் Sports பிரிவு உள்ளது. அங்கு sportswear, gym மற்றும் fitness ஆடைகள், sports T-shirts, shorts, trousers மற்றும் sports accessories உள்ளன."
    },

    "branches": {
        "en": "Our showrooms are located in Kandy, Colombo, Gampaha and Hanguranketha.",
        "si": "අපගේ showrooms මහනුවර, කොළඹ, ගම්පහ සහ හඟුරන්කෙත පිහිටා තිබෙනවා.",
        "ta": "எங்கள் showroom-கள் கண்டி, கொழும்பு, கம்பஹா மற்றும் ஹங்குரன்கெத்தையில் உள்ளன."
    },

    "promotion": {
        "en": "Selected items may have 20% or 50% discounts. Customers spending over LKR 20,000 may be eligible for a promotional coupon associated with an iPhone 18 Pro Max. Please confirm the current terms with the store.",
        "si": "තෝරාගත් භාණ්ඩ සඳහා 20% හෝ 50% discounts තිබිය හැකියි. රු. 20,000ට වැඩි මිලදී ගැනීම් සඳහා iPhone 18 Pro Max prize එකට සම්බන්ධ promotional coupon එකකට සුදුසුකම් ලැබිය හැකියි. නිවැරදි කොන්දේසි store එකෙන් තහවුරු කරගන්න.",
        "ta": "தேர்ந்தெடுக்கப்பட்ட பொருட்களுக்கு 20% அல்லது 50% discount இருக்கலாம். LKR 20,000க்கு மேல் வாங்குபவர்கள் iPhone 18 Pro Max prize தொடர்பான promotional coupon பெற தகுதியுடையவர்களாக இருக்கலாம். தற்போதைய நிபந்தனைகளை கடையில் உறுதிப்படுத்தவும்."
    },

    "exchange": {
        "en": "Underwear cannot be exchanged under any circumstances. Other items can be exchanged within 15 days of purchase, provided their tags are still attached.",
        "si": "Underwear මිලදී ගත් පසු කිසිදු අවස්ථාවක exchange කළ නොහැකියි. අනෙකුත් භාණ්ඩ මිලදී ගත් දින සිට දින 15ක් ඇතුළත, tags ඉවත් කර නොමැති නම් exchange කළ හැකියි.",
        "ta": "Underwear வாங்கிய பிறகு எந்தச் சூழ்நிலையிலும் மாற்ற முடியாது. மற்ற பொருட்களை வாங்கிய 15 நாட்களுக்குள், அவற்றின் tags அகற்றப்படாமல் இருந்தால் மாற்றிக்கொள்ளலாம்."
    },

    "special": {
        "en": "These are examples only, not confirmed current offers: 20% off selected men's shoes, 30% off selected handbags and 15% off selected children's clothing.",
        "si": "මේවා උදාහරණ පමණයි, දැනට ක්‍රියාත්මක බව තහවුරු කළ offers නොවේ: තෝරාගත් men's shoes සඳහා 20%, handbags සඳහා 30% සහ ළමා ඇඳුම් සඳහා 15% discount.",
        "ta": "இவை உதாரணங்கள் மட்டுமே, தற்போது நடைமுறையில் உள்ள சலுகைகள் என்று உறுதிப்படுத்தப்படவில்லை: தேர்ந்தெடுக்கப்பட்ட men's shoes 20%, handbags 30%, குழந்தைகள் ஆடைகள் 15% discount."
    }
}


QUICK_ACTIONS = {
    "tell me about women's clothing.": "women",
    "tell me about men's clothing.": "men",
    "tell me about children's clothing.": "children",
    "tell me about handbags and accessories.": "accessories",
    "tell me about your current promotions and discounts.": "promotion",
    "tell me about your branches.": "branches",
    "tell me about your exchange policy.": "exchange",
    "show me example special offers.": "special",

    "කාන්තා ඇඳුම් ගැන විස්තර කියන්න.": "women",
    "පිරිමි ඇඳුම් ගැන විස්තර කියන්න.": "men",
    "ළමා ඇඳුම් ගැන විස්තර කියන්න.": "children",
    "අත්බෑග් සහ accessories ගැන කියන්න.": "accessories",
    "දැනට තිබෙන discounts සහ promotions ගැන කියන්න.": "promotion",
    "ඔබගේ ශාඛා ගැන විස්තර කියන්න.": "branches",
    "ඔබගේ භාණ්ඩ exchange කිරීමේ policy එක ගැන කියන්න.": "exchange",
    "විශේෂ දීමනා උදාහරණ පෙන්වන්න.": "special",

    "பெண்கள் ஆடைகள் பற்றி கூறுங்கள்.": "women",
    "ஆண்கள் ஆடைகள் பற்றி கூறுங்கள்.": "men",
    "குழந்தைகள் ஆடைகள் பற்றி கூறுங்கள்.": "children",
    "கைப்பைகள் மற்றும் accessories பற்றி கூறுங்கள்.": "accessories",
    "தற்போதைய தள்ளுபடிகள் பற்றி கூறுங்கள்.": "promotion",
    "உங்கள் கிளைகள் பற்றி கூறுங்கள்.": "branches",
    "exchange policy பற்றி கூறுங்கள்.": "exchange",
    "பொருள் மாற்றக் கொள்கை பற்றி கூறுங்கள்": "exchange",
    "உதாரண சிறப்பு சலுகைகளை காட்டுங்கள்.": "special"
}


def detect_language(message):
    if any("\u0D80" <= c <= "\u0DFF" for c in message):
        return "si"

    if any("\u0B80" <= c <= "\u0BFF" for c in message):
        return "ta"

    return "en"


def greeting(language):
    greetings = {
        "en": "Welcome to WIJESINGHE TEXTILES!",
        "si": "WIJESINGHE TEXTILES වෙත සාදරයෙන් පිළිගනිමු!",
        "ta": "WIJESINGHE TEXTILES உங்களை வரவேற்கிறது!"
    }

    return greetings.get(language, greetings["en"])


def normalize(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def deterministic_intent(text):
    t = normalize(text)

    # Floors must be checked before cashier keywords.
    floor_keys = {
        "floor1": (
            "1st floor", "first floor", "floor 1", "floor one",
            "1 වන මහල", "පළමු මහල", "முதல் மாடி"
        ),

        "floor2": (
            "2nd floor", "second floor", "floor 2", "floor two",
            "2 වන මහල", "දෙවන මහල",
            "இரண்டாம் மாடி", "இரண்டாவது மாடி",
            "2ஆம் மாடி", "2வது மாடி"
        ),

        "floor3": (
            "3rd floor", "third floor", "floor 3", "floor three",
            "3 වන මහල", "තුන්වන මහල",
            "மூன்றாம் மாடி", "மூன்றாவது மாடி",
            "3ஆம் மாடி", "3வது மாடி"
        ),

        "floor4": (
            "4th floor", "fourth floor", "floor 4", "floor four",
            "4 වන මහල", "හතරවන මහල",
            "நான்காம் மாடி", "நான்காவது மாடி",
            "4ஆம் மாடி", "4வது மாடி"
        ),

        "floor5": (
            "5th floor", "fifth floor", "floor 5", "floor five",
            "5 වන මහල", "පස්වන මහල",
            "ஐந்தாம் மாடி", "ஐந்தாவது மாடி",
            "5ஆம் மாடி", "5வது மாடி"
        )
    }

    for intent, keywords in floor_keys.items():
        if any(keyword in t for keyword in keywords):
            return intent

    # Cashier
    if any(k in t for k in (
        "cashier", "cash counter", "කැෂියර්",
        "මුදල් කවුන්ටරය", "காசாளர்"
    )):
        return "cashier"

    # Women
    women_keywords = (
        "women's wear", "women clothing", "women's clothing",
        "ladies clothing", "ladies wear",
        "කාන්තා ඇඳුම්", "කාන්තා ඇඳු", "කාන්තාවන්ගේ ඇඳුම්",
        "பெண்கள் ஆடை", "பெண்கள் உடைகள்"
    )

    if any(k in t for k in women_keywords):
        return "women"

    # Men
    men_keywords = (
        "men's wear", "men clothing", "men's clothing",
        "menswear", "පිරිමි ඇඳුම්", "පිරිමි ඇඳු",
        "ஆண்கள் ஆடை", "ஆண்கள் உடைகள்"
    )

    if any(k in t for k in men_keywords):
        return "men"

    # Kids
    children_keywords = (
        "kids", "children", "childrens clothing",
        "kids clothing", "kids wear",
        "ළමා ඇඳුම්", "ළමා ඇඳු",
        "ළමයින්ගේ ඇඳුම්",
        "குழந்தைகள் ஆடை", "குழந்தைகள் உடைகள்"
    )

    if any(k in t for k in children_keywords):
        return "children"

    # Sports
    sports_keywords = (
        "sports section", "sportswear", "gym wear",
        "sport items", "sports items", "sports",
        "fitness clothing", "ක්‍රීඩා ඇඳුම්", "ක්‍රීඩා",
        "விளையாட்டு ஆடை", "விளையாட்டு உடைகள்"
    )

    if any(k in t for k in sports_keywords):
        return "sports"

    # Accessories
    accessories_keywords = (
        "accessories", "handbags", "bags", "perfume",
        "teddy", "wallet", "purse", "sunglasses",
        "watches", "jewellery", "jewelry",
        "අමතර භාණ්ඩ", "අමතර භාණ්ඩ ගැන",
        "අත්බෑග්", "බෑග්", "බෑග් ගැන",
        "විලාසිතා භාණ්ඩ", "උපාංග",
        "பைகள்", "அணிகலன்கள்", "accessory"
    )

    if any(k in t for k in accessories_keywords):
        return "accessories"

    # Branches
    branch_keywords = (
        "branch", "branches", "showroom", "showrooms",
        "store locations", "locations",
        "ශාඛා", "ශාඛාව", "ශාඛා ගැන",
        "අපගේ ශාඛා", "අපේ ශාඛා",
        "කොහෙද තියෙන්නේ", "කොහෙද තිබෙන්නේ",
        "கிளைகள்", "கிளை", "showroom எங்கே"
    )

    if any(k in t for k in branch_keywords):
        return "branches"

    # Promotions and discounts
    promotion_keywords = (
        "promotion", "promotions", "discount", "discounts",
        "sale", "offers", "offer", "current promotions",
        "දීමනා", "ප්‍රවර්ධන", "promotion ගැන",
        "discounts ගැන", "වට්ටම්", "වට්ටම් ගැන",
        "தள்ளுபடி", "தள்ளுபடிகள்", "சலுகைகள்"
    )

    if any(k in t for k in promotion_keywords):
        return "promotion"

    # Exchange policy
    exchange_keywords = (
        "exchange policy", "exchange", "return policy",
        "return items", "can i exchange",
        "භාණ්ඩ මාරු", "exchange කිරීම",
        "exchange policy එක", "හුවමාරු",
        "මාරු කරගන්න", "මාරු කිරීමේ",
        "பரிமாற்றம்", "exchange policy",
        "பொருள் மாற்றக் கொள்கை", "பொருள் மாற்ற",
        "பொருட்களை மாற்ற", "மாற்றிக் கொள்ள", "மாற்றிக்கொள்ள",
        "மாற்றும் கொள்கை", "பொருட்களை திருப்பி"
    )

    if any(k in t for k in exchange_keywords):
        return "exchange"

    # Special offers
    special_keywords = (
        "special offer", "special offers",
        "special deal", "special deals",
        "example offers", "example special offers",
        "විශේෂ දීමනා", "විශේෂ offer",
        "විශේෂ offers", "උදාහරණ දීමනා",
        "சிறப்பு சலுகைகள்", "சிறப்பு offer"
    )

    if any(k in t for k in special_keywords):
        return "special"

    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    messages = data.get("messages")

    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "Please enter a message."}), 400

    if len(messages) > 30:
        return jsonify({"error": "Conversation is too long."}), 400

    clean_messages = []

    for msg in messages:
        if (
            isinstance(msg, dict)
            and msg.get("role") in ("user", "assistant")
            and isinstance(msg.get("content"), str)
        ):
            content = msg["content"].strip()

            if content:
                clean_messages.append({
                    "role": msg["role"],
                    "content": content[:4000]
                })

    if not clean_messages or clean_messages[-1]["role"] != "user":
        return jsonify({"error": "Please send a valid message."}), 400

    last = clean_messages[-1]["content"].strip()
    language = detect_language(last)

    # Exact Quick Action match
    matched = QUICK_ACTIONS.get(normalize(last))

    if matched:
        answer = CATEGORY_ANSWERS[matched].get(language)

        if answer:
            return jsonify({
                "reply": f"{greeting(language)}\n\n{answer}"
            })

    # Deterministic answers
    intent = deterministic_intent(last)

    if intent:
        answer = CATEGORY_ANSWERS[intent].get(language)

        if answer:
            return jsonify({
                "reply": f"{greeting(language)}\n\n{answer}"
            })

    # API fallback for questions not covered by predefined responses
    if client is None:
        app.logger.error("OPENAI_API_KEY is not configured.")

        error_messages = {
            "en": "The AI service is currently unavailable. Please try again later.",
            "si": "AI සේවාව මේ මොහොතේ ලබාගත නොහැකියි. කරුණාකර පසුව නැවත උත්සාහ කරන්න.",
            "ta": "AI சேவை தற்போது கிடைக்கவில்லை. தயவுசெய்து பின்னர் மீண்டும் முயற்சிக்கவும்."
        }

        return jsonify({
            "reply": f"{greeting(language)}\n\n{error_messages[language]}"
        }), 503

    language_names = {
        "en": "English",
        "si": "Sinhala",
        "ta": "Tamil"
    }

    language_instruction = (
        f"IMPORTANT: Respond ONLY in {language_names[language]}. "
        f"Start with this greeting: {greeting(language)} "
        "Do not answer in another language."
    )

    try:
        response = client.responses.create(
            model=model_name,
            instructions=STORE_INSTRUCTIONS + "\n\n" + language_instruction,
            input=clean_messages,
            max_output_tokens=250
        )

        answer = response.output_text

        if not answer or not answer.strip():
            raise ValueError("The API returned an empty response.")

        answer = answer.strip()

        # Ensure the greeting is present
        if not answer.startswith(greeting(language)):
            answer = f"{greeting(language)}\n\n{answer}"

        return jsonify({"reply": answer})

    except Exception as e:
        app.logger.exception("AI response error: %s", e)

        error_messages = {
            "en": "Sorry, I couldn't generate a response right now. Please try again.",
            "si": "කණගාටුයි, මේ මොහොතේ පිළිතුර ලබාදීමට නොහැකි වුණා. කරුණාකර නැවත උත්සාහ කරන්න.",
            "ta": "மன்னிக்கவும், இப்போது பதிலை வழங்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்."
        }

        return jsonify({
            "reply": f"{greeting(language)}\n\n{error_messages[language]}"
        }), 500


if __name__ == "__main__":
    app.run(debug=False)