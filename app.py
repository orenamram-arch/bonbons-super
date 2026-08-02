import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import requests
import google.generativeai as genai

# הגדרת עמוד האפליקציה (חייב להיות ראשון)
st.set_page_config(page_title="ניהול קניות משפחתי", page_icon="🛒", layout="centered")

# ==========================================
# הגדרות GitHub
# ==========================================
GITHUB_TOKEN = "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"
REPO_OWNER = "orenamram-arch"
REPO_NAME = "mrp_checking"
FILE_PATH = "shopping_data.json"

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
    "ירקות ופירות": 1, "מאפים": 2, "מוצרי חלב": 3, "בשר ודגים": 4,
    "שימורים ויבשים": 5, "חטיפים וממתקים": 6, "חומרי ניקוי": 7, "שונות": 8
}

# ----------------------------------------------------
# פונקציות סנכרון מול GitHub
# ----------------------------------------------------
def fetch_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_info = response.json()
            file_content = base64.b64decode(file_info['content']).decode('utf-8')
            return json.loads(file_content)
    except Exception:
        pass
    return None

def save_to_github():
    data = {
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "recurring_items": st.session_state.recurring_items,
        "learned_categories": st.session_state.learned_categories,
        "all_purchased_items": st.session_state.all_purchased_items,
        "budget": st.session_state.budget
    }
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        get_resp = requests.get(url, headers=headers)
        sha = get_resp.json().get('sha') if get_resp.status_code == 200 else None
        json_str = json.dumps(data, ensure_ascii=False, indent=4)
        encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        
        payload = {"message": "Sync shopping data", "content": encoded_content}
        if sha: payload["sha"] = sha
        
        put_resp = requests.put(url, headers=headers, json=payload)
        if put_resp.status_code in [200, 201]:
            st.toast("✅ הנתונים סונכרנו ונשמרו בענן בהצלחה!", icon="☁️")
        else:
            st.error(f"שגיאת סנכרון מול הענן: {put_resp.text}")
    except Exception as e:
        st.error(f"שגיאת תקשורת מול GitHub: {e}")

# הגדרת ה-AI (Gemini)
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
except:
    AI_AVAILABLE = False

# טעינה ראשונית לעבודה מול זיכרון המערכת
if 'data_loaded' not in st.session_state:
    cloud_data = fetch_from_github()
    if not cloud_data or not cloud_data.get("stores"):
        cloud_data = {
            "stores": {"סופרמרקט מרכזי": []},
            "active_store": "סופרמרקט מרכזי",
            "next_trip_list": [],
            "purchase_history": [],
            "recurring_items": [],
            "learned_categories": {},
            "all_purchased_items": [],
            "budget": 300.0
        }

    st.session_state.stores = cloud_data.get("stores", {"סופרמרקט מרכזי": []})
    st.session_state.active_store = cloud_data.get("active_store", "סופרמרקט מרכזי")
    st.session_state.next_trip_list = cloud_data.get("next_trip_list", [])
    st.session_state.purchase_history = cloud_data.get("purchase_history", [])
    st.session_state.recurring_items = cloud_data.get("recurring_items", [])
    st.session_state.learned_categories = cloud_data.get("learned_categories", {})
    st.session_state.all_purchased_items = cloud_data.get("all_purchased_items", [])
    st.session_state.budget = cloud_data.get("budget", 300.0)
    st.session_state.data_loaded = True

if st.session_state.active_store not in st.session_state.stores:
    st.session_state.stores[st.session_state.active_store] = []

current_shopping_list = st.session_state.stores[st.session_state.active_store]

# --- עיצוב דינמי ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');
    :root { --app-bg: #f7f9fb; --card-bg: #ffffff; --app-text: #0f172a; --sub-text: #64748b; --app-border: #e2e8f0; }
    @media (prefers-color-scheme: dark) {
        :root { --app-bg: #0f172a; --card-bg: #1e293b; --app-text: #f8fafc; --sub-text: #94a3b8; --app-border: #334155; }
    }
    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] { display: none !important; }
    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif !important; color: var(--app-text) !important;
    }
    .stApp { background-color: var(--app-bg); }
    h1, h2, h3 { color: var(--app-text) !important; font-weight: 800 !important; }
    .product-card {
        background-color: var(--card-bg); border: 1px solid var(--app-border); padding: 14px 16px; border-radius: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 6px; display: flex; align-items: center;
    }
    .product-name { font-size: 18px !important; font-weight: 700 !important; color: var(--app-text); }
    .product-details { font-size: 13px; color: var(--sub-text); }
    .stButton>button { border-radius: 10px; font-weight: 600; transition: all 0.2s; width: 100%; }
</style>
""", unsafe_allow_html=True)

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
        return st.session_state.learned_categories[clean_name], 12.0

    if AI_AVAILABLE:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"You are a smart shopping assistant. Categorize '{clean_name}' into EXACTLY ONE of: {', '.join(CATEGORIES)}. Reply ONLY with the exact category name in Hebrew."
            response = model.generate_content(prompt)
            predicted_category = response.text.strip()
            if predicted_category in CATEGORIES:
                st.session_state.learned_categories[clean_name] = predicted_category
                return predicted_category, 12.0
        except Exception:
            pass
    return "שונות", 12.0

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🛒 רשימה", "➕ הוספה", "⭐ מועדפים", "🗺️ סידור", "🧮 השוואה", "🛍️ לקנייה הבאה", "📊 קבלות", "🏪 חנויות"
])

with tab1:
    # כפתור סנכרון ידני מהיר בראש הרשימה
    c_store, c_sync = st.columns([3, 1.3])
    with c_store:
        store_list = list(st.session_state.stores.keys())
        selected_store = st.selectbox("🏪 חנות פעילה כרגע:", store_list, index=store_list.index(st.session_state.active_store), label_visibility="collapsed")
        if selected_store != st.session_state.active_store:
            st.session_state.active_store = selected_store
            save_to_github(); st.rerun()
    with c_sync:
        if st.button("🔄 סנכרן ענן", use_container_width=True):
            cloud_data = fetch_from_github()
            if cloud_data and cloud_data.get("stores"):
                st.session_state.stores = cloud_data.get("stores")
                st.session_state.active_store = cloud_data.get("active_store", list(st.session_state.stores.keys())[0])
                st.session_state.next_trip_list = cloud_data.get("next_trip_list", [])
                st.session_state.purchase_history = cloud_data.get("purchase_history", [])
                st.session_state.recurring_items = cloud_data.get("recurring_items", [])
                st.session_state.learned_categories = cloud_data.get("learned_categories", {})
                st.session_state.all_purchased_items = cloud_data.get("all_purchased_items", [])
                st.session_state.budget = cloud_data.get("budget", 300.0)
                st.success("הנתונים עודכנו מהענן!")
                st.rerun()
            else:
                st.warning("לא נמצאו נתונים בענן")

    st.markdown("---")
    total_cost = sum(item['quantity'] * item['estimated_price'] for item in current_shopping_list if not item['checked'])

    col1, col2 = st.columns(2)
    with col1: st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2: st.metric(label="📦 פריטים שנותרו", value=len([i for i in current_shopping_list if not i['checked']]))

    if not current_shopping_list:
        st.info("💡 רשימת הקניות ריקה!")
    else:
        for idx, item in enumerate(current_shopping_list):
            if not item['checked']:
                icon, card_color = get_product_icon_and_color(item['category'])
                st.markdown(f"""
                <div class="product-card" style="border-right: 6px solid {card_color};">
                    <span style="font-size: 26px; margin-left: 12px;">{icon}</span>
                    <div style="flex-grow: 1;">
                        <span class="product-name">{item['name']}</span> &nbsp;|&nbsp; <b>כמות: {item['quantity']}</b><br>
                        <span class="product-details">מחיר משוער: <b>₪{item['quantity'] * item['estimated_price']:.2f}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c_buy, c_minus, c_plus, c_del = st.columns([1.2, 0.8, 0.8, 1])
                with c_buy:
                    if st.button("✔️ נקנה", key=f"buy_{idx}", type="primary"):
                        current_shopping_list[idx]['checked'] = True
                        save_to_github(); st.rerun()
                with c_minus:
                    if st.button("➖", key=f"minus_{idx}") and item['quantity'] > 1:
                        current_shopping_list[idx]['quantity'] -= 1
                        save_to_github(); st.rerun()
                with c_plus:
                    if st.button("➕", key=f"plus_{idx}"):
                        current_shopping_list[idx]['quantity'] += 1
                        save_to_github(); st.rerun()
                with c_del:
                    if st.button("🗑️ מחק", key=f"del_{idx}"):
                        current_shopping_list.pop(idx)
                        save_to_github(); st.rerun()

        checked_items = [i for i in current_shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            if st.button("🏁 סיים ושמור קנייה", type="primary", use_container_width=True):
                trip_total = sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                st.session_state.purchase_history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "store": st.session_state.active_store, "total_cost": trip_total})
                st.session_state.stores[st.session_state.active_store] = [i for i in current_shopping_list if not i['checked']]
                save_to_github(); st.rerun()

with tab2:
    st.subheader("➕ הוספת פריט")
    with st.form("add_form"):
        item_name = st.text_input("שם הפריט:")
        if st.form_submit_button("הוסף לרשימה 🛒", type="primary") and item_name.strip():
            cat, price = ai_smart_categorize_and_price(item_name)
            current_shopping_list.append({
                "name": item_name.strip(), 
                "quantity": 1, 
                "category": cat, 
                "estimated_price": price, 
                "checked": False
            })
            save_to_github()
            st.success("נוסף ונשמר בענן בהצלחה!")
            st.rerun()

with tab3:
    st.subheader("⭐ מועדפים")
    for idx, fav in enumerate(FAVOURITES_DB):
        if st.button(f"➕ {fav['name']} (₪{fav['estimated_price']})", key=f"fav_{idx}"):
            current_shopping_list.append({"name": fav['name'], "quantity": 1, "category": fav['category'], "estimated_price": fav['estimated_price'], "checked": False})
            save_to_github(); st.success("נוסף!"); st.rerun()

with tab4:
    st.subheader("🗺️ מסלול הליכה בסופר")
    for item in sorted([i for i in current_shopping_list if not i['checked']], key=lambda x: AISLE_ORDER.get(x['category'], 99)):
        st.write(f"• **{item['name']}** ({item['category']})")

with tab5:
    st.subheader("🧮 השוואת מחירים")
    pa = st.number_input("מחיר א'", value=10.0, key="pa")
    aa = st.number_input("כמות א'", value=500.0, key="aa")
    pb = st.number_input("מחיר ב'", value=18.0, key="pb")
    ab = st.number_input("כמות ב'", value=1000.0, key="ab")
    if aa > 0 and ab > 0:
        st.success("אריזה א' זולה יותר!" if (pa/aa) < (pb/ab) else "אריזה ב' זולה יותר!")

with tab6:
    st.subheader("🛍️ לקנייה הבאה")
    st.info("כאן יופיעו פריטים שסומנו כחסרים.")

with tab7:
    st.subheader("📊 תקציב והיסטוריה")
    new_budget = st.number_input("תקציב מקסימלי (₪):", value=float(st.session_state.budget))
    if new_budget != st.session_state.budget:
        st.session_state.budget = new_budget; save_to_github()
    if st.session_state.purchase_history:
        st.dataframe(pd.DataFrame(st.session_state.purchase_history), use_container_width=True)

with tab8:
    st.subheader("🏪 ניהול חנויות")
    new_store = st.text_input("שם חנות חדשה:")
    if st.button("צור חנות ✅") and new_store.strip():
        st.session_state.stores[new_store.strip()] = []
        st.session_state.active_store = new_store.strip()
        save_to_github(); st.rerun()
