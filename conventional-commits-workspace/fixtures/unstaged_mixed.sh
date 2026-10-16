#!/bin/bash
source "$(dirname "$0")/common.sh" "$1"
mkdir -p weatherbot
cat > weatherbot/main.py <<'P'
import argparse
from weatherbot.fetch import get_forecast


def main():
    p = argparse.ArgumentParser()
    p.add_argument("city")
    a = p.parse_args()
    print(get_forecast(a.city))
P
cat > weatherbot/fetch.py <<'P'
import os
import urllib.request
import json

API = "https://api.example-weather.com/v1/forecast"


def get_forecast(city):
    key = os.environ["WEATHER_API_KEY"]
    with urllib.request.urlopen(f"{API}?q={city}&key={key}") as r:
        return json.load(r)["summary"]
P
cat > README.md <<'P'
# weatherbot

Prints a forcast summary for a city. Set WEATHER_API_KEY first.
P
echo "__pycache__/" > .gitignore
git add -A; c 1 "feat: initial weatherbot cli"
git commit -q --allow-empty -m "fix(fetch): url-encode city names"
# working tree changes (nothing staged)
cat > weatherbot/main.py <<'P'
import argparse
import logging
from weatherbot.fetch import get_forecast


def main():
    p = argparse.ArgumentParser()
    p.add_argument("city")
    p.add_argument("-v", "--verbose", action="store_true", help="log HTTP requests")
    a = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.WARNING)
    print(get_forecast(a.city))
P
sed -i '' 's/^import json$/import json\nimport logging\n\nlog = logging.getLogger(__name__)/' weatherbot/fetch.py
sed -i '' 's/^    with urllib.request.urlopen/    log.debug("GET %s q=%s", API, city)\n    with urllib.request.urlopen/' weatherbot/fetch.py
sed -i '' 's/forcast/forecast/' README.md
echo "WEATHER_API_KEY=sk_live_9f8a7b6c5d4e3f2a1b0c" > .env
