
#Imports
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import anthropic
import os

#Loads secrets from .env file
load_dotenv()

#Creates flask app
app = Flask(__name__)

#Connects to anthropic API using the key from .env file
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

#Stores conversation history per customer phone number 
conversation_store = {}

#System Prompt for the AI asistant (Claude)
SYSTEM_PROMPT = """you are a friendly order taking assistant for Baba Ibeta, a nigerian bread business specialising in agege bread.

Your job is to collect the following information from the customer:
1. Their Name
2. What they want and the quantity
3. Whether they want delivery of pickup
4. Their contact number 

Once you have all 4 pieces of informtion, confirm the full order back to the customer in a clear summary.

Be warm and friendly and conversational. Keep your messages short and to the point.

Do not ask for all information at once, collect it naturally one step at a time"""



#Creates webhook endpoint for incoming messages
@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get("Body", "")
    customer_number = request.values.get("From", "")
    
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

