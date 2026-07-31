import streamlit as st
import pandas as pd
from datetime import datetime

# הגדרת עמוד האפליקציה
st.set_page_config(page_title="ניהול קניות חכם", page_icon="🛒", layout="centered")

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
    # כל פריט מכיל: name, quantity, category, estimated_price, checked, missing
    st.session_state.shopping_list = [
        {"name": "חלב 3%", "quantity": 2, "category": "מוצרי חלב", "estimated_price": 7.0, "checked": False, "missing": False},
        {"name": "לחם אחיד", "quantity": 1, "category": "מאפים", "estimated_price": 8.5, "checked": False, "missing": False},
        {"name": "עגבניות", "quantity": 1, "category": "ירקות ופירות", "estimated_price": 12.0, "checked": False, "missing": False},
        {"name": "מלפפונים", "quantity": 1, "category": "ירקות ופירות", "estimated_price": 10.0, "checked": False, "missing": False},
    ]

if 'next_trip_list' not in st.session_state:
    st.session_state.next_trip_list = []

if 'purchase_history' not in st.session_state:
    st.session_state.purchase_history = []

categories = ["ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים", "חומרי ניקוי", "שונות"]

# תפריט ניווט צידי (Sidebar)
menu = st.sidebar.selectbox("תפריט ניווט", ["🛒 רשימת קניות פעילה", "➕ הוספת פריטים", "📊 סטטיסטיקות והיסטוריה"])

# ----------------------------------------------------
# 1. רשימת קניות פעילה (בסופר)
# ----------------------------------------------------
if menu == "🛒 רשימת קניות פעילה":
    st.title("🛒 רשימת הקניות לסופר")
    st.write("סמן פריטים שלקחת עגלות, או דווח אם משהו חסר.")

    # חישוב עלות משוערת כוללת לרשימה
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
        # הצגת הפריטים שטרם סומנו
        st.subheader("לקנות עכשיו:")
        for idx, item in enumerate(st.session_state.shopping_list):
            if not item['checked']:
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
                    if st.button("❌ חסר בסופר", key=f"missing_{idx}"):
                        # העברה לרשימת הקניות הבאה
                        st.session_state.next_trip_list.append({
                            "name": item['name'],
                            "quantity": item['quantity'],
                            "category": item['category'],
                            "estimated_price": item['estimated_price']
                        })
                        # מחיקה מהרשימה הנוכחית
                        st.session_state.shopping_list.pop(idx)
                        st.rerun()

        # הצגת פריטים שכבר סומנו כ"לקוחו"
        checked_items = [i for i in st.session_state.shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שכבר עגלות לסל:")
            for item in checked_items:
                st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")

            if st.button("🏁 סיים קנייה ושמור היסטוריה"):
                # שמירה בהיסטוריה
                trip_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                trip_total = sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                st.session_state.purchase_history.append({
                    "date": trip_date,
                    "items_count": len(checked_items),
                    "total_cost": trip_total
                })
                # ניקוי הפריטים שנקנו מהרשימה והשארת פריטים שלא נקנו (אם יש) + טעינת הרשימה הבאה אם קיימת
                st.session_state.shopping_list = [i for i in st.session_state.shopping_list if not i['checked']]
                if st.session_state.next_trip_list:
                    for n_item in st.session_state.next_trip_list:
                        n_item['checked'] = False
                        st.session_state.shopping_list.append(n_item)
                    st.session_state.next_trip_list = []
                
                st.success("הקנייה עודכנה בהצלחה ונשמרה בסטטיסטיקות!")
                st.rerun()

    # הצגת רשימת הקניות הבאה (פריטים שהיו חסרים)
    if st.session_state.next_trip_list:
        st.markdown("---")
        st.subheader("📋 פריטים שהועברו לרשימה הבאה (כי היו חסרים):")
        for n_item in st.session_state.next_trip_list:
            st.write(f"• {n_item['name']} (כמות: {n_item['quantity']})")

# ----------------------------------------------------
# 2. הוספת פריטים
# ----------------------------------------------------
elif menu == "➕ הוספת פריטים":
    st.title("➕ הוספת פריט חדש לרשימה")
    
    with st.form("add_item_form"):
        item_name = st.text_input("שם הפריט (למשל: גבינה לבנה)")
        item_qty = st.number_input("כמות", min_value=1, value=1, step=1)
        item_cat = st.selectbox("קטגוריה", categories)
        item_price = st.number_input("מחיר משוער ליחידה (בשקלים)", min_value=0.0, value=5.0, step=0.5)
        
        submit_btn = st.form_submit_button("הוסף לרשימה 🛒")
        
        if submit_btn:
            if item_name.strip():
                st.session_state.shopping_list.append({
                    "name": item_name.strip(),
                    "quantity": item_qty,
                    "category": item_cat,
                    "estimated_price": item_price,
                    "checked": False,
                    "missing": False
                })
                st.success(f"הפריט '{item_name}' נוסף בהצלחה לרשימת הקניות!")
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