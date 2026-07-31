import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import difflib
import requests

# -----------------------------
# הגדרות בסיס
# -----------------------------
st.set_page_config(page_title="ניהול קניות חכם", page_icon="🛒", layout="centered")

DATA_FILE = "shopping_data.json"
CATEGORIES = [
    "ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים",
    "חומרי ניקוי", "חטיפים וממתקים", "שימורים ויבשים", "שונות"
]

FAVOURITES_DB = [
    {"name": "חלב 3%", "category": "מוצרי חלב", "estimated_price": 7.2},
    {"name": "לחם אחיד", "category": "מאפים", "estimated_price": 8.5},
    {"name": "ביצים (לארג')", "category": "מוצרי חלב", "estimated_price": 14.0},
    {"name": "מלפפונים", "category": "ירקות ופירות", "estimated_price": 10.0},
    {"name": "עגבניות", "category": "ירקות ופירות", "estimated_price": 12.0},
    {"name": "קוטג'", "category": "מוצרי חלב", "estimated_price": 6.8}
]

SMART_DB = {
    "מלפפונים": ("ירקות ופירות", 10.0),
    "עגבניות": ("ירקות ופירות", 12.0),
    "בצל": ("ירקות ופירות", 6.0),
    "תפוחים": ("ירקות ופירות", 14.0),
    "בננות": ("ירקות ופירות", 10.0),
    "גזר": ("ירקות ופירות", 6.0),
    "פלפלים": ("ירקות ופירות", 15.0),
    "חלב": ("מוצרי חלב", 7.2),
    "גבינה": ("מוצרי חלב", 6.8),
    "קוטג'": ("מוצרי חלב", 6.8),
    "ביצים": ("מוצרי חלב", 14.0),
    "עוף": ("בשר ודגים", 35.0),
    "לחם": ("מאפים", 8.5),
    "אקונומיקה": ("חומרי ניקוי", 10.0),
    "שוקולד": ("חטיפים וממתקים", 6.5),
    "אורז": ("שימורים ויבשים", 10.0),
    "פסטה": ("שימורים ויבשים", 6.5),
}

# -----------------------------
# טעינת נתונים
# -----------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "shopping_list" in data and "stores" not in data:
                    data["stores"] = {"סופרמרקט מרכזי": data["shopping_list"]}
                    data["active_store"] = "סופרמרקט מרכזי"
                return data
        except:
            pass

    return {
        "stores": {"סופרמרקט מרכזי": []},
        "active_store": "סופרמרקט מרכזי",
        "next_trip_list": [],
        "purchase_history": [],
        "budget": 300.0,
        "cloud_sync_url": "",
        "dark_mode": False
    }

def save_data():
    data = {
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "budget": st.session_state.budget,
        "cloud_sync_url": st.session_state.cloud_sync_url,
        "dark_mode": st.session_state.dark_mode
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    if st.session_state.cloud_sync_url:
        try:
            requests.put(st.session_state.cloud_sync_url, json=data, timeout=2)
        except:
            pass

# -----------------------------
# אתחול session_state
# -----------------------------
saved = load_data()

for key, val in saved.items():
    if key not in st.session_state:
        st.session_state[key] = val

# -----------------------------
# AI קטגוריזציה חכמה
# -----------------------------
def ai_smart_categorize_and_price(name):
    name = name.strip().lower()
    keys = list(SMART_DB.keys())
    match = difflib.get_close_matches(name, keys, n=1, cutoff=0.6)
    if match:
        return SMART_DB[match[0]]
    return "שונות", 12.0

# -----------------------------
# UI – מצב כהה
# -----------------------------
dark = st.session_state.dark_mode
bg = "#0f172a" if dark else "#f7f9fb"
card = "#1e293b" if dark else "#ffffff"
text = "#f8fafc" if dark else "#0f172a"
sub = "#94a3b8" if dark else "#64748b"
border = "#334155" if dark else "#e2e8f0"

st.markdown(f"""
<style>
body, .stApp {{
    direction: rtl;
    text-align: right;
    background-color: {bg};
    color: {text};
    font-family: 'Assistant', sans-serif;
}}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# תפריט צד
# -----------------------------
st.sidebar.title("🛒 ניהול קניות")
st.sidebar.markdown("---")

store_list = list(st.session_state.stores.keys())
selected_store = st.sidebar.selectbox("🏪 חנות:", store_list)

if selected_store != st.session_state.active_store:
    st.session_state.active_store = selected_store
    save_data()
    st.rerun()

new_store = st.sidebar.text_input("➕ הוסף חנות:")
if st.sidebar.button("צור"):
    if new_store.strip() and new_store not in st.session_state.stores:
        st.session_state.stores[new_store] = []
        st.session_state.active_store = new_store
        save_data()
        st.rerun()

menu = st.sidebar.radio("ניווט:", [
    "🛒 רשימת קניות",
    "➕ הוספת פריט",
    "⭐ מועדפים",
    "📷 סריקת טקסט",
    "📊 סטטיסטיקות",
    "⚙️ הגדרות"
])

st.sidebar.markdown("---")
dark_toggle = st.sidebar.toggle("🌙 מצב כהה", value=st.session_state.dark_mode)
if dark_toggle != st.session_state.dark_mode:
    st.session_state.dark_mode = dark_toggle
    save_data()
    st.rerun()

# -----------------------------
# מסכים
# -----------------------------
current_list = st.session_state.stores[st.session_state.active_store]

# -----------------------------
# 1. רשימת קניות
# -----------------------------
if menu == "🛒 רשימת קניות":
    st.title(f"🛒 רשימה עבור: {st.session_state.active_store}")

    total_cost = sum(i["quantity"] * i["estimated_price"] for i in current_list if not i["checked"])
    st.metric("💰 עלות נוכחית", f"₪{total_cost:.2f}")

    if st.session_state.budget > 0:
        st.progress(min(total_cost / st.session_state.budget, 1.0))

    st.markdown("---")

    for idx, item in enumerate(current_list):
        if not item["checked"]:
            st.write(f"**{item['name']}** — כמות: {item['quantity']} — ₪{item['estimated_price'] * item['quantity']:.2f}")
            col1, col2, col3 = st.columns(3)
            if col1.button("✔️ נקנה", key=f"buy{idx}"):
                item["checked"] = True
                save_data()
                st.rerun()
            if col2.button("➕", key=f"plus{idx}"):
                item["quantity"] += 1
                save_data()
                st.rerun()
            if col3.button("🗑️", key=f"del{idx}"):
                current_list.pop(idx)
                save_data()
                st.rerun()

    st.markdown("---")
    st.subheader("נקנו:")
    for idx, item in enumerate(current_list):
        if item["checked"]:
            st.write(f"~~{item['name']}~~")
            if st.button("↩️ החזר", key=f"ret{idx}"):
                item["checked"] = False
                save_data()
                st.rerun()

# -----------------------------
# 2. הוספת פריט
# -----------------------------
elif menu == "➕ הוספת פריט":
    st.title("➕ הוספת פריט")
    with st.form("add_form"):
        name = st.text_input("שם הפריט")
        qty = st.number_input("כמות", min_value=1, value=1)
        submit = st.form_submit_button("הוסף")
        if submit and name.strip():
            cat, price = ai_smart_categorize_and_price(name)
            current_list.append({
                "name": name.strip(),
                "quantity": qty,
                "category": cat,
                "estimated_price": price,
                "checked": False
            })
            save_data()
            st.success("נוסף!")

# -----------------------------
# 3. מועדפים
# -----------------------------
elif menu == "⭐ מועדפים":
    st.title("⭐ מועדפים")
    for fav in FAVOURITES_DB:
        if st.button(f"➕ {fav['name']}"):
            current_list.append({
                "name": fav["name"],
                "quantity": 1,
                "category": fav["category"],
                "estimated_price": fav["estimated_price"],
                "checked": False
            })
            save_data()
            st.success("נוסף!")

# -----------------------------
# 4. סריקת טקסט
# -----------------------------
elif menu == "📷 סריקת טקסט":
    st.title("📷 סריקת טקסט")
    raw = st.text_area("הכנס טקסט:")
    if st.button("הוסף"):
        for part in raw.split(","):
            part = part.strip()
            if part:
                cat, price = ai_smart_categorize_and_price(part)
                current_list.append({
                    "name": part,
                    "quantity": 1,
                    "category": cat,
                    "estimated_price": price,
                    "checked": False
                })
        save_data()
        st.success("נוסף!")

# -----------------------------
# 5. סטטיסטיקות
# -----------------------------
elif menu == "📊 סטטיסטיקות":
    st.title("📊 סטטיסטיקות")
    df = pd.DataFrame(st.session_state.purchase_history)
    if df.empty:
        st.info("אין היסטוריה.")
    else:
        st.dataframe(df)

# -----------------------------
# 6. הגדרות
# -----------------------------
elif menu == "⚙️ הגדרות":
    st.title("⚙️ הגדרות")
    url = st.text_input("כתובת סנכרון:", value=st.session_state.cloud_sync_url)
    if st.button("שמור"):
        st.session_state.cloud_sync_url = url.strip()
        save_data()
        st.success("נשמר!")
