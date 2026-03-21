import streamlit as st
import requests
import os
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkyPulse",
    page_icon="🌤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── API Keys ───────────────────────────────────────────────────────────────────
OWM_KEY    = os.environ.get("OPENWEATHER_API_KEY", "YOUR_OWM_KEY_HERE")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY",   "YOUR_CLAUDE_KEY_HERE")
BASE_URL   = "https://api.openweathermap.org/data/2.5"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

# Language → (display name, BCP-47 for SpeechRecognition/TTS, OWM code)
LANGUAGES = {
    "English":    ("en-US",  "en"),
    "Hindi":      ("hi-IN",  "hi"),
    "Gujarati":   ("gu-IN",  "gu"),
    "Marathi":    ("mr-IN",  "mr"),
    "Bengali":    ("bn-IN",  "bn"),
    "Tamil":      ("ta-IN",  "ta"),
    "Telugu":     ("te-IN",  "te"),
    "Urdu":       ("ur-PK",  "ur"),
    "Arabic":     ("ar-SA",  "ar"),
    "Chinese":    ("zh-CN",  "zh_cn"),
    "French":     ("fr-FR",  "fr"),
    "German":     ("de-DE",  "de"),
    "Spanish":    ("es-ES",  "es"),
    "Italian":    ("it-IT",  "it"),
    "Japanese":   ("ja-JP",  "ja"),
    "Korean":     ("ko-KR",  "ko"),
    "Portuguese": ("pt-BR",  "pt"),
    "Russian":    ("ru-RU",  "ru"),
    "Turkish":    ("tr-TR",  "tr"),
    "Dutch":      ("nl-NL",  "nl"),
    "Polish":     ("pl-PL",  "pl"),
    "Swedish":    ("sv-SE",  "sv"),
    "Ukrainian":  ("uk-UA",  "uk"),
    "Indonesian": ("id-ID",  "id"),
    "Thai":       ("th-TH",  "th"),
    "Vietnamese": ("vi-VN",  "vi"),
}

OWM_ICONS = {
    "01d":"☀️","01n":"🌙","02d":"⛅","02n":"🌥","03d":"☁️","03n":"☁️",
    "04d":"☁️","04n":"☁️","09d":"🌧","09n":"🌧","10d":"🌦","10n":"🌧",
    "11d":"⛈","11n":"⛈","13d":"❄️","13n":"❄️","50d":"🌫","50n":"🌫",
}
AQI_INFO = {
    1:("Good","🟢","#4ade80"),
    2:("Fair","🔵","#38bdf8"),
    3:("Moderate","🟡","#facc15"),
    4:("Poor","🟠","#fb923c"),
    5:("Very Poor","🔴","#f87171"),
}

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "city": "",
    "weather_data": None,
    "chat_history": [],
    "last_chat_q": "",
    "tts_text": "",
    "lang": "English",
    "units": "metric",
    "pending_city": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────
def owm_icon(code): return OWM_ICONS.get(code, "🌡")

def wind_dir(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / (360 / len(dirs))) % len(dirs)]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(city, units, owm_lang):
    params = {"q": city, "appid": OWM_KEY, "units": units, "lang": owm_lang}
    r = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
    if r.status_code == 404: return None, f"City '{city}' not found."
    if r.status_code == 401: return None, "Invalid OpenWeather API key."
    r.raise_for_status()
    cur = r.json()
    lat, lon = cur["coord"]["lat"], cur["coord"]["lon"]

    fr = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
    fr.raise_for_status()
    fraw = fr.json()

    aqr = requests.get(f"{BASE_URL}/air_pollution",
                       params={"lat": lat, "lon": lon, "appid": OWM_KEY}, timeout=10)
    aqd = aqr.json() if aqr.status_code == 200 else None

    daily = {}
    for item in fraw["list"]:
        ds, ts = item["dt_txt"].split(" ")
        if ds not in daily and ts == "12:00:00": daily[ds] = item
    if len(daily) < 5:
        daily = {}
        for item in fraw["list"]:
            ds = item["dt_txt"].split(" ")[0]
            if ds not in daily: daily[ds] = item

    forecast = []
    for ds, item in list(daily.items())[:5]:
        dt = datetime.strptime(ds, "%Y-%m-%d")
        forecast.append({
            "day": dt.strftime("%a"),
            "temp_max": round(item["main"]["temp_max"]),
            "temp_min": round(item["main"]["temp_min"]),
            "description": item["weather"][0]["description"].title(),
            "icon": item["weather"][0]["icon"],
            "pop": round(item.get("pop", 0) * 100),
        })

    hourly = [{"time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
               "temp": round(item["main"]["temp"]),
               "icon": item["weather"][0]["icon"],
               "pop":  round(item.get("pop", 0) * 100)}
              for item in fraw["list"][:8]]

    aqi_val = aqi_lbl = aqi_col = None
    if aqd and aqd.get("list"):
        av = aqd["list"][0]["main"]["aqi"]
        aqi_val = av
        aqi_lbl, _, aqi_col = AQI_INFO.get(av, ("Unknown","⚪","#fff"))

    sym   = "°C" if units == "metric" else "°F"
    speed = "m/s" if units == "metric" else "mph"

    return {
        "city": cur["name"], "country": cur["sys"]["country"],
        "lat": lat, "lon": lon,
        "temp": round(cur["main"]["temp"]),
        "feels_like": round(cur["main"]["feels_like"]),
        "temp_min": round(cur["main"]["temp_min"]),
        "temp_max": round(cur["main"]["temp_max"]),
        "humidity": cur["main"]["humidity"],
        "pressure": cur["main"]["pressure"],
        "visibility": round(cur.get("visibility", 0) / 1000, 1),
        "wind_speed": round(cur["wind"]["speed"]),
        "wind_dir": wind_dir(cur["wind"].get("deg", 0)),
        "description": cur["weather"][0]["description"].title(),
        "icon": cur["weather"][0]["icon"],
        "clouds": cur["clouds"]["all"],
        "sunrise": datetime.fromtimestamp(cur["sys"]["sunrise"]).strftime("%H:%M"),
        "sunset":  datetime.fromtimestamp(cur["sys"]["sunset"]).strftime("%H:%M"),
        "sym": sym, "speed": speed,
        "aqi": aqi_val, "aqi_label": aqi_lbl, "aqi_color": aqi_col,
        "forecast": forecast, "hourly": hourly,
    }, None


def ask_claude(messages_history, weather_ctx):
    """Call Claude with full chat history + weather context."""
    if CLAUDE_KEY == "YOUR_CLAUDE_KEY_HERE":
        return "Please add your ANTHROPIC_API_KEY to Streamlit secrets to enable AI chat."
    system = (
        "You are SkyBot, a warm and conversational AI weather assistant built into SkyPulse. "
        "You sound like a knowledgeable friend — not a robot. Use natural, friendly language. "
        "Give practical advice: should someone carry an umbrella? Is it good for outdoor sports? "
        "Is it safe to travel? What to wear? Keep answers concise (2-4 sentences) unless more detail is asked. "
        "If you don't know something, say so honestly.\n\n"
        f"Current weather data for context:\n{weather_ctx}"
    )
    try:
        resp = requests.post(CLAUDE_URL,
            headers={"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 400,
                  "system": system, "messages": messages_history},
            timeout=20)
        return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"Oops, couldn't reach Claude right now: {e}"


def build_weather_context(d, lang_name, units):
    sym = "°C" if units == "metric" else "°F"
    spd = "m/s" if units == "metric" else "mph"
    aqi_info = ""
    if d.get("aqi"):
        lbl, _, _ = AQI_INFO.get(d["aqi"], ("Unknown","",""))
        aqi_info = f"\nAir Quality: {lbl} ({d['aqi']}/5)"
    forecast_txt = ""
    for f in d.get("forecast", []):
        forecast_txt += f"\n  {f['day']}: {f['description']}, High {f['temp_max']}{sym}, Low {f['temp_min']}{sym}, Rain chance {f['pop']}%"
    return (
        f"Location: {d['city']}, {d['country']}\n"
        f"Temperature: {d['temp']}{sym} (feels like {d['feels_like']}{sym})\n"
        f"Today High/Low: {d['temp_max']}{sym} / {d['temp_min']}{sym}\n"
        f"Condition: {d['description']}\n"
        f"Humidity: {d['humidity']}%\n"
        f"Wind: {d['wind_speed']} {spd} {d['wind_dir']}\n"
        f"Visibility: {d['visibility']} km\n"
        f"Cloud cover: {d['clouds']}%\n"
        f"Pressure: {d['pressure']} hPa\n"
        f"Sunrise: {d['sunrise']}, Sunset: {d['sunset']}"
        f"{aqi_info}\n"
        f"5-Day Forecast:{forecast_txt}\n"
        f"User's selected language: {lang_name}"
    )


def build_tts_script(d, units, lang_name):
    """Build a natural, human-sounding weather narration for TTS."""
    sym_word = "degrees Celsius" if units == "metric" else "degrees Fahrenheit"
    spd_word = "metres per second" if units == "metric" else "miles per hour"
    aqi_note = ""
    if d.get("aqi"):
        lbl, _, _ = AQI_INFO.get(d["aqi"], ("Unknown","",""))
        advice = {
            "Good": "Air quality is great — perfect for outdoor activities.",
            "Fair": "Air quality is fair, generally safe to be outdoors.",
            "Moderate": "Air quality is moderate — sensitive groups should limit prolonged outdoor exposure.",
            "Poor": "Air quality is poor today. Try to limit time outside if you can.",
            "Very Poor": "Air quality is very poor right now. It's best to stay indoors if possible.",
        }
        aqi_note = advice.get(lbl, "")

    rain_note = ""
    for f in d.get("forecast", [])[:2]:
        if f["pop"] > 40:
            rain_note = f"There's a {f['pop']} percent chance of rain {f['day'].lower() if f['day'] != datetime.now().strftime('%a') else 'today'}, so you might want to keep an umbrella handy."
            break

    wind_note = ""
    ws = d["wind_speed"]
    if ws > 10 and units == "metric":
        wind_note = "It's quite windy today, so dress accordingly."
    elif ws > 20 and units == "imperial":
        wind_note = "It's quite windy today, so dress accordingly."

    script = (
        f"Here's the weather in {d['city']}, {d['country']}. "
        f"Right now it's {d['temp']} {sym_word}, but it feels like {d['feels_like']} {sym_word} due to {d['description'].lower()}. "
        f"Today's high will be {d['temp_max']} and the low will be {d['temp_min']} {sym_word}. "
        f"Humidity is at {d['humidity']} percent. "
    )
    if wind_note: script += wind_note + " "
    if rain_note: script += rain_note + " "
    if aqi_note:  script += aqi_note  + " "
    script += f"Sunrise is at {d['sunrise']} and sunset at {d['sunset']}. Have a great day!"
    return script


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

*, html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; box-sizing: border-box; }

.stApp {
  background: #060b14;
  background-image:
    radial-gradient(ellipse 80% 50% at 20% -10%, rgba(56,189,248,.13) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 110%, rgba(129,140,248,.10) 0%, transparent 60%);
  min-height: 100vh;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden !important; }
[data-testid="stSidebar"] { background: #0d1526 !important; border-right: 1px solid rgba(255,255,255,0.07) !important; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stTextInput"] input {
  background: rgba(255,255,255,0.07) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 12px !important;
  color: #e2e8f0 !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #38bdf8 !important;
  box-shadow: 0 0 0 3px rgba(56,189,248,.12) !important;
}
[data-testid="stSelectbox"] > div > div {
  background: rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  color: #e2e8f0 !important;
}
.stButton > button {
  background: #38bdf8 !important; color: #060b14 !important;
  border: none !important; border-radius: 12px !important;
  font-weight: 700 !important; padding: 10px 24px !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
[data-testid="metric-container"] {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 16px !important; padding: 16px !important;
  transition: border-color .2s, transform .2s !important;
}
[data-testid="metric-container"]:hover { border-color: #38bdf8 !important; transform: translateY(-2px) !important; }
[data-testid="stMetricValue"]  { font-family: 'Space Mono', monospace !important; color: #e2e8f0 !important; }
[data-testid="stMetricLabel"]  { color: #64748b !important; }
.stProgress > div > div { background: linear-gradient(90deg,#38bdf8,#818cf8) !important; border-radius: 99px !important; }
.stProgress > div        { background: rgba(255,255,255,0.05) !important; border-radius: 99px !important; }
hr { border-color: rgba(255,255,255,0.07) !important; }
[data-testid="stExpander"] { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 16px !important; }
.stRadio > div { flex-direction: row !important; gap: 12px; }
.stRadio label { color: #e2e8f0 !important; }
h1,h2,h3,h4,h5,h6,p,label,div { color: #e2e8f0; }

/* ── TOP SEARCH BAR ── */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 9000;
  background: rgba(6,11,20,0.92); backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(56,189,248,0.12);
  padding: 10px 24px;
  display: flex; align-items: center; gap: 12px;
}
.topbar-logo { font-size: 1.3rem; font-weight: 800; color: #38bdf8 !important;
  font-family: 'Outfit', sans-serif; white-space: nowrap; flex-shrink: 0; }
.search-pill {
  flex: 1; display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.11);
  border-radius: 50px; padding: 6px 8px 6px 18px;
  transition: border-color .2s;
  max-width: 520px;
}
.search-pill:focus-within { border-color: rgba(56,189,248,0.5); }
.search-pill input {
  flex: 1; background: transparent; border: none; outline: none;
  color: #e2e8f0; font-family: 'Outfit', sans-serif;
  font-size: 0.95rem; min-width: 0;
}
.search-pill input::placeholder { color: #475569; }
.icon-btn {
  background: transparent; border: none; cursor: pointer;
  color: #64748b; font-size: 1.05rem; padding: 4px 6px;
  border-radius: 50%; transition: color .15s, background .15s;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.icon-btn:hover { color: #38bdf8; background: rgba(56,189,248,.1); }
.icon-btn.recording { color: #ef4444 !important; background: rgba(239,68,68,.12) !important;
  animation: rec-pulse 1s ease-in-out infinite; }
@keyframes rec-pulse {
  0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,.35); }
  50%      { box-shadow: 0 0 0 7px rgba(239,68,68,0); }
}
.search-go-btn {
  background: #38bdf8; color: #060b14; border: none;
  border-radius: 50px; padding: 6px 18px;
  font-weight: 700; font-size: .85rem; cursor: pointer;
  font-family: 'Outfit', sans-serif; flex-shrink: 0;
  transition: opacity .15s;
}
.search-go-btn:hover { opacity: .82; }
.topbar-lang {
  flex-shrink: 0; font-size: .78rem; color: #64748b;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; padding: 4px 10px; cursor: pointer; white-space: nowrap;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #ef4444; animation: rec-pulse 1s infinite;
  display: inline-block; margin-right: 4px;
}

/* ── MAIN CONTENT ── */
.main-wrap { padding-top: 72px; }

/* ── HERO CARD ── */
.hero-card {
  background: linear-gradient(135deg, rgba(56,189,248,.1) 0%, rgba(129,140,248,.07) 100%);
  border: 1px solid rgba(56,189,248,.18); border-radius: 24px;
  padding: 32px; margin-bottom: 24px; position: relative; overflow: hidden;
}
.hero-temp {
  font-size: 5.5rem; font-weight: 700; line-height: 1;
  font-family: 'Space Mono', monospace;
  background: linear-gradient(135deg, #fff 30%, #38bdf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-city  { font-size: 1.7rem; font-weight: 700; color: #e2e8f0 !important; }
.hero-sub   { font-size: .9rem; color: #64748b !important; margin-top: 3px; }
.hero-feels { font-size: .9rem; color: #7dd3fc !important; margin-top: 3px; }
.badge { display: inline-block; padding: 4px 14px; border-radius: 50px; font-size: .78rem; font-weight: 600; margin: 2px; }
.badge-sky    { background: rgba(56,189,248,.13); color: #38bdf8; border: 1px solid rgba(56,189,248,.22); }
.badge-indigo { background: rgba(129,140,248,.13); color: #818cf8; border: 1px solid rgba(129,140,248,.22); }

/* ── SPEAK BUTTON ── */
.speak-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: rgba(56,189,248,.08); color: #38bdf8;
  border: 1px solid rgba(56,189,248,.22); border-radius: 50px;
  padding: 8px 20px; font-size: .88rem; font-weight: 600;
  font-family: 'Outfit', sans-serif; cursor: pointer;
  transition: background .18s, transform .18s; margin-top: 10px;
}
.speak-btn:hover { background: rgba(56,189,248,.18); transform: translateY(-1px); }
.speak-btn.speaking { background: rgba(129,140,248,.15); color: #818cf8;
  border-color: rgba(129,140,248,.3); animation: speak-glow 1.4s ease-in-out infinite; }
@keyframes speak-glow {
  0%,100% { box-shadow: 0 0 0 0 rgba(129,140,248,.3); }
  50%      { box-shadow: 0 0 12px 4px rgba(129,140,248,.15); }
}

/* ── HOURLY ── */
.hourly-row { display: flex; gap: 10px; overflow-x: auto; padding: 6px 0;
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.08) transparent; }
.hour-card { flex: 0 0 76px; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07); border-radius: 12px;
  padding: 10px 6px; text-align: center; min-width: 76px; transition: border-color .15s; }
.hour-card:hover { border-color: #38bdf8; }
.htime { font-size: .68rem; color: #64748b; font-weight: 600; }
.hicon { font-size: 1.35rem; margin: 4px 0; }
.htemp { font-size: .88rem; font-weight: 700; color: #e2e8f0; }
.hpop  { font-size: .65rem; color: #7dd3fc; margin-top: 2px; }

/* ── FORECAST ROWS ── */
.fc-row { display: flex; align-items: center; gap: 14px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px; padding: 13px 18px; margin-bottom: 9px; transition: border-color .15s; }
.fc-row:hover { border-color: #38bdf8; }
.fc-day  { width: 40px; font-weight: 600; font-size: .92rem; color: #e2e8f0; }
.fc-icon { font-size: 1.45rem; }
.fc-desc { flex: 1; font-size: .85rem; color: #64748b; }
.fc-pop  { font-size: .78rem; color: #7dd3fc; min-width: 42px; text-align: right; }
.fc-temp { font-size: .9rem; font-weight: 600; color: #e2e8f0; min-width: 88px; text-align: right; }
.fc-lo   { color: #64748b; font-weight: 400; }

/* ── SECTION HEADER ── */
.sec-hdr { font-size: .7rem; text-transform: uppercase; letter-spacing: .12em;
  color: #475569; font-weight: 700; margin: 18px 0 10px; }

/* ── CHAT FAB ── */
.chat-fab {
  position: fixed; bottom: 26px; right: 26px; z-index: 8000;
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8, #818cf8);
  border: none; cursor: pointer; font-size: 1.4rem;
  box-shadow: 0 6px 20px rgba(56,189,248,.35);
  transition: transform .2s, box-shadow .2s;
}
.chat-fab:hover { transform: scale(1.1); box-shadow: 0 10px 28px rgba(56,189,248,.5); }

/* ── CHAT PANEL ── */
.chat-panel {
  position: fixed; bottom: 94px; right: 26px; z-index: 7999;
  width: 360px; max-height: 520px;
  background: #0c1422; border: 1px solid rgba(56,189,248,.18); border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,.65);
  display: flex; flex-direction: column; overflow: hidden;
}
.chat-head {
  padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.06);
  background: linear-gradient(135deg, rgba(56,189,248,.1), rgba(129,140,248,.07));
  display: flex; align-items: center; justify-content: space-between;
}
.chat-head-title { font-weight: 700; font-size: .94rem; color: #e2e8f0 !important; }
.chat-head-close { background: none; border: none; color: #475569;
  cursor: pointer; font-size: 1rem; padding: 0; }
.chat-messages { flex: 1; overflow-y: auto; padding: 14px;
  display: flex; flex-direction: column; gap: 9px;
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.07) transparent; }
.cmsg-u { align-self: flex-end; background: rgba(56,189,248,.13);
  border: 1px solid rgba(56,189,248,.2); border-radius: 16px 16px 4px 16px;
  padding: 9px 14px; font-size: .85rem; color: #e2e8f0; max-width: 88%; line-height: 1.5; }
.cmsg-a { align-self: flex-start; background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 16px 16px 16px 4px;
  padding: 9px 14px; font-size: .85rem; color: #e2e8f0; max-width: 88%; line-height: 1.5; }
.chat-foot { padding: 10px 12px; border-top: 1px solid rgba(255,255,255,0.06);
  display: flex; gap: 7px; align-items: center; }
.chat-input {
  flex: 1; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.09);
  border-radius: 12px; padding: 8px 12px; color: #e2e8f0;
  font-family: 'Outfit', sans-serif; font-size: .86rem; outline: none; min-width: 0;
}
.chat-input:focus { border-color: rgba(56,189,248,.4); }
.chat-mic-btn { background: rgba(56,189,248,.08); color: #64748b; border: 1px solid rgba(255,255,255,.08);
  border-radius: 10px; padding: 8px 10px; cursor: pointer; font-size: .9rem;
  transition: all .15s; }
.chat-mic-btn:hover { color: #38bdf8; background: rgba(56,189,248,.15); }
.chat-mic-btn.recording { color: #ef4444; background: rgba(239,68,68,.12);
  border-color: rgba(239,68,68,.3); animation: rec-pulse 1s infinite; }
.chat-send { background: #38bdf8; color: #060b14; border: none; border-radius: 10px;
  padding: 8px 14px; cursor: pointer; font-weight: 700; font-size: .85rem;
  font-family: 'Outfit', sans-serif; flex-shrink: 0; }
.chat-send:hover { opacity: .85; }
.typing-dot { display: inline-block; animation: dot-bounce .9s infinite; }
.typing-dot:nth-child(2) { animation-delay: .15s; }
.typing-dot:nth-child(3) { animation-delay: .30s; }
@keyframes dot-bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }
</style>
""", unsafe_allow_html=True)


# ── Sidebar: settings ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")
    lang_choice = st.selectbox("🌐 Language", list(LANGUAGES.keys()),
                               index=list(LANGUAGES.keys()).index(st.session_state.lang))
    st.session_state.lang = lang_choice
    unit_choice = st.radio("🌡 Units", ["°C Metric", "°F Imperial"], index=0 if st.session_state.units == "metric" else 1)
    st.session_state.units = "metric" if "°C" in unit_choice else "imperial"
    st.markdown("---")
    st.markdown("""<div style='font-size:.78rem;color:#475569;line-height:2'>
    <b style='color:#38bdf8'>How to use</b><br>
    🔍 Type city in top bar → Enter<br>
    🎤 Click mic → speak city name<br>
    🔊 Click Speak to hear weather<br>
    🤖 Click bot icon → chat away
    </div>""", unsafe_allow_html=True)

bcp47, owm_lang = LANGUAGES[st.session_state.lang]
units = st.session_state.units


# ── Chat question handler (server side) ───────────────────────────────────────
chat_q_raw = st.text_input("__chatq__", value="", key="chatq_bridge",
                           label_visibility="collapsed")
if chat_q_raw and chat_q_raw != st.session_state.last_chat_q:
    st.session_state.last_chat_q = chat_q_raw
    # Build API messages array from history
    api_msgs = []
    for m in st.session_state.chat_history:
        api_msgs.append({"role": m["role"], "content": m["text"]})
    api_msgs.append({"role": "user", "content": chat_q_raw})
    ctx = build_weather_context(st.session_state.weather_data, st.session_state.lang, units) \
          if st.session_state.weather_data else "No weather data loaded yet."
    answer = ask_claude(api_msgs, ctx)
    st.session_state.chat_history.append({"role": "user",      "text": chat_q_raw})
    st.session_state.chat_history.append({"role": "assistant", "text": answer})

# ── City search handler (server side) ─────────────────────────────────────────
city_raw = st.text_input("__city__", value=st.session_state.city,
                         key="city_bridge", label_visibility="collapsed",
                         placeholder="Enter city…")
if city_raw and city_raw != st.session_state.city:
    st.session_state.city = city_raw
    st.rerun()


# ── TOP BAR (HTML — purely visual; JS submits via the hidden Streamlit inputs) ─
bcp47_js = bcp47
lang_label = st.session_state.lang
cur_city   = st.session_state.city

# Build chat history JSON for JS
import json as _json
chat_js = _json.dumps([{"r": m["role"][0], "t": m["text"]}
                       for m in st.session_state.chat_history[-30:]])

# TTS script (built after weather fetch, placeholder before)
tts_script = st.session_state.get("tts_script", "")

st.markdown(f"""
<!-- ═══════════════ TOP BAR ═══════════════ -->
<div class="topbar" id="topbar">
  <span class="topbar-logo">🌤 SkyPulse</span>

  <div class="search-pill" id="search-pill">
    <input id="search-input" type="text"
      placeholder="Search city or say it aloud…"
      value="{cur_city}"
      autocomplete="off"
      onkeydown="if(event.key==='Enter'){{event.preventDefault();doSearch();}}" />
    <button class="icon-btn" id="mic-btn" onclick="toggleVoiceSearch()" title="Voice search">🎤</button>
    <button class="search-go-btn" onclick="doSearch()">Search</button>
  </div>

  <button class="icon-btn" onclick="speakWeather()" id="speak-btn"
    title="Read weather aloud" style="font-size:1.2rem;width:38px;height:38px">🔊</button>

  <span class="topbar-lang" onclick="document.querySelector('[data-testid=stSidebar]') && window.parent.document.querySelector('[data-testid=stSidebarNavButton]') && window.parent.document.querySelector('[data-testid=stSidebarNavButton]').click()">
    {lang_label} ⚙️
  </span>
</div>

<div id="voice-status" style="display:none;position:fixed;top:60px;left:50%;transform:translateX(-50%);
  background:rgba(239,68,68,.9);color:#fff;padding:6px 18px;border-radius:50px;font-size:.82rem;
  font-weight:600;z-index:9001;backdrop-filter:blur(8px)">
  <span class="status-dot"></span><span id="voice-status-text">Listening…</span>
</div>
""", unsafe_allow_html=True)


# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

if not st.session_state.city:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px'>
      <div style='font-size:5rem;margin-bottom:16px'>🌍</div>
      <h2 style='color:#e2e8f0;font-size:1.6rem;margin-bottom:10px'>Welcome to SkyPulse</h2>
      <p style='color:#64748b;font-size:1rem'>Type any city in the search bar, or click the 🎤 mic to speak</p>
      <div style='margin-top:28px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap'>
        <span style='background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.18);
          border-radius:50px;padding:7px 18px;font-size:.84rem;color:#7dd3fc'>🎤 Voice search in 25 languages</span>
        <span style='background:rgba(129,140,248,.08);border:1px solid rgba(129,140,248,.18);
          border-radius:50px;padding:7px 18px;font-size:.84rem;color:#a5b4fc'>🔊 Natural voice weather report</span>
        <span style='background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.18);
          border-radius:50px;padding:7px 18px;font-size:.84rem;color:#86efac'>🤖 AI chatbot — should I go out today?</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    with st.spinner(f"Loading weather for **{st.session_state.city}**…"):
        try:
            data, err = fetch_weather(st.session_state.city.strip(), units, owm_lang)
        except Exception as e:
            st.error(f"❌ Network error: {e}"); st.stop()

    if err:
        st.error(f"❌ {err}")
    else:
        st.session_state.weather_data = data
        d = data
        sym = d["sym"]
        spd = d["speed"]

        tts_script = build_tts_script(d, units, st.session_state.lang)
        st.session_state.tts_script = tts_script

        # ── Hero ──────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="hero-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
              <div class="hero-city">{owm_icon(d['icon'])} {d['city']}, {d['country']}</div>
              <div class="hero-sub">{d['lat']:.2f}°, {d['lon']:.2f}°</div>
            </div>
            <div style="text-align:right">
              <div>
                <span class="badge badge-sky">{d['description']}</span>
                <span class="badge badge-indigo">H:{d['temp_max']}{sym} · L:{d['temp_min']}{sym}</span>
              </div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:18px;margin-top:18px;flex-wrap:wrap">
            <div style="font-size:4.5rem;filter:drop-shadow(0 4px 14px rgba(56,189,248,.4))">{owm_icon(d['icon'])}</div>
            <div>
              <div class="hero-temp">{d['temp']}{sym}</div>
              <div class="hero-feels">Feels like {d['feels_like']}{sym} · {d['humidity']}% humidity</div>
            </div>
          </div>
          <button class="speak-btn" id="hero-speak-btn" onclick="speakWeather()">
            🔊 &nbsp;Hear weather report
          </button>
        </div>
        """, unsafe_allow_html=True)

        # ── Stats grid ────────────────────────────────────────────────────────
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("💧 Humidity",   f"{d['humidity']}%")
        c2.metric("💨 Wind",       f"{d['wind_speed']} {spd}", d['wind_dir'])
        c3.metric("🌡 Pressure",   f"{d['pressure']} hPa")
        c4.metric("👁 Visibility", f"{d['visibility']} km")
        c5.metric("☁️ Cloud",      f"{d['clouds']}%")
        if d['aqi']:
            lbl,emj,_ = AQI_INFO.get(d['aqi'],("?","⚪","#fff"))
            c6.metric("🌿 AQI", f"{emj} {lbl}", f"{d['aqi']}/5")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Sunrise + AQI ─────────────────────────────────────────────────────
        cs, ca = st.columns(2)
        with cs:
            st.markdown('<div class="sec-hdr">🌅 Sunrise &amp; Sunset</div>', unsafe_allow_html=True)
            s1,s2 = st.columns(2)
            s1.metric("🌅 Sunrise", d['sunrise'])
            s2.metric("🌇 Sunset",  d['sunset'])
        with ca:
            if d['aqi']:
                st.markdown('<div class="sec-hdr">🌿 Air Quality</div>', unsafe_allow_html=True)
                lbl,emj,col = AQI_INFO.get(d['aqi'],("?","⚪","#fff"))
                st.markdown(f"<div style='font-size:1rem;font-weight:600;margin-bottom:8px'>{emj} <span style='color:{col}'>{lbl}</span></div>",
                            unsafe_allow_html=True)
                st.progress(d['aqi'] / 5)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Hourly ────────────────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr">⏱ Next 24 Hours</div>', unsafe_allow_html=True)
        hh = '<div class="hourly-row">'
        for h in d['hourly']:
            pp = f'<div class="hpop">💧{h["pop"]}%</div>' if h['pop'] else ''
            hh += (f'<div class="hour-card">'
                   f'<div class="htime">{h["time"]}</div>'
                   f'<div class="hicon">{owm_icon(h["icon"])}</div>'
                   f'<div class="htemp">{h["temp"]}{sym}</div>{pp}</div>')
        hh += '</div>'
        st.markdown(hh, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # ── 5-Day ────────────────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr">📅 5-Day Forecast</div>', unsafe_allow_html=True)
        fh = ""
        for f in d['forecast']:
            pt = f"💧{f['pop']}%" if f['pop'] else ""
            fh += (f'<div class="fc-row">'
                   f'<div class="fc-day">{f["day"]}</div>'
                   f'<div class="fc-icon">{owm_icon(f["icon"])}</div>'
                   f'<div class="fc-desc">{f["description"]}</div>'
                   f'<div class="fc-pop">{pt}</div>'
                   f'<div class="fc-temp">{f["temp_max"]}{sym} '
                   f'<span class="fc-lo">/ {f["temp_min"]}{sym}</span></div></div>')
        st.markdown(fh, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Map ───────────────────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr">🗺 Location Map</div>', unsafe_allow_html=True)
        map_url = (f"https://www.openstreetmap.org/export/embed.html"
                   f"?bbox={d['lon']-1}%2C{d['lat']-1}%2C{d['lon']+1}%2C{d['lat']+1}"
                   f"&layer=mapnik&marker={d['lat']}%2C{d['lon']}")
        st.markdown(f'<div style="border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.07)">'
                    f'<iframe src="{map_url}" width="100%" height="240" frameborder="0" style="display:block"></iframe>'
                    f'</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("🔬 Raw JSON Data"):
            st.json({k:v for k,v in d.items() if k not in ("forecast","hourly")})

st.markdown('</div>', unsafe_allow_html=True)


# ── CHAT PANEL HTML ───────────────────────────────────────────────────────────
chat_msgs_html = ""
if st.session_state.chat_history:
    for m in st.session_state.chat_history[-40:]:
        cls = "cmsg-u" if m["role"] == "user" else "cmsg-a"
        safe_text = m["text"].replace("<","&lt;").replace(">","&gt;").replace('"', '&quot;')
        chat_msgs_html += f'<div class="{cls}">{safe_text}</div>'

tts_safe = tts_script.replace("'", "\\'").replace("\n", " ").replace('"', '\\"') if tts_script else ""

st.markdown(f"""
<!-- ═══════════════ CHAT PANEL ═══════════════ -->
<div id="chat-panel" class="chat-panel" style="display:none">
  <div class="chat-head">
    <span class="chat-head-title">🤖 SkyBot · AI Weather Chat</span>
    <button class="chat-head-close" onclick="closeChat()">✕</button>
  </div>
  <div class="chat-messages" id="chat-msgs">
    {'<div class="cmsg-a">👋 Hey! I\'m SkyBot. Ask me anything — should you go out today? What to wear? Is it safe to travel? I\'m here to help!</div>' if not st.session_state.chat_history else chat_msgs_html}
  </div>
  <div class="chat-foot">
    <button class="chat-mic-btn" id="chat-mic-btn" onclick="toggleChatMic()" title="Voice input">🎤</button>
    <input id="chat-input" class="chat-input" placeholder="Ask about today's weather…" />
    <button class="chat-send" onclick="sendChatMsg()">Send</button>
  </div>
</div>

<button class="chat-fab" id="chat-fab" onclick="toggleChat()">🤖</button>

<!-- ═══════════════ ALL JAVASCRIPT ═══════════════ -->
<script>
// ════════════════════════════════════════════════
// UTILITIES
// ════════════════════════════════════════════════
var TTS_SCRIPT  = "{tts_safe}";
var BCP47_LANG  = "{bcp47_js}";
var chatOpen    = false;
var isSpeaking  = false;
var searchRec   = null;
var searchRecOn = false;
var chatRec     = null;
var chatRecOn   = false;

function escapeHtml(t) {{
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

// ════════════════════════════════════════════════
// STREAMLIT BRIDGE — write into hidden text inputs
// produced by st.text_input inside the Streamlit app
// ════════════════════════════════════════════════
function setStreamlitInput(placeholder, value) {{
  // Streamlit renders text inputs as <input> inside shadow-like iframe contexts.
  // We search all inputs in the SAME document (no cross-frame needed here
  // because Streamlit embeds the markdown HTML in the same document).
  var inputs = document.querySelectorAll('input[type="text"]');
  for (var i = 0; i < inputs.length; i++) {{
    var inp = inputs[i];
    if (inp.placeholder === placeholder || inp.getAttribute('aria-label') === placeholder) {{
      var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(inp, value);
      inp.dispatchEvent(new Event('input', {{bubbles: true}}));
      inp.dispatchEvent(new Event('change', {{bubbles: true}}));
      return true;
    }}
  }}
  // Fallback: try parent frame
  try {{
    var pinputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var j = 0; j < pinputs.length; j++) {{
      if (pinputs[j].placeholder === placeholder) {{
        var s2 = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;
        s2.call(pinputs[j], value);
        pinputs[j].dispatchEvent(new Event('input',{{bubbles:true}}));
        return true;
      }}
    }}
  }} catch(e) {{}}
  return false;
}}

// ════════════════════════════════════════════════
// SEARCH
// ════════════════════════════════════════════════
function doSearch() {{
  var v = document.getElementById('search-input').value.trim();
  if (!v) return;
  setStreamlitInput('Enter city…', v);
}}

// ════════════════════════════════════════════════
// VOICE SEARCH  (SpeechRecognition)
// ════════════════════════════════════════════════
function hasSpeechRecognition() {{
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}}

function showVoiceStatus(text) {{
  var el = document.getElementById('voice-status');
  var tx = document.getElementById('voice-status-text');
  if (el && tx) {{ tx.textContent = text; el.style.display = 'block'; }}
}}
function hideVoiceStatus() {{
  var el = document.getElementById('voice-status'); if (el) el.style.display = 'none';
}}

function toggleVoiceSearch() {{
  if (!hasSpeechRecognition()) {{
    alert('Voice search works in Chrome and Edge browsers. Please type the city name instead.');
    return;
  }}
  if (searchRecOn) {{ stopSearchRec(); return; }}
  startSearchRec();
}}

function startSearchRec() {{
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  searchRec = new SR();
  searchRec.lang            = BCP47_LANG;
  searchRec.interimResults  = true;
  searchRec.maxAlternatives = 1;
  searchRecOn = true;
  document.getElementById('mic-btn').classList.add('recording');
  showVoiceStatus('Listening in ' + BCP47_LANG + '…');

  searchRec.onresult = function(e) {{
    var transcript = '';
    for (var i = e.resultIndex; i < e.results.length; i++) {{
      transcript += e.results[i][0].transcript;
    }}
    // Strip common prefixes in any language
    transcript = transcript
      .replace(/^(weather in|weather for|show me weather|show weather|check weather for)[  ]*/i, '')
      .trim();
    document.getElementById('search-input').value = transcript;
    if (e.results[e.results.length - 1].isFinal) {{
      showVoiceStatus('Got it: "' + transcript + '" — searching…');
      setTimeout(function() {{
        stopSearchRec();
        doSearch();
      }}, 600);
    }}
  }};
  searchRec.onerror = function(e) {{
    var msg = e.error === 'no-speech'   ? 'No speech detected. Try again.' :
              e.error === 'not-allowed' ? 'Microphone blocked. Please allow mic access.' :
              'Voice error: ' + e.error;
    showVoiceStatus(msg);
    setTimeout(hideVoiceStatus, 3000);
    stopSearchRec();
  }};
  searchRec.onend = function() {{ stopSearchRec(); }};
  searchRec.start();
}}

function stopSearchRec() {{
  searchRecOn = false;
  if (searchRec) {{ try {{ searchRec.stop(); }} catch(e) {{}} searchRec = null; }}
  document.getElementById('mic-btn').classList.remove('recording');
  setTimeout(hideVoiceStatus, 2000);
}}

// ════════════════════════════════════════════════
// TEXT-TO-SPEECH  — natural, non-robotic
// ════════════════════════════════════════════════
function speakWeather() {{
  if (!TTS_SCRIPT) {{
    alert('Search for a city first to get the weather report.');
    return;
  }}
  if (!window.speechSynthesis) {{
    alert('Text-to-speech is not supported in this browser.');
    return;
  }}
  if (isSpeaking) {{
    window.speechSynthesis.cancel();
    isSpeaking = false;
    setSpeakBtnState(false);
    return;
  }}

  var utt   = new SpeechSynthesisUtterance(TTS_SCRIPT);
  utt.lang  = BCP47_LANG;
  utt.rate  = 0.93;   // slightly slower than default = more natural
  utt.pitch = 1.02;   // very slightly warmer pitch

  // Pick the best available voice for the language
  var voices = window.speechSynthesis.getVoices();
  var preferred = null;
  // Prefer neural/enhanced voices
  var neural = voices.filter(function(v) {{
    return v.lang.startsWith(BCP47_LANG.split('-')[0]) &&
           (v.name.indexOf('Neural') > -1 || v.name.indexOf('Enhanced') > -1 ||
            v.name.indexOf('Premium') > -1 || v.name.indexOf('Natural') > -1);
  }});
  if (neural.length) {{ preferred = neural[0]; }}
  else {{
    var any = voices.filter(function(v) {{ return v.lang.startsWith(BCP47_LANG.split('-')[0]); }});
    if (any.length) preferred = any[0];
  }}
  if (preferred) utt.voice = preferred;

  utt.onstart = function() {{ isSpeaking = true;  setSpeakBtnState(true); }};
  utt.onend   = function() {{ isSpeaking = false; setSpeakBtnState(false); }};
  utt.onerror = function() {{ isSpeaking = false; setSpeakBtnState(false); }};

  window.speechSynthesis.cancel(); // cancel any prior
  window.speechSynthesis.speak(utt);
}}

function setSpeakBtnState(speaking) {{
  var btns = document.querySelectorAll('#speak-btn, #hero-speak-btn');
  btns.forEach(function(b) {{
    if (speaking) {{
      b.classList.add('speaking');
      b.innerHTML = '⏹ &nbsp;Stop reading';
    }} else {{
      b.classList.remove('speaking');
      b.innerHTML = b.id === 'speak-btn' ? '🔊' : '🔊 &nbsp;Hear weather report';
    }}
  }});
}}

// Voices may load async on some browsers
if (window.speechSynthesis) {{
  window.speechSynthesis.onvoiceschanged = function() {{ window.speechSynthesis.getVoices(); }};
}}

// ════════════════════════════════════════════════
// CHAT PANEL
// ════════════════════════════════════════════════
function toggleChat() {{
  chatOpen = !chatOpen;
  document.getElementById('chat-panel').style.display = chatOpen ? 'flex' : 'none';
  if (chatOpen) {{
    scrollMsgs();
    setTimeout(function() {{ document.getElementById('chat-input').focus(); }}, 120);
  }}
}}
function closeChat() {{
  chatOpen = false;
  document.getElementById('chat-panel').style.display = 'none';
}}

function scrollMsgs() {{
  var m = document.getElementById('chat-msgs'); if (m) m.scrollTop = m.scrollHeight;
}}

function addMsg(text, role) {{
  var m   = document.getElementById('chat-msgs'); if (!m) return null;
  var div = document.createElement('div');
  div.className = role === 'user' ? 'cmsg-u' : 'cmsg-a';
  div.textContent = text;
  m.appendChild(div); scrollMsgs();
  return div;
}}

function addTypingIndicator() {{
  var m   = document.getElementById('chat-msgs'); if (!m) return null;
  var div = document.createElement('div');
  div.className = 'cmsg-a'; div.id = 'typing-indicator';
  div.innerHTML = '<span class="typing-dot">●</span><span class="typing-dot">●</span><span class="typing-dot">●</span>';
  m.appendChild(div); scrollMsgs();
  return div;
}}

function sendChatMsg() {{
  var inp = document.getElementById('chat-input');
  var msg = inp.value.trim(); if (!msg) return;
  inp.value = '';
  addMsg(msg, 'user');
  addTypingIndicator();
  // Send to Streamlit
  setStreamlitInput('Ask about today\'s weather…', msg);
  // Poll for the typing indicator to be replaced (Streamlit reruns and redraws)
  // After rerun the whole page refreshes — typing indicator is cosmetic only
}}

// Enter to send
document.addEventListener('DOMContentLoaded', function() {{
  var ci = document.getElementById('chat-input');
  if (ci) ci.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') {{ e.preventDefault(); sendChatMsg(); }}
  }});
}});

// ── Chat voice input ──────────────────────────────────────────────────────────
function toggleChatMic() {{
  if (!hasSpeechRecognition()) {{
    alert('Voice input works in Chrome and Edge.');
    return;
  }}
  if (chatRecOn) {{ stopChatRec(); return; }}
  startChatRec();
}}

function startChatRec() {{
  var SR  = window.SpeechRecognition || window.webkitSpeechRecognition;
  chatRec = new SR();
  chatRec.lang           = BCP47_LANG;
  chatRec.interimResults = false;
  chatRecOn = true;
  document.getElementById('chat-mic-btn').classList.add('recording');

  chatRec.onresult = function(e) {{
    var t = e.results[0][0].transcript.trim();
    document.getElementById('chat-input').value = t;
    stopChatRec();
  }};
  chatRec.onerror = chatRec.onend = function() {{ stopChatRec(); }};
  chatRec.start();
}}

function stopChatRec() {{
  chatRecOn = false;
  if (chatRec) {{ try {{ chatRec.stop(); }} catch(e) {{}} chatRec = null; }}
  var b = document.getElementById('chat-mic-btn'); if (b) b.classList.remove('recording');
}}
</script>
""", unsafe_allow_html=True)
