"""
SkyPulse — Streamlit Weather App
One search bar (text + working mic), speak-aloud weather, 25 languages.
No chatbot. No sidebar search. Settings in sidebar only.
"""

import streamlit as st
import streamlit.components.v1 as components
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

# lang display name → (BCP-47, OWM code)
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
AQI_LABELS = {1:"Good",2:"Fair",3:"Moderate",4:"Poor",5:"Very Poor"}
AQI_COLORS = {1:"#4ade80",2:"#38bdf8",3:"#facc15",4:"#fb923c",5:"#f87171"}

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [("city",""),("lang","English"),("units","metric"),
             ("weather_data",None),("tts_text",""),
             ("chat_history",[]),("last_chat_q","")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────
def owm_icon(code): return OWM_ICONS.get(code, "🌡")

def wind_dir(deg):
    d = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return d[round(deg / (360 / len(d))) % len(d)]

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(city, units, owm_lang):
    p = {"q": city, "appid": OWM_KEY, "units": units, "lang": owm_lang}
    r = requests.get(f"{BASE_URL}/weather", params=p, timeout=10)
    if r.status_code == 404: return None, f"City '{city}' not found."
    if r.status_code == 401: return None, "Invalid API key."
    r.raise_for_status()
    c = r.json()
    lat, lon = c["coord"]["lat"], c["coord"]["lon"]

    fr = requests.get(f"{BASE_URL}/forecast", params=p, timeout=10); fr.raise_for_status()
    fraw = fr.json()

    aqr = requests.get(f"{BASE_URL}/air_pollution",
                       params={"lat":lat,"lon":lon,"appid":OWM_KEY}, timeout=10)
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

    aqi_val = aqi_lbl = None
    if aqd and aqd.get("list"):
        av = aqd["list"][0]["main"]["aqi"]
        aqi_val = av; aqi_lbl = AQI_LABELS.get(av, "Unknown")

    sym   = "°C" if units == "metric" else "°F"
    speed = "m/s" if units == "metric" else "mph"
    return {
        "city": c["name"], "country": c["sys"]["country"], "lat": lat, "lon": lon,
        "temp": round(c["main"]["temp"]), "feels_like": round(c["main"]["feels_like"]),
        "temp_min": round(c["main"]["temp_min"]), "temp_max": round(c["main"]["temp_max"]),
        "humidity": c["main"]["humidity"], "pressure": c["main"]["pressure"],
        "visibility": round(c.get("visibility", 0) / 1000, 1),
        "wind_speed": round(c["wind"]["speed"]),
        "wind_direction": wind_dir(c["wind"].get("deg", 0)),
        "description": c["weather"][0]["description"].title(),
        "icon": c["weather"][0]["icon"], "clouds": c["clouds"]["all"],
        "sunrise": datetime.fromtimestamp(c["sys"]["sunrise"]).strftime("%H:%M"),
        "sunset":  datetime.fromtimestamp(c["sys"]["sunset"]).strftime("%H:%M"),
        "sym": sym, "speed": speed, "units": units,
        "aqi": aqi_val, "aqi_label": aqi_lbl,
        "forecast": forecast, "hourly": hourly,
    }, None


def build_tts(d, units):
    """Human-sounding TTS script with weather advice."""
    sym_word = "degrees Celsius" if units == "metric" else "degrees Fahrenheit"
    spd_word = "metres per second" if units == "metric" else "miles per hour"

    advice = ""
    if d.get("aqi"):
        advice_map = {
            "Good":      "Air quality is great — perfect for outdoor activities.",
            "Fair":      "Air quality is fair, generally safe to go outside.",
            "Moderate":  "Air quality is moderate. Sensitive groups should limit time outdoors.",
            "Poor":      "Air quality is poor today — try to limit outdoor exposure.",
            "Very Poor": "Air quality is very poor. It's best to stay indoors if possible.",
        }
        advice = advice_map.get(d["aqi_label"], "")

    rain_note = ""
    for f in d.get("forecast", [])[:2]:
        if f["pop"] > 40:
            rain_note = f"There's a {f['pop']} percent chance of rain {f['day']}, so keep an umbrella handy."
            break

    wind_note = ""
    ws = d["wind_speed"]
    if (units == "metric" and ws > 10) or (units == "imperial" and ws > 22):
        wind_note = "It's quite windy, so dress accordingly."

    should_go = ""
    if d.get("aqi") and d["aqi"] >= 4:
        should_go = "Given the poor air quality, I'd suggest limiting time outside today."
    elif d["clouds"] > 80 and any(f["pop"] > 50 for f in d.get("forecast", [])[:1]):
        should_go = "It looks overcast with a good chance of rain — carry an umbrella if you're heading out."
    elif d["temp"] > 38 and units == "metric":
        should_go = "It's very hot outside. Stay hydrated and avoid the afternoon sun if possible."
    elif d["temp"] < 5 and units == "metric":
        should_go = "It's quite cold — bundle up well before heading out."
    else:
        should_go = "Conditions look generally fine for going out. Enjoy your day!"

    script = (
        f"Here's the weather in {d['city']}, {d['country']}. "
        f"Right now it's {d['temp']} {sym_word}, feeling like {d['feels_like']} {sym_word}. "
        f"The sky shows {d['description'].lower()}. "
        f"Humidity is {d['humidity']} percent, and wind is {d['wind_speed']} {spd_word} from the {d['wind_direction']}. "
        f"Today's high is {d['temp_max']} and the low is {d['temp_min']} {sym_word}. "
    )
    if wind_note:  script += wind_note + " "
    if rain_note:  script += rain_note + " "
    if advice:     script += advice    + " "
    script += should_go
    return script


def ask_claude(question, weather_ctx):
    if CLAUDE_KEY == "YOUR_CLAUDE_KEY_HERE":
        return "Add ANTHROPIC_API_KEY to Streamlit secrets to enable AI answers."
    try:
        api_msgs = []
        for m in st.session_state.chat_history[-10:]:
            api_msgs.append({"role": m["role"], "content": m["text"]})
        api_msgs.append({"role": "user", "content": question})
        resp = requests.post(CLAUDE_URL,
            headers={"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 350,
                  "system": (
                      "You are SkyBot, a friendly weather assistant. "
                      "Answer in 2-3 natural sentences. Give practical advice — "
                      "should I go out? what to wear? is travel safe? "
                      f"Weather context:\n{weather_ctx}"
                  ),
                  "messages": api_msgs},
            timeout=20)
        return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"Error: {e}"


# ── Sidebar: settings only ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    lang_choice = st.selectbox(
        "🌐 Language",
        list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state.lang),
        key="lang_select",
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

    unit_label = st.radio("🌡 Units", ["°C  Metric", "°F  Imperial"],
                          index=0 if st.session_state.units == "metric" else 1)
    new_units = "metric" if "°C" in unit_label else "imperial"
    if new_units != st.session_state.units:
        st.session_state.units = new_units
        st.rerun()

    st.markdown("---")
    st.markdown("""<div style='font-size:.8rem;color:#64748b;line-height:1.9'>
    <b style='color:#38bdf8'>Tips</b><br>
    🎤 Chrome / Edge for voice search<br>
    🔊 Click speak for weather report<br>
    🤖 Scroll down for AI chat<br>
    ⚙️ Change language &amp; units here
    </div>""", unsafe_allow_html=True)

bcp47, owm_lang = LANGUAGES[st.session_state.lang]
units = st.session_state.units


# ── Handle chat question (server-side) ────────────────────────────────────────
chat_q = st.text_input("__chatq__", value="", key="chatq_in",
                       label_visibility="collapsed")
if chat_q and chat_q != st.session_state.last_chat_q:
    st.session_state.last_chat_q = chat_q
    d2 = st.session_state.weather_data
    ctx = ""
    if d2:
        ctx = (f"City:{d2['city']},{d2['country']} Temp:{d2['temp']}{d2['sym']} "
               f"Feels:{d2['feels_like']}{d2['sym']} Condition:{d2['description']} "
               f"Humidity:{d2['humidity']}% Wind:{d2['wind_speed']} {d2['speed']} {d2['wind_direction']} "
               f"AQI:{d2.get('aqi_label','N/A')} Forecast next days: "
               + " | ".join(f"{f['day']}:{f['description']},High:{f['temp_max']},Rain:{f['pop']}%"
                             for f in d2.get("forecast", [])[:3]))
    ans = ask_claude(chat_q, ctx)
    st.session_state.chat_history.append({"role":"user",      "text": chat_q})
    st.session_state.chat_history.append({"role":"assistant", "text": ans})

# ── Handle city submitted from JS component ───────────────────────────────────
city_in = st.text_input("__city__", value=st.session_state.city,
                        key="city_in", label_visibility="collapsed",
                        placeholder="Type a city name…")
if city_in != st.session_state.city:
    st.session_state.city = city_in
    st.rerun()


# ── FULL-PAGE HTML component (search bar + all JS) ────────────────────────────
# This runs in its own iframe — no cross-frame issues.
# It calls window.parent.postMessage to send city back to Streamlit.

tts_text = st.session_state.get("tts_text", "")
cur_city  = st.session_state.city
cur_lang  = st.session_state.lang
cur_bcp47 = bcp47

lang_options_html = "\n".join(
    f'<option value="{bcp}" data-owm="{owm}" {"selected" if name == cur_lang else ""}>{name}</option>'
    for name, (bcp, owm) in LANGUAGES.items()
)

search_component_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family:'Outfit',sans-serif;
    background:transparent;
    padding:0;
  }}

  .bar {{
    display:flex; align-items:center; gap:8px;
    background:rgba(13,21,38,0.96); backdrop-filter:blur(20px);
    border:1px solid rgba(56,189,248,0.28);
    border-radius:50px; padding:7px 10px 7px 20px;
    box-shadow:0 6px 28px rgba(0,0,0,.45);
  }}
  .bar input {{
    flex:1; background:transparent; border:none; outline:none;
    color:#e2e8f0; font-family:'Outfit',sans-serif; font-size:.97rem;
    font-weight:500; min-width:0;
  }}
  .bar input::placeholder {{ color:#475569; }}

  .icon-btn {{
    background:transparent; border:none; cursor:pointer;
    color:#64748b; font-size:1.1rem; padding:5px 7px; border-radius:50%;
    transition:color .15s, background .15s; display:flex;
    align-items:center; justify-content:center; flex-shrink:0;
  }}
  .icon-btn:hover {{ color:#38bdf8; background:rgba(56,189,248,.1); }}
  .icon-btn.listening {{
    color:#ef4444 !important; background:rgba(239,68,68,.14) !important;
    animation:pulse .9s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%,100% {{ box-shadow:0 0 0 0 rgba(239,68,68,.35); }}
    50%      {{ box-shadow:0 0 0 8px rgba(239,68,68,0); }}
  }}

  .go-btn {{
    background:#38bdf8; color:#060b14; border:none; border-radius:50px;
    padding:7px 20px; font-weight:700; font-size:.88rem; cursor:pointer;
    font-family:'Outfit',sans-serif; flex-shrink:0; transition:opacity .15s;
    white-space:nowrap;
  }}
  .go-btn:hover {{ opacity:.82; }}

  /* Voice toast */
  .toast {{
    margin-top:8px; display:none;
    background:rgba(17,29,53,0.95); border:1px solid rgba(255,255,255,.09);
    border-radius:50px; padding:7px 18px; font-size:.82rem; color:#e2e8f0;
    align-items:center; gap:8px;
  }}
  .toast.show {{ display:flex; }}
  .toast-dot {{
    width:8px; height:8px; background:#ef4444; border-radius:50%;
    animation:blink .6s ease infinite alternate; flex-shrink:0;
  }}
  @keyframes blink {{ from{{opacity:1}} to{{opacity:.2}} }}

  /* Language + Units row */
  .controls {{
    display:flex; align-items:center; gap:10px; margin-top:10px; flex-wrap:wrap;
  }}
  .lang-sel {{
    appearance:none; background:rgba(255,255,255,0.07);
    border:1px solid rgba(255,255,255,0.1);
    border-radius:50px; padding:6px 32px 6px 14px;
    color:#e2e8f0; font-family:'Outfit',sans-serif; font-size:.82rem; font-weight:600;
    cursor:pointer; outline:none; transition:border .2s;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
    background-repeat:no-repeat; background-position:right 10px center;
  }}
  .lang-sel:focus {{ border-color:#38bdf8; }}
  .lang-sel option {{ background:#111d35; color:#e2e8f0; }}

  .unit-toggle {{
    display:flex; background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.1); border-radius:50px; overflow:hidden;
  }}
  .unit-btn {{
    padding:6px 14px; cursor:pointer; border:none; background:transparent;
    color:#64748b; font-family:'Outfit',sans-serif; font-size:.82rem;
    font-weight:600; transition:all .18s;
  }}
  .unit-btn.active {{ background:#38bdf8; color:#060b14; }}

  .no-support {{
    margin-top:6px; display:none;
    background:rgba(250,204,21,.1); border:1px solid rgba(250,204,21,.3);
    border-radius:8px; padding:7px 14px; font-size:.78rem; color:#facc15;
  }}
</style>
</head>
<body>

<!-- Search bar -->
<div class="bar">
  <input id="inp" type="text" placeholder="Search city… or click 🎤 to speak"
         value="{cur_city}" autocomplete="off"
         onkeydown="if(event.key==='Enter')doSearch()" />
  <button class="icon-btn" id="micBtn" onclick="toggleVoice()" title="Voice search">🎤</button>
  <button class="icon-btn" onclick="doGeolocate()" title="Use my location">📍</button>
  <button class="go-btn" onclick="doSearch()">Search</button>
</div>

<!-- Voice feedback toast -->
<div class="toast" id="toast">
  <div class="toast-dot"></div>
  <span id="toastText">Listening…</span>
</div>

<!-- No-support warning -->
<div class="no-support" id="noSupport">
  ⚠️ Voice search requires Chrome or Edge browser.
</div>

<!-- Controls: language + units -->
<div class="controls">
  <select class="lang-sel" id="langSel" onchange="onLangChange()">
    {lang_options_html}
  </select>
  <div class="unit-toggle">
    <button class="unit-btn {'active' if units=='metric' else ''}"
      data-unit="metric" onclick="setUnit('metric')">°C</button>
    <button class="unit-btn {'active' if units=='imperial' else ''}"
      data-unit="imperial" onclick="setUnit('imperial')">°F</button>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────────────────────
var currentUnit = "{units}";
var currentLang = "{cur_bcp47}";
var recognition  = null;
var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// ── Helpers ────────────────────────────────────────────────────────────────────
function toast(msg) {{
  var t = document.getElementById('toast');
  document.getElementById('toastText').textContent = msg;
  t.classList.add('show');
}}
function hideToast() {{
  document.getElementById('toast').classList.remove('show');
}}

function postToStreamlit(type, value) {{
  // Works because Streamlit's components.html() uses postMessage
  window.parent.postMessage({{type: type, value: value}}, '*');
}}

// ── Search ─────────────────────────────────────────────────────────────────────
function doSearch() {{
  var v = document.getElementById('inp').value.trim();
  if (!v) return;
  postToStreamlit('city', v);
}}

// ── Unit toggle ────────────────────────────────────────────────────────────────
function setUnit(u) {{
  currentUnit = u;
  document.querySelectorAll('.unit-btn').forEach(function(b) {{
    b.classList.toggle('active', b.dataset.unit === u);
  }});
  postToStreamlit('unit', u);
}}

// ── Language change ────────────────────────────────────────────────────────────
function onLangChange() {{
  var sel = document.getElementById('langSel');
  var name = sel.options[sel.selectedIndex].text;
  currentLang = sel.value;  // BCP-47
  postToStreamlit('lang', name);  // send display name to Python
}}

// ── Geolocation ────────────────────────────────────────────────────────────────
function doGeolocate() {{
  if (!navigator.geolocation) {{ alert('Geolocation not supported.'); return; }}
  toast('Getting your location…');
  navigator.geolocation.getCurrentPosition(
    function(pos) {{
      hideToast();
      var city = pos.coords.latitude.toFixed(4) + ',' + pos.coords.longitude.toFixed(4);
      document.getElementById('inp').value = city;
      postToStreamlit('city', city);
    }},
    function() {{ hideToast(); alert('Location access denied.'); }}
  );
}}

// ── Voice search (exact pattern from Flask app) ────────────────────────────────
function toggleVoice() {{
  if (!SpeechRecognition) {{
    document.getElementById('noSupport').style.display = 'block';
    return;
  }}
  if (recognition) {{ recognition.stop(); return; }}

  recognition = new SpeechRecognition();
  recognition.lang            = currentLang;
  recognition.interimResults  = true;
  recognition.maxAlternatives = 1;
  recognition.continuous      = false;

  var btn = document.getElementById('micBtn');
  btn.classList.add('listening');
  btn.textContent = '⏹';
  toast('Listening… say your city name');

  recognition.onresult = function(e) {{
    var transcript = Array.from(e.results).map(function(r) {{ return r[0].transcript; }}).join('');
    document.getElementById('inp').value = transcript;
    if (e.results[e.results.length - 1].isFinal) {{
      toast('Got it: "' + transcript + '"');
      setTimeout(function() {{
        doSearch();
      }}, 500);
    }}
  }};

  recognition.onerror = function(e) {{
    var msgs = {{
      'no-speech':     'No speech detected — try again.',
      'audio-capture': 'No microphone found.',
      'not-allowed':   'Microphone blocked. Please allow access in your browser.',
      'network':       'Network error during voice recognition.',
    }};
    hideToast();
    toast(msgs[e.error] || 'Voice error: ' + e.error);
    setTimeout(hideToast, 3000);
    resetMic();
  }};

  recognition.onend = function() {{
    hideToast();
    resetMic();
    recognition = null;
  }};

  recognition.start();
}}

function resetMic() {{
  var btn = document.getElementById('micBtn');
  btn.classList.remove('listening');
  btn.textContent = '🎤';
}}
</script>
</body>
</html>"""

# Render search component and capture messages via query params trick
component_value = components.html(
    search_component_html,
    height=110,
    scrolling=False,
)


# ── Handle postMessage from component via Streamlit query params ───────────────
# Streamlit components.html sends values via window.parent.postMessage.
# We use a secondary hidden JS snippet to intercept and reflect into st.query_params.
msg_listener = """
<script>
window.addEventListener('message', function(e) {
  if (!e.data || !e.data.type) return;
  var type  = e.data.type;
  var value = e.data.value;

  // Reflect into the hidden Streamlit text inputs using React's internal setter
  function setInput(placeholder, val) {
    var inputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].placeholder === placeholder) {
        var nativeSetter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(inputs[i], val);
        inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
        return;
      }
    }
  }

  if (type === 'city') {
    setInput('Type a city name\u2026', value);
  }
});
</script>
"""
st.markdown(msg_listener, unsafe_allow_html=True)


# ── Handle lang + unit changes from component ─────────────────────────────────
# These use query_params since they are simple state changes
qp = st.query_params
if "lang" in qp and qp["lang"] != st.session_state.lang:
    if qp["lang"] in LANGUAGES:
        st.session_state.lang = qp["lang"]
        st.rerun()
if "unit" in qp:
    new_u = qp["unit"]
    if new_u in ("metric","imperial") and new_u != st.session_state.units:
        st.session_state.units = new_u
        st.rerun()


# ── Main weather display ───────────────────────────────────────────────────────
# Global CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
*, html, body, [class*="css"] { font-family:'Outfit',sans-serif !important; }
.stApp {
  background:#060b14;
  background-image:
    radial-gradient(ellipse 80% 50% at 20% -10%,rgba(56,189,248,.12) 0%,transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 110%,rgba(129,140,248,.1) 0%,transparent 60%);
}
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility:hidden !important; }
[data-testid="stSidebar"] { background:#0d1526 !important; border-right:1px solid rgba(255,255,255,.07) !important; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
h1,h2,h3,h4,p,label,div { color:#e2e8f0; }
[data-testid="metric-container"] {
  background:rgba(255,255,255,.04) !important; border:1px solid rgba(255,255,255,.08) !important;
  border-radius:16px !important; padding:16px !important; transition:border-color .2s,transform .2s !important;
}
[data-testid="metric-container"]:hover { border-color:#38bdf8 !important; transform:translateY(-2px) !important; }
[data-testid="stMetricValue"] { font-family:'Space Mono',monospace !important; color:#e2e8f0 !important; }
[data-testid="stMetricLabel"] { color:#64748b !important; }
.stProgress>div>div { background:linear-gradient(90deg,#38bdf8,#818cf8) !important; border-radius:99px !important; }
.stProgress>div { background:rgba(255,255,255,.05) !important; border-radius:99px !important; }
[data-testid="stExpander"] { background:rgba(255,255,255,.04) !important; border:1px solid rgba(255,255,255,.08) !important; border-radius:16px !important; }
.stTextInput input { background:rgba(255,255,255,.07) !important; border:1px solid rgba(255,255,255,.1) !important; border-radius:10px !important; color:#e2e8f0 !important; }
.stButton>button { background:#38bdf8 !important; color:#060b14 !important; border:none !important; border-radius:12px !important; font-weight:700 !important; }

/* hero */
.hero-card {
  background:linear-gradient(135deg,rgba(56,189,248,.1) 0%,rgba(129,140,248,.07) 100%);
  border:1px solid rgba(56,189,248,.18); border-radius:24px; padding:32px; margin-bottom:20px;
}
.hero-temp {
  font-size:5rem; font-weight:700; line-height:1; font-family:'Space Mono',monospace;
  background:linear-gradient(135deg,#fff 30%,#38bdf8);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.hero-city  { font-size:1.7rem; font-weight:700; color:#e2e8f0 !important; }
.hero-sub   { font-size:.9rem; color:#64748b !important; margin-top:3px; }
.hero-feels { font-size:.9rem; color:#7dd3fc !important; margin-top:3px; }
.badge { display:inline-block; padding:4px 14px; border-radius:50px; font-size:.78rem; font-weight:600; margin:2px; }
.badge-sky    { background:rgba(56,189,248,.13); color:#38bdf8; border:1px solid rgba(56,189,248,.22); }
.badge-indigo { background:rgba(129,140,248,.13); color:#818cf8; border:1px solid rgba(129,140,248,.22); }
/* speak btn */
.speak-btn {
  display:inline-flex; align-items:center; gap:7px;
  background:rgba(56,189,248,.08); color:#38bdf8;
  border:1px solid rgba(56,189,248,.2); border-radius:50px;
  padding:8px 20px; font-size:.88rem; font-weight:600;
  font-family:'Outfit',sans-serif; cursor:pointer; margin-top:12px;
  transition:all .18s;
}
.speak-btn:hover { background:rgba(56,189,248,.18); }
.speak-btn.speaking { background:rgba(74,222,128,.13); color:#4ade80; border-color:rgba(74,222,128,.3); }
/* hourly */
.h-row { display:flex; gap:10px; overflow-x:auto; padding:4px 0 8px; scrollbar-width:thin; scrollbar-color:rgba(255,255,255,.07) transparent; }
.h-card { flex:0 0 76px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); border-radius:12px; padding:10px 6px; text-align:center; transition:border-color .15s; }
.h-card:hover { border-color:#38bdf8; }
.ht { font-size:.68rem; color:#64748b; font-weight:600; }
.hi { font-size:1.3rem; margin:4px 0; }
.hv { font-size:.88rem; font-weight:700; color:#e2e8f0; }
.hp { font-size:.65rem; color:#7dd3fc; margin-top:2px; }
/* forecast */
.fc { display:flex; align-items:center; gap:14px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.07); border-radius:12px; padding:13px 18px; margin-bottom:9px; transition:border-color .15s; }
.fc:hover { border-color:#38bdf8; }
.fcd { width:40px; font-weight:600; font-size:.92rem; }
.fci { font-size:1.45rem; }
.fce { flex:1; font-size:.85rem; color:#64748b; }
.fcp { font-size:.78rem; color:#7dd3fc; min-width:40px; text-align:right; }
.fct { font-size:.9rem; font-weight:600; min-width:88px; text-align:right; }
.lo  { color:#64748b; font-weight:400; }
/* section header */
.shdr { font-size:.7rem; text-transform:uppercase; letter-spacing:.12em; color:#475569; font-weight:700; margin:16px 0 10px; }
/* chat */
.chat-wrap { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.08); border-radius:16px; padding:18px; margin-top:8px; }
.cmsg-u { background:rgba(56,189,248,.1); border:1px solid rgba(56,189,248,.18); border-radius:14px 14px 4px 14px; padding:9px 14px; font-size:.86rem; margin-bottom:8px; max-width:85%; margin-left:auto; }
.cmsg-a { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); border-radius:14px 14px 14px 4px; padding:9px 14px; font-size:.86rem; margin-bottom:8px; max-width:85%; line-height:1.55; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;color:#38bdf8;font-family:Outfit,sans-serif;margin:0 0 4px'>🌤 SkyPulse</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#64748b;margin-bottom:18px'>Real-time weather · Voice search · Speak aloud · 25 languages</p>", unsafe_allow_html=True)

if not st.session_state.city:
    st.markdown("""
    <div style='text-align:center;padding:48px 20px'>
      <div style='font-size:4.5rem;margin-bottom:14px'>🌍</div>
      <h2 style='color:#e2e8f0;font-size:1.5rem;margin-bottom:8px'>Welcome to SkyPulse</h2>
      <p style='color:#64748b'>Type a city above and press Enter — or click 🎤 to speak</p>
      <div style='margin-top:22px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap'>
        <span style='background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.18);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#7dd3fc'>🎤 Voice search (Chrome/Edge)</span>
        <span style='background:rgba(129,140,248,.08);border:1px solid rgba(129,140,248,.18);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#a5b4fc'>🔊 Natural voice weather report</span>
        <span style='background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.18);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#86efac'>🤖 Ask AI — should I go outside?</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Fetch weather ──────────────────────────────────────────────────────────────
with st.spinner(f"Loading weather for **{st.session_state.city}**…"):
    try:
        data, err = fetch_weather(st.session_state.city.strip(), units, owm_lang)
    except Exception as e:
        st.error(f"❌ Network error: {e}"); st.stop()

if err:
    st.error(f"❌ {err}"); st.stop()

st.session_state.weather_data = data
d   = data
sym = d["sym"]
spd = d["speed"]

tts = build_tts(d, units)
# Escape for JS string
tts_js = tts.replace("\\","\\\\").replace("`","\\`").replace("$","\\$")
st.session_state.tts_text = tts

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <div class="hero-city">{owm_icon(d['icon'])} {d['city']}, {d['country']}</div>
      <div class="hero-sub">{d['lat']:.2f}°, {d['lon']:.2f}°</div>
    </div>
    <div style="text-align:right">
      <span class="badge badge-sky">{d['description']}</span>
      <span class="badge badge-indigo">H:{d['temp_max']}{sym} · L:{d['temp_min']}{sym}</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:18px;margin-top:18px;flex-wrap:wrap">
    <div style="font-size:4rem;filter:drop-shadow(0 4px 14px rgba(56,189,248,.4))">{owm_icon(d['icon'])}</div>
    <div>
      <div class="hero-temp">{d['temp']}{sym}</div>
      <div class="hero-feels">Feels like {d['feels_like']}{sym} · 💧 {d['humidity']}%</div>
    </div>
  </div>
  <button class="speak-btn" id="speakBtn" onclick="speakWeather()">🔊 Hear weather report</button>
</div>
""", unsafe_allow_html=True)

# ── Stats ──────────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("💧 Humidity",   f"{d['humidity']}%")
c2.metric("💨 Wind",       f"{d['wind_speed']} {spd}", d['wind_direction'])
c3.metric("🌡 Pressure",   f"{d['pressure']} hPa")
c4.metric("👁 Visibility", f"{d['visibility']} km")
c5.metric("☁️ Cloud",      f"{d['clouds']}%")
if d['aqi']:
    c6.metric("🌿 AQI", f"{d['aqi_label']}", f"{d['aqi']}/5")

st.markdown("<br>", unsafe_allow_html=True)

# ── Sunrise + AQI ─────────────────────────────────────────────────────────────
cs, ca = st.columns(2)
with cs:
    st.markdown('<div class="shdr">🌅 Sunrise &amp; Sunset</div>', unsafe_allow_html=True)
    s1,s2 = st.columns(2)
    s1.metric("🌅 Sunrise", d['sunrise']); s2.metric("🌇 Sunset", d['sunset'])
with ca:
    if d['aqi']:
        col = AQI_COLORS.get(d['aqi'],"#fff")
        st.markdown('<div class="shdr">🌿 Air Quality</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:1rem;font-weight:600;margin-bottom:8px;color:{col}'>{d['aqi_label']} ({d['aqi']}/5)</div>",
                    unsafe_allow_html=True)
        st.progress(d['aqi'] / 5)

st.markdown("<br>", unsafe_allow_html=True)

# ── Hourly ────────────────────────────────────────────────────────────────────
st.markdown('<div class="shdr">⏱ Next 24 Hours</div>', unsafe_allow_html=True)
hh = '<div class="h-row">'
for h in d['hourly']:
    pp = f'<div class="hp">💧{h["pop"]}%</div>' if h['pop'] else ''
    hh += f'<div class="h-card"><div class="ht">{h["time"]}</div><div class="hi">{owm_icon(h["icon"])}</div><div class="hv">{h["temp"]}{sym}</div>{pp}</div>'
hh += '</div>'
st.markdown(hh, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── 5-Day Forecast ────────────────────────────────────────────────────────────
st.markdown('<div class="shdr">📅 5-Day Forecast</div>', unsafe_allow_html=True)
fh = ""
for f in d['forecast']:
    pt = f"💧{f['pop']}%" if f['pop'] else ""
    fh += (f'<div class="fc"><div class="fcd">{f["day"]}</div>'
           f'<div class="fci">{owm_icon(f["icon"])}</div>'
           f'<div class="fce">{f["description"]}</div>'
           f'<div class="fcp">{pt}</div>'
           f'<div class="fct">{f["temp_max"]}{sym} <span class="lo">/ {f["temp_min"]}{sym}</span></div></div>')
st.markdown(fh, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="shdr">🗺 Location Map</div>', unsafe_allow_html=True)
map_url = (f"https://www.openstreetmap.org/export/embed.html"
           f"?bbox={d['lon']-1}%2C{d['lat']-1}%2C{d['lon']+1}%2C{d['lat']+1}"
           f"&layer=mapnik&marker={d['lat']}%2C{d['lon']}")
st.markdown(f'<div style="border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.07)">'
            f'<iframe src="{map_url}" width="100%" height="230" frameborder="0"></iframe></div>',
            unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── AI Chat ───────────────────────────────────────────────────────────────────
with st.expander("🤖 Ask SkyBot — Should I go outside? What to wear? Is it safe to travel?"):
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    if st.session_state.chat_history:
        for m in st.session_state.chat_history[-20:]:
            cls = "cmsg-u" if m["role"] == "user" else "cmsg-a"
            safe = m["text"].replace("<","&lt;").replace(">","&gt;")
            st.markdown(f'<div class="{cls}">{safe}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col_q, col_btn = st.columns([5,1])
    with col_q:
        user_q = st.text_input("Ask about this weather…", key="chat_user_input",
                               label_visibility="collapsed",
                               placeholder="e.g. Should I go jogging today?")
    with col_btn:
        if st.button("Ask", key="chat_send_btn"):
            if user_q:
                ctx = (f"City:{d['city']},{d['country']} Temp:{d['temp']}{sym} "
                       f"Feels:{d['feels_like']}{sym} Condition:{d['description']} "
                       f"Humidity:{d['humidity']}% Wind:{d['wind_speed']} {spd} {d['wind_direction']} "
                       f"AQI:{d.get('aqi_label','N/A')} "
                       + " | ".join(f"{f['day']}:{f['description']},H:{f['temp_max']},Rain:{f['pop']}%"
                                    for f in d.get("forecast",[])[:3]))
                ans = ask_claude(user_q, ctx)
                st.session_state.chat_history.append({"role":"user",      "text": user_q})
                st.session_state.chat_history.append({"role":"assistant", "text": ans})
                st.rerun()

with st.expander("🔬 Raw JSON"):
    st.json({k:v for k,v in d.items() if k not in ("forecast","hourly")})


# ── TTS JavaScript (injected into main page, not inside component) ─────────────
st.markdown(f"""
<script>
// TTS — runs in the main Streamlit page (not iframe)
var _tts = `{tts_js}`;
var _bcp = "{bcp47}";
var _speaking = false;

function speakWeather() {{
  if (!window.speechSynthesis) {{ alert('TTS not supported in this browser.'); return; }}
  if (_speaking) {{
    window.speechSynthesis.cancel();
    _speaking = false;
    updateSpeakBtn(false);
    return;
  }}
  var utt   = new SpeechSynthesisUtterance(_tts);
  utt.lang  = _bcp;
  utt.rate  = 0.93;
  utt.pitch = 1.02;

  // Pick best voice: prefer Neural/Enhanced/Premium
  var voices = window.speechSynthesis.getVoices();
  var langCode = _bcp.split('-')[0];
  var picks = voices.filter(function(v) {{ return v.lang.startsWith(langCode); }});
  var neural = picks.filter(function(v) {{
    return /neural|enhanced|premium|natural/i.test(v.name);
  }});
  if (neural.length)      utt.voice = neural[0];
  else if (picks.length)  utt.voice = picks[0];

  utt.onstart = function() {{ _speaking = true;  updateSpeakBtn(true);  }};
  utt.onend   = function() {{ _speaking = false; updateSpeakBtn(false); }};
  utt.onerror = function() {{ _speaking = false; updateSpeakBtn(false); }};

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utt);
}}

function updateSpeakBtn(active) {{
  var btn = document.getElementById('speakBtn');
  if (!btn) return;
  btn.classList.toggle('speaking', active);
  btn.innerHTML = active ? '⏹ &nbsp;Stop reading' : '🔊 Hear weather report';
}}

if (window.speechSynthesis) {{
  window.speechSynthesis.onvoiceschanged = function() {{ window.speechSynthesis.getVoices(); }};
}}
</script>
""", unsafe_allow_html=True)
