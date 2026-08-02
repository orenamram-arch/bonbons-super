import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, date, datetime
import math
import urllib.parse
import requests
import json
import os

# הגדרת תצורת העמוד (חייב להיות ראשון)
st.set_page_config(page_title="תכנון טיול משפחתי לגאורגיה", page_icon="🇬🇪", layout="wide")

# ==========================================
# ניהול קובץ שמירה מקומי (JSON) ותיקיית מסמכים
# ==========================================
DATA_FILE = "georgia_trip_data.json"
DOCS_DIR = "uploaded_docs"

if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass

# טעינת נתונים קיימים מקובץ השמירה
saved_data = load_data()

# הגדרת תאריך תחילת הטיול (עם שמירה)
if 'start_date' not in st.session_state:
    if saved_data and "start_date" in saved_data:
        try:
            st.session_state.start_date = date.fromisoformat(saved_data["start_date"])
        except:
            st.session_state.start_date = date.today()
    else:
        st.session_state.start_date = date.today()

if 'expenses' not in st.session_state:
    if saved_data and "expenses" in saved_data:
        st.session_state.expenses = saved_data["expenses"]
    else:
        st.session_state.expenses = [
            {"id": 1, "desc": "מונית משדה התעופה", "category": "תחבורה", "amount": 50, "payer": "אני"},
            {"id": 2, "desc": "ארוחת ערב ראשונה", "category": "אוכל", "amount": 120, "payer": "אני"}
        ]

if 'packing_list' not in st.session_state:
    if saved_data and "packing_list" in saved_data:
        st.session_state.packing_list = saved_data["packing_list"]
    else:
        st.session_state.packing_list = [
            {"item": "דרכונים וביטוח רפואי", "checked": True},
            {"item": "כרטיסי טיסה ושוברים למלונות", "checked": True},
            {"item": "כסף מזומן (דולרים חדשים + לארי)", "checked": False},
            {"item": "תרופות אישיות ועזרה ראשונה", "checked": False},
            {"item": "מתאמים לחשמל ובנקים ניידים", "checked": False},
            {"item": "מעילים חמים (לגודאורי וקזבגי)", "checked": False},
            {"item": "נעלי הליכה נוחות", "checked": False}
        ]

if 'tasks_list' not in st.session_state:
    if saved_data and "tasks_list" in saved_data:
        st.session_state.tasks_list = saved_data["tasks_list"]
    else:
        st.session_state.tasks_list = [
            {"task": "הזמנת רכב השכרה", "checked": True},
            {"task": "וידוא תוקף דרכונים (מעל חצי שנה)", "checked": True},
            {"task": "רכישת חבילת גלישה לחו\"ל", "checked": False},
            {"task": "המרת דולרים חדשים מזומן", "checked": False},
            {"task": "הורדת אפליקציות ניווט וחניה (Waze, ParkMate)", "checked": False}
        ]

if 'journal_notes' not in st.session_state:
    if saved_data and "journal_notes" in saved_data:
        st.session_state.journal_notes = saved_data["journal_notes"]
    else:
        st.session_state.journal_notes = "כאן תוכל לכתוב תובנות, שמות של מסעדות סודיות שמצאתם בדרך, או חוויות מהשטח..."

if 'uploaded_files_meta' not in st.session_state:
    if saved_data and "uploaded_files_meta" in saved_data:
        st.session_state.uploaded_files_meta = saved_data["uploaded_files_meta"]
    else:
        st.session_state.uploaded_files_meta = []

if 'contacts_list' not in st.session_state:
    if saved_data and "contacts_list" in saved_data:
        st.session_state.contacts_list = saved_data["contacts_list"]
    else:
        st.session_state.contacts_list = [
            {"name": "מוקד חירום כללי בגאורגיה", "phone": "112", "role": "משטרה, אמבולנס, כיבוי"},
            {"name": "שגרירות ישראל בטביליסי", "phone": "+995 32 255 65 00", "role": "שגרירות / חירום מדיני"},
            {"name": "חברת השכרת רכב", "phone": "+995 ...", "role": "תמיכה ותקלות רכב"},
            {"name": "ביטוח רפואי (מוקד חו\"ל)", "phone": "+972 ...", "role": "פתיחת תביעות וייעוץ רפואי"}
        ]

if 'total_budget_gel' not in st.session_state:
    if saved_data and "total_budget_gel" in saved_data:
        st.session_state.total_budget_gel = saved_data["total_budget_gel"]
    else:
        st.session_state.total_budget_gel = 4000.0

def persist_all():
    """שומר את כל הנתונים הדינאמיים לקובץ המקומי לצמיתות"""
    data = {
        "start_date": st.session_state.start_date.isoformat(),
        "expenses": st.session_state.expenses,
        "packing_list": st.session_state.packing_list,
        "tasks_list": st.session_state.tasks_list,
        "journal_notes": st.session_state.journal_notes,
        "uploaded_files_meta": st.session_state.uploaded_files_meta,
        "contacts_list": st.session_state.contacts_list,
        "total_budget_gel": st.session_state.total_budget_gel
    }
    save_data(data)

# ==========================================
# פונקציות עזר
# ==========================================
def calculate_travel_estimation(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    aerial_distance = R * c
    road_distance = aerial_distance * 1.4 
    estimated_hours = road_distance / 55.0 
    
    return road_distance, estimated_hours

def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            temp = data["current_weather"]["temperature"]
            wind = data["current_weather"]["windspeed"]
            return f"{temp}°C, רוח: {wind} קמ\"ש"
    except:
        pass
    return "לא ניתן לטעון תחזית כרגע"

# ==========================================
# עיצוב מותאם אישית (CSS) - פתרון גלילה לנייד ו-RTL
# ==========================================
st.markdown("""
<style>
    .block-container { direction: rtl; text-align: right; }
    
    /* תיקון גלילה בסרגל הצד במובייל */
    section[data-testid="stSidebar"] {
        overflow-y: auto !important;
    }
    section[data-testid="stSidebar"] > div {
        height: 100%;
        overflow-y: auto !important;
    }

    div[data-testid="metric-container"] { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important; border: 1px solid #dee2e6; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; border-right: 5px solid #28a745; }
    div[data-testid="metric-container"] label, div[data-testid="metric-container"] div { color: #111111 !important; }
    .site-card { background-color: #ffffff !important; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.04); margin-bottom: 20px; border-right: 6px solid #ff4b4b; }
    .site-card h2, .site-card p, .site-card b { color: #222222 !important; }
    .date-badge { background-color: #e3f2fd; color: #1565c0; padding: 4px 10px; border-radius: 15px; font-size: 0.9em; font-weight: bold; margin-right: 10px; }
    .info-box { background-color: #f8f9fa; border-right: 4px solid #17a2b8; padding: 10px 15px; border-radius: 8px; margin-top: 10px; font-size: 0.95em; }
    .countdown-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

st.title("🇬🇪 דשבורד טיול משפחתי לגאורגיה")
st.markdown("ניהול מסלול מלא, תקציב הוצאות, פיצול תשלומים, ציוד ארוז, משימות מנהליות, יומן מסע וניהול מסמכים ואנשי קשר.")

# ==========================================
# ווידג'ט ספירה לאחור (Countdown) בראש העמוד
# ==========================================
today_date = date.today()
delta_days = (st.session_state.start_date - today_date).days
if delta_days > 0:
    st.markdown(f"""
    <div class="countdown-box">
        ⏳ עוד {delta_days} ימים בדיוק לתחילת ההרפתקה בגאורגיה! (מתחיל ב-{st.session_state.start_date.strftime('%d/%m/%Y')})
    </div>
    """, unsafe_allow_html=True)
elif delta_days == 0:
    st.markdown("""
    <div class="countdown-box" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
        ✈️ הטיול מתחיל היום! סעו לשלום ותעשו חיים!
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="countdown-box" style="background: linear-gradient(135deg, #4ca1af 0%, #c4e0e5 100%); color: #333;">
        🌟 הטיול בעיצומו או כבר הסתיים! מקווים שנהניתם מכל רגע.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# מסד הנתונים המלא של הטיול
# ==========================================
itinerary = [
    {
        "day": 1, "region": "באטומי (חוף וטיילת)", "site": "שדרות באטומי (Batumi Boulevard)", "hours": "פתוח 24/7", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 2.5, "travel_time": 0.0, "icon": "🌴", "lat": 41.6530, "lon": 41.6360, 
        "details": "טיול רגלי או רכיבה לאורך הטיילת המרשימה (7 ק\"מ).",
        "parking": "חניה עירונית מוסדרת בבאטומי.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Retro (מפורסם בזכות האצ'פורי אג'רולי)", "Fanfan (אוכל אירופאי וגאורגי מעוצב)"]
    },
    {
        "day": 1, "region": "באטומי (חוף וטיילת)", "site": "פסל עלי ונינו (Ali and Nino)", "hours": "פתוח 24/7", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 0.5, "travel_time": 0.3, "icon": "🗿", "lat": 41.6556, "lon": 41.6394, 
        "details": "צפייה בפסל הדינמי המפורסם על קו המים.",
        "parking": "חניה ציבורית סמוך לנמל.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Chef's Grill", "Batumeti"]
    },
    {
        "day": 2, "region": "באטומי (אטרקציות)", "site": "הדולפינריום של באטומי", "hours": "16:00 / 19:00", 
        "adult_cost": 25, "child_cost": 25, "activity_hours": 2.0, "travel_time": 0.4, "icon": "🐬", "lat": 41.6475, "lon": 41.6231, 
        "details": "מופע דולפינים מרהיב וחווייתי.",
        "parking": "חניון סביב פארק 6 במאי.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Restaurant 360 (במלון שירטון הסמוך)", "Laguna (מאפיית פחמימות מיתולוגית)"]
    },
    {
        "day": 2, "region": "באטומי (אטרקציות)", "site": "רכבל ארגו (Argo Cable Car)", "hours": "10:00 - 22:00", 
        "adult_cost": 30, "child_cost": 15, "activity_hours": 1.5, "travel_time": 0.3, "icon": "🚡", "lat": 41.6472, "lon": 41.6455, "details": "עלייה לתצפית פנורמית מרהיבה.",
        "parking": "חניון רשמי של הרכבל.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Argo Cafe (בראש ההר)", "Old Boulevard"]
    },
    {
        "day": 2, "region": "באטומי (אטרקציות)", "site": "הגנים הבוטניים של באטומי", "hours": "09:00 - 19:30", 
        "adult_cost": 30, "child_cost": 30, "activity_hours": 3.0, "travel_time": 0.4, "icon": "🌳", "lat": 41.6963, "lon": 41.7163, "details": "סיור בטבע ירוק ועשיר הנושק לים.",
        "parking": "חניון בכניסה הראשית לגנים.",
        "parking_app": "תשלום במקום", "parking_link": "",
        "restaurants": ["Green Cape Cafe", "מסעדות דגים מקומיות בחוף מחירינגי"]
    },
    {
        "day": 3, "region": "מרטווילי ופרומתאוס", "site": "מערת פרומתאוס (Prometheus Cave)", "hours": "10:00 - 17:00", 
        "adult_cost": 40, "child_cost": 40, "activity_hours": 2.5, "travel_time": 2.0, "icon": "🦇", "lat": 42.3768, "lon": 42.6009, "details": "מערת נטיפים תת-קרקעית מרהיבה.",
        "parking": "חניון מסודר וחינמי של מתחם המערה.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Prometheus Cafe", "מסעדות כפריות באזור צקלטובו (Tskaltubo)"]
    },
    {
        "day": 3, "region": "מרטווילי ופרומתאוס", "site": "קניון מרטווילי (Martvili Canyon)", "hours": "10:00 - 17:30", 
        "adult_cost": 32.25, "child_cost": 32.25, "activity_hours": 2.5, "travel_time": 1.0, "icon": "🛶", "lat": 42.4578, "lon": 42.3767, "details": "שייט בסירות מתנפחות בתוך קניון מים.",
        "parking": "חניון מוסדר של האתר (חינם).",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Dadiani Cafe (בתוך הקניון)", "Oda Family Winery (אוכל ביתי מנגרלואי אותנטי בהזמנה מראש)"]
    },
    {
        "day": 4, "region": "טביליסי", "site": "פארק מתאצמינדה (Mtatsminda Park)", "hours": "11:00 - 22:00", 
        "adult_cost": 10, "child_cost": 10, "activity_hours": 3.5, "travel_time": 0.5, "icon": "🎢", "lat": 41.6946, "lon": 44.7865, "details": "פארק שעשועים בראש ההר המשקיף על טביליסי.",
        "parking": "חניון עליון בפארק.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Funicular Restaurant (מסעדה יוקרתית עם נוף מטורף)", "Doner House"]
    },
    {
        "day": 4, "region": "טביליסי", "site": "רכבל ומצודת נריקלה (Narikala)", "hours": "10:00 - 22:00", 
        "adult_cost": 5, "child_cost": 5, "activity_hours": 1.5, "travel_time": 0.3, "icon": "🏰", "lat": 41.6881, "lon": 44.8093, "details": "רכבל, מצודה ופסל אמא גאורגיה.",
        "parking": "חניה עירונית באזור Rike Park.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Machakhela (כיכר הבמבה)", "Samikitno (פתוח 24/7, אוכל גאורגי מעולה)"]
    },
    {
        "day": 5, "region": "דשבשי + קחתי", "site": "גשר היהלום בדשבשי", "hours": "10:00 - 19:00", 
        "adult_cost": 49, "child_cost": 49, "activity_hours": 2.5, "travel_time": 2.0, "icon": "💎", "lat": 41.5975, "lon": 44.0253, "details": "גשר זכוכית שקוף מעל קניון עמוק.",
        "parking": "חניון עפר מסודר בכניסה למתחם.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Diamond Bridge Panorama Restaurant (מסעדה תלויה עם נוף לקניון)"]
    },
    {
        "day": 5, "region": "דשבשי + קחתי", "site": "מנזר בודבה ועיירת האהבה סיגנאגי", "hours": "שעות יום", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 2.0, "travel_time": 1.5, "icon": "⛪", "lat": 41.6116, "lon": 45.9333, "details": "חומות ציוריות, סמטאות אבן ונוף.",
        "parking": "חניה מוסדרת בכניסה למנזר וברחובות סיגנאגי.",
        "parking_app": "חניה מקומית", "parking_link": "",
        "restaurants": ["Pheasant's Tears (יקב ומסעדה אורגנית מומלצת בסיגנאגי)", "Okro's Wine"]
    },
    {
        "day": 5, "region": "דשבשי + קחתי", "site": "יקב חארבה (Khareba)", "hours": "10:00 - 18:00", 
        "adult_cost": 25, "child_cost": 10, "activity_hours": 1.5, "travel_time": 0.5, "icon": "🍇", "lat": 41.9366, "lon": 45.8361, "details": "מנהרות אבן לאחסון יין וטעימות.",
        "parking": "חניון ענק ומסודר של היקב.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Tunnel Restaurant (בתוך המנהרות של היקב)", "Kindzmarauli Marani (בעיר קוור렐ิ)"]
    },
    {
        "day": 6, "region": "הדרך הצבאית וגודאורי", "site": "מצודת אננורי ומאגר ז'ינוואלי", "hours": "09:00 - 19:00", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 1.0, "travel_time": 1.5, "icon": "🌊", "lat": 42.1643, "lon": 44.7032, "details": "אגם טורקיז ומצודה היסטורית שמורה.",
        "parking": "חניה לצד הדרך / חניון עפר ליד המצודה.",
        "parking_app": "תשלום במקום", "parking_link": "",
        "restaurants": ["Pasanauri Khinkali House (בדרך, מומלץ לעצור לחינקלי)", "Ananuri Cafe"]
    },
    {
        "day": 6, "region": "הדרך הצבאית וגודאורי", "site": "אנדרטת גודאורי + רכבת הרים", "hours": "שעות היום", 
        "adult_cost": 20, "child_cost": 20, "activity_hours": 2.0, "travel_time": 1.0, "icon": "🛷", "lat": 42.4925, "lon": 44.4533, "details": "תצפית נוף וגלישה בקרוניות הרים.",
        "parking": "חניון רחב ידיים לצד האנדרטה.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Gudauri Lodge Restaurant", "Cafe Quadra"]
    },
    {
        "day": 7, "region": "קזבגי (סטפנצמינדה)", "site": "כנסיית גרגטי", "hours": "אור יום", 
        "adult_cost": 60, "child_cost": 60, "activity_hours": 2.5, "travel_time": 1.0, "icon": "🏔️", "lat": 42.6629, "lon": 44.6203, "details": "כנסייה מפורסמת למרגלות הר קזבק.",
        "parking": "חניה למעלה ליד הכנסייה (עפר).",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Mountain Freaks Cafe (בסטפנצמינדה)", "Cafe 5047m"]
    },
    {
        "day": 7, "region": "קזבגי (סטפנצמינדה)", "site": "מלון Rooms Kazbegi", "hours": "12:00 - 22:00", 
        "adult_cost": 40, "child_cost": 30, "activity_hours": 1.5, "travel_time": 0.3, "icon": "☕", "lat": 42.6566, "lon": 44.6464, "details": "ארוחה או קפה במרפסת המפורסמת עם נוף להר.",
        "parking": "חניה מסודרת לאורחי המלון והמסעדה.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Rooms Hotel Restaurant (אוכל אירופאי-גאורגי עילי)", "Sno Cafe"]
    },
    {
        "day": 8, "region": "טביליסי העתיקה", "site": "מרחצאות חמי אורבליאני", "hours": "08:00 - 23:00", 
        "adult_cost": 75, "child_cost": 0, "activity_hours": 1.5, "travel_time": 0.3, "icon": "🛁", "lat": 41.6880, "lon": 44.8115, "details": "חדר פרטי במרחצאות הגופרית.",
        "parking": "חניון רחוב בתשלום עירוני.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Culinarium Khasheria (שף לוקה טרזני - מעולה)", "Gastro Chef"]
    },
    {
        "day": 8, "region": "טביליסי העתיקה", "site": "מפל לגווטכבי וגשר השלום", "hours": "24/7", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 2.0, "travel_time": 0.3, "icon": "🌉", "lat": 41.6865, "lon": 44.8090, "details": "מפל טבעי המסתתר בלב העיר.",
        "parking": "חניון Rike Park הסמוך.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Pur Pur (מסעדה וינטג' קסומה במרכז)", "Shavi Lomi (מסעדת גורמה מקומית מדהימה - דורשת הזמנה מראש)"]
    },
    {
        "day": 9, "region": "שקווטילי", "site": "הפארק הדנדרולוגי", "hours": "10:00 - 18:00", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 2.5, "travel_time": 1.0, "icon": "🦩", "lat": 41.9372, "lon": 41.7644, "details": "פארק עצום עם ציפורים ופלמינגו.",
        "parking": "חניון מסודר וחינמי בכניסה לפארק.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Black Sea Arena Cafe", "מסעדות חוף באזור שקווטילי ואורקיבי"]
    },
    {
        "day": 9, "region": "שקווטילי", "site": "פארק המוזיקאים", "hours": "24/7", 
        "adult_cost": 0, "child_cost": 0, "activity_hours": 1.5, "travel_time": 0.3, "icon": "🎵", "lat": 41.9167, "lon": 41.7681, "details": "יער קסום עם פסלי מוזיקאים.",
        "parking": "חניה לצד הפארק ביער.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["Magnetic Beach Cafe", "Paragraph Resort Restaurants"]
    },
    {
        "day": 10, "region": "באטומי (סיום)", "site": "שוק הדגים של באטומי", "hours": "09:00 - 20:00", 
        "adult_cost": 40, "child_cost": 30, "activity_hours": 2.0, "travel_time": 0.0, "icon": "🐟", "lat": 41.6495, "lon": 41.6521, "details": "בוחרים דגים ומבשלים במקום.",
        "parking": "חניון השוק.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["שוק הדגים עצמו (בוחרים דג טרי בצד ומבקשים שיבשלו במסעדות שבתוך השוק)", "Station Cafe"]
    }
]

# ==========================================
# סרגל צד (Sidebar)
# ==========================================
with st.sidebar:
    try:
        st.image("IMG_1101.jpg", use_container_width=True, caption="המשפחה המטיילת ✈️")
    except FileNotFoundError:
        pass  
        
    st.markdown("---")
    st.header("📅 תאריכים והרכב")
    
    new_start_date = st.date_input("תאריך תחילת הטיול:", value=st.session_state.start_date)
    if new_start_date != st.session_state.start_date:
        st.session_state.start_date = new_start_date
        persist_all()
        st.rerun()
    
    adults = st.number_input("מספר מבוגרים", min_value=1, value=2, step=1)
    children = st.number_input("מספר ילדים", min_value=0, value=2, step=1)
    
    st.markdown("---")
    st.header("💰 בקרת תקציב כללי")
    new_budget = st.number_input("תקציב כולל מוגדר (GEL):", min_value=100.0, value=float(st.session_state.total_budget_gel), step=100.0)
    if new_budget != st.session_state.total_budget_gel:
        st.session_state.total_budget_gel = new_budget
        persist_all()
        
    st.markdown("---")
    st.header("💱 המרת מטבע מהירה")
    gel_input = st.number_input("סכום בלארי (GEL):", min_value=0.0, value=100.0, step=10.0)
    exchange_rate = st.number_input("שער לארי לשקל:", value=1.38, step=0.01)
    ils_calc = gel_input * exchange_rate
    st.info(f"💡 שווה ערך: **{ils_calc:,.1f} ₪** | טיפ מומלץ (10%): **{gel_input*0.1:.1f} לארי**")

    st.markdown("---")
    st.header("⚙️ בקרת מסלול")
    
    selected_tab = st.radio(
        "בחר מצב תצוגה:", 
        options=[
            "📅 פירוט מסלול ואטרקציות", 
            "🏨 מלונות", 
            "🚗 מחשבון ניווט וזמני נסיעה",
            "📊 דשבורד עלויות ופיצול תשלומים",
            "🎒 רשימת ציוד (Packing List)",
            "📋 משימות טרום-טיול",
            "📓 יומן מסע אישי",
            "📄 שוברים ומסמכים דיגיטליים",
            "📞 אנשי קשר וחירום",
            "🍷 אירוח משפחתי וסופרה",
            "🚨 חירום וטיפים לשטח",
            "🗺️ מפת האטרקציות"
        ],
        index=0
    )
    
    st.markdown("---")
    
    max_days = max([item['day'] for item in itinerary])
    day_options = ["הכל"]
    for d in range(1, max_days + 1):
        actual_date = st.session_state.start_date + timedelta(days=d-1)
        day_options.append(f"יום {d} ({actual_date.strftime('%d/%m/%Y')})")
        
    selected_day_str = st.selectbox("סינון לפי יום בטיול:", options=day_options)
    
    if selected_day_str != "הכל":
        selected_day = int(selected_day_str.split(" ")[1])
    else:
        selected_day = "הכל"

    # אזור גיבוי נתונים
    st.markdown("---")
    st.header("💾 גיבוי ושחזור")
    
    backup_json = json.dumps({
        "start_date": st.session_state.start_date.isoformat(),
        "expenses": st.session_state.expenses,
        "packing_list": st.session_state.packing_list,
        "tasks_list": st.session_state.tasks_list,
        "journal_notes": st.session_state.journal_notes,
        "uploaded_files_meta": st.session_state.uploaded_files_meta,
        "contacts_list": st.session_state.contacts_list,
        "total_budget_gel": st.session_state.total_budget_gel
    }, ensure_ascii=False, indent=4)
    
    st.download_button(
        label="📥 הורד קובץ גיבוי מלא",
        data=backup_json,
        file_name="georgia_trip_backup.json",
        mime="application/json"
    )

# עיבוד הנתונים
df = pd.DataFrame(itinerary)
df['total_cost_gel'] = (adults * df['adult_cost']) + (children * df['child_cost'])
df['total_hours'] = df['activity_hours'] + df['travel_time']
df['actual_date'] = df['day'].apply(lambda d: st.session_state.start_date + timedelta(days=d-1))

# בסיס נתונים למלונות
hotels_raw = [
    {
        "hotel": "King Suite Black Sea View Hotel", "check_in_day": 1, "check_out_day": 3, "area": "באטומי",
        "parking": "חניה פרטית של המלון / חניה ברחוב סמוך.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Retro (חצ'פורי)", "Fanfan", "Heart of Batumi"]
    },
    {
        "hotel": "Novotel Tbilisi Center", "check_in_day": 3, "check_out_day": 6, "area": "טביליסי",
        "parking": "חניון תת-קרקעי פרטי של המלון.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Shavi Lomi", "Culinarium Khasheria", "Pur Pur"]
    },
    {
        "hotel": "Gudauri Lodge", "check_in_day": 6, "check_out_day": 8, "area": "גודאורי",
        "parking": "חניה מסודרת חינם לאורחי המלון בחזית.",
        "parking_app": "חניה חינם", "parking_link": "",
        "restaurants": ["מסעדת המלון הראשית", "Cafe Quadra"]
    },
    {
        "hotel": "Novotel Tbilisi Center", "check_in_day": 8, "check_out_day": 9, "area": "טביליסי",
        "parking": "חניון תת-קרקעי פרטי של המלון.",
        "parking_app": "Tbilisi Parking", "parking_link": "https://parking.tbilisi.gov.ge/",
        "restaurants": ["Samikitno", "Machakhela"]
    },
    {
        "hotel": "King Suite Black Sea View Hotel", "check_in_day": 9, "check_out_day": 11, "area": "באטומי",
        "parking": "חניה פרטית של המלון / ברחוב סמוך.",
        "parking_app": "ParkMate Batumi", "parking_link": "https://play.google.com/store/apps/details?id=com.mkakhidze.parkingbatumi",
        "restaurants": ["Retro", "Chef's Grill"]
    }
]

hotels_processed = []
for h in hotels_raw:
    ci_date = st.session_state.start_date + timedelta(days=h["check_in_day"]-1)
    co_date = st.session_state.start_date + timedelta(days=h["check_out_day"]-1)
    
    parking_display = h["parking"]
    if h["parking_link"]:
        parking_display += f" | <a href='{h['parking_link']}' target='_blank'><b>[אפליקציה: {h['parking_app']}]</b></a>"
        
    hotels_processed.append({
        "hotel": h["hotel"],
        "area": h["area"],
        "check_in": ci_date.strftime('%d/%m/%Y'),
        "check_out": co_date.strftime('%d/%m/%Y'),
        "parking": parking_display,
        "restaurants": ", ".join(h["restaurants"])
    })
df_hotels = pd.DataFrame(hotels_processed)

filtered_df = df.copy()
if selected_day != "הכל":
    filtered_df = filtered_df[filtered_df['day'] == selected_day]

# ==========================================
# תצוגה 1: פירוט מסלול ומזג אוויר חי
# ==========================================
if selected_tab == "📅 פירוט מסלול ואטרקציות":
    st.subheader("📍 אטרקציות המסלול, חניות ואפליקציות תשלום")
    
    with st.expander("🌤️ בדוק תחזית מזג אוויר חיה באזורי הטיול"):
        w_col1, w_col2, w_col3, w_col4 = st.columns(4)
        with w_col1:
            st.metric("באטומי (חוף)", get_weather(41.65, 41.63))
        with w_col2:
            st.metric("טביליסי (בירה)", get_weather(41.69, 44.80))
        with w_col3:
            st.metric("גודאורי (הרים)", get_weather(42.49, 44.45))
        with w_col4:
            st.metric("קזבגי (פסגה)", get_weather(42.65, 44.64))
            
    st.markdown("---")
    
    csv = filtered_df.drop(columns=['restaurants', 'parking', 'parking_app', 'parking_link']).to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 הורד מסלול לאקסל", data=csv, file_name='georgia_trip.csv', mime='text/csv')
    st.markdown("---")
    
    for idx, row in filtered_df.iterrows():
        date_str = row['actual_date'].strftime("%d/%m/%Y")
        item_cost_ils = row['total_cost_gel'] * exchange_rate
        
        restaurants_html = ""
        for rest in row['restaurants']:
            rest_encoded = urllib.parse.quote(f"{rest}, {row['region']}, Georgia")
            restaurants_html += f"&bull; <a href='https://www.google.com/maps/search/?api=1&query={rest_encoded}' target='_blank'>{rest}</a><br>"
        
        parking_text = row['parking']
        if row['parking_link']:
            parking_text += f" | <a href='{row['parking_link']}' target='_blank'><b>[פתח את {row['parking_app']}]</b></a>"
        
        card_content = "<div class='site-card'>"
        card_content += f"<h2>{row['icon']} <span class='date-badge'>{date_str}</span> יום {row['day']} | {row['site']}</h2>"
        card_content += f"<p><b>📍 אזור:</b> {row['region']}</p>"
        card_content += f"<p><b>📝 פרטים:</b> {row['details']}</p>"
        card_content += f"<p>🕒 <b>שעות פתיחה:</b> {row['hours']}</p>"
        card_content += f"<p>⏱️ <b>משך פעילות:</b> {row['activity_hours']} שעות &nbsp;&nbsp;|&nbsp;&nbsp; 🚗 <b>זמן נסיעה:</b> {row['travel_time']} שעות</p>"
        card_content += f"<p style='color: #2e7d32; font-weight: bold;'>💰 עלות עבור {adults} מבוגרים ו-{children} ילדים: {row['total_cost_gel']} לארי (~ {item_cost_ils:,.0f} ₪)</p>"
        card_content += "<div class='info-box'>"
        card_content += f"<p><b>🅿️ מידע ואפליקציית חניה:</b> {parking_text}</p>"
        card_content += f"<p><b>🍽️ מסעדות מומלצות בסביבה:</b><br>{restaurants_html}</p>"
        card_content += "</div></div>"
        
        st.markdown(card_content, unsafe_allow_html=True)

# ==========================================
# תצוגה 2: מלונות וניווט
# ==========================================
elif selected_tab == "🏨 מלונות":
    st.subheader("🏨 בתי המלון שלנו, הסדרי חניה ואפליקציות")
    
    for idx, h in df_hotels.iterrows():
        hotel_content = "<div class='site-card' style='border-right-color: #3b82f6;'>"
        hotel_content += f"<h2>🏨 {h['hotel']} ({h['area']})</h2>"
        hotel_content += f"<p><b>📅 תקופת שהייה:</b> {h['check_in']} עד {h['check_out']}</p>"
        hotel_content += "<div class='info-box'>"
        hotel_content += f"<p><b>🅿️ הסדר חניה במלון:</b> {h['parking']}</p>"
        hotel_content += f"<p><b>🍽️ מסעדות באזור המלון:</b> {h['restaurants']}</p>"
        hotel_content += "</div></div>"
        
        st.markdown(hotel_content, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🚗 תכנון נסיעה מהמלון")
    
    unique_hotels = df_hotels["hotel"].unique()
    origin_hotel = st.selectbox("אנחנו יוצאים מ:", unique_hotels)
    destination = st.text_input("לאן נוסעים? (למשל: Kazbegi, Martvili Canyon)", "Kazbegi")
    
    if st.button("הפק קישורי ניווט", type="primary"):
        if destination:
            origin_encoded = urllib.parse.quote(f"{origin_hotel}, Georgia")
            destination_encoded = urllib.parse.quote(f"{destination}, Georgia")
            
            gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={destination_encoded}&travelmode=driving"
            waze_url = f"https://waze.com/ul?q={destination_encoded}&navigate=yes"
            
            st.success("הקישורים מוכנים!")
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                st.markdown(f"""
                <a href="{gmaps_url}" target="_blank" style="display: block; padding: 12px; background-color: #4285F4; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    🗺️ פתח ב-Google Maps
                </a>
                """, unsafe_allow_html=True)
            with col_nav2:
                st.markdown(f"""
                <a href="{waze_url}" target="_blank" style="display: block; padding: 12px; background-color: #33ccff; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    🚗 פתח ב-Waze
                </a>
                """, unsafe_allow_html=True)
        else:
            st.warning("אנא הזן יעד כדי לחשב מסלול.")

# ==========================================
# תצוגה 3: מחשבון ניווט בין אטרקציות
# ==========================================
elif selected_tab == "🚗 מחשבון ניווט וזמני נסיעה":
    st.subheader("🚗 מחשבון זמני נסיעה וניווט בגאורגיה")
    st.markdown("בחר יעד מוצא ויעד להגעה כדי לקבל הערכת זמן נסיעה וקישורי ניווט ישירים.")
    st.markdown("---")
    
    all_sites = df['site'].tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        origin = st.selectbox("📍 בחר יעד מוצא:", options=all_sites, index=0)
    with col2:
        default_dest_index = 1 if len(all_sites) > 1 else 0
        destination = st.selectbox("🏁 בחר יעד הבא:", options=all_sites, index=default_dest_index)
        
    if origin and destination:
        if origin == destination:
            st.warning("בחרת את אותו היעד במוצא וביעד.")
        else:
            loc1 = df[df['site'] == origin].iloc[0]
            loc2 = df[df['site'] == destination].iloc[0]
            
            km_dist, est_hours = calculate_travel_estimation(loc1['lat'], loc1['lon'], loc2['lat'], loc2['lon'])
            
            hours = int(est_hours)
            minutes = int((est_hours - hours) * 60)
            
            gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={loc1['lat']},{loc1['lon']}&destination={loc2['lat']},{loc2['lon']}"
            waze_url = f"https://waze.com/ul?ll={loc2['lat']},{loc2['lon']}&navigate=yes"
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.success(f"**מרחק משוער בכביש:** {km_dist:.1f} ק\"מ")
            if hours > 0:
                st.info(f"**זמן נסיעה מוערך:** {hours} שעות ו-{minutes} דקות")
            else:
                st.info(f"**זמן נסיעה מוערך:** {minutes} דקות")
                
            st.markdown("<br>", unsafe_allow_html=True)
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                st.markdown(f"""
                <a href="{gmaps_url}" target="_blank" style="display: block; padding: 12px; background-color: #4285F4; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    🗺️ פתח ב-Google Maps
                </a>
                """, unsafe_allow_html=True)
            with col_n2:
                st.markdown(f"""
                <a href="{waze_url}" target="_blank" style="display: block; padding: 12px; background-color: #33ccff; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    🚗 פתח ב-Waze
                </a>
                """, unsafe_allow_html=True)

# ==========================================
# תצוגה 4: דשבורד עלויות ופיצול תשלומים
# ==========================================
elif selected_tab == "📊 דשבורד עלויות ופיצול תשלומים":
    st.subheader("📊 דשבורד עלויות, פיצול הוצאות משפחתי ובקרת תקציב")
    st.markdown("---")
    
    total_cost_gel = filtered_df['total_cost_gel'].sum()
    total_cost_ils = total_cost_gel * exchange_rate
    
    actual_spent_gel = sum([e['amount'] for e in st.session_state.expenses])
    actual_spent_ils = actual_spent_gel * exchange_rate
    
    # מד התקדמות תקציב
    budget_limit = st.session_state.total_budget_gel
    budget_progress = min(actual_spent_gel / budget_limit, 1.0) if budget_limit > 0 else 0
    
    st.markdown(f"### 🎯 מעקב תקציב: {actual_spent_gel:,.0f} GEL מתוך {budget_limit:,.0f} GEL מוגדרים")
    st.progress(budget_progress)
    if actual_spent_gel > budget_limit:
        st.warning("⚠️ שימו לב! חרגתם מהתקציב שהוגדר לטיול.")
    else:
        st.success(f"✨ נותרו עוד {budget_limit - actual_spent_gel:,.0f} GEL בתקציב.")

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 עלות אטרקציות תאורטית", f"{total_cost_gel:,.0f} GEL", f"~ {total_cost_ils:,.0f} ₪")
    col2.metric("קטגוריית הוצאות שוטפות", f"{actual_spent_gel:,.0f} GEL", f"~ {actual_spent_ils:,.0f} ₪")
    col3.metric("⏱️ סך שעות פעילות", f"{filtered_df['activity_hours'].sum():,.1f} שעות")
    
    st.markdown("---")
    st.subheader("👥 סיכום פיצול הוצאות לפי משלם")
    payer_summary = {}
    for e in st.session_state.expenses:
        p = e.get("payer", "אני")
        payer_summary[p] = payer_summary.get(p, 0) + e['amount']
    
    p_cols = st.columns(max(len(payer_summary), 1))
    for i, (payer, amt) in enumerate(payer_summary.items()):
        with p_cols[i % len(p_cols)]:
            st.metric(f"שולם על ידי: {payer}", f"{amt:,.1f} GEL", f"~ {amt*exchange_rate:,.0f} ₪")

    st.markdown("---")
    st.subheader("➕ הוסף הוצאה חדשה בפועל")
    with st.form("add_expense_form", clear_on_submit=True):
        e_desc = st.text_input("תיאור ההוצאה (למשל: תדלוק, חניה בבאטומי):")
        e_cat = st.selectbox("קטגוריה:", ["אוכל", "תחבורה ודלק", "חניה", "קניות", "שונות"])
        e_amount = st.number_input("סכום בלארי (GEL):", min_value=1.0, value=20.0)
        e_payer = st.selectbox("מי שילם?", ["אני", "משפחה שנייה / חברים", "התחלקנו שווה בשווה"])
        submitted = st.form_submit_button("הוסף הוצאה לרשימה")
        if submitted and e_desc.strip():
            new_id = max([e.get("id", 0) for e in st.session_state.expenses], default=0) + 1
            st.session_state.expenses.append({
                "id": new_id, 
                "desc": e_desc.strip(), 
                "category": e_cat, 
                "amount": e_amount,
                "payer": e_payer
            })
            persist_all()
            st.success("ההוצאה נוספה ונשמרה לצמיתות!")
            st.rerun()
                
    if st.session_state.expenses:
        st.markdown("---")
        st.subheader("📋 ניהול הוצאות קיימות (מחיקה ועריכה)")
        
        for idx, exp in enumerate(st.session_state.expenses):
            with st.expander(f"📝 {exp['desc']} — {exp['amount']} GEL ({exp['category']}) | שולם ע\"י: {exp.get('payer', 'אני')}"):
                with st.form(f"edit_exp_{exp.get('id', idx)}"):
                    ed_desc = st.text_input("תיאור ההוצאה:", value=exp['desc'], key=f"ed_desc_{idx}")
                    categories = ["אוכל", "תחבורה ודלק", "חניה", "קניות", "שונות"]
                    default_cat_idx = categories.index(exp['category']) if exp['category'] in categories else 0
                    ed_cat = st.selectbox("קטגוריה:", categories, index=default_cat_idx, key=f"ed_cat_{idx}")
                    ed_amount = st.number_input("סכום בלארי (GEL):", min_value=1.0, value=float(exp['amount']), key=f"ed_amt_{idx}")
                    
                    payers_list = ["אני", "משפחה שנייה / חברים", "התחלקנו שווה בשווה"]
                    curr_payer = exp.get('payer', 'אני')
                    default_payer_idx = payers_list.index(curr_payer) if curr_payer in payers_list else 0
                    ed_payer = st.selectbox("מי שילם?", payers_list, index=default_payer_idx, key=f"ed_payer_{idx}")
                    
                    col_b1, col_b2 = st.columns(2)
                    save_clicked = col_b1.form_submit_button("💾 שמור שינויים")
                    delete_clicked = col_b2.form_submit_button("🗑️ מחק הוצאה זו")
                    
                    if save_clicked:
                        st.session_state.expenses[idx]["desc"] = ed_desc
                        st.session_state.expenses[idx]["category"] = ed_cat
                        st.session_state.expenses[idx]["amount"] = ed_amount
                        st.session_state.expenses[idx]["payer"] = ed_payer
                        persist_all()
                        st.success("ההוצאה עודכנה בהצלחה!")
                        st.rerun()
                        
                    if delete_clicked:
                        st.session_state.expenses.pop(idx)
                        persist_all()
                        st.success("ההוצאה נמחקה!")
                        st.rerun()

# ==========================================
# תצוגה 5: רשימת ציוד (Packing List)
# ==========================================
elif selected_tab == "🎒 רשימת ציוד (Packing List)":
    st.subheader("🎒 רשימת ציוד ומזוודות למשפחה")
    st.markdown("סמן את הפריטים שכבר ארזתם – השינויים נשמרים באופן אוטומטי לצמיתות:")
    st.markdown("---")
    
    data_changed = False
    for i, item_dict in enumerate(st.session_state.packing_list):
        new_status = st.checkbox(item_dict["item"], value=item_dict["checked"], key=f"pack_{i}")
        if new_status != item_dict["checked"]:
            st.session_state.packing_list[i]["checked"] = new_status
            data_changed = True
            
    if data_changed:
        persist_all()
        
    st.markdown("---")
    st.subheader("➕ הוסף פריט חדש לרשימה")
    with st.form("add_gear_form", clear_on_submit=True):
        new_gear = st.text_input("שם הפריט החדש:")
        gear_submitted = st.form_submit_button("הוסף לפריטים")
        if gear_submitted and new_gear.strip():
            existing_items = [d["item"] for d in st.session_state.packing_list]
            if new_gear.strip() not in existing_items:
                st.session_state.packing_list.append({"item": new_gear.strip(), "checked": False})
                persist_all()
                st.success("הפריט נוסף ונשמר לצמיתות!")
                st.rerun()
            else:
                st.warning("הפריט כבר קיים ברשימה.")

# ==========================================
# תצוגה 6: משימות טרום-טיול
# ==========================================
elif selected_tab == "📋 משימות טרום-טיול":
    st.subheader("📋 משימות ומנהלות לפני היציאה לטיול")
    st.markdown("סמן את המשימות שכבר סגרתם לקראת הנסיעה:")
    st.markdown("---")
    
    tasks_changed = False
    for i, t_dict in enumerate(st.session_state.tasks_list):
        t_status = st.checkbox(t_dict["task"], value=t_dict["checked"], key=f"task_{i}")
        if t_status != t_dict["checked"]:
            st.session_state.tasks_list[i]["checked"] = t_status
            tasks_changed = True
            
    if tasks_changed:
        persist_all()
        
    st.markdown("---")
    st.subheader("➕ הוסף משימה חדשה לרשימה")
    with st.form("add_task_form", clear_on_submit=True):
        new_task = st.text_input("תיאור המשימה (למשל: רכישת אינטרנט בחו\"ל):")
        task_submitted = st.form_submit_button("הוסף משימה")
        if task_submitted and new_task.strip():
            existing_tasks = [d["task"] for d in st.session_state.tasks_list]
            if new_task.strip() not in existing_tasks:
                st.session_state.tasks_list.append({"task": new_task.strip(), "checked": False})
                persist_all()
                st.success("המשימה נוספה ונשמרה לצמיתות!")
                st.rerun()
            else:
                st.warning("המשימה כבר קיימת ברשימה.")

# ==========================================
# תצוגה 7: יומן מסע אישי
# ==========================================
elif selected_tab == "📓 יומן מסע אישי":
    st.subheader("📓 יומן מסע ופתקים אישיים מהשטח")
    st.markdown("כאן תוכל לכתוב חופשי תובנות, שמות של מקומות מיוחדים שנתקלתם בהם, או זכרונות מהטיול:")
    st.markdown("---")
    
    current_notes = st.text_area("תוכן היומן:", value=st.session_state.journal_notes, height=250)
    if current_notes != st.session_state.journal_notes:
        st.session_state.journal_notes = current_notes
        persist_all()
        st.success("💾 השינויים ביומן נשמרו אוטומטית!")

# ==========================================
# תצוגה 8: שוברים ומסמכים דיגיטליים
# ==========================================
elif selected_tab == "📄 שוברים ומסמכים דיגיטליים":
    st.subheader("📄 מרכז מסמכים, שוברים והעלאת קבצים")
    st.markdown("כאן תוכלו להעלות ולרכז את כל האישורים, כרטיסי הטיסה, פוליסות הביטוח ושוברי המלונות שלכם.")
    st.markdown("---")
    
    st.markdown("### 📤 העלאת קובץ חדש (PDF, תמונות, מסמכים)")
    uploaded_file = st.file_uploader("בחר קובץ להעלאה:", type=["pdf", "png", "jpg", "jpeg", "txt"])
    file_category = st.selectbox("בחר סוג מסמך:", ["טיסות", "ביטוח רפואי", "מלון", "השכרת רכב", "שונות"])
    
    if uploaded_file is not None:
        if st.button("שמור קובץ במערכת", type="primary"):
            file_path = os.path.join(DOCS_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            exists_idx = next((i for i, item in enumerate(st.session_state.uploaded_files_meta) if item["filename"] == uploaded_file.name), None)
            file_info = {
                "filename": uploaded_file.name,
                "category": file_category,
                "path": file_path
            }
            if exists_idx is not None:
                st.session_state.uploaded_files_meta[exists_idx] = file_info
            else:
                st.session_state.uploaded_files_meta.append(file_info)
                
            persist_all()
            st.success(f"הקובץ '{uploaded_file.name}' הועלה ונשמר בהצלחה!")
            st.rerun()

    st.markdown("---")
    st.subheader("📁 המסמכים והשוברים השמורים שלך:")
    
    if not st.session_state.uploaded_files_meta:
        st.info("עדיין לא הועלו קבצים. השתמש בטופס למעלה כדי להעלות מסמכים.")
    else:
        for idx, f_meta in enumerate(st.session_state.uploaded_files_meta):
            col_d1, col_d2, col_d3 = st.columns([3, 2, 1])
            with col_d1:
                st.markdown(f"<b>📄 {f_meta['filename']}</b> <span style='color: gray; font-size: 0.85em;'>({f_meta['category']})</span>", unsafe_allow_html=True)
            with col_d2:
                if os.path.exists(f_meta['path']):
                    with open(f_meta['path'], "rb") as file_to_down:
                        st.download_button(
                            label="📥 הורד / הצג",
                            data=file_to_down,
                            file_name=f_meta['filename'],
                            key=f"down_file_{idx}"
                        )
                else:
                    st.warning("הקובץ חסר בשרת")
            with col_d3:
                if st.button("🗑️ מחק", key=f"del_file_{idx}"):
                    if os.path.exists(f_meta['path']):
                        try:
                            os.remove(f_meta['path'])
                        except:
                            pass
                    st.session_state.uploaded_files_meta.pop(idx)
                    persist_all()
                    st.success("הקובץ נמחק!")
                    st.rerun()

# ==========================================
# תצוגה 9: אנשי קשר וחירום (כולל הוספה ומחיקה)
# ==========================================
elif selected_tab == "📞 אנשי קשר וחירום":
    st.subheader("📞 ספריית אנשי קשר, מלונות וגורמי חירום")
    st.markdown("כאן תוכלו לשמור, להוסיף ולמחוק את כל מספרי הטלפון החשובים שתרצו שיהיו זמינים בשטח:")
    st.markdown("---")
    
    if st.session_state.contacts_list:
        for idx, contact in enumerate(st.session_state.contacts_list):
            c_col1, c_col2, c_col3 = st.columns([2, 2, 1])
            with c_col1:
                st.markdown(f"**👤 {contact['name']}**<br><span style='color:gray;'>{contact.get('role', '')}</span>", unsafe_allow_html=True)
            with c_col2:
                st.markdown(f"📞 <b>{contact['phone']}</b>", unsafe_allow_html=True)
            with c_col3:
                if st.button("🗑️ מחק", key=f"del_contact_{idx}"):
                    st.session_state.contacts_list.pop(idx)
                    persist_all()
                    st.success("איש הקשר נמחק!")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("אין אנשי קשר שמורים כרגע.")

    st.subheader("➕ הוסף איש קשר חדש")
    with st.form("add_contact_form", clear_on_submit=True):
        c_name = st.text_input("שם איש הקשר / הגורם (למשל: נהג מונית אמין / מלון באטומי):")
        c_phone = st.text_input("מספר טלפון (כולל קידומת):")
        c_role = st.text_input("תפקיד או הערה (למשל: זמין 24/7):")
        contact_submitted = st.form_submit_button("הוסף איש קשר")
        
        if contact_submitted and c_name.strip() and c_phone.strip():
            st.session_state.contacts_list.append({
                "name": c_name.strip(),
                "phone": c_phone.strip(),
                "role": c_role.strip()
            })
            persist_all()
            st.success("איש הקשר נוסף ונשמר לצמיתות!")
            st.rerun()

# ==========================================
# תצוגה 10: חוויית סופרה ואירוח משפחתי
# ==========================================
elif selected_tab == "🍷 אירוח משפחתי וסופרה":
    st.subheader("🍷 חוויית 'סופרה' וארוחות משפחתיות מסורתיות בגאורגיה")
    st.markdown("חוויית חובה בטיול! ארוחת משתה גאורגית אותנטית (סופרה) הכוללת מטעמים ביתיים, יינות מקומיים והופעות פולקלור ריבוי-קולות וריקודים סוערים.")
    st.markdown("---")

    col_sup1, col_sup2 = st.columns(2)
    with col_sup1:
        st.markdown("""
        ### 🍇 חבל קחתי (אזור היין - סיגנאגי ותלביאוי)
        * **מה מחכה לכם:** יקבים בוטיקיים משפחתיים שבהם מכינים יין בכדים טמונים באדמה (קגוורי). המשפחות מארחות בחצרות ירוקות לארוחות שף ביתיות מלאות כל טוב.
        * **איפה לחפש / מומלצים:** 
          * *Pheasant’s Tears (סיגנאגי)* - יקב אורגני מדהים עם אירוח מוקפד ואווירה כפרית.
          * יקבים משפחתיים קטנים לאורך הדרך בקאחתי (ניתן לתאם דרך המלון או במקום).
        """)
    with col_sup2:
        st.markdown("""
        ### 🏔️ הרי אג'ריה (אזור באטומי וההרים)
        * **מה מחכה לכם:** כפרים קסומים בהרים סביב באטומי (כמו אזור Keda). משפחות הרריות מציעות ארוחות כפריות (מאפים מיוחדים, גבינות מקומיות, בשרים) בליווי מוזיקה כפרית.
        * **טיפ:** מושלם לשילוב ביום טיול מבאטומי לכיוון ההרים הפנימיים.
        """)

    st.markdown("---")
    st.markdown("""
    ### 🏙️ טביליסי והסביבה
    * **מסעדת Shavi Lomi (טביליסי):** אמנם זו מסעדה ולא בית פרטי, אבל היא מעוצבת בדיוק כמו חצר טביליסאית עתיקה עם אוכל ביתי אגדי ואווירה משפחתית חמה.
    * **איך מתאמים ערב פולקלור אמיתי?** רוב המשפחות המארחות וההופעות הפרטיות דורשות **תיאום מראש** של כמה ימים. הדרך הקלה והטובה ביותר היא לבקש מבעל המלון שבו תלונו בטביליסי או בבאטומי להרים טלפון למארחים מקומיים שהם מכירים ולסדר עבורכם ערב סופרה מושלם.
    """)

# ==========================================
# תצוגה 11: חירום וטיפים לשטח
# ==========================================
elif selected_tab == "🚨 חירום וטיפים לשטח":
    st.subheader("🚨 מספרי חירום, עזרה ראשונה וטיפים לנהיגה בהרים")
    st.markdown("---")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("""
        ### 📞 מספרי חירום בגאורגיה:
        * **מוקד חירום כללי (משטרה, אמבולנס, כיבוי):** `112` (דוברים אנגלית)
        * **משטרה תיירותית:** חינם דרך מוקד 112
        * **שגרירות ישראל בטביליסי:** `+995 32 255 65 00`
        
        ### 🅿️ טיפים לתשלום חניה בעיר:
        * בטביליסי ובבאטומי אסור להחנות איפה שמסומן באדום-לבן או צהוב בלי אישור.
        * מומלץ להוריד מראש את אפליקציות החניה הרשמיות (`Tbilisi Parking` / `ParkMate Batumi`) ולהזין מספר רכב ואשראי.
        """)
    with col_t2:
        st.markdown("""
        ### 🚗 טיפים חשובים לנהיגה בהרים:
        * **פרות בכביש:** בהרים (במיוחד בדרך הצבאית לקזבגי) פרות וסוסים מסתובבים חופשי על הכביש. להיזהר בסיבובים!
        * **עקיפות מסוכנות:** הנהגים המקומיים לעיתים עוקפים בפראות. שמרו ימין והיו עירניים.
        * **דלק:** מומלץ לתדלק תמיד כשמיכל הדלק יורד מתחת לחצי, בעיקר לפני האזורים ההרריים שבהם תחנות הדלק דלילות יותר.
        """)

    st.markdown("---")
    st.markdown("""
    <a href="https://maps.google.com/?q=hospital" target="_blank" style="display: block; padding: 12px; background-color: #dc3545; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
        🏥 מצא בית חולים או מרכז רפואי קרוב ב-Google Maps
    </a>
    """, unsafe_allow_html=True)

# ==========================================
# תצוגה 12: מפה אינטראקטיבית
# ==========================================
elif selected_tab == "🗺️ מפת האטרקציות":
    st.subheader("🗺️ מפת האטרקציות האינטראקטיבית")
    st.markdown("---")
    if not filtered_df.empty:
        fig_map = px.scatter_mapbox(
            filtered_df,
            lat="lat",
            lon="lon",
            hover_name="site",
            hover_data=["day", "region", "icon"],
            zoom=7,
            height=500
        )
        fig_map.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("אין אטרקציות להצגה בסינון הנוכחי.")
