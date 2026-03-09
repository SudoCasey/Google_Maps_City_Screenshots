# Google Maps City Screenshots

This script reads a text file containing US cities, searches each city in Google Maps, and saves a `500x500` PNG screenshot for every city.

## 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 2. Create your city list

Put one city per line in a text file:

```text
New York, NY
Chicago, IL
Seattle, WA
```

Comments starting with `#` are ignored.

## 3. Run the script

```powershell
python .\google_maps_city_screenshots.py --input .\cities.txt --output .\screenshots
```

Optional flags:

- `--headless` runs without opening the browser window
- `--wait-seconds 5` waits longer before capturing each screenshot

## Notes

- Google may occasionally show consent or anti-bot prompts. The script tries to dismiss common consent dialogs, but Google Maps can still change over time.
- Screenshots are saved as `001_city_name.png`, `002_city_name.png`, and so on.
