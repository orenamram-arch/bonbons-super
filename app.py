import streamlit as st
import pandas as pd
from datetime import datetime
import json
import urllib.parse
import google.generativeai as genai
from supabase import create_client, Client

# הגדרת עמוד האפליקציה (חייב להיות ראשון)
st.set_page_config(page_title="ניהול קניות אולטימטיבי", page_icon="🛒", layout="centered")

# ==========================================
# 1. מערכת התחברות / בחירת רשימה
# ==========================================
if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>ברוכים הבאים לאפליקציית הקניות 🛒</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>כדי להתחיל, אנא בחר את שם הרשימה שלך.</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        user_input = st.text_input("מזהה רשימה (למשל: oren או amram_family):")
        submitted = st.form_submit_button("היכנס לרשימה", type="primary")
        if submitted:
            if user_input.strip():
                st.session_state.username = user_input.strip().lower()
                st.rerun()
            else:
                st.warning("אנא הזן מזהה רשימה תקין.")
    st.stop() # עוצר את המשך ריצת הקוד עד שהמשתמש יתחבר

LIST_KEY = f"shopping_app_main_data_{st.session_state.username}"

_, col_logout = st.columns([4, 1])
with col_logout:
    if st.button("🚪 החלף רשימה"):
        del st.session_state.username
        st.rerun()

# ==========================================
# חיבור ל-Supabase בענן
# ==========================================
SUPABASE_URL = "https://vobzhjutimeowgsjhgyt.supabase.co"
SUPABASE_KEY = "sb_publishable_OC3UKQ-UdO3ba4yHgvt9RQ_-AZdenBv"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

CATEGORIES = ["ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים", "חומרי ניקוי", "חטיפים וממתקים", "שימורים ויבשים", "שונות"]
FAVOURITES_DB = [
    {"name": "חלב 3%", "category": "מוצרי חלב", "estimated_price": 7.2},
    {"name": "לחם אחיד", "category": "מאפים", "estimated_price": 8.5},
    {"name": "ביצים (לארג')", "category": "מוצרי חלב", "estimated_price": 14.0},
    {"name": "מלפפונים", "category": "ירקות ופירות", "estimated_price": 10.0},
    {"name": "עגבניות", "category": "ירקות ופירות", "estimated_price": 12.0},
    {"name": "קוטג'", "category": "מוצרי חלב", "estimated_price": 6.8}
]

AISLE_ORDER = {
    "ירקות ופירות": 1,
    "מאפים": 2,
    "מוצרי חלב": 3,
    "בשר ודגים": 4,
    "שימורים ויבשים": 5,
    "חטיפים וממתקים": 6,
    "חומרי ניקוי": 7,
    "שונות": 8
}

MISSING_ITEM_SUGGESTION_THRESHOLD = 3

# הגדרת ה-AI (Gemini)
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
except:
    AI_AVAILABLE = False

@st.cache_resource
def get_gemini_model():
    if AI_AVAILABLE:
        try:
            return genai.GenerativeModel('gemini-1.5-flash')
        except Exception:
            return None
    return None

# ==========================================
# פונקציות שליפת מחירים מרשתות השיווק (Live)
# ==========================================
@st.cache_data(ttl=3600)
def get_live_market_prices():
    """שולף את טבלת השוואת המחירים המעודכנת מ-Supabase עם קאש לשעה[cite: 1]."""
    try:
        response = supabase.table("supermarket_prices").select("*").execute()
        if response.data:
            return {row["item_name"].strip().lower(): row for row in response.data}
    except Exception:
        pass
    return {}

def get_best_market_price(item_name):
    """בודק אם יש מחיר מעודכן מהרשתות הגדולות, ומחזיר את הזול ביניהם או ברירת מחדל[cite: 1]."""
    market_prices = get_live_market_prices()
    clean_name = item_name.strip().lower()
    if clean_name in market_prices:
        data = market_prices[clean_name]
        prices = [p for p in [data.get('rami_levy_price'), data.get('shufersal_price'), data.get('yohananof_price')] if p is not None and p > 0]
        if prices:
            return min(prices)
    return None


def load_data():
    try:
        response = supabase.table("app_data").select("content").eq("key", LIST_KEY).execute()
        if response.data and len(response.data) > 0:
            data = response.data[0]["content"]
            if "shopping_list" in data and "stores" not in data:
                old_list = data["shopping_list"]
                data["stores"] = {"סופרמרקט מרכזי": old_list}
                data["active_store"] = "סופרמרקט מרכזי"
            
            st.session_state.data_loaded_successfully = True
            return data
        else:
            st.session_state.data_loaded_successfully = True
            
    except Exception as e:
        st.error(f"שגיאה קריטית בטעינת הנתונים מ-Supabase: {e}")
        st.session_state.data_loaded_successfully = False

    return {
        "stores": {"סופרמרקט מרכזי": []},
        "active_store": "סופרמרקט מרכזי",
        "next_trip_list": [],
        "purchase_history": [],
        "recurring_items": [],
        "learned_categories": {},
        "all_purchased_items": [],
        "budget": 300.0,
        "personal_favourites": [],
        "missing_item_counts": {}
    }


def save_data():
    if not st.session_state.get("data_loaded_successfully", True):
        st.error("⚠️ השמירה נחסמה: הנתונים לא נטענו כראוי מהשרת ולכן שמירה עכשיו תדרוס אותם. אנא רענן את העמוד.")
        return

    data = {
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "recurring_items": st.session_state.recurring_items,
        "learned_categories": st.session_state.learned_categories,
        "all_purchased_items": st.session_state.all_purchased_items,
        "budget": st.session_state.budget,
        "personal_favourites": st.session_state.personal_favourites,
        "missing_item_counts": st.session_state.missing_item_counts
    }
    try:
        supabase.table("app_data").upsert(
            {"key": LIST_KEY, "content": data},
            on_conflict="key"
        ).execute()
        st.toast("💾 נשמר בהצלחה בענן Supabase!", icon="✅")
        st.session_state.last_save_failed_backup = None
    except Exception as e:
        st.error(f"שגיאה בשמירת הנתונים ב-Supabase: {e}")
        try:
            st.session_state.last_save_failed_backup = json.dumps(data, ensure_ascii=False, indent=4)
        except Exception:
            pass


if 'stores' not in st.session_state:
    saved_data = load_data()
    st.session_state.stores = saved_data.get("stores", {"סופרמרקט מרכזי": []})
    st.session_state.active_store = saved_data.get("active_store", "סופרמרקט מרכזי")
    st.session_state.next_trip_list = saved_data.get("next_trip_list", [])
    st.session_state.purchase_history = saved_data.get("purchase_history", [])
    st.session_state.recurring_items = saved_data.get("recurring_items", [])
    st.session_state.learned_categories = saved_data.get("learned_categories", {})
    st.session_state.all_purchased_items = saved_data.get("all_purchased_items", [])
    st.session_state.budget = saved_data.get("budget", 300.0)
    st.session_state.personal_favourites = saved_data.get("personal_favourites", [])
    st.session_state.missing_item_counts = saved_data.get("missing_item_counts", {})
    st.session_state.last_save_failed_backup = None

if st.session_state.active_store not in st.session_state.stores:
    st.session_state.stores[st.session_state.active_store] = []

# --- עיצוב דינמי ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

    :root {
        --app-bg: #f7f9fb;
        --card-bg: #ffffff;
        --app-text: #0f172a;
        --sub-text: #64748b;
        --app-border: #e2e8f0;
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --app-bg: #0f172a;
            --card-bg: #1e293b;
            --app-text: #f8fafc;
            --sub-text: #94a3b8;
            --app-border: #334155;
        }
    }

    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] {
        display: none !important;
    }

    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
        color: var(--app-text) !important;
    }

    .stApp { background-color: var(--app-bg); }
    h1, h2, h3 { color: var(--app-text) !important; font-weight: 800 !important; }

    div[data-testid="metric-container"] {
        background: var(--card-bg);
        border: 1px solid var(--app-border);
        padding: 12px 15px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        border-right: 5px solid #3b82f6;
    }
    div[data-testid="metric-container"] label { color: var(--sub-text) !important; font-size: 14px !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: var(--app-text) !important; font-size: 22px !important; font-weight: 700 !important; }

    .product-card {
        background-color: var(--card-bg);
        border: 1px solid var(--app-border);
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 6px;
        display: flex;
        align-items: center;
    }
    .product-name { font-size: 18px !important; font-weight: 700 !important; color: var(--app-text); }
    .product-details { font-size: 13px; color: var(--sub-text); }

    .stButton>button { border-radius: 10px; font-weight: 600; transition: all 0.2s; width: 100%; }
</style>
""", unsafe_allow_html=True)

if st.session_state.last_save_failed_backup:
    st.warning("⚠️ השמירה האחרונה בענן נכשלה! מומלץ להוריד גיבוי חירום כדי לא לאבד נתונים.")
    st.download_button(
        label="📥 הורד גיבוי חירום עכשיו",
        data=st.session_state.last_save_failed_backup,
        file_name=f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="emergency_backup_download"
    )

def get_product_icon_and_color(category):
    if category == "ירקות ופירות": return "🥗", "#10b981"
    if category == "מוצרי חלב": return "🥛", "#0ea5e9"
    if category == "בשר ודגים": return "🥩", "#ef4444"
    if category == "מאפים": return "🍞", "#f59e0b"
    if category == "חומרי ניקוי": return "🧻", "#8b5cf6"
    if category == "חטיפים וממתקים": return "🍫", "#ec4899"
    if category == "שימורים ויבשים": return "☕", "#6366f1"
    return "🛒", "#64748b"


def ai_smart_categorize_and_price(item_name):
    clean_name = item_name.strip().lower()

    if clean_name in st.session_state.learned_categories:
        cat = st.session_state.learned_categories[clean_name]
        live_p = get_best_market_price(clean_name)
        return cat, (live_p if live_p is not None else 12.0)

    live_p = get_best_market_price(clean_name)
    default_price = live_p if live_p is not None else 12.0

    model = get_gemini_model()
    if model is not None:
        try:
            prompt = (
                f"You are a smart shopping assistant. Categorize the shopping item "
                f"'{clean_name}' into EXACTLY ONE of these categories: "
                f"{', '.join(CATEGORIES)}. "
                f"Reply ONLY with the exact category name in Hebrew."
            )

            response = model.generate_content(prompt)
            predicted_category = response.text.strip()

            if predicted_category in CATEGORIES:
                st.session_state.learned_categories[clean_name] = predicted_category
                return predicted_category, default_price
        except Exception:
            pass

    smart_db = {
        "מלפפון": ("ירקות ופירות", 10.0), "עגבנייה": ("ירקות ופירות", 12.0),
        "תפוח": ("ירקות ופירות", 14.0), "בננה": ("ירקות ופירות", 10.0),
        "בצל": ("ירקות ופירות", 6.0), "תפוח אדמה": ("ירקות ופירות", 7.0),
        "גזר": ("ירקות ופירות", 6.5), "לימון": ("ירקות ופירות", 9.0),
        "כוסברה": ("ירקות ופירות", 4.0), "פטרוזיליה": ("ירקות ופירות", 4.0),
        "שמיר": ("ירקות ופירות", 4.0), "נענע": ("ירקות ופירות", 5.0),
        "חלב": ("מוצרי חלב", 7.2), "גבינה": ("מוצרי חלב", 6.8),
        "ביצים": ("מוצרי חלב", 14.0), "קוטג'": ("מוצרי חלב", 6.8),
        "גבינה צהובה": ("מוצרי חלב", 32.0), "יוגורט": ("מוצרי חלב", 4.5),
        "עוף": ("בשר ודגים", 35.0), "בקר": ("בשר ודגים", 55.0),
        "סלמון": ("בשר ודגים", 90.0), "טונה": ("בשר ודגים", 8.0),
        "לחם": ("מאפים", 8.5), "פיתות": ("מאפים", 15.0),
        "חלה": ("מאפים", 7.0), "בורקס": ("מאפים", 25.0),
        "שמפו": ("חומרי ניקוי", 18.0), "נייר טואלט": ("חומרי ניקוי", 32.0),
        "אבקת כביסה": ("חומרי ניקוי", 29.0), "נוזל כלים": ("חומרי ניקוי", 8.5),
        "אורז": ("שימורים ויבשים", 10.0), "שמן": ("שימורים ויבשים", 12.0),
        "קמח": ("שימורים ויבשים", 6.0), "סוכר": ("שימורים ויבשים", 6.5),
        "קפה": ("שימורים ויבשים", 35.0), "פסטה": ("שימורים ויבשים", 6.0),
        "שוקולד": ("חטיפים וממתקים", 6.5), "במבה": ("חטיפים וממתקים", 4.5),
        "ביסלי": ("חטיפים וממתקים", 4.5), "עוגיות": ("חטיפים וממתקים", 10.0)
    }
    for key, (cat, price) in smart_db.items():
        if key in clean_name:
            return cat, (live_p if live_p is not None else price)

    return "שונות", default_price

current_shopping_list = st.session_state.stores[st.session_state.active_store]

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🛒 רשימה",
    "➕ הוספה",
    "⭐ מועדפים",
    "🗺️ סידור",
    "🧮 השוואה",
    "🛍️ לקנייה הבאה",
    "📊 קבלות",
    "🏪 חנויות"
])

# ----------------------------------------------------
# 1. רשימת קניות פעילה
# ----------------------------------------------------
with tab1:
    store_list = list(st.session_state.stores.keys())
    selected_store = st.selectbox("🏪 חנות פעילה כרגע:", store_list, index=store_list.index(st.session_state.active_store))
    if selected_store != st.session_state.active_store:
        st.session_state.active_store = selected_store
        save_data()
        st.rerun()

    st.markdown("---")

    total_cost = sum(item['quantity'] * item['estimated_price'] for item in current_shopping_list if not item['checked'])

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2:
        remaining_items = len([i for i in current_shopping_list if not i['checked']])
        st.metric(label="📦 פריטים שנותרו", value=remaining_items)

    if st.session_state.budget > 0:
        budget_ratio = min(total_cost / st.session_state.budget, 1.0)
        st.progress(budget_ratio)
        if total_cost > st.session_state.budget:
            st.error("⚠️ שימו לב! עברתם את תקציב הקניות שהוגדר!")

    st.markdown("---")

    if not current_shopping_list:
        st.info("💡 רשימת הקניות ריקה! הוסף פריטים מלשונית 'הוספה' או 'מועדפים'.")
    else:
        active_items = [i for i in current_shopping_list if not i['checked']]
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))

        col_search, col_cat = st.columns([1.4, 1])
        with col_search:
            search_query = st.text_input("🔎 חיפוש פריט ברשימה:", value="", placeholder="הקלד שם פריט...")
        with col_cat:
            selected_category_filter = st.selectbox("📂 סינון מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        market_prices_cache = get_live_market_prices()

        for idx, item in enumerate(current_shopping_list):
            if not item['checked']:
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
                    continue
                if search_query.strip() and search_query.strip().lower() not in item['name'].lower():
                    continue

                icon, card_color = get_product_icon_and_color(item['category'])
                
                # שליפת פירוט מחירים מהרשתות עבור הכרטיס הנוכחי
                item_clean_name = item['name'].strip().lower()
                market_info = market_prices_cache.get(item_clean_name)
                
                prices_text_parts = []
                if market_info:
                    rl = market_info.get('rami_levy_price')
                    sh = market_info.get('shufersal_price')
                    yo = market_info.get('yohananof_price')
                    if rl: prices_text_parts.append(f"רמי לוי: ₪{rl}")
                    if sh: prices_text_parts.append(f"שופרסל: ₪{sh}")
                    if yo: prices_text_parts.append(f"יוחננוף: ₪{yo}")
                
                market_prices_str = " | ".join(prices_text_parts) if prices_text_parts else "אין נתוני רשתות עדכניים"

                with st.container():
                    st.markdown(f"""
                    <div class="product-card" style="border-right: 6px solid {card_color};">
                        <span style="font-size: 26px; margin-left: 12px;">{icon}</span>
                        <div style="flex-grow: 1;">
                            <span class="product-name">{item['name']}</span> &nbsp;|&nbsp; <b>כמות: {item['quantity']}</b><br>
                            <span class="product-details">מחיר משוער: <b>₪{item['quantity'] * item['estimated_price']:.2f}</b> &nbsp;&bull;&nbsp; קטגוריה: {item['category']}</span><br>
                            <span style="font-size: 11px; color: #0284c7;">🛒 השוואת רשתות: {market_prices_str}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_buy, col_minus, col_plus, col_edit, col_mis, col_del = st.columns([1.1, 0.6, 0.6, 1, 0.9, 0.9])
                    with col_buy:
                        if st.button("✔️ נקנה", key=f"buy_{idx}", type="primary"):
                            current_shopping_list[idx]['checked'] = True
                            save_data()
                            st.rerun()
                    with col_minus:
                        if st.button("➖", key=f"minus_{idx}"):
                            if item['quantity'] > 1:
                                current_shopping_list[idx]['quantity'] -= 1
                                save_data()
                                st.rerun()
                    with col_plus:
                        if st.button("➕", key=f"plus_{idx}"):
                            current_shopping_list[idx]['quantity'] += 1
                            save_data()
                            st.rerun()
                    with col_edit:
                        if st.button("✏️ עריכה", key=f"edit_btn_{idx}"):
                            curr_state = st.session_state.get(f"show_edit_shop_{idx}", False)
                            st.session_state[f"show_edit_shop_{idx}"] = not curr_state
                    with col_mis:
                        if st.button("❌ חסר", key=f"missing_{idx}"):
                            st.session_state.next_trip_list.append(item)
                            name_key = item['name'].strip().lower()
                            st.session_state.missing_item_counts[name_key] = st.session_state.missing_item_counts.get(name_key, 0) + 1
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                    with col_del:
                        if st.session_state.get(f"confirm_delete_{idx}", False):
                            if st.button("⚠️ למחוק?", key=f"delete_confirm_{idx}"):
                                current_shopping_list.pop(idx)
                                st.session_state.pop(f"confirm_delete_{idx}", None)
                                save_data()
                                st.rerun()
                        else:
                            if st.button("🗑️ מחק", key=f"delete_{idx}"):
                                st.session_state[f"confirm_delete_{idx}"] = True
                                st.rerun()

                if st.session_state.get(f"confirm_delete_{idx}", False):
                    col_cancel_del, _ = st.columns([1, 3])
                    with col_cancel_del:
                        if st.button("✖️ ביטול מחיקה", key=f"cancel_delete_{idx}"):
                            st.session_state.pop(f"confirm_delete_{idx}", None)
                            st.rerun()

                if st.session_state.get(f"show_edit_shop_{idx}", False):
                    with st.container():
                        with st.form(f"form_edit_item_{idx}"):
                            e_name = st.text_input("שם הפריט:", value=item['name'])
                            e_price = st.number_input("מחיר משוער ליחידה (₪):", value=float(item['estimated_price']))
                            current_cat_index = CATEGORIES.index(item['category']) if item['category'] in CATEGORIES else 7
                            e_category = st.selectbox("תקן קטגוריה:", CATEGORIES, index=current_cat_index)

                            if st.form_submit_button("שמור שינויים", type="primary"):
                                new_name_clean = e_name.strip()
                                current_shopping_list[idx]['name'] = new_name_clean
                                current_shopping_list[idx]['estimated_price'] = e_price
                                current_shopping_list[idx]['category'] = e_category

                                st.session_state.learned_categories[new_name_clean.lower()] = e_category
                                save_data()

                                st.session_state[f"show_edit_shop_{idx}"] = False
                                st.success("השינויים נשמרו והמערכת למדה את הקטגוריה לצמיתות!")
                                st.rerun()

                st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

        active_items = [i for i in current_shopping_list if not i['checked']]
        if active_items:
            st.markdown("---")
            msg_lines = [
                f"🛒 רשימת קניות ({st.session_state.active_store})",
                "",
                "הנה הפריטים שעדיין צריך לקנות:"
            ]
            for item in active_items:
                msg_lines.append(f"• {item['name']} (כמות: {item['quantity']})")

            whatsapp_msg = "\n".join(msg_lines)
            url_encoded_msg = urllib.parse.quote(whatsapp_msg)
            whatsapp_url = f"https://wa.me/?text={url_encoded_msg}"

            st.link_button(
                "📱 שתף את הרשימה בוואטסאפ",
                whatsapp_url,
                type="secondary",
                use_container_width=True
            )

        checked_items = [i for i in current_shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שסומנו כנקנו:")
            for idx, item in enumerate(current_shopping_list):
                if item['checked']:
                    col_chk_name, col_chk_return = st.columns([4, 1.2])
                    with col_chk_name:
                        st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")
                    with col_chk_return:
                        if st.button("↩️ החזר", key=f"return_{idx}"):
                            current_shopping_list[idx]['checked'] = False
                            save_data()
                            st.rerun()

            actual_prices_map = {}
            with st.expander("✏️ (אופציונלי) עדכן מחירים בפועל ששולמו, לפני שמירת הקנייה"):
                st.caption("ברירת המחדל היא המחיר המשוער. שנה רק אם אתה יודע את המחיר בפועל ששילמת.")
                for idx, item in enumerate(checked_items):
                    actual_prices_map[idx] = st.number_input(
                        f"{item['name']} (כמות {item['quantity']}) - מחיר בפועל ליחידה (₪):",
                        value=float(item['estimated_price']),
                        min_value=0.0,
                        key=f"actual_price_input_{idx}_{item['name']}"
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            col_end1, col_end2, col_end3 = st.columns(3)

            with col_end1:
                if st.button("🏁 סיים ושמור", type="primary", use_container_width=True):
                    trip_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    trip_total_estimated = sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                    trip_total_actual = sum(
                        i['quantity'] * actual_prices_map.get(idx, i['estimated_price'])
                        for idx, i in enumerate(checked_items)
                    )
                    st.session_state.purchase_history.append({
                        "date": trip_date,
                        "store": st.session_state.active_store,
                        "items_count": len(checked_items),
                        "total_cost": trip_total_estimated,
                        "actual_cost": trip_total_actual
                    })
                    st.session_state.stores[st.session_state.active_store] = [i for i in current_shopping_list if not i['checked']]
                    save_data()
                    st.success("הקנייה נשמרה בהצלחה!")
                    st.rerun()

            with col_end2:
                if st.button("🧹 מחק מסומנים", use_container_width=True):
                    st.session_state.stores[st.session_state.active_store] = [i for i in current_shopping_list if not i['checked']]
                    save_data()
                    st.rerun()

            with col_end3:
                confirm_empty = st.checkbox("אשר ריקון", key="confirm_empty_list")
                if st.button("🗑️ רוקן רשימה", use_container_width=True, disabled=not confirm_empty):
                    st.session_state.stores[st.session_state.active_store] = []
                    save_data()
                    st.session_state["confirm_empty_list"] = False
                    st.rerun()

# ----------------------------------------------------
# 2. הוספת פריט ידנית
# ----------------------------------------------------
with tab2:
    st.subheader("➕ הוספת פריט ידנית")

    if st.session_state.get('last_added_item'):
        last = st.session_state.last_added_item
        st.success(f"✅ נוסף בהצלחה: **{last['name']}** (כמות: {last['qty']}) | מחלקה: {last['cat']} | מחיר משוער: ₪{last['price']:.2f}")
        st.session_state.pop('last_added_item', None)

    with st.form("add_item_form"):
        known_items = sorted(list(set(st.session_state.all_purchased_items)))

        st.write("בחר פריט מתוך ההיסטוריה שלמדת או הקלד פריט חדש:")
        selected_known_item = st.selectbox("פריטים מוכרים בהיסטוריה:", ["-- בחר מההיסטוריה או הקלד למטה --"] + known_items)
        manual_item_name = st.text_input("או הקלד שם פריט חדש באופן חופשי:")

        item_qty = st.number_input("כמות", min_value=1, value=1)

        if st.form_submit_button("הוסף לרשימה 🛒", type="primary"):
            final_name = ""
            if manual_item_name.strip():
                final_name = manual_item_name.strip()
            elif selected_known_item != "-- בחר מההיסטוריה או הקלד למטה --":
                final_name = selected_known_item

            if final_name:
                exists = any(
                    item['name'] == final_name and not item['checked']
                    for item in current_shopping_list
                )

                if exists:
                    st.warning(f"⚠️ הפריט '{final_name}' כבר קיים ברשימת הקניות הנוכחית!")
                else:
                    category, price = ai_smart_categorize_and_price(final_name)

                    current_shopping_list.append({
                        "name": final_name,
                        "quantity": item_qty,
                        "category": category,
                        "estimated_price": price,
                        "checked": False
                    })

                    if final_name not in st.session_state.all_purchased_items:
                        st.session_state.all_purchased_items.append(final_name)

                    save_data()

                    st.session_state.last_added_item = {
                        "name": final_name,
                        "qty": item_qty,
                        "cat": category,
                        "price": price
                    }
                    st.rerun()
            else:
                st.warning("נא לבחור פריט מהרשימה או להקליד שם פריט חדש.")

# ----------------------------------------------------
# 3. מועדפים
# ----------------------------------------------------
with tab3:
    st.subheader("⭐ הוספה מהירה ממועדפים")
    for idx, fav in enumerate(FAVOURITES_DB):
        col_f, col_btn = st.columns([3, 1])
        live_fav_price = get_best_market_price(fav['name'])
        display_fav_price = live_fav_price if live_fav_price is not None else fav['estimated_price']
        
        col_f.write(f"**{fav['name']}** (₪{display_fav_price})")
        if col_btn.button("➕ הוסף", key=f"fav_{idx}"):
            current_shopping_list.append({
                "name": fav['name'],
                "quantity": 1,
                "category": fav['category'],
                "estimated_price": display_fav_price,
                "checked": False
            })
            if fav['name'] not in st.session_state.all_purchased_items:
                st.session_state.all_purchased_items.append(fav['name'])
            save_data()
            st.success(f"נוסף בהצלחה: {fav['name']}!")

    st.markdown("---")
    st.subheader("🌟 המועדפים האישיים שלי")
    st.caption("מועדפים שאתה בעצמך הוספת - נשמרים בענן ומופיעים כאן לתמיד.")

    if not st.session_state.personal_favourites:
        st.info("עדיין לא הוספת מועדפים אישיים. אפשר להוסיף למטה, או דרך לשונית 'לקנייה הבאה'.")
    else:
        for pidx, pfav in enumerate(st.session_state.personal_favourites):
            col_pf, col_pf_add, col_pf_del = st.columns([2.4, 1, 1])
            live_pf_price = get_best_market_price(pfav['name'])
            display_pf_price = live_pf_price if live_pf_price is not None else pfav['estimated_price']

            col_pf.write(f"**{pfav['name']}** (₪{display_pf_price}) | {pfav['category']}")
            if col_pf_add.button("➕ הוסף", key=f"personal_fav_add_{pidx}"):
                current_shopping_list.append({
                    "name": pfav['name'],
                    "quantity": 1,
                    "category": pfav['category'],
                    "estimated_price": display_pf_price,
                    "checked": False
                })
                if pfav['name'] not in st.session_state.all_purchased_items:
                    st.session_state.all_purchased_items.append(pfav['name'])
                save_data()
                st.success(f"נוסף בהצלחה: {pfav['name']}!")
            if col_pf_del.button("🗑️ הסר", key=f"personal_fav_del_{pidx}"):
                st.session_state.personal_favourites.pop(pidx)
                save_data()
                st.rerun()

    with st.expander("➕ הוסף מועדף אישי חדש"):
        with st.form("add_personal_fav_form"):
            pf_name = st.text_input("שם הפריט:")
            pf_category = st.selectbox("קטגוריה:", CATEGORIES, key="pf_new_cat")
            pf_price = st.number_input("מחיר משוער (₪):", min_value=0.0, value=10.0, key="pf_new_price")
            if st.form_submit_button("שמור כמועדף אישי", type="primary"):
                if pf_name.strip():
                    st.session_state.personal_favourites.append({
                        "name": pf_name.strip(),
                        "category": pf_category,
                        "estimated_price": pf_price
                    })
                    save_data()
                    st.success(f"'{pf_name.strip()}' נוסף למועדפים האישיים!")
                    st.rerun()
                else:
                    st.warning("נא להזין שם פריט.")

# ----------------------------------------------------
# 4. סידור מסלול
# ----------------------------------------------------
with tab4:
    st.subheader("🗺️ מסלול הליכה חכם בסופר")
    active_items = [i for i in current_shopping_list if not i['checked']]
    sorted_items = sorted(active_items, key=lambda x: AISLE_ORDER.get(x['category'], 99))
    for item in sorted_items:
        icon, _ = get_product_icon_and_color(item['category'])
        st.write(f"• {icon} **{item['name']}** (מחלקה: {item['category']})")

# ----------------------------------------------------
# 5. השוואת מחירים
# ----------------------------------------------------
with tab5:
    st.subheader("🧮 השוואת מחירים בין רשתות (מהטבלה המעודכנת)")
    
    market_prices_dict = get_live_market_prices()
    if market_prices_dict:
        st.write("מחירים מעודכנים שנשלפו מהרשתות הגדולות:")
        price_table_data = []
        for name, data in market_prices_dict.items():
            price_table_data.append({
                "שם המוצר": name,
                "רמי לוי (₪)": data.get('rami_levy_price'),
                "שופרסל (₪)": data.get('shufersal_price'),
                "יוחננוף (₪)": data.get('yohananof_price'),
                "עדכון אחרון": data.get('last_updated')
            })
        st.dataframe(pd.DataFrame(price_table_data), use_container_width=True)
    else:
        st.info("עדיין לא קיימים נתוני מחירים חיים בטבלת supermarket_prices במסד הנתונים.")

    st.markdown("---")
    st.subheader("🧮 מחשבון כדאיות אריזות (מה משתלם יותר?)")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("אריזה א'")
        pa = st.number_input("מחיר ₪", value=10.0, key="pa")
        aa = st.number_input("כמות/משקל", value=500.0, key="aa")
    with col_b:
        st.write("אריזה ב'")
        pb = st.number_input("מחיר ₪", value=18.0, key="pb")
        ab = st.number_input("כמות/משקל", value=1000.0, key="ab")
    if aa > 0 and ab > 0:
        if (pa / aa) < (pb / ab):
            st.success("אריזה א' זולה יותר ליחידה!")
        elif (pb / ab) < (pa / aa):
            st.success("אריזה ב' זולה יותר ליחידה!")
        else:
            st.info("המחיר ליחידה זהה.")

# ----------------------------------------------------
# 6. לקנייה הבאה
# ----------------------------------------------------
with tab6:
    st.subheader("🛍️ פריטים שהוגדרו כחסרים (לקנייה הבאה)")
    st.write("כאן מופיעים פריטים שסימנת כ'חסר' בסופר. תוכל להחזיר אותם לרשימה הפעילה לקראת הקנייה הבאה:")

    if not st.session_state.next_trip_list:
        st.info("אין פריטים חסרים כרגע.")
    else:
        for idx, item in enumerate(st.session_state.next_trip_list):
            col_n, col_add_back, col_rem_next = st.columns([3, 1.2, 1])
            col_n.write(f"• **{item['name']}** (כמות: {item['quantity']}, מחלקה: {item['category']})")

            if col_add_back.button("➕ החזר לסל", key=f"add_back_{idx}"):
                current_shopping_list.append(item)
                st.session_state.next_trip_list.pop(idx)
                save_data()
                st.success("הפריט הוחזר לרשימה הפעילה!")
                st.rerun()

            if col_rem_next.button("🗑️ הסר", key=f"rem_next_{idx}"):
                st.session_state.next_trip_list.pop(idx)
                save_data()
                st.rerun()

            name_key = item['name'].strip().lower()
            times_missing = st.session_state.missing_item_counts.get(name_key, 0)
            already_fav = any(pf['name'].strip().lower() == name_key for pf in st.session_state.personal_favourites)
            if times_missing >= MISSING_ITEM_SUGGESTION_THRESHOLD and not already_fav:
                st.info(f"💡 שמתם לב? '{item['name']}' חסר לכם כבר {times_missing} פעמים. כדאי להוסיף אותו למועדפים?")
                if st.button(f"⭐ הוסף את '{item['name']}' למועדפים האישיים", key=f"suggest_fav_{idx}"):
                    st.session_state.personal_favourites.append({
                        "name": item['name'],
                        "category": item['category'],
                        "estimated_price": item['estimated_price']
                    })
                    save_data()
                    st.success("נוסף למועדפים האישיים!")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 העבר את כל הפריטים החסרים לסל הפעיל", type="primary"):
            for item in st.session_state.next_trip_list:
                current_shopping_list.append(item)
            st.session_state.next_trip_list = []
            save_data()
            st.success("כל הפריטים הוחזרו לרשימת הקניות הפעילה!")
            st.rerun()

# ----------------------------------------------------
# 7. קבלות והיסטוריה
# ----------------------------------------------------
with tab7:
    st.subheader("📊 תקציב והיסטוריה")
    new_budget = st.number_input("הגדר תקציב מקסימלי (₪):", value=float(st.session_state.budget))
    if new_budget != st.session_state.budget:
        st.session_state.budget = new_budget
        save_data()

    if st.session_state.purchase_history:
        history_df = pd.DataFrame(st.session_state.purchase_history)
        st.dataframe(history_df, use_container_width=True)

        csv_data = history_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 הורד היסטוריית קניות כקובץ CSV",
            data=csv_data,
            file_name="purchase_history.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.subheader("📈 גרף הוצאות")

        cost_column = "total_cost"
        if "actual_cost" in history_df.columns and history_df["actual_cost"].notna().any():
            st.caption("הגרף מציג את המחיר בפועל כשקיים, אחרת את המחיר המשוער.")
            history_df["display_cost"] = history_df["actual_cost"].fillna(history_df["total_cost"])
            cost_column = "display_cost"

        chart_view = st.radio("הצג הוצאות לפי:", ["חנות", "תאריך קנייה"], horizontal=True)

        if chart_view == "חנות":
            by_store = history_df.groupby("store")[cost_column].sum()
            st.bar_chart(by_store)
        else:
            by_date = history_df.groupby("date")[cost_column].sum()
            st.bar_chart(by_date)

        if "actual_cost" in history_df.columns and history_df["actual_cost"].notna().any():
            avg_estimated = history_df["total_cost"].mean()
            avg_actual = history_df["actual_cost"].mean()
            diff = avg_actual - avg_estimated
            col_avg1, col_avg2, col_avg3 = st.columns(3)
            col_avg1.metric("ממוצע משוער לקנייה", f"₪{avg_estimated:.2f}")
            col_avg2.metric("ממוצע בפועל לקנייה", f"₪{avg_actual:.2f}")
            col_avg3.metric("פער ממוצע", f"₪{diff:.2f}", delta=f"{diff:.2f}")
    else:
        st.info("עדיין אין היסטוריית קניות שמורה.")

# ----------------------------------------------------
# 8. ניהול חנויות והגדרות
# ----------------------------------------------------
with tab8:
    st.title("🏪 חנויות והגדרות")

    st.subheader("💾 גיבוי ושחזור נתוני הקניות")
    st.write("כדי לוודא שלעולם לא תאבד את הרשימות, ההיסטוריה והחנויות שלך, תוכל להוריד קובץ גיבוי או לשחזר ממנו:")

    backup_data_json = json.dumps({
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "recurring_items": st.session_state.recurring_items,
        "learned_categories": st.session_state.learned_categories,
        "all_purchased_items": st.session_state.all_purchased_items,
        "budget": st.session_state.budget,
        "personal_favourites": st.session_state.personal_favourites,
        "missing_item_counts": st.session_state.missing_item_counts
    }, ensure_ascii=False, indent=4)

    st.download_button(
        label="📥 הורד קובץ גיבוי מלא (JSON)",
        data=backup_data_json,
        file_name="shopping_trip_backup.json",
        mime="application/json"
    )

    uploaded_backup = st.file_uploader("📤 שחזר נתונים מקובץ גיבוי קודם:", type=["json"])
    if uploaded_backup is not None:
        try:
            restored_data = json.load(uploaded_backup)
            st.session_state.stores = restored_data.get("stores", {"סופרמרקט מרכזי": []})
            st.session_state.active_store = restored_data.get("active_store", "סופרמרקט מרכזי")
            st.session_state.next_trip_list = restored_data.get("next_trip_list", [])
            st.session_state.purchase_history = restored_data.get("purchase_history", [])
            st.session_state.recurring_items = restored_data.get("recurring_items", [])
            st.session_state.learned_categories = restored_data.get("learned_categories", {})
            st.session_state.all_purchased_items = restored_data.get("all_purchased_items", [])
            st.session_state.budget = restored_data.get("budget", 300.0)
            st.session_state.personal_favourites = restored_data.get("personal_favourites", [])
            st.session_state.missing_item_counts = restored_data.get("missing_item_counts", {})
            save_data()
            st.success("הנתונים שוחזרו בהצלחה!")
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשחזור הקובץ: {e}")

    st.markdown("---")
    st.subheader("➕ הוספת חנות חדשה")
    store_types = ["סופרמרקט", "סופר-פארם / בית מרקחת", "ירקניה", "קצבייה", "מאפייה", "חנות חיות", "טמבוריה", "אחר"]
    selected_type = st.selectbox("בחר סוג חנות:", store_types)
    new_store_name = st.text_input("שם החנות החדשה:", value=f"{selected_type} חדש")

    if st.button("צור חנות ✅", type="primary"):
        if new_store_name.strip():
            if new_store_name.strip() not in st.session_state.stores:
                st.session_state.stores[new_store_name.strip()] = []
                st.session_state.active_store = new_store_name.strip()
                save_data()
                st.success(f"החנות '{new_store_name.strip()}' נוספה בהצלחה!")
                st.rerun()
            else:
                st.error("כבר קיימת חנות בשם זה.")
        else:
            st.warning("נא להזין שם תקין לחנות.")

    st.markdown("---")
    st.subheader("📋 שכפול רשימה לחנות אחרת")
    st.caption(f"מעתיק את הפריטים הפעילים (שלא נקנו) מהחנות '{st.session_state.active_store}' לחנות אחרת.")
    other_stores = [s for s in st.session_state.stores.keys() if s != st.session_state.active_store]
    if not other_stores:
        st.info("אין עדיין חנות נוספת להעתיק אליה. צור חנות חדשה למעלה קודם.")
    else:
        target_store = st.selectbox("העתק אל חנות:", other_stores, key="duplicate_target_store")
        if st.button("📋 שכפל רשימה לחנות שנבחרה"):
            items_to_copy = [dict(i) for i in current_shopping_list if not i['checked']]
            for i in items_to_copy:
                i['checked'] = False
            st.session_state.stores[target_store].extend(items_to_copy)
            save_data()
            st.success(f"{len(items_to_copy)} פריטים שוכפלו לחנות '{target_store}'!")
            st.rerun()

    st.markdown("---")
    st.subheader("🗑️ מחיקת חנות קיימת")
    store_to_delete = st.selectbox("בחר חנות למחיקה:", list(st.session_state.stores.keys()))
    confirm_store_delete = st.checkbox(f"אני מאשר מחיקה סופית של החנות '{store_to_delete}' וכל תוכן", key="confirm_store_delete")
    if st.button("🗑️ מחק חנות זו לצמיתות", disabled=not confirm_store_delete):
        if len(st.session_state.stores) > 1:
            del st.session_state.stores[store_to_delete]
            if st.session_state.active_store == store_to_delete:
                st.session_state.active_store = list(st.session_state.stores.keys())[0]
            save_data()
            st.session_state["confirm_store_delete"] = False
            st.success("החנות נמחקה!")
            st.rerun()
        else:
            st.error("חייבת להישאר לפחות חנות אחת פעילה באפליקציה.")
