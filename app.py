import streamlit as st
import pandas as pd
from datetime import datetime
from duckduckgo_search import DDGS
import re

# הגדרת עמוד האפליקציה
st.set_page_config(page_title="ניהול קניות חכם וחצי-אוטומטי", page_icon="🛒", layout="centered")

# עיצוב מותאם לעברית (RTL)
st.markdown("""
<style>
    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', 'Alef', sans-serif;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# אתחול הנתונים בזיכרון (Session State)
if 'shopping_list' not in st.session_state:
    st.session_state.shopping_list = [
        {"name": "חלב 3%", "quantity": 2, "category": "מוצרי חלב", "estimated_price": 7.2, "checked": False},
        {"name": "לחם אחיד", "quantity": 1, "category": "מאפים", "estimated_price": 8.5, "checked": False},
        {"name": "מלפפונים", "quantity": 1, "category": "ירקות ופירות", "estimated_price": 10.0, "checked": False},
    ]

if 'next_trip_list' not in st.session_state:
    st.session_state.next_trip_list = []

if 'purchase_history' not in st.session_state:
    st.session_state.purchase_history = []

CATEGORIES = ["ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים", "חומרי ניקוי", "חטיפים וממתקים", "שימורים ויבשים", "שונות"]

def auto_categorize_and_price(item_name):
    """פונקציה שמזהה אוטומטית קטגוריה ומחפשת מחיר משוער ברשת"""
    name_lower = item_name.lower()
    
    # 1. זיהוי קטגוריה אוטומטי לפי מילות מפתח
    category = "שונות"
    if any(w in name_lower for w in ["מלפפון", "עגבנייה", "בצל", "תפוח", "בננה", "גזר", "פלפל", "לימון", "חסה", "תפוחי אדמה", "אבוקדו"]):
        category = "ירקות ופירות"
    elif any(w in name_lower for w in ["חלב", "גבינה", "יוגורט", "חמאה", "קוטג", "שמנת"]):
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

    # 2. חיפוש מחיר משוער ברשת דרך DuckDuckGo
    estimated_price = 10.0 # ברירת מחדל אם החיפוש נכשל
    try:
        query = f"מחיר {item_name} שופרסל רמי לוי"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for r in results:
                snippet = r.get('body', '')
                # חיפוש מספרים שמוצמדים לסימן שקל או מילים כמו ש"ח
                prices = re.findall(r'(\d+[\.,]?\d*)\s*(?:₪|ש"ח|שקל)', snippet)
                if prices:
                    # נבחר מחיר הגיוני ראשון שנמצא (למשל בין 2 ל-200 שקל)
                    valid_prices = [float(p.replace(',', '.')) for p in prices if 2 <= float(p.replace(',', '.')) <= 200]
                    if valid_prices:
                        estimated_price = valid_prices[0]
                        break
    except Exception:
        pass # במקרה של בעיית תקשורת נשאר עם ברירת המחדל

    return category, estimated_price

# תפריט ניווט צידי
menu = st.sidebar.selectbox("תפריט ניווט", ["🛒 רשימת קניות פעילה", "➕ הוספת פריטים חכמה", "📊 סטטיסטיקות והיסטוריה"])

# ----------------------------------------------------
# 1. רשימת קניות פעילה עם אפשרות מיון לפי קטגוריות
# ----------------------------------------------------
if menu == "🛒 רשימת קניות פעילה":
    st.title("🛒 רשימת הקניות לסופר")
    
    # חישוב עלות כוללת לסל
    total_cost = sum(item['quantity'] * item['estimated_price'] for item in st.session_state.shopping_list if not item['checked'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 עלות משוערת לסל הנוכחי", value=f"₪{total_cost:.2f}")
    with col2:
        remaining_items = len([i for i in st.session_state.shopping_list if not i['checked']])
        st.metric(label="📦 פריטים שנותרו לקנות", value=remaining_items)

    st.markdown("---")

    if not st.session_state.shopping_list:
        st.info("רשימת הקניות ריקה לגמרי! אפשר להוסיף פריטים דרך התפריט בצד.")
    else:
        # פילטר מיון לפי קטגוריות
        active_items = [i for i in st.session_state.shopping_list if not i['checked']]
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))
        
        selected_category_filter = st.selectbox("📂 מיון וסינון לפי מחלקה/קטגוריה:", ["הכל (ללא סינון)"] + categories_in_list)

        st.subheader("לקנות עכשיו:")
        
        for idx, item in enumerate(st.session_state.shopping_list):
            if not item['checked']:
                # סינון לפי הקטגוריה שנבחרה
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
                    continue

                col_c, col_name, col_cat, col_price, col_miss = st.columns([0.5, 2, 1.5, 1, 1.5])
                
                with col_c:
                    checked = st.checkbox("V", key=f"check_{idx}", value=item['checked'])
                    if checked != item['checked']:
                        st.session_state.shopping_list[idx]['checked'] = checked
                        st.rerun()
                
                with col_name:
                    st.write(f"**{item['name']}** (כמות: {item['quantity']})")
                with col_cat:
                    st.caption(item['category'])
                with col_price:
                    st.write(f"₪{item['quantity'] * item['estimated_price']:.2f}")
                with col_miss:
                    if st.button("❌ חסר", key=f"missing_{idx}"):
                        st.session_state.next_trip_list.append({
                            "name": item['name'],
                            "quantity": item['quantity'],
                            "category": item['category'],
                            "estimated_price": item['estimated_price']
                        })
                        st.session_state.shopping_list.pop(idx)
                        st.rerun()

        # פריטים שנקנו
        checked_items = [i for i in st.session_state.shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שסומנו כנקנו:")
            for item in checked_items:
                st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")

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
                
                st.success("הקנייה עודכנה בהצלחה ונשמרה בהיסטוריה!")
                st.rerun()

    if st.session_state.next_trip_list:
        st.markdown("---")
        st.subheader("📋 פריטים שהועברו לרשימה הבאה (כי היו חסרים):")
        for n_item in st.session_state.next_trip_list:
            st.write(f"• {n_item['name']} (כמות: {n_item['quantity']})")

# ----------------------------------------------------
# 2. הוספת פריטים חכמה (זיהוי אוטומטי וחיפוש מחיר)
# ----------------------------------------------------
elif menu == "➕ הוספת פריטים חכמה":
    st.title("➕ הוספת פריט חדש (אוטומטי לחלוטין)")
    st.write("הקלד את שם הפריט – המערכת תזהה לבד את הקטגוריה ותחפש את המחיר ברשת עבורך!")
    
    with st.form("add_item_form"):
        item_name = st.text_input("שם הפריט (למשל: מלפפונים, קורנפלקס, אקונומיקה)")
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
                st.success(f"הפריט '{item_name}' נוסף בהצלחה! סווג כ־**{category}** במחיר משוער של **₪{estimated_price:.2f}** ליחידה.")
            else:
                st.warning("נא להזין שם פריט תקין.")

# ----------------------------------------------------
# 3. סטטיסטיקות והיסטוריה
# ----------------------------------------------------
elif menu == "📊 סטטיסטיקות והיסטוריה":
    st.title("📊 סטטיסטיקות קניות והוצאות")
    
    if not st.session_state.purchase_history:
        st.info("עדיין אין היסטוריית קניות. סיים קנייה לפחות פעם אחת כדי לראות נתונים!")
    else:
        total_spent = sum(trip['total_cost'] for trip in st.session_state.purchase_history)
        total_trips = len(st.session_state.purchase_history)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="💵 סך הכל הוצאות היסטוריות", value=f"₪{total_spent:.2f}")
        with col2:
            st.metric(label="🛍️ מספר קניות שבוצעו", value=total_trips)
            
        st.markdown("---")
        st.subheader("היסטוריית הקניות האחרונות:")
        
        history_df = pd.DataFrame(st.session_state.purchase_history)
        history_df.columns = ["תאריך ושעה", "כמות פריטים", "עלות כוללת (₪)"]
        st.dataframe(history_df, use_container_width=True)
