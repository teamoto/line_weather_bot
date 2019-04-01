import os
import sys
import requests
from geopy.geocoders import Nominatim
from flask import Flask, request, abort
from datetime import datetime, timedelta
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)

app = Flask(__name__)

# get env variables
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
LINE_CHANNEL_SECRET = os.environ['LINE_CHANNEL_SECRET']
DARK_SKY_API_KEY = os.environ['DARK_SKY_API_KEY']

# instaciate classes
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# create a base url to get weather info:
base_url = 'https://api.darksky.net/forecast'
base_url += '/' + DARK_SKY_API_KEY
# specify options for query results
option = "exclude=currently,minutely,hourly,alerts&amp;units=si"


# define function to get weather info
def get_weather(base_url, option, location):
    # get location info throuh geopy
    geo_code = Nominatim().geocode(str(location.strip()), language='en-US')
    latitude = str(geo_code.latitude)
    longitude = str(geo_code.longitude)
    # set date info
    d = datetime.today().strftime('%Y-%m-%d')
    search_date = d + 'T00:00:00'
    # create a request url
    request_url = base_url + '/' + latitude + ',' + longitude
    request_url += ',' + search_date + '?' + option
    # query a request to get wather informaiton
    r = requests.get(request_url)
    # get result in a json format
    json_res = r.json()
    # specify condition to set temp unit
    unit_type = '°F' if json_res['flags']['units'] == 'us' else '°C'
    # organize result
    weather = str(json_res['daily']['data'][0]['summary'])
    temp_max = str(json_res['daily']['data'][0]['apparentTemperatureMax'])
    temp_min = str(json_res['daily']['data'][0]['apparentTemperatureMin'])
    # return a result as a dictionary
    return {
        'location': geo_code.address,
        'weather': weather,
        'temp_max': (temp_max+unit_type),
        'temp_min': (temp_min+unit_type)
    }


@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info(f'Request body: {body}')

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    location = event.message.text
    data = get_weather(base_url, option, location)
    reply_text = f"Location: {data['location']}\n"
    reply_text += f"Weather: {data['weather']}\n"
    reply_text += f"Max Temp: {data['temp_max']}\n"
    reply_text += f"Min Temp: {data['temp_min']}\n"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
