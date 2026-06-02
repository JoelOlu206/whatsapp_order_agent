
#imports
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

#loads secrets from .env file
load_dotenv()

#creates flask app
app = Flask(__name__)

#creates webhook endpoint for incoming messages
@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get("body", "")
    print(f"imconing message: {incoming_msg}")

    #responds to incoming message with a confirmation
    resp = MessagingResponse()
    resp.message("Hello your message was received.")
    return str(resp)




if __name__ == "__main__":
    app.run(port=5000, debug=True)

