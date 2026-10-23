from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import requests
import math
import os
from datetime import datetime

# Keys are read from the environment (or a local .env file that is never committed)
load_dotenv()
TOKEN = os.environ['BOT_TOKEN']
LTA_KEY = os.environ['LTA_KEY']

ARRIVAL_URL = "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival"
STOPS_URL = "https://datamall2.mytransport.sg/ltaodataservice/BusStops"
HEADERS = {'AccountKey': LTA_KEY, 'accept': 'application/json'}

LOAD_ICONS = {'SEA': '🟢', 'SDA': '🟡', 'LSD': '🔴'}

def load_bus_stops():
    """Fetch every bus stop once. LTA only returns 500 records per call, so page through with $skip."""
    stops = {}
    skip = 0
    while True:
        response = requests.get(STOPS_URL, headers=HEADERS, params={'$skip': skip}, timeout=10)
        response.raise_for_status()
        page = response.json()['value']
        if not page:
            break
        for stop in page:
            stops[stop['BusStopCode']] = stop
        skip += 500
    return stops

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def format_next_bus(bus):
    """Turns one NextBus entry into e.g. '3 🟢', or None if there is no bus."""
    if not bus or not bus.get('EstimatedArrival'):
        return None
    arrival_time = datetime.fromisoformat(bus['EstimatedArrival'])
    current_time = datetime.now(arrival_time.tzinfo)
    minutes = int((arrival_time - current_time).total_seconds() / 60)
    next_time = "Arr" if minutes <= 0 else f"{minutes}"
    load = LOAD_ICONS.get(bus.get('Load'), '')
    return f"{next_time} {load}".strip()

def bus_arrival(bus_stop_code):
    stop = BUS_STOPS.get(bus_stop_code)
    if stop is None:
        return f"Bus stop {bus_stop_code} not found. Use a 5-digit code, e.g. /bus 83139"

    try:
        response = requests.get(ARRIVAL_URL, headers=HEADERS, params={'BusStopCode': bus_stop_code}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return "Couldn't reach LTA right now, please try again."

    data = response.json()
    result = f"<b><u>{stop['Description']}, {stop['RoadName']} ({bus_stop_code}):</u></b>\n\n\n"
    if not data['Services']:
        return result + "No buses are running at this stop right now."

    for i in data['Services']:
        times = [format_next_bus(i.get(key)) for key in ('NextBus', 'NextBus2', 'NextBus3')]
        times = [t for t in times if t]
        if not times:
            continue
        result += f"<b>{i['ServiceNo']}</b> : {', '.join(times)}\n\n"

    return result


async def bus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("/bus [bus stop code]")
        return
    stop_code = context.args[0]

    result = bus_arrival(stop_code)
    await update.message.reply_text(result, parse_mode='HTML')



async def request_loc(update: Update, context: ContextTypes.DEFAULT_TYPE):

    amount = 5
    if context.args:
        try:
            if 0 < int(context.args[0]) < 11:
                amount = int(context.args[0])
            else:
                await update.message.reply_text("Please enter within range 1-10")
                return
        except ValueError:
            await update.message.reply_text("Please enter a valid number (1-10)")
            return

    context.user_data['num_stops'] = amount
    contact_keyboard = [[KeyboardButton("Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(contact_keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Share your location to find nearby bus stops", reply_markup=reply_markup)

async def handle_loc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_loc = update.message.location
    num_stops = context.user_data.get('num_stops', 5)

    distances = []
    for stop in BUS_STOPS.values():
        distance = calculate_distance(user_loc.latitude, user_loc.longitude, stop['Latitude'], stop['Longitude'])
        distances.append((distance, stop))
    distances.sort(key=lambda x: x[0])

    out = f"<b><u>The {num_stops} nearest Bus Stops are:</u></b>\n\n\n"
    for distance, stop in distances[:num_stops]:
        out += f"{stop['Description']}, {stop['RoadName']} ({stop['BusStopCode']}) - {round(distance)}m\n\n"

    await update.message.reply_text(out, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a greeting when the command /start is issued."""
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n"
        "/bus [stop code] - live arrivals at a bus stop\n"
        "/nearby [1-10] - find the nearest bus stops to you"
    )

if __name__ == '__main__':
    print("Loading bus stops...")
    BUS_STOPS = load_bus_stops()
    print(f"Loaded {len(BUS_STOPS)} bus stops")

    # Build the application
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nearby", request_loc))
    app.add_handler(MessageHandler(filters.LOCATION, handle_loc))
    app.add_handler(CommandHandler("bus", bus_command))
    print("Bot is running...")
    # Start the bot
    app.run_polling()
