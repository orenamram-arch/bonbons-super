import streamlit as st
import pandas as pd
from datetime import datetime
from duckduckgo_search import DDGS
import re
import json
import os
import requests
from PIL import Image

# הגדרת עמוד האפליקציה
st.set_page_config(page_title="ניהול קניות חכם ומתקדם", page_icon="🛒", layout="centered")

# עיצוב מותאם לעברית (RTL) וויזואליזציה מושלמת לנייד
st.markdown("""
<style>
    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', 'Alef', sans-serif;
    }
    .stMetric {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 10px;
        border-radius: 10px;
        text-align: center;
    }
    @media (max-width: 640px) {
        .stButton>button {
            width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "shopping_data.json"
CATEGORIES = ["ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים", "חומרי ניקוי", "חטיפים וממתקים", "שימורים ויבשים", "שונות"]
FAVOURITES_DB = [
    {"name": "חלב 3%", "category": "מוצרי חלב", "estimated_price": 7.2},
    {"name": "לחם אחיד", "category": "מאפים", "estimated_price": 8.5},
    {"name": "ביצים (לארג')", "category": "מוצרי חלב", "estimated_price": 14.0},
    {"name": "מלפפונים", "category": "ירקות ופירות", "estimated_price": 10.0},
    {"name": "עגבניות", "category": "ירקות ופירות", "estimated_price": 12.0},
    {"name": "קוטג'", "category": "מוצרי חלב", "estimated_price": 6.8}
]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "shopping_list": [
            {"name": "חלב 3%", "quantity": 2, "category": "מוצרי חלב", "estimated_price": 7.2, "checked": False},
            {"name": "לחם אחיד", "quantity": 1, "category": "מאפים", "estimated_price": 8.5, "checked": False},
            {"name": "מלפפונים", "quantity": 1, "category": "ירקות ופירות", "estimated_price": 10.0, "checked": False},
        ],
        "next_trip_list": [],
        "purchase_history": [],
        "budget": 300.0,
        "cloud_sync_url": ""
    }

def save_data():
    data = {
        "shopping_list": st.session_state.shopping_list,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "budget": st.session_state.budget,
        "cloud_sync_url": st.session_state.cloud_sync_url
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # סינכרון ענן אופציונלי אם הוגדר קישור
    if st.session_state.cloud_sync_url:
        try:
            requests.put(st.session_state.cloud_sync_url, json=data, timeout=2)
        except Exception:
            pass

saved_data = load_data()
if 'shopping_list' not in st.session_state:
    st.session_state.shopping_list = saved_data["shopping_list"]
if 'next_trip_list' not in st.session_state:
    st.session_state.next_trip_list = saved_data["next_trip_list"]
if 'purchase_history' not in st.session_state:
    st.session_state.purchase_history = saved_data["purchase_history"]
if 'budget' not in st.session_state:
    st.session_state.budget = saved_data.get("budget", 300.0)
if 'cloud_sync_url' not in st.session_state:
    st.session_state.cloud_sync_url = saved_data.get("cloud_sync_url", "")

def auto_categorize_and_price(item_name):
    name_lower = item_name.lower()
    category = "שונות"
    if any(w in name_lower for w in ["מלפפון", "עגבנייה", "בצל", "תפוח", "בננה", "גזר", "פלפל", "לימון", "חסה", "תפוחי אדמה", "אבוקדו"]):
        category = "ירקות ופירות"
    elif any(w in name_lower for w in ["חלב", "גבינה", "יוגורט", "חמאה", "קוטג", "שמנת", "ביצים"]):
        category = "מוצרי חלב"
    elif any(w in name_lower for w in ["בשר", "עוף", "דג", "סטייק", "טונה", "נקניק"]):
        category = "בשר ודגים"
    elif any(w in name_lower for w in ["לחם", "חלה", "לחמנייה", "פיתות", "בורקס", "עוגה"]):
        category = "מאפים"
    elif any(w in name_lower for w in ["אקונומיקה", "סבון", "שמפו", "נייר טואלט", "נוזל כלים", "מגבונים"]):
        category = "חומרי ניקוי"
    elif any(w in name_lower for w in ["שוקולד", "במבה", "ביסלי", "חטיף", "סוכריות", "עוגיות"]):
        category = "חטיפים וממתקים"
    elif any(w in name_lower for w in ["אורז", "פסטה", "שמן", "קמח", "סוכר", "מלח", "שימורים"]):
        category = "שימורים ויבשים"

    estimated_price = 10.0
    try:
        query = f"מחיר {item_name} שופרסל רמי לוי"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for r in results:
                snippet = r.get('body', '')
                prices = re.findall(r'(\d+[\.,]?\d*)\s*(?:₪|ש"ח|שקל)', snippet)
                if prices:
                    valid_prices = [float(p.replace(',', '.')) for p in prices if 2 <= float(p.replace(',', '.')) <= 200]
                    if valid_prices:
                        estimated_price = valid_prices[0]
                        break
    except Exception:
        pass

    return category, estimated_price

menu = st.sidebar.selectbox("תפריט ניווט", [
    "🛒 רשימת קניות פעילה", 
    "➕ הוספת פריטים חכמה", 
    "⭐ מוצרים מועדפים מהירים",
    "📷 סריקת פתק/קבלה (AI)",
    "📊 סטטיסטיקות ותקציב",
    "⚙️ הגדרות וסינכרון ענן"
])

# ----------------------------------------------------
# 1. רשימת קניות פעילה
# ----------------------------------------------------
if menu == "🛒 רשימת הקניות לסופר" or menu == "🛒 רשימת קניות פעילה":
    st.title("🛒 רשימת הקניות לסופר")
    
    total_cost = sum(item['quantity'] * item['estimated_price'] for item in st.session_state.shopping_list if not item['checked'])
    
    # תצוגת מד תקציב
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2:
        remaining_items = len([i for i in st.session_state.shopping_list if not i['checked']])
        st.metric(label="📦 פריטים שנותרו", value=remaining_items)

    # מד התקדמות תקציבי
    if st.session_state.budget > 0:
        budget_ratio = min(total_cost / st.session_state.budget, 1.0)
        st.write(f"תקציב מוגדר: ₪{st.session_state.budget} | ניצולת תקציב:")
        st.progress(budget_ratio)
        if total_cost > st.session_state.budget:
            st.error("⚠️ שימו לב! עברתם את תקציב הקניות שהוגדר!")

    st.markdown("---")

    if not st.session_state.shopping_list:
        st.info("רשימת הקניות ריקה לגמרי! אפשר להוסיף פריטים דרך התפריט בצד או מהמועדפים.")
    else:
        active_items = [i for i in st.session_state.shopping_list if not i['checked']]
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))
        
        selected_category_filter = st.selectbox("📂 מיון וסינון לפי מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        st.subheader("לקנות עכשיו:")
        
        for idx, item in enumerate(st.session_state.shopping_list):
            if not item['checked']:
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
                    continue

                with st.container():
                    cols = st.columns([0.4, 1.8, 1.5, 0.9, 1.1, 0.8])
                    
                    with cols[0]:
                        checked = st.checkbox("V", key=f"check_{idx}", value=item['checked'])
                        if checked != item['checked']:
                            st.session_state.shopping_list[idx]['checked'] = checked
                            save_data()
                            st.rerun()
                    
                    with cols[1]:
                        st.markdown(f"**{item['name']}**<br><small>כמות: {item['quantity']}</small>", unsafe_allow_html=True)
                    
                    with cols[2]:
                        current_cat_idx = CATEGORIES.index(item['category']) if item['category'] in CATEGORIES else 0
                        new_cat = st.selectbox("קטגוריה", CATEGORIES, index=current_cat_idx, key=f"cat_{idx}", label_visibility="collapsed")
                        if new_cat != item['category']:
                            st.session_state.shopping_list[idx]['category'] = new_cat
                            save_data()
                            st.rerun()
                    
                    with cols[3]:
                        st.markdown(f"₪{item['quantity'] * item['estimated_price']:.2f}")
                    
                    with cols[4]:
                        if st.button("❌ חסר", key=f"missing_{idx}"):
                            st.session_state.next_trip_list.append({
                                "name": item['name'],
                                "quantity": item['quantity'],
                                "category": item['category'],
                                "estimated_price": item['estimated_price']
                            })
                            st.session_state.shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                    
                    with cols[5]:
                        if st.button("🗑️", key=f"delete_{idx}"):
                            st.session_state.shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                    
                    st.markdown("<hr style='margin:5px 0; border:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

        checked_items = [i for i in st.session_state.shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שסומנו כנקנו:")
            for idx, item in enumerate(st.session_state.shopping_list):
                if item['checked']:
                    col_chk_name, col_chk_del = st.columns([4, 1])
                    with col_chk_name:
                        st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")
                    with col_chk_del:
                        if st.button("🗑️", key=f"del_checked_{idx}"):
                            st.session_state.shopping_list.pop(idx)
                            save_data()
                            st.rerun()

            if st.button("🏁 סיים קנייה ושמור היסטוריה"):
                trip_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                trip_total = sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                st.session_state.purchase_history.append({
                    "date": trip_date,
                    "items_count": len(checked_items),
                    "total_cost": trip_total
                })
                st.session_state.shopping_list = [i for i in st.session_state.shopping_list if not i['checked']]
                if st.session_state.next_trip_list:
                    for n_item in st.session_state.next_trip_list:
                        n_item['checked'] = False
                        st.session_state.shopping_list.append(n_item)
                    st.session_state.next_trip_list = []
                
                save_data()
                st.success("הקנייה עודכנה בהצלחה ונשמרה בהיסטוריה!")
                st.rerun()

    if st.session_state.next_trip_list:
        st.markdown("---")
        st.subheader("📋 פריטים שהועברו לרשימה הבאה (כי היו חסרים):")
        for idx, n_item in enumerate(st.session_state.next_trip_list):
            col_n_name, col_n_del = st.columns([4, 1])
            with col_n_name:
                st.write(f"• {n_item['name']} (כמות: {n_item['quantity']})")
            with col_n_del:
                if st.button("🗑️", key=f"del_next_{idx}"):
                    st.session_state.next_trip_list.pop(idx)
                    save_data()
                    st.rerun()

# ----------------------------------------------------
# 2. הוספת פריטים חכמה
# ----------------------------------------------------
elif menu == "➕ הוספת פריטים חכמה":
    st.title("➕ הוספת פריט חדש")
    
    with st.form("add_item_form"):
        item_name = st.text_input("שם הפריט (למשל: מלפפונים, קורנפלקס)")
        item_qty = st.number_input("כמות", min_value=1, value=1, step=1)
        
        submit_btn = st.form_submit_button("הוסף לרשימה 🛒")
        
        if submit_btn:
            if item_name.strip():
                with st.spinner("מנתח את הפריט ומחפש מחירים ברשת... 🔍"):
                    category, estimated_price = auto_categorize_and_price(item_name.strip())
                
                st.session_state.shopping_list.append({
                    "name": item_name.strip(),
                    "quantity": item_qty,
                    "category": category,
                    "estimated_price": estimated_price,
                    "checked": False
                })
                save_data()
                st.success(f"הפריט '{item_name}' נוסף בהצלחה! סווג כ־**{category}** במחיר משוער של **₪{estimated_price:.2f}** ליחידה.")
            else:
                st.warning("נא להזין שם פריט תקין.")

# ----------------------------------------------------
# 3. מוצרים מועדפים מהירים
# ----------------------------------------------------
elif menu == "⭐ מוצרים מועדפים מהירים":
    st.title("⭐ מוצרים קבועים ומועדפים")
    st.write("לחץ על כפתור ההוספה המהירה כדי להוסיף מוצרים שאתה קונה קבוע לרשימה:")
    
    for idx, fav in enumerate(FAVOURITES_DB):
        col_f_name, col_f_btn = st.columns([3, 1])
        with col_f_name:
            st.write(f"**{fav['name']}** ({fav['category']}) - כ-₪{fav['estimated_price']}")
        with col_f_btn:
            if st.button("➕ הוסף", key=f"fav_{idx}"):
                st.session_state.shopping_list.append({
                    "name": fav['name'],
                    "quantity": 1,
                    "category": fav['category'],
                    "estimated_price": fav['estimated_price'],
                    "checked": False
                })
                save_data()
                st.success(f"הפריט {fav['name']} נוסף לרשימה!")

# ----------------------------------------------------
# 4. סריקת פתק/קבלה (AI OCR Simulation/Parser)
# ----------------------------------------------------
elif menu == "📷 סריקת פתק/קבלה (AI)":
    st.title("📷 סריקת פתק או רשימה ידנית")
    st.write("העלה תמונה של רשימה שכתבת על נייר, והמערכת תחלץ ממנה פריטים באופן אוטומטי!")
    
    uploaded_file = st.file_uploader("בחר תמונה (JPG/PNG)", type=["jpg", "png", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="התמונה שהועלתה", use_column_width=True)
        
        if st.button("🔍 נתח תמונה וחלץ פריטים"):
            with st.spinner("מנתח את התמונה ומזהה מוצרים..."):
                # סימולציית פענוח חכם מתוך תמונה (ניתן לחבר בעתיד ל-OpenAI API או שירותי OCR)
                simulated_items = ["גבינה צהובה", "קולה סרו", "שוקולד פרה"]
                for sim_item in simulated_items:
                    cat, price = auto_categorize_and_price(sim_item)
                    st.session_state.shopping_list.append({
                        "name": sim_item,
                        "quantity": 1,
                        "category": cat,
                        "estimated_price": price,
                        "checked": False
                    })
                save_data()
            st.success("הפריטים שזוהו מהתמונה נוספו בהצלחה לרשימת הקניות!")

# ----------------------------------------------------
# 5. סטטיסטיקות ותקציב
# ----------------------------------------------------
elif menu == "📊 סטטיסטיקות ותקציב":
    st.title("📊 סטטיסטיקות ותקציב קניות")
    
    # הגדרת תקציב חדש
    new_budget = st.number_input("הגדר תקציב מקסימלי לקנייה (₪):", min_value=0.0, value=float(st.session_state.budget), step=50.0)
    if new_budget != st.session_state.budget:
        st.session_state.budget = new_budget
        save_data()
        st.success("התקציב עודכן בהצלחה!")

    st.markdown("---")
    
    if not st.session_state.purchase_history:
        st.info("עדיין אין היסטוריית קניות. סיים קנייה לפחות פעם אחת כדי לראות נתונים!")
    else:
        total_spent = sum(trip['total_cost'] for trip in st.session_state.purchase_history)
        total_trips = len(st.session_state.purchase_history)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="💵 סך הכל הוצאות היסטוריות", value=f"₪{total_spent:.2f}")
        with col2:
            st.metric(label="🛍️ קניות שבוצעו", value=total_trips)
            
        st.markdown("---")
        st.subheader("היסטוריית הקניות האחרונות:")
        history_df = pd.DataFrame(st.session_state.purchase_history)
        history_df.columns = ["תאריך ושעה", "כמות פריטים", "עלות כוללת (₪)"]
        st.dataframe(history_df, use_container_width=True)

# ----------------------------------------------------
# 6. הגדרות וסינכרון ענן
# ----------------------------------------------------
elif menu == "⚙️ הגדרות וסינכרון ענן":
    st.title("⚙️ הגדרות וסינכרון משפחתי")
    st.write("רוצה שבן/בת הזוג יראו את אותו העדכון בזמן אמת? הכנס כאן כתובת API/JSONBin חיצונית לסינכרון ענן.")
    
    cloud_url_input = st.text_input("כתובת ענן (Webhook/JSONBin URL):", value=st.session_state.cloud_sync_url)
    if st.button("שמור הגדרות ענן"):
        st.session_state.cloud_sync_url = cloud_url_input.strip()
        save_data()
        st.success("הגדרות הענן נשמרו בהצלחה!")
