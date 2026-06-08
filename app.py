#Imports
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import anthropic
import os
import gspread
from google.oauth2.service_account import Credentials




#Loads secrets from .env file
load_dotenv()

#Creates flask app
app = Flask(__name__)

#Connects to anthropic API using the key from .env file
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

#Stores conversation history per customer phone number 
conversation_store = {}

#Function to connect to google sheets and log order details
def log_order_to_sheet(name, order, quantity, delivery_or_pickup, phone):
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(os.getenv("GOOGLE_SHEETS_ID")).sheet1

    from datetime import datetime
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    sheet.append_row([timestamp, name, order, quantity, delivery_or_pickup, phone, "Pending"])
    print(f"Order logged to sheet for {name}")



#System Prompt for the AI asistant (Claude)
SYSTEM_PROMPT = """you are a friendly order taking assistant for Baba Ibeta, a nigerian food business based in Milton Keynes.

You sell the following items:

BREADS & BURGERS:
- Baba Beta Loaf (Agege Bread) - £3.00
- Baba Beta Rolls (4 per pack) - £2.50
- Baba Beta Chicken Sandwich - £7.99
- Vegetable soup with boiled plantain and pepper hake fish - £12.00
- Boiled yam and designer sauce - £7.99

NIGERIAN CLASSICS:
- Grilled peppered Goat meat - £15.99
- Premium Jollof Rice and Chicken (650ml) - £15.00
- Jollof Rice and Chicken (650ml) - £12.00
- Premium Beans with Agoyin Sauce & Protein (650ml) - £18.50
- Beans with Agoyin Sauce (500ml) - £13.50
- Beans Porridge (650ml) - £12.00
- Yam porridge - £10.50
- Vegetables soup with pounded Yam - £15.00
- Meat Pie (Medium) - £2.00
- Chicken Pie (Medium) - £2.00
- Fish Pie (Medium) - £2.00

DESSERTS:
- Puff Puff (10 pieces) - £8.00
- Puff Puff with Chocolate or Caramel Drizzle (10 pieces) - £10.00
- Oreo Banana Cake - £8.50
- Banana Bread/Cake - £6.50

DRINKS:
- Coca-Cola - £2.99
- Coke Zero - £2.99
- Diet Coke - £2.99
- Fanta (300ml) - £2.99
- Sprite (300ml) - £1.99
- 7UP Zero - £2.99
- Dr Pepper - £1.99
- Schweppes - £2.99
- Malta Guinness - £3.50
- Old Jamaica Ginger Beer - £1.99
- Bottled Still Water - £1.99


Your job is to collect the following information from the customer:
1. Their Name
2. What they want and the quantity
3. Whether they want delivery or pickup
4. Their contact number 

If a customer asks about something not on the menu, politely let them know it is not available
If a customer asks for the menu, share the categories and items clearly.

Once you have all 4 pieces of informtion, confirm the full order back to the customer in a clear summary and ask them to confirm.

When the customer confirms their order, end your message with this exact tag on a new line:
ORDER_COMPLETE:name|order|quantity|delivery_or_pickup|phone

For example:
ORDER_COMPLETE:Joel|Agege Bread|3 loaves|Delivery|07851494936

Customers may greet you in yoruba or use informal greetings. Treat any opening message as the start of an order conversaion and respond warmly in English.
Be warm and friendly and conversational. Keep your messages short and to the point.
Do not ask for all information at once, collect it naturally one step at a time"""



#Creates webhook endpoint for incoming messages
@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get("Body", "")
    customer_number = request.values.get("From", "")
    
    #Handles empty messages (voice notes, images and stickers)
    if not incoming_msg:
        resp = MessagingResponse()
        resp.message("Hi, i can only process text messages. Please send your order details in a text message.")
        return str(resp)
    
    #Resets conversation if customer sends a greeting or wants to start a new order.
    if incoming_msg.lower().strip() in ["hi", "hello", "hey", "new order", "start", "restart"]:
        if customer_number in conversation_store:
            del conversation_store[customer_number]

    print(f"Incoming message from {customer_number}: {incoming_msg}")

    #Gets or creates converstaion history for the customer
    if customer_number not in conversation_store:
        conversation_store[customer_number] = []

    #Adds customer message to conversation history
    conversation_store[customer_number].append({
        "role": "user",
        "content": incoming_msg
    })
    
    #Sends message history to Claude and get reply
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system =SYSTEM_PROMPT,
        messages=conversation_store[customer_number]
    )
    
    #Extracts Claude's reply
    claude_reply = response.content[0].text

    #Checks if order is complete and logs to sheet if so.
    if "ORDER_COMPLETE:" in claude_reply:
        try:
            order_data = claude_reply.split("ORDER_COMPLETE:")[1].strip().split("|")
            
            if len(order_data) == 5:
                log_order_to_sheet(order_data[0], order_data[1], order_data[2], order_data[3], order_data[4])
            
            #remove the tag from the reply before sending to customer
            claude_reply = claude_reply.split("ORDER_COMPLETE:")[0].strip()
        
        except Exception as e:
            print(f"Error logging order: {e}")


    #Adds Claude reply to conversation history
    conversation_store[customer_number].append({
        "role": "assistant",
        "content": claude_reply
    })

    print(f"Claude reply: {claude_reply}")

    #Sends reply back to customer on WhatsApp
    resp = MessagingResponse()
    resp.message(claude_reply)
    return str(resp)



if __name__ == "__main__":
    app.run(port=5000, debug=True)

