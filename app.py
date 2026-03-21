import streamlit as st
import requests
import os
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkyPulse — Weather Forecast",
    page_icon="🌤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── API Keys (set in Streamlit secrets) ───────────────────────────────────────
API_KEY    = os.environ.get("OPENWEATHER_API_KEY", "YOUR_OWM_KEY_HERE")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY",   "YOUR_CLAUDE_KEY_HERE")
BASE_URL   = "https://api.openweathermap.org/data/2.5"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

LANGUAGES = {
    "en":"English","hi":"Hindi","ar":"Arabic","zh_cn":"Chinese","fr":"French",
    "de":"German","es":"Spanish","it":"Italian","ja":"Japanese","ko":"Korean",
    "pt":"Portuguese","ru":"Russian","tr":"Turkish","nl":"Dutch","pl":"Polish",
    "sv":"Swedish","uk":"Ukrainian","id":"Indonesian","th":"Thai","vi":"Vietnamese",
    "bn":"Bengali","gu":"Gujarati","ta":"Tamil","te":"Telugu","mr":"Marathi","ur":"Urdu",
}
OWM_ICONS = {
    "01d":"☀️","01n":"🌙","02d":"⛅","02n":"🌥","03d":"☁️","03n":"☁️",
    "04d":"☁️","04n":"☁️","09d":"🌧","09n":"🌧","10d":"🌦","10n":"🌧",
    "11d":"⛈","11n":"⛈","13d":"❄️","13n":"❄️","50d":"🌫","50n":"🌫",
}
AQI_INFO = {
    1:("Good","🟢","#4ade80"),2:("Fair","🔵","#38bdf8"),
    3:("Moderate","🟡","#facc15"),4:("Poor","🟠","#fb923c"),5:("Very Poor","🔴","#f87171"),
}

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in [("chat_history",[]),("weather_data",None),("last_city",""),
            ("chat_response","__WAITING__"),("last_chat_q","")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Outfit',sans-serif!important}
.stApp{background:#060b14;background-image:
  radial-gradient(ellipse 80% 50% at 20% -10%,rgba(56,189,248,.12) 0%,transparent 60%),
  radial-gradient(ellipse 60% 40% at 80% 110%,rgba(129,140,248,.10) 0%,transparent 60%)}
[data-testid="stSidebar"]{background:#0d1526!important;border-right:1px solid rgba(255,255,255,0.08)}
[data-testid="stSidebar"] *{color:#e2e8f0!important}
h1,h2,h3,h4,h5,h6,p,label,div{color:#e2e8f0}
[data-testid="stTextInput"] input{background:rgba(255,255,255,0.09)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:12px!important;color:#e2e8f0!important;font-family:'Outfit',sans-serif!important}
[data-testid="stTextInput"] input:focus{border-color:#38bdf8!important;box-shadow:0 0 0 3px rgba(56,189,248,.15)!important}
[data-testid="stSelectbox"]>div>div{background:rgba(255,255,255,0.09)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:12px!important;color:#e2e8f0!important}
.stButton>button{background:#38bdf8!important;color:#060b14!important;border:none!important;border-radius:12px!important;font-weight:700!important;font-family:'Outfit',sans-serif!important;padding:10px 24px!important;transition:opacity .2s!important}
.stButton>button:hover{opacity:0.85!important}
[data-testid="metric-container"]{background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:16px!important;padding:16px!important;transition:border-color .2s,transform .2s!important}
[data-testid="metric-container"]:hover{border-color:#38bdf8!important;transform:translateY(-2px)!important}
[data-testid="stMetricValue"]{font-family:'Space Mono',monospace!important;color:#e2e8f0!important}
[data-testid="stMetricLabel"]{color:#64748b!important}
.stProgress>div>div{background:linear-gradient(90deg,#38bdf8,#818cf8)!important;border-radius:99px!important}
.stProgress>div{background:rgba(255,255,255,0.05)!important;border-radius:99px!important}
hr{border-color:rgba(255,255,255,0.08)!important}
[data-testid="stExpander"]{background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:16px!important}
#MainMenu,footer,header{visibility:hidden}
.stRadio>div{flex-direction:row!important;gap:12px}
.stRadio label{color:#e2e8f0!important}
.stSpinner>div{border-top-color:#38bdf8!important}

/* Floating search bar */
.float-search{
  position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:9999;
  display:flex;align-items:center;gap:8px;
  background:rgba(13,21,38,0.94);backdrop-filter:blur(20px);
  border:1px solid rgba(56,189,248,0.3);border-radius:50px;
  padding:7px 12px 7px 20px;min-width:440px;max-width:620px;
  box-shadow:0 8px 32px rgba(0,0,0,0.45),0 0 0 1px rgba(56,189,248,.08)}
.float-search-input{
  flex:1;background:transparent;border:none;outline:none;
  color:#e2e8f0;font-family:'Outfit',sans-serif;font-size:.97rem;font-weight:500}
.float-search-input::placeholder{color:#475569}
.float-btn{
  background:#38bdf8;color:#060b14;border:none;border-radius:50px;
  padding:6px 18px;font-weight:700;font-size:.85rem;cursor:pointer;
  font-family:'Outfit',sans-serif;transition:opacity .2s;white-space:nowrap}
.float-btn:hover{opacity:0.85}
.mic-btn{
  background:rgba(56,189,248,0.1);color:#38bdf8;
  border:1px solid rgba(56,189,248,0.25);border-radius:50%;
  width:34px;height:34px;cursor:pointer;font-size:.9rem;
  display:flex;align-items:center;justify-content:center;
  transition:all .2s;flex-shrink:0;padding:0}
.mic-btn:hover{background:rgba(56,189,248,0.22)}
.mic-btn.listening{background:rgba(239,68,68,.2);color:#ef4444;border-color:rgba(239,68,68,.4);animation:pmicpulse 1s infinite}
@keyframes pmicpulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.3)}50%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}

/* Content top padding */
.main-wrap{padding-top:70px}

/* Hero card */
.hero-card{
  background:linear-gradient(135deg,rgba(56,189,248,.12) 0%,rgba(129,140,248,.08) 100%);
  border:1px solid rgba(56,189,248,.2);border-radius:24px;
  padding:32px;margin-bottom:24px;position:relative;overflow:hidden}
.hero-temp{font-size:5rem;font-weight:700;line-height:1;font-family:'Space Mono',monospace;
  background:linear-gradient(135deg,#fff 30%,#38bdf8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-city{font-size:1.8rem;font-weight:700;color:#e2e8f0}
.hero-desc{font-size:1rem;color:#64748b;margin-top:4px}
.hero-feels{font-size:.9rem;color:#7dd3fc;margin-top:4px}
.badge{display:inline-block;padding:4px 14px;border-radius:50px;font-size:.78rem;font-weight:600;margin:2px}
.badge-blue{background:rgba(56,189,248,.15);color:#38bdf8;border:1px solid rgba(56,189,248,.25)}
.badge-purple{background:rgba(129,140,248,.15);color:#818cf8;border:1px solid rgba(129,140,248,.25)}
.speak-btn{background:rgba(56,189,248,.1);color:#38bdf8;border:1px solid rgba(56,189,248,.25);
  border-radius:8px;padding:5px 14px;cursor:pointer;font-size:.78rem;font-weight:600;
  font-family:'Outfit',sans-serif;transition:background .2s;margin-top:6px}
.speak-btn:hover{background:rgba(56,189,248,.22)}

/* Hourly */
.hourly-container{display:flex;gap:12px;overflow-x:auto;padding:8px 0;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.hourly-card{flex:0 0 80px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 8px;text-align:center;min-width:80px}
.hourly-card:hover{border-color:#38bdf8}
.hourly-time{font-size:.72rem;color:#64748b;font-weight:600}
.hourly-icon{font-size:1.4rem;margin:5px 0}
.hourly-temp{font-size:.9rem;font-weight:700;color:#e2e8f0}
.hourly-pop{font-size:.68rem;color:#7dd3fc;margin-top:3px}

/* Forecast rows */
.forecast-row{display:flex;align-items:center;gap:14px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:14px 18px;margin-bottom:10px;transition:border-color .2s}
.forecast-row:hover{border-color:#38bdf8}
.forecast-day{width:44px;font-weight:600;font-size:.95rem;color:#e2e8f0}
.forecast-icon{font-size:1.5rem}
.forecast-desc{flex:1;font-size:.88rem;color:#64748b}
.forecast-hum{font-size:.8rem;color:#7dd3fc;min-width:44px;text-align:right}
.forecast-temps{font-size:.92rem;font-weight:600;color:#e2e8f0;min-width:90px;text-align:right}
.temp-min-text{color:#64748b;font-weight:400}
.section-hdr{font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;color:#64748b;font-weight:700;margin-bottom:12px;margin-top:4px}

/* Chat FAB */
.chat-fab{
  position:fixed;bottom:28px;right:28px;z-index:9998;
  width:54px;height:54px;border-radius:50%;
  background:linear-gradient(135deg,#38bdf8,#818cf8);
  border:none;cursor:pointer;font-size:1.3rem;
  box-shadow:0 8px 24px rgba(56,189,248,0.38);
  transition:transform .2s,box-shadow .2s}
.chat-fab:hover{transform:scale(1.08);box-shadow:0 12px 32px rgba(56,189,248,0.55)}

/* Chat panel */
.chat-panel{
  position:fixed;bottom:94px;right:28px;z-index:9997;width:350px;
  background:#0d1526;border:1px solid rgba(56,189,248,0.2);border-radius:20px;
  box-shadow:0 24px 64px rgba(0,0,0,0.65);
  flex-direction:column;overflow:hidden;max-height:460px;display:none}
.chat-panel.open{display:flex}
.chat-hdr{
  background:linear-gradient(135deg,rgba(56,189,248,.15),rgba(129,140,248,.1));
  padding:13px 18px;border-bottom:1px solid rgba(255,255,255,0.06);
  display:flex;align-items:center;justify-content:space-between;
  font-weight:700;font-size:.93rem;color:#e2e8f0}
.chat-msgs{
  flex:1;overflow-y:auto;padding:14px;
  display:flex;flex-direction:column;gap:10px;max-height:310px;
  scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.cmsg-user{align-self:flex-end;background:rgba(56,189,248,.15);border:1px solid rgba(56,189,248,.2);border-radius:14px 14px 4px 14px;padding:8px 13px;font-size:.85rem;color:#e2e8f0;max-width:87%}
.cmsg-ai{align-self:flex-start;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:14px 14px 14px 4px;padding:8px 13px;font-size:.85rem;color:#e2e8f0;max-width:87%;line-height:1.5}
.chat-inp-row{padding:10px;border-top:1px solid rgba(255,255,255,0.06);display:flex;gap:8px;align-items:center}
.chat-inp{flex:1;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:7px 12px;color:#e2e8f0;font-family:'Outfit',sans-serif;font-size:.86rem;outline:none}
.chat-inp:focus{border-color:#38bdf8}
.chat-send{background:#38bdf8;color:#060b14;border:none;border-radius:10px;padding:7px 14px;cursor:pointer;font-weight:700;font-size:.85rem;font-family:'Outfit',sans-serif}
.chat-mic{background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.25);border-radius:8px;padding:7px 10px;cursor:pointer;font-size:.85rem}
.chat-mic.listening{background:rgba(239,68,68,.2);color:#ef4444;border-color:rgba(239,68,68,.4);animation:pmicpulse 1s infinite}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_wind_direction(degrees):
    dirs=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(degrees/(360/len(dirs)))%len(dirs)]

def owm_icon(code): return OWM_ICONS.get(code,"🌡")

@st.cache_data(ttl=600,show_spinner=False)
def fetch_weather(city,units,lang):
    params={"q":city,"appid":API_KEY,"units":units,"lang":lang}
    r=requests.get(f"{BASE_URL}/weather",params=params,timeout=10)
    if r.status_code==404: return None,f"City **'{city}'** not found."
    if r.status_code==401: return None,"Invalid API key. Set **OPENWEATHER_API_KEY** in secrets."
    r.raise_for_status()
    current=r.json()
    lat,lon=current["coord"]["lat"],current["coord"]["lon"]
    fr=requests.get(f"{BASE_URL}/forecast",params=params,timeout=10); fr.raise_for_status()
    forecast_raw=fr.json()
    aq_r=requests.get(f"{BASE_URL}/air_pollution",params={"lat":lat,"lon":lon,"appid":API_KEY},timeout=10)
    aq_data=aq_r.json() if aq_r.status_code==200 else None
    daily={}
    for item in forecast_raw["list"]:
        ds,ts=item["dt_txt"].split(" ")
        if ds not in daily and ts=="12:00:00": daily[ds]=item
    if len(daily)<5:
        daily={}
        for item in forecast_raw["list"]:
            ds=item["dt_txt"].split(" ")[0]
            if ds not in daily: daily[ds]=item
    forecast_list=[]
    for ds,item in list(daily.items())[:5]:
        dt=datetime.strptime(ds,"%Y-%m-%d")
        forecast_list.append({"day":dt.strftime("%a"),"temp_max":round(item["main"]["temp_max"]),
            "temp_min":round(item["main"]["temp_min"]),"description":item["weather"][0]["description"].title(),
            "icon":item["weather"][0]["icon"],"pop":round(item.get("pop",0)*100)})
    hourly_list=[{"time":datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
        "temp":round(item["main"]["temp"]),"icon":item["weather"][0]["icon"],
        "pop":round(item.get("pop",0)*100)} for item in forecast_raw["list"][:8]]
    aqi_value=aqi_label=aqi_color=None
    if aq_data and aq_data.get("list"):
        av=aq_data["list"][0]["main"]["aqi"]; aqi_value=av
        aqi_label,_,aqi_color=AQI_INFO.get(av,("Unknown","⚪","#fff"))
    sym="°C" if units=="metric" else "°F"; speed="m/s" if units=="metric" else "mph"
    return {"city":current["name"],"country":current["sys"]["country"],"lat":lat,"lon":lon,
        "temp":round(current["main"]["temp"]),"feels_like":round(current["main"]["feels_like"]),
        "temp_min":round(current["main"]["temp_min"]),"temp_max":round(current["main"]["temp_max"]),
        "humidity":current["main"]["humidity"],"pressure":current["main"]["pressure"],
        "visibility":round(current.get("visibility",0)/1000,1),
        "wind_speed":round(current["wind"]["speed"]),
        "wind_direction":get_wind_direction(current["wind"].get("deg",0)),
        "description":current["weather"][0]["description"].title(),
        "icon":current["weather"][0]["icon"],"clouds":current["clouds"]["all"],
        "sunrise":datetime.fromtimestamp(current["sys"]["sunrise"]).strftime("%H:%M"),
        "sunset":datetime.fromtimestamp(current["sys"]["sunset"]).strftime("%H:%M"),
        "sym":sym,"speed":speed,"units":units,"lang":lang,"lang_name":LANGUAGES.get(lang,"English"),
        "aqi":aqi_value,"aqi_label":aqi_label,"aqi_color":aqi_color,
        "forecast":forecast_list,"hourly":hourly_list},None

def ask_claude(question,weather_context=""):
    if CLAUDE_KEY=="YOUR_CLAUDE_KEY_HERE":
        return "Add ANTHROPIC_API_KEY to Streamlit secrets to enable AI chat."
    try:
        system=(
            "You are SkyBot, a friendly AI weather assistant inside SkyPulse. "
            "Answer concisely (2-3 sentences max unless more detail is needed). "
            "Use weather context when provided.\n\nWeather context:\n"+weather_context
            if weather_context else
            "You are SkyBot, a friendly AI weather assistant inside SkyPulse. Answer concisely."
        )
        resp=requests.post(CLAUDE_URL,
            headers={"x-api-key":CLAUDE_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":300,
                "system":system,"messages":[{"role":"user","content":question}]},timeout=15)
        return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"Error: {e}"

# ── Sidebar (units + language; accessible via hamburger ☰) ────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")
    st.markdown("**🌡 Temperature Units**")
    unit_choice=st.radio("Units",["°C (Metric)","°F (Imperial)"],index=0,label_visibility="collapsed")
    st.markdown("**🌐 Language**")
    lang_names=list(LANGUAGES.values()); lang_codes=list(LANGUAGES.keys())
    lang_choice=st.selectbox("Language",lang_names,index=0,label_visibility="collapsed")
    selected_lang=lang_codes[lang_names.index(lang_choice)]
    st.markdown("---")
    st.markdown("""<div style='color:#64748b;font-size:.78rem;line-height:1.9'>
    <b style='color:#38bdf8'>SkyPulse Features</b><br>
    ☀️ Current weather &amp; stats<br>⏱ 24-hour hourly forecast<br>
    📅 5-day daily forecast<br>🌿 Air Quality Index<br>
    🎤 Voice city search<br>🔊 Speak weather aloud<br>
    🤖 AI weather chatbot<br>🗺 Interactive map
    </div>""",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='color:#64748b;font-size:.73rem'>Powered by <a href='https://openweathermap.org' style='color:#38bdf8'>OpenWeatherMap</a> + Claude AI</div>",unsafe_allow_html=True)

units="metric" if "°C" in unit_choice else "imperial"

# ── Chat question handler ──────────────────────────────────────────────────────
chat_q=st.text_input("chatq","",key="chatq_input",label_visibility="collapsed")
if chat_q and chat_q!=st.session_state.last_chat_q:
    st.session_state.last_chat_q=chat_q
    ctx=""
    if st.session_state.weather_data:
        d2=st.session_state.weather_data
        ctx=(f"City: {d2['city']}, {d2['country']}\nTemp: {d2['temp']}{d2['sym']} "
             f"(feels {d2['feels_like']}{d2['sym']})\nWeather: {d2['description']}\n"
             f"Humidity: {d2['humidity']}%, Wind: {d2['wind_speed']} {d2['speed']} {d2['wind_direction']}\n"
             f"AQI level: {d2.get('aqi_label','N/A')}")
    answer=ask_claude(chat_q,ctx)
    st.session_state.chat_history.append({"r":"user","t":chat_q})
    st.session_state.chat_history.append({"r":"ai","t":answer})
    st.session_state.chat_response=answer

# ── Floating search bar ────────────────────────────────────────────────────────
cur=st.session_state.last_city
st.markdown(f"""
<div class="float-search" id="float-search">
  <span style="color:#38bdf8;font-size:1.05rem;flex-shrink:0">🌤</span>
  <input id="fsi" class="float-search-input" type="text"
    placeholder="Search any city… (or press 🎤)"
    value="{cur}"
    onkeydown="if(event.key==='Enter')fsSearch()" />
  <button class="mic-btn" id="micbtn" onclick="toggleMic()" title="Voice search">🎤</button>
  <button class="float-btn" onclick="fsSearch()">Search</button>
</div>
""",unsafe_allow_html=True)

# Hidden Streamlit text_input that receives city from JS
city_input=st.text_input("city","",key="city_bridge",label_visibility="collapsed",
    placeholder="Type city name…")

# ── JS block: voice search, TTS, chat panel ───────────────────────────────────
chat_msgs_js="["
for m in st.session_state.chat_history[-20:]:
    safe=m['t'].replace('"','\\"').replace('\n',' ')
    chat_msgs_js+=f'{{r:"{m["r"]}",t:"{safe}"}},'
chat_msgs_js+="]"
chat_resp_safe=(st.session_state.chat_response or "__WAITING__").replace('"','\\"').replace('\n',' ')

st.markdown(f"""
<script>
// ── floating search bridge ────────────────────────────────────────────────────
function fsSearch(){{
  var v=document.getElementById('fsi').value.trim();
  if(!v)return;
  var inp=window.parent.document.querySelectorAll('input[type="text"]');
  for(var i=0;i<inp.length;i++){{
    if(inp[i].getAttribute('aria-label')==='city'||
       inp[i].placeholder==='Type city name…'){{
      var nativeInputValueSetter=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;
      nativeInputValueSetter.call(inp[i],v);
      inp[i].dispatchEvent(new Event('input',{{bubbles:true}}));
      break;
    }}
  }}
  // Also find by data-testid pattern fallback
  var allInp=window.parent.document.getElementsByTagName('input');
  for(var j=0;j<allInp.length;j++){{
    if(allInp[j].value===v){{
      allInp[j].dispatchEvent(new Event('change',{{bubbles:true}}));
    }}
  }}
}}

// ── Voice search ──────────────────────────────────────────────────────────────
var recog=null,isListen=false;
function initRecog(){{
  if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){{
    alert('Voice search needs Chrome or Edge browser.');return null;
  }}
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  var r=new SR();r.lang='en-US';r.interimResults=false;r.maxAlternatives=1;
  r.onresult=function(e){{
    var city=e.results[0][0].transcript
      .replace(/^(weather in|weather for|show me|search|check)\\s+/i,'').trim();
    document.getElementById('fsi').value=city;
    showVoiceBanner(city);
    stopListen();
  }};
  r.onerror=function(){{stopListen();}};
  r.onend=function(){{stopListen();}};
  return r;
}}
function startListen(){{recog=initRecog();if(!recog)return;isListen=true;recog.start();
  var b=document.getElementById('micbtn');if(b){{b.classList.add('listening');b.textContent='⏹';}}
  var cb=document.getElementById('chat-micbtn');if(cb){{cb.classList.add('listening');}}}}
function stopListen(){{isListen=false;if(recog)try{{recog.stop();}}catch(e){{}}
  var b=document.getElementById('micbtn');if(b){{b.classList.remove('listening');b.textContent='🎤';}}
  var cb=document.getElementById('chat-micbtn');if(cb){{cb.classList.remove('listening');}}}}
function toggleMic(){{if(isListen)stopListen();else startListen();}}

var vRecogForChat=null,chatListening=false;
function startChatMic(){{
  if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){{
    alert('Voice needs Chrome/Edge');return;
  }}
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  vRecogForChat=new SR();vRecogForChat.lang='en-US';vRecogForChat.interimResults=false;
  chatListening=true;
  var cb=document.getElementById('chat-micbtn');if(cb)cb.classList.add('listening');
  vRecogForChat.onresult=function(e){{
    var t=e.results[0][0].transcript;
    var ci=document.getElementById('chat-inp');if(ci)ci.value=t;
    chatListening=false;if(cb)cb.classList.remove('listening');
  }};
  vRecogForChat.onerror=vRecogForChat.onend=function(){{
    chatListening=false;if(cb)cb.classList.remove('listening');
  }};
  vRecogForChat.start();
}}

function showVoiceBanner(city){{
  var b=document.getElementById('vbanner');
  if(b){{b.innerHTML='🎤 Heard: <b>'+city+'</b> — click Search';b.style.display='block';
    setTimeout(function(){{b.style.display='none';}},5000);}}
}}

// ── TTS ───────────────────────────────────────────────────────────────────────
function speakText(txt){{
  if(!window.speechSynthesis){{alert('TTS not supported in this browser.');return;}}
  window.speechSynthesis.cancel();
  var u=new SpeechSynthesisUtterance(txt);u.rate=0.95;u.pitch=1;u.lang='en-US';
  window.speechSynthesis.speak(u);
}}

// ── Chat panel ────────────────────────────────────────────────────────────────
var chatOpen=false;
function toggleChat(){{
  chatOpen=!chatOpen;
  var p=document.getElementById('chat-panel');
  if(p){{p.style.display=chatOpen?'flex':'none';}}
  if(chatOpen){{
    scrollChatToBottom();
    setTimeout(function(){{var ci=document.getElementById('chat-inp');if(ci)ci.focus();}},120);
  }}
}}

function scrollChatToBottom(){{
  var m=document.getElementById('chat-msgs');if(m)m.scrollTop=m.scrollHeight;
}}

function sendChat(){{
  var ci=document.getElementById('chat-inp');
  if(!ci||!ci.value.trim())return;
  var msg=ci.value.trim();ci.value='';
  appendChatMsg(msg,'user');
  var tid='typing'+Date.now();
  appendChatMsg('⟳ Thinking…','ai',tid);

  // Bridge to Streamlit via the chatq input
  var inp=window.parent.document.querySelectorAll('input[type="text"]');
  for(var i=0;i<inp.length;i++){{
    if(inp[i].getAttribute('aria-label')==='chatq'||inp[i].placeholder===''){{
      try{{
        var s=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;
        s.call(inp[i],msg);
        inp[i].dispatchEvent(new Event('input',{{bubbles:true}}));
        break;
      }}catch(e){{}}
    }}
  }}

  // Poll hidden output div for Streamlit response
  var tries=0;
  var poll=setInterval(function(){{
    var out=document.getElementById('chat-out');
    if(out&&out.textContent&&out.textContent!=='__WAITING__'){{
      clearInterval(poll);
      var tel=document.getElementById(tid);if(tel)tel.remove();
      appendChatMsg(out.textContent,'ai');
      out.textContent='__WAITING__';
    }}
    if(++tries>90)clearInterval(poll);
  }},500);
}}

function appendChatMsg(text,role,id){{
  var m=document.getElementById('chat-msgs');if(!m)return;
  var d=document.createElement('div');
  d.className=role==='user'?'cmsg-user':'cmsg-ai';
  if(id)d.id=id;d.textContent=text;
  m.appendChild(d);scrollChatToBottom();
}}

// Pre-populate chat history on load
(function(){{
  var history={chat_msgs_js};
  if(history.length===0){{
    appendChatMsg('👋 Hi! I am SkyBot. Ask me anything about the weather!','ai');
  }}else{{
    history.forEach(function(m){{appendChatMsg(m.t,m.r);}});
  }}
}})();

// Key handler for chat input
document.addEventListener('keydown',function(e){{
  if(e.key==='Enter'&&document.activeElement&&document.activeElement.id==='chat-inp'){{
    sendChat();
  }}
}});
</script>

<!-- Voice banner -->
<div id="vbanner" style="display:none;background:rgba(56,189,248,0.09);border:1px solid rgba(56,189,248,.2);
  border-radius:10px;padding:8px 16px;margin-top:4px;font-size:.88rem;color:#7dd3fc"></div>

<!-- Hidden chat response output (Streamlit writes here) -->
<div id="chat-out" style="display:none">{chat_resp_safe}</div>
""",unsafe_allow_html=True)

# ── Main content ───────────────────────────────────────────────────────────────
st.markdown('<div class="main-wrap">',unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;color:#38bdf8;font-family:Outfit,sans-serif;margin-bottom:4px'>🌤 SkyPulse</h1>",unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#64748b;margin-bottom:24px'>Real-time weather · 🎤 Voice search · 🔊 Voice answers · 🤖 AI chatbot · Open ☰ for settings</p>",unsafe_allow_html=True)

if not city_input:
    st.markdown("""
    <div style='text-align:center;padding:50px 20px;color:#64748b'>
        <div style='font-size:4rem;margin-bottom:16px'>🌍</div>
        <h2 style='color:#e2e8f0;font-size:1.5rem;margin-bottom:8px'>Welcome to SkyPulse</h2>
        <p>Type a city in the <b style='color:#38bdf8'>search bar above</b> and press Enter — or click 🎤 to speak</p>
        <p style='margin-top:8px;font-size:.84rem;color:#475569'>Open <b style='color:#38bdf8'>☰</b> sidebar to change units &amp; language &nbsp;·&nbsp; Click 🤖 for AI chat</p>
        <div style='margin-top:28px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap'>
            <span style='background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.2);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#7dd3fc'>🎤 Voice city search</span>
            <span style='background:rgba(129,140,248,.08);border:1px solid rgba(129,140,248,.2);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#a5b4fc'>🔊 Speak weather aloud</span>
            <span style='background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.2);border-radius:50px;padding:6px 16px;font-size:.82rem;color:#86efac'>🤖 AI weather chatbot</span>
        </div>
    </div>""",unsafe_allow_html=True)
    st.stop()

with st.spinner(f"Fetching weather for **{city_input}**…"):
    try:
        data,err=fetch_weather(city_input.strip(),units,selected_lang)
    except Exception as e:
        st.error(f"❌ Network error: {e}"); st.stop()

if err:
    st.error(f"❌ {err}"); st.stop()

st.session_state.weather_data=data
st.session_state.last_city=city_input
d=data; sym=d["sym"]; spd=d["speed"]

spoken=(f"Weather in {d['city']}, {d['country']}. "
    f"Currently {d['temp']} degrees {'Celsius' if units=='metric' else 'Fahrenheit'}, "
    f"feels like {d['feels_like']}. {d['description']}. "
    f"Humidity {d['humidity']} percent, wind {d['wind_speed']} {spd} {d['wind_direction']}. "
    f"Today's high {d['temp_max']}, low {d['temp_min']}.")

st.markdown(f"""
<div class="hero-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <div class="hero-city">{owm_icon(d['icon'])} {d['city']}, {d['country']}</div>
      <div class="hero-desc">{d['lat']:.2f}°, {d['lon']:.2f}° &nbsp;·&nbsp; 🌐 {d['lang_name']}</div>
    </div>
    <div style="text-align:right">
      <div><span class="badge badge-blue">{d['description']}</span>
      <span class="badge badge-purple">H:{d['temp_max']}{sym} L:{d['temp_min']}{sym}</span></div>
      <button class="speak-btn" onclick="speakText('{spoken}')">🔊 Speak weather</button>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-top:20px">
    <div style="font-size:4rem;filter:drop-shadow(0 4px 12px rgba(56,189,248,.4))">{owm_icon(d['icon'])}</div>
    <div>
      <div class="hero-temp">{d['temp']}{sym}</div>
      <div class="hero-feels">Feels like {d['feels_like']}{sym}</div>
    </div>
  </div>
</div>""",unsafe_allow_html=True)

c1,c2,c3,c4,c5,c6=st.columns(6)
c1.metric("💧 Humidity",f"{d['humidity']}%")
c2.metric("💨 Wind",f"{d['wind_speed']} {spd}",d['wind_direction'])
c3.metric("🌡 Pressure",f"{d['pressure']} hPa")
c4.metric("👁 Visibility",f"{d['visibility']} km")
c5.metric("☁️ Cloud Cover",f"{d['clouds']}%")
if d['aqi']:
    lbl,emj,_=AQI_INFO.get(d['aqi'],("Unknown","⚪","#fff"))
    c6.metric("🌿 Air Quality",f"{emj} {lbl}",f"{d['aqi']}/5")

st.markdown("<br>",unsafe_allow_html=True)

col_sun,col_aqi=st.columns(2)
with col_sun:
    st.markdown('<div class="section-hdr">🌅 Sunrise &amp; Sunset</div>',unsafe_allow_html=True)
    s1,s2=st.columns(2); s1.metric("🌅 Sunrise",d['sunrise']); s2.metric("🌇 Sunset",d['sunset'])
with col_aqi:
    if d['aqi']:
        st.markdown('<div class="section-hdr">🌿 Air Quality Index</div>',unsafe_allow_html=True)
        lbl,emj,col=AQI_INFO.get(d['aqi'],("Unknown","⚪","#fff"))
        st.markdown(f"<div style='font-size:1.1rem;font-weight:600;margin-bottom:8px'>{emj} <span style='color:{col}'>{lbl}</span> <span style='color:#64748b;font-size:.85rem'>({d['aqi']}/5)</span></div>",unsafe_allow_html=True)
        st.progress(d['aqi']/5)

st.markdown("<br>",unsafe_allow_html=True)
st.markdown('<div class="section-hdr">⏱ 24-Hour Forecast</div>',unsafe_allow_html=True)
hhtml='<div class="hourly-container">'
for h in d['hourly']:
    pp=f'<div class="hourly-pop">💧{h["pop"]}%</div>' if h['pop'] else ''
    hhtml+=f'<div class="hourly-card"><div class="hourly-time">{h["time"]}</div><div class="hourly-icon">{owm_icon(h["icon"])}</div><div class="hourly-temp">{h["temp"]}{sym}</div>{pp}</div>'
hhtml+='</div>'; st.markdown(hhtml,unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)
st.markdown('<div class="section-hdr">📅 5-Day Forecast</div>',unsafe_allow_html=True)
fhtml=""
for f in d['forecast']:
    pt=f"💧{f['pop']}%" if f['pop'] else ""
    fhtml+=f'<div class="forecast-row"><div class="forecast-day">{f["day"]}</div><div class="forecast-icon">{owm_icon(f["icon"])}</div><div class="forecast-desc">{f["description"]}</div><div class="forecast-hum">{pt}</div><div class="forecast-temps">{f["temp_max"]}{sym} <span class="temp-min-text">/ {f["temp_min"]}{sym}</span></div></div>'
st.markdown(fhtml,unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)
st.markdown('<div class="section-hdr">🗺 Location Map</div>',unsafe_allow_html=True)
map_url=(f"https://www.openstreetmap.org/export/embed.html"
    f"?bbox={d['lon']-1}%2C{d['lat']-1}%2C{d['lon']+1}%2C{d['lat']+1}"
    f"&layer=mapnik&marker={d['lat']}%2C{d['lon']}")
st.markdown(f'<div style="border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08)"><iframe src="{map_url}" width="100%" height="260" frameborder="0" style="display:block"></iframe></div>',unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)
with st.expander("🔬 Raw Weather Data (JSON)"):
    st.json({k:v for k,v in d.items() if k not in ("forecast","hourly")})

st.markdown('</div>',unsafe_allow_html=True)

# ── Floating chat panel + FAB ──────────────────────────────────────────────────
st.markdown("""
<div id="chat-panel" class="chat-panel" style="display:none;flex-direction:column">
  <div class="chat-hdr">
    <span>🤖 SkyBot — AI Weather Chat</span>
    <button onclick="toggleChat()" style="background:none;border:none;color:#64748b;cursor:pointer;font-size:1rem;padding:0">✕</button>
  </div>
  <div class="chat-msgs" id="chat-msgs"></div>
  <div class="chat-inp-row">
    <button class="chat-mic" id="chat-micbtn" onclick="startChatMic()" title="Voice input">🎤</button>
    <input id="chat-inp" class="chat-inp" placeholder="Ask about weather…" />
    <button class="chat-send" onclick="sendChat()">Send</button>
  </div>
</div>
<button class="chat-fab" onclick="toggleChat()" title="Chat with SkyBot AI">🤖</button>
""",unsafe_allow_html=True)
