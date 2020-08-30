from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from airq import forecasts


app = Flask(__name__)


@app.route("/")
def index():
    return "OK"


@app.route("/sms", methods=["POST"])
def sms_reply():
    resp = MessagingResponse()
    body = request.values.get("Body", "").strip()
    resp.message(forecasts.get_forecast_message_for_zipcode(body))
    return str(resp)


@app.route('/forecast')
def forecast():
    zipcode = request.args.get('zipcode', "").strip()
    return forecasts.get_forecast_message_for_zipcode(zipcode)