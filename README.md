# SG Bus Telegram Bot

A Telegram bot for Singapore buses, built in Python on the [LTA DataMall](https://datamall.lta.gov.sg/) API.

## Features

- **`/bus <stop code>`**: live arrival times for the next three buses of every service at a stop, with crowding shown as 🟢 seats available / 🟡 standing / 🔴 limited standing.
- **`/nearby [1-10]`**: share your location and get the closest bus stops (default 5), ranked by Haversine distance across all of Singapore's bus stops.

The full bus stop list is loaded once at startup. LTA pages it in blocks of 500, so the bot pages through all of it and keeps it in memory for name lookups and nearest-stop search.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
python main.py
```

- `BOT_TOKEN`: from [@BotFather](https://t.me/BotFather)
- `LTA_KEY`: request an account key from LTA DataMall
