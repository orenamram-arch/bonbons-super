import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import requests
from PIL import Image

# הגדרת עמוד האפליקציה
st.set_page_config(page_title="ניהול קניות חכם", page_icon="🛒", layout="centered")

# עיצוב מתקדם ומודרני (Modern UI & RTL)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
    }

    /* רקע כללי רך */
    .stApp {
        background-color: #f7f9fb;
    }

    /* כותרות ראשיות */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 800 !important;
    }

    /* עיצוב כרטיסי מטריקות (Metrics) */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 12px 15px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        border-right: 5px solid #3b82f6;
    }
    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 14px !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 22px !important;
        font-weight: 700 !important;
    }

    /* כרטיס מוצר מעוצב */
    .product-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 6px;
        border-right: 5px solid #10b981;
    }
    .product-name {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #0f172a;
    }
    .product-details {
        font-size: 13px;
        color: #64748b;
    }

    /* עיצוב כפתורים כללי */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }

    /* התאמה למסכי טלפון נייד */
    @media (max-width: 768px) {
        .stButton>button {
            font-size: 12px !important;
            padding: 6px !important;
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

def ai_smart_categorize_and_price(item_name):
    name_lower = item_name.strip().lower()
    smart_db = {
        "מלפפון": ("ירקות ופירות", 10.0), "מלפפונים": ("ירקות ופירות", 10.0),
        "עגבנייה": ("ירקות ופירות", 12.0), "עגבניות": ("ירקות ופירות", 12.0),
        "בצל": ("ירקות ופירות", 6.0), "תפוח": ("ירקות ופירות", 14.0), "תפוחים": ("ירקות ופירות", 14.0),
        "בננה": ("ירקות ופירות", 10.0), "בננות": ("ירקות ופירות", 10.0), "גזר": ("ירקות ופירות", 6.0),
        "פלפל": ("ירקות ופירות", 15.0), "פלפלים": ("ירקות ופירות", 15.0), "לימון": ("ירקות ופירות", 9.0),
        "חסה": ("ירקות ופירות", 6.0), "תפוחי אדמה": ("ירקות ופירות", 7.0), "אבוקדו": ("ירקות ופירות", 18.0),
        "חלב": ("מוצרי חלב", 7.2), "חלב 3%": ("מוצרי חלב", 7.2),
        "גבינה": ("מוצרי חלב", 6.8), "גבינה לבנה": ("מוצרי חלב", 6.8), "גבינה צהובה": ("מוצרי חלב", 28.0),
        "קוטג": ("מוצרי חלב", 6.8), "קוטג'": ("מוצרי חלב", 6.8), "יוגורט": ("מוצרי חלב", 4.5),
        "חמאה": ("מוצרי חלב", 8.5), "שמנת": ("מוצרי חלב", 5.5), "ביצים": ("מוצרי חלב", 14.0),
        "עוף": ("בשר ודגים", 35.0), "חזה עוף": ("בשר ודגים", 38.0), "בשר": ("בשר ודגים", 65.0),
        "בשר טחון": ("בשר ודגים", 50.0), "דג": ("בשר ודגים", 45.0), "סלמון": ("בשר ודגים", 90.0),
        "טונה": ("בשר ודגים", 7.5), "שימורי טונה": ("בשר ודגים", 25.0), "נקניק": ("בשר ודגים", 22.0),
        "לחם": ("מאפים", 8.5), "לחם אחיד": ("מאפים", 8.5), "חלה": ("מאפים", 12.0),
        "פיתות": ("מאפים", 15.0), "בורקס": ("מאפים", 25.0), "עוגה": ("מאפים", 30.0),
        "אקונומיקה": ("חומרי ניקוי", 10.0), "סבון": ("חומרי ניקוי", 12.0), "שמפו": ("חומרי ניקוי", 18.0),
        "נייר טואלט": ("חומרי ניקוי", 32.0), "נוזל כלים": ("חומרי ניקוי", 9.0), "מגבונים": ("חומרי ניקוי", 8.0),
        "שוקולד": ("חטיפים וממתקים", 6.5), "במבה": ("חטיפים וממתקים", 5.0), "ביסלי": ("חטיפים וממתקים", 5.0),
        "עוגיות": ("חטיפים וממתקים", 12.0),
        "אורז": ("שימורים ויבשים", 10.0), "פסטה": ("שימורים ויבשים", 6.5), "שמן": ("שימורים ויבשים", 12.0),
        "קמח": ("שימורים ויבשים", 6.0), "סוכר": ("שימורים ויבשים", 6.5), "מלח": ("שימורים ויבשים", 3.5)
    }

    for key, (cat, price) in smart_db.items():
        if key == name_lower or key in name_lower:
            return cat, price

    if any(w in name_lower for w in ["מלפפון", "עגבנייה", "בצל", "תפוח", "בננה", "גזר", "פלפל", "לימון", "חסה", "תפוח אדמה", "אבוקדו", "פרי", "ירק"]):
        return "ירקות ופירות", 10.0
    elif any(w in name_lower for w in ["חלב", "גבינה", "יוגורט", "חמאה", "שמנת", "מעדן", "ביצים"]):
        return "מוצרי חלב", 8.0
    elif any(w in name_lower for w in ["בשר", "עוף", "דג", "סטייק", "שניצל", "קבב", "נקניק"]):
        return "בשר ודגים", 45.0
    elif any(w in name_lower for w in ["לחם", "חלה", "פיתה", "בורקס", "עוגה", "מאפה", "לחמנייה"]):
        return "מאפים", 10.0
    elif any(w in name_lower for w in ["ניקוי", "סבון", "שמפו", "נייר", "מגבונים", "כביסה", "אקונומיקה"]):
        return "חומרי ניקוי", 15.0
    elif any(w in name_lower for w in ["שוקולד", "במבה", "ביסלי", "עוגיות", "חטיף", "סוכריה"]):
        return "חטיפים וממתקים", 7.0
    elif any(w in name_lower for w in ["אורז", "פסטה", "שמן", "קמח", "סוכר", "מלח", "שימורי", "קפה", "תה"]):
        return "שימורים ויבשים", 10.0

    return "שונות", 12.0

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "shopping_list": [],
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

# תפריט ניווט נקי בסרגל הצד
menu = st.sidebar.radio("תפריט:", [
    "🛒 רשימת קניות פעילה", 
    "➕ הוספת פריטים חכמה", 
    "⭐ מוצרים מועדפים מהירים",
    "📷 סריקת פתק/קבלה (AI)",
    "📊 סטטיסטיקות ותקציב",
    "⚙️ הגדרות וסינכרון ענן"
], label_visibility="collapsed")

# ----------------------------------------------------
# 1. רשימת קניות פעילה
# ----------------------------------------------------
if menu == "🛒 רשימת קניות פעילה":
    st.title("🛒 רשימת הקניות לסופר")
    
    total_cost = sum(item['quantity'] * item['estimated_price'] for item in st.session_state.shopping_list if not item['checked'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2:
        remaining_items = len([i for i in st.session_state.shopping_list if not i['checked']])
        st.metric(label="📦 פריטים שנותרו", value=remaining_items)

    if st.session_state.budget > 0:
        budget_ratio = min(total_cost / st.session_state.budget, 1.0)
        st.write(f"תקציב מוגדר: ₪{st.session_state.budget}")
        st.progress(budget_ratio)
        if total_cost > st.session_state.budget:
            st.error("⚠️ שימו לב! עברתם את תקציב הקניות שהוגדר!")

    st.markdown("---")

    if not st.session_state.shopping_list:
        st.info("💡 רשימת הקניות ריקה! אפשר להוסיף פריטים דרך התפריט בצד או מהמועדפים.")
    else:
        active_items = [i for i in st.session_state.shopping_list if not i['checked']]
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))
        
        selected_category_filter = st.selectbox("📂 סינון מהיר לפי מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        st.subheader("לקנות עכשיו:")
        
        for idx, item in enumerate(st.session_state.shopping_list):
            if not item['checked']:
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
                    continue

                with st.container():
                    st.markdown(f"""
                    <div class="product-card">
                        <span class="product-name">{item['name']}</span> &nbsp;|&nbsp; <b>כמות: {item['quantity']}</b><br>
                        <span class="product-details">מחיר משוער: <b>₪{item['quantity'] * item['estimated_price']:.2f}</b> &nbsp;&bull;&nbsp; קטגוריה: {item['category']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_buy, col_cat, col_mis, col_del = st.columns([1.2, 2.2, 1, 1])
                    with col_buy:
                        if st.button("✔️ נקנה", key=f"buy_{idx}", type="primary"):
                            st.session_state.shopping_list[idx]['checked'] = True
                            save_data()
                            st.rerun()
                    with col_cat:
                        current_cat_idx = CATEGORIES.index(item['category']) if item['category'] in CATEGORIES else 0
                        new_cat = st.selectbox("קטגוריה", CATEGORIES, index=current_cat_idx, key=f"cat_{idx}", label_visibility="collapsed")
                        if new_cat != item['category']:
                            st.session_state.shopping_list[idx]['category'] = new_cat
                            save_data()
                            st.rerun()
                    with col_mis:
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
                    with col_del:
                        if st.button("🗑️ מחק", key=f"delete_{idx}"):
                            st.session_state.shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

        checked_items = [i for i in st.session_state.shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שסומנו כנקנו:")
            for idx, item in enumerate(st.session_state.shopping_list):
                if item['checked']:
                    col_chk_name, col_chk_return, col_chk_del = st.columns([3, 1.2, 1])
                    with col_chk_name:
                        st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")
                    with col_chk_return:
                        if st.button("↩️ החזר", key=f"return_{idx}"):
                            st.session_state.shopping_list[idx]['checked'] = False
                            save_data()
                            st.rerun()
                    with col_chk_del:
                        if st.button("🗑️ מחק", key=f"del_checked_{idx}"):
                            st.session_state.shopping_list.pop(idx)
                            save_data()
                            st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏁 סיים קנייה ושמור היסטוריה", type="primary"):
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
        
        submit_btn = st.form_submit_button("הוסף לרשימה 🛒", type="primary")
        
        if submit_btn:
            if item_name.strip():
                category, estimated_price = ai_smart_categorize_and_price(item_name.strip())
                
                st.session_state.shopping_list.append({
                    "name": item_name.strip(),
                    "quantity": item_qty,
                    "category": category,
                    "estimated_price": estimated_price,
                    "checked": False
                })
                save_data()
                st.success(f"הפריט '{item_name}' נוסף בהצלחה! סווג אוטומטית כ־**{category}** במחיר משוער של **₪{estimated_price:.2f}** ליחידה.")
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
# 4. סריקת פתק/קבלה (AI Vision)
# ----------------------------------------------------
elif menu == "📷 סריקת פתק/קבלה (AI)":
    st.title("📷 סריקת פתק או רשימה ידנית")
    st.write("העלה תמונה של רשימה שכתבת על נייר, והזן את שמות המוצרים המופרדים בפסיקים:")
    
    uploaded_file = st.file_uploader("בחר תמונה (JPG/PNG)", type=["jpg", "png", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="התמונה שהועלתה", use_container_width=True)
        
        manual_ocr_input = st.text_input("המוצרים שזוהו בתמונה (מופרדים בפסיקים):")
        
        if st.button("הוסף את המוצרים האלו לרשימה ✅", type="primary"):
            if manual_ocr_input.strip():
                items_list = [item.strip() for item in manual_ocr_input.split(",") if item.strip()]
                for item_name in items_list:
                    category, estimated_price = ai_smart_categorize_and_price(item_name)
                    st.session_state.shopping_list.append({
                        "name": item_name,
                        "quantity": 1,
                        "category": category,
                        "estimated_price": estimated_price,
                        "checked": False
                    })
                save_data()
                st.success(f"נוספו בהצלחה {len(items_list)} פריטים חדשים לרשימת הקניות!")
            else:
                st.warning("נא לרשום לפחות פריט אחד בשדה.")

# ----------------------------------------------------
# 5. סטטיסטיקות ותקציב
# ----------------------------------------------------
elif menu == "📊 סטטיסטיקות ותקציב":
    st.title("📊 סטטיסטיקות ותקציב קניות")
    
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
            st.metric(label="💵 סך הכל הוצאות", value=f"₪{total_spent:.2f}")
        with col2:
            st.metric(label="🛍️ סך קניות", value=total_trips)
            
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
    if st.button("שמור הגדרות ענן", type="primary"):
        st.session_state.cloud_sync_url = cloud_url_input.strip()
        save_data()
        st.success("הגדרות הענן נשמרו בהצלחה!")
