import streamlit as st
import requests
import os
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkyPulse — Weather Forecast",
    page_icon="🌤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
API_KEY  = os.environ.get("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://api.openweathermap.org/data/2.5"
GEO_URL  = "http://api.openweathermap.org/geo/1.0"

LANGUAGES = {
    "en":"English",   "hi":"Hindi",      "ar":"Arabic",     "zh_cn":"Chinese",
    "fr":"French",    "de":"German",     "es":"Spanish",    "it":"Italian",
    "ja":"Japanese",  "ko":"Korean",     "pt":"Portuguese", "ru":"Russian",
    "tr":"Turkish",   "nl":"Dutch",      "pl":"Polish",     "sv":"Swedish",
    "uk":"Ukrainian", "id":"Indonesian", "th":"Thai",       "vi":"Vietnamese",
    "bn":"Bengali",   "gu":"Gujarati",   "ta":"Tamil",      "te":"Telugu",
    "mr":"Marathi",   "ur":"Urdu",
}

OWM_ICONS = {
    "01d":"☀️","01n":"🌙","02d":"⛅","02n":"🌥","03d":"☁️","03n":"☁️",
    "04d":"☁️","04n":"☁️","09d":"🌧","09n":"🌧","10d":"🌦","10n":"🌧",
    "11d":"⛈","11n":"⛈","13d":"❄️","13n":"❄️","50d":"🌫","50n":"🌫",
}

AQI_INFO = {
    1: ("Good",      "🟢", "#4ade80"),
    2: ("Fair",      "🔵", "#38bdf8"),
    3: ("Moderate",  "🟡", "#facc15"),
    4: ("Poor",      "🟠", "#fb923c"),
    5: ("Very Poor", "🔴", "#f87171"),
}

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}

/* Dark background */
.stApp {
    background: #060b14;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(56,189,248,.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(129,140,248,.10) 0%, transparent 60%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1526 !important;
    border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Main text */
h1,h2,h3,h4,h5,h6,p,label,div { color: #e2e8f0; }

/* Input */
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.09) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,.15) !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.09) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
}

/* Buttons */
.stButton > button {
    background: #38bdf8 !important;
    color: #060b14 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    padding: 10px 24px !important;
    transition: opacity .2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
    padding: 16px !important;
    transition: border-color .2s, transform .2s !important;
}
[data-testid="metric-container"]:hover {
    border-color: #38bdf8 !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    color: #e2e8f0 !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg,#38bdf8,#818cf8) !important; border-radius: 99px !important; }
.stProgress > div { background: rgba(255,255,255,0.05) !important; border-radius: 99px !important; }

/* Divider */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* Expander */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Radio buttons */
.stRadio > div { flex-direction: row !important; gap: 12px; }
.stRadio label { color: #e2e8f0 !important; }

/* Spinner */
.stSpinner > div { border-top-color: #38bdf8 !important; }

/* Scrollable hourly row */
.hourly-container {
    display: flex; gap: 12px; overflow-x: auto; padding: 8px 0;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.1) transparent;
}
.hourly-card {
    flex: 0 0 80px; background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 12px 8px; text-align: center;
    min-width: 80px;
}
.hourly-card:hover { border-color: #38bdf8; }
.hourly-time { font-size: .72rem; color: #64748b; font-weight: 600; }
.hourly-icon { font-size: 1.4rem; margin: 5px 0; }
.hourly-temp { font-size: .9rem; font-weight: 700; color: #e2e8f0; }
.hourly-pop  { font-size: .68rem; color: #7dd3fc; margin-top: 3px; }

/* Hero card */
.hero-card {
    background: linear-gradient(135deg,rgba(56,189,248,.12) 0%,rgba(129,140,248,.08) 100%);
    border: 1px solid rgba(56,189,248,.2); border-radius: 24px;
    padding: 32px; margin-bottom: 24px; position: relative; overflow: hidden;
}
.hero-temp {
    font-size: 5rem; font-weight: 700; line-height: 1;
    font-family: 'Space Mono', monospace;
    background: linear-gradient(135deg,#fff 30%,#38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-city { font-size: 1.8rem; font-weight: 700; color: #e2e8f0; }
.hero-desc { font-size: 1rem; color: #64748b; margin-top: 4px; }
.hero-feels { font-size: .9rem; color: #7dd3fc; margin-top: 4px; }
.badge {
    display: inline-block; padding: 4px 14px; border-radius: 50px;
    font-size: .78rem; font-weight: 600; margin: 2px;
}
.badge-blue  { background: rgba(56,189,248,.15);  color: #38bdf8;  border: 1px solid rgba(56,189,248,.25); }
.badge-purple{ background: rgba(129,140,248,.15); color: #818cf8; border: 1px solid rgba(129,140,248,.25); }

/* Forecast rows */
.forecast-row {
    display: flex; align-items: center; gap: 14px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
    transition: border-color .2s;
}
.forecast-row:hover { border-color: #38bdf8; }
.forecast-day   { width: 44px; font-weight: 600; font-size: .95rem; color:#e2e8f0; }
.forecast-icon  { font-size: 1.5rem; }
.forecast-desc  { flex: 1; font-size: .88rem; color: #64748b; }
.forecast-hum   { font-size: .8rem; color: #7dd3fc; min-width:44px; text-align:right; }
.forecast-temps { font-size: .92rem; font-weight: 600; color: #e2e8f0; min-width:90px; text-align:right; }
.temp-min-text  { color: #64748b; font-weight: 400; }

/* Section header */
.section-hdr {
    font-size: .75rem; text-transform: uppercase; letter-spacing: .1em;
    color: #64748b; font-weight: 700; margin-bottom: 12px; margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_wind_direction(degrees):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(degrees / (360 / len(dirs))) % len(dirs)]

def owm_icon(code):
    return OWM_ICONS.get(code, "🌡")

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(city, units, lang):
    params = {"q": city, "appid": API_KEY, "units": units, "lang": lang}
    r = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
    if r.status_code == 404:
        return None, f"City **'{city}'** not found. Please try another name."
    if r.status_code == 401:
        return None, "Invalid API key. Please set **OPENWEATHER_API_KEY** in Streamlit secrets."
    r.raise_for_status()
    current = r.json()
    lat, lon = current["coord"]["lat"], current["coord"]["lon"]

    fr = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
    fr.raise_for_status()
    forecast_raw = fr.json()

    aq_r = requests.get(f"{BASE_URL}/air_pollution",
                        params={"lat": lat, "lon": lon, "appid": API_KEY}, timeout=10)
    aq_data = aq_r.json() if aq_r.status_code == 200 else None

    # Daily forecast
    daily = {}
    for item in forecast_raw["list"]:
        ds, ts = item["dt_txt"].split(" ")
        if ds not in daily and ts == "12:00:00":
            daily[ds] = item
    if len(daily) < 5:
        daily = {}
        for item in forecast_raw["list"]:
            ds = item["dt_txt"].split(" ")[0]
            if ds not in daily:
                daily[ds] = item

    forecast_list = []
    for ds, item in list(daily.items())[:5]:
        dt = datetime.strptime(ds, "%Y-%m-%d")
        forecast_list.append({
            "day": dt.strftime("%a"), "full_day": dt.strftime("%A"),
            "temp_max": round(item["main"]["temp_max"]),
            "temp_min": round(item["main"]["temp_min"]),
            "description": item["weather"][0]["description"].title(),
            "icon": item["weather"][0]["icon"],
            "humidity": item["main"]["humidity"],
            "pop": round(item.get("pop", 0) * 100),
        })

    hourly_list = []
    for item in forecast_raw["list"][:8]:
        hourly_list.append({
            "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
            "temp": round(item["main"]["temp"]),
            "icon": item["weather"][0]["icon"],
            "pop":  round(item.get("pop", 0) * 100),
        })

    aqi_value = aqi_label = aqi_color = None
    if aq_data and aq_data.get("list"):
        av = aq_data["list"][0]["main"]["aqi"]
        aqi_value = av
        aqi_label, _aqi_emoji, aqi_color = AQI_INFO.get(av, ("Unknown", "⚪", "#fff"))

    sym   = "°C" if units == "metric" else "°F"
    speed = "m/s" if units == "metric" else "mph"

    return {
        "city": current["name"], "country": current["sys"]["country"],
        "lat": lat, "lon": lon,
        "temp": round(current["main"]["temp"]),
        "feels_like": round(current["main"]["feels_like"]),
        "temp_min": round(current["main"]["temp_min"]),
        "temp_max": round(current["main"]["temp_max"]),
        "humidity": current["main"]["humidity"],
        "pressure": current["main"]["pressure"],
        "visibility": round(current.get("visibility", 0) / 1000, 1),
        "wind_speed": round(current["wind"]["speed"]),
        "wind_direction": get_wind_direction(current["wind"].get("deg", 0)),
        "description": current["weather"][0]["description"].title(),
        "icon": current["weather"][0]["icon"],
        "clouds": current["clouds"]["all"],
        "sunrise": datetime.fromtimestamp(current["sys"]["sunrise"]).strftime("%H:%M"),
        "sunset":  datetime.fromtimestamp(current["sys"]["sunset"]).strftime("%H:%M"),
        "sym": sym, "speed": speed, "units": units, "lang": lang,
        "lang_name": LANGUAGES.get(lang, "English"),
        "aqi": aqi_value, "aqi_label": aqi_label, "aqi_color": aqi_color,
        "forecast": forecast_list, "hourly": hourly_list,
    }, None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌤 SkyPulse")
    st.markdown("---")

    city_input = st.text_input("🔍 City Name", placeholder="e.g. Mumbai, London, Tokyo…", key="city")

    lang_names  = list(LANGUAGES.values())
    lang_codes  = list(LANGUAGES.keys())
    lang_choice = st.selectbox("🌐 Language", lang_names, index=0)
    selected_lang = lang_codes[lang_names.index(lang_choice)]

    unit_choice = st.radio("🌡 Units", ["°C (Metric)", "°F (Imperial)"], index=0)
    units = "metric" if "°C" in unit_choice else "imperial"

    search_btn = st.button("🔎 Get Weather", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style='color:#64748b;font-size:.8rem;line-height:1.6'>
    <b style='color:#38bdf8'>Features</b><br>
    ☀️ Current weather<br>
    ⏱ 24-hour hourly<br>
    📅 5-day forecast<br>
    🌿 Air quality (AQI)<br>
    🌅 Sunrise & Sunset<br>
    🗺 Location map<br>
    🌐 25 languages
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='color:#64748b;font-size:.75rem'>Powered by <a href='https://openweathermap.org' style='color:#38bdf8'>OpenWeatherMap</a></div>", unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;color:#38bdf8;font-family:Outfit,sans-serif;margin-bottom:4px'>🌤 SkyPulse</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#64748b;margin-bottom:28px'>Real-time weather forecast · 25 languages · 5-day outlook</p>", unsafe_allow_html=True)

# Trigger search
if search_btn or (city_input and st.session_state.get("last_city") != city_input):
    st.session_state["last_city"] = city_input

if not city_input:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px;color:#64748b'>
        <div style='font-size:4rem;margin-bottom:16px'>🌍</div>
        <h2 style='color:#e2e8f0;font-size:1.5rem;margin-bottom:8px'>Welcome to SkyPulse</h2>
        <p>Enter a city name in the sidebar and click <b style='color:#38bdf8'>Get Weather</b></p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Fetch
with st.spinner(f"Fetching weather for **{city_input}**…"):
    try:
        data, err = fetch_weather(city_input.strip(), units, selected_lang)
    except Exception as e:
        st.error(f"❌ Network error: {e}")
        st.stop()

if err:
    st.error(f"❌ {err}")
    st.stop()

d   = data
sym = d["sym"]
spd = d["speed"]

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <div class="hero-city">{owm_icon(d['icon'])} {d['city']}, {d['country']}</div>
      <div class="hero-desc">{d['lat']:.2f}°, {d['lon']:.2f}° &nbsp;·&nbsp; 🌐 {d['lang_name']}</div>
    </div>
    <div>
      <span class="badge badge-blue">{d['description']}</span>
      <span class="badge badge-purple">H:{d['temp_max']}{sym} L:{d['temp_min']}{sym}</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-top:20px">
    <div style="font-size:4rem;filter:drop-shadow(0 4px 12px rgba(56,189,248,.4))">{owm_icon(d['icon'])}</div>
    <div>
      <div class="hero-temp">{d['temp']}{sym}</div>
      <div class="hero-feels">Feels like {d['feels_like']}{sym}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stats ──────────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("💧 Humidity",    f"{d['humidity']}%")
c2.metric("💨 Wind",        f"{d['wind_speed']} {spd}", d['wind_direction'])
c3.metric("🌡 Pressure",    f"{d['pressure']} hPa")
c4.metric("👁 Visibility",  f"{d['visibility']} km")
c5.metric("☁️ Cloud Cover", f"{d['clouds']}%")
if d['aqi']:
    label, emoji, _ = AQI_INFO.get(d['aqi'], ("Unknown","⚪","#fff"))
    c6.metric("🌿 Air Quality", f"{emoji} {label}", f"{d['aqi']}/5")

st.markdown("<br>", unsafe_allow_html=True)

# ── Sunrise/Sunset + AQI ──────────────────────────────────────────────────────
col_sun, col_aqi = st.columns(2)

with col_sun:
    st.markdown('<div class="section-hdr">🌅 Sunrise & Sunset</div>', unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    s1.metric("🌅 Sunrise", d['sunrise'])
    s2.metric("🌇 Sunset",  d['sunset'])

with col_aqi:
    if d['aqi']:
        st.markdown('<div class="section-hdr">🌿 Air Quality Index</div>', unsafe_allow_html=True)
        label, emoji, color = AQI_INFO.get(d['aqi'], ("Unknown","⚪","#fff"))
        st.markdown(f"<div style='font-size:1.1rem;font-weight:600;margin-bottom:8px'>{emoji} <span style='color:{color}'>{label}</span> <span style='color:#64748b;font-size:.85rem'>({d['aqi']}/5)</span></div>", unsafe_allow_html=True)
        st.progress(d['aqi'] / 5)

st.markdown("<br>", unsafe_allow_html=True)

# ── Hourly ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">⏱ 24-Hour Forecast</div>', unsafe_allow_html=True)
hourly_html = '<div class="hourly-container">'
for h in d['hourly']:
    pop_html = f'<div class="hourly-pop">💧{h["pop"]}%</div>' if h['pop'] else ''
    hourly_html += f"""
    <div class="hourly-card">
      <div class="hourly-time">{h['time']}</div>
      <div class="hourly-icon">{owm_icon(h['icon'])}</div>
      <div class="hourly-temp">{h['temp']}{sym}</div>
      {pop_html}
    </div>"""
hourly_html += '</div>'
st.markdown(hourly_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 5-Day Forecast ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">📅 5-Day Forecast</div>', unsafe_allow_html=True)
forecast_html = ""
for f in d['forecast']:
    pop_txt = f"💧{f['pop']}%" if f['pop'] else ""
    forecast_html += f"""
    <div class="forecast-row">
      <div class="forecast-day">{f['day']}</div>
      <div class="forecast-icon">{owm_icon(f['icon'])}</div>
      <div class="forecast-desc">{f['description']}</div>
      <div class="forecast-hum">{pop_txt}</div>
      <div class="forecast-temps">{f['temp_max']}{sym} <span class="temp-min-text">/ {f['temp_min']}{sym}</span></div>
    </div>"""
st.markdown(forecast_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Map ────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">🗺 Location Map</div>', unsafe_allow_html=True)
map_url = (f"https://www.openstreetmap.org/export/embed.html"
           f"?bbox={d['lon']-1}%2C{d['lat']-1}%2C{d['lon']+1}%2C{d['lat']+1}"
           f"&layer=mapnik&marker={d['lat']}%2C{d['lon']}")
st.markdown(f"""
<div style="border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08)">
  <iframe src="{map_url}" width="100%" height="260" frameborder="0" style="display:block"></iframe>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Raw data expander ──────────────────────────────────────────────────────────
with st.expander("🔬 Raw Weather Data (JSON)"):
    st.json({k: v for k, v in d.items() if k not in ("forecast","hourly")})
