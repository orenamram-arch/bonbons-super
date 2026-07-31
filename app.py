import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import requests

# הגדרת עמוד האפליקציה (חייב להיות ראשון)
st.set_page_config(page_title="ניהול קניות אולטימטיבי", page_icon="🛒", layout="centered")

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

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "shopping_list" in data and "stores" not in data:
                    old_list = data["shopping_list"]
                    data["stores"] = {"סופרמרקט מרכזי": old_list}
                    data["active_store"] = "סופרמרקט מרכזי"
                return data
        except Exception:
            pass
            
    return {
        "stores": {"סופרמרקט מרכזי": []},
        "active_store": "סופרמרקט מרכזי",
        "next_trip_list": [],
        "purchase_history": [],
        "recurring_items": [],
        "budget": 300.0,
        "family_code": "family123",
        "dark_mode": False
    }

def save_data():
    data = {
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "recurring_items": st.session_state.recurring_items,
        "budget": st.session_state.budget,
        "family_code": st.session_state.family_code,
        "dark_mode": st.session_state.dark_mode
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

saved_data = load_data()
if 'stores' not in st.session_state: st.session_state.stores = saved_data.get("stores", {"סופרמרקט מרכזי": []})
if 'active_store' not in st.session_state: st.session_state.active_store = saved_data.get("active_store", "סופרמרקט מרכזי")
if 'next_trip_list' not in st.session_state: st.session_state.next_trip_list = saved_data["next_trip_list"]
if 'purchase_history' not in st.session_state: st.session_state.purchase_history = saved_data["purchase_history"]
if 'recurring_items' not in st.session_state: st.session_state.recurring_items = saved_data.get("recurring_items", [])
if 'budget' not in st.session_state: st.session_state.budget = saved_data.get("budget", 300.0)
if 'family_code' not in st.session_state: st.session_state.family_code = saved_data.get("family_code", "family123")
if 'dark_mode' not in st.session_state: st.session_state.dark_mode = saved_data.get("dark_mode", False)

if st.session_state.active_store not in st.session_state.stores:
    st.session_state.stores[st.session_state.active_store] = []

# --- עיצוב דינמי והעלמה מוחלטת של הוילון ותפריט הצד ---
dark = st.session_state.dark_mode
bg_color = "#0f172a" if dark else "#f7f9fb"
card_bg = "#1e293b" if dark else "#ffffff"
text_color = "#f8fafc" if dark else "#0f172a"
sub_text = "#94a3b8" if dark else "#64748b"
border_color = "#334155" if dark else "#e2e8f0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');

    /* הסתרה מוחלטת של סרגל הצד, כפתור הוילון, התפריטים והכותרת העליונה של Streamlit */
    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] {{
        display: none !important;
    }}

    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {{
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
        color: {text_color} !important;
    }}

    .stApp {{ background-color: {bg_color}; }}
    h1, h2, h3 {{ color: {text_color} !important; font-weight: 800 !important; }}

    div[data-testid="metric-container"] {{
        background: {card_bg};
        border: 1px solid {border_color};
        padding: 12px 15px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        border-right: 5px solid #3b82f6;
    }}
    div[data-testid="metric-container"] label {{ color: {sub_text} !important; font-size: 14px !important; }}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{ color: {text_color} !important; font-size: 22px !important; font-weight: 700 !important; }}

    .product-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 6px;
        display: flex;
        align-items: center;
    }}
    .product-name {{ font-size: 18px !important; font-weight: 700 !important; color: {text_color}; }}
    .product-details {{ font-size: 13px; color: {sub_text}; }}

    .stButton>button {{ border-radius: 10px; font-weight: 600; transition: all 0.2s; width: 100%; }}
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
    return "שונות", 12.0

current_shopping_list = st.session_state.stores[st.session_state.active_store]

# --- ניהול ראשי דרך כרטיסיות (Tabs) נקיות בלבד ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🛒 רשימה פעילה", 
    "➕ הוספה חכמה", 
    "⭐ מועדפים",
    "🗺️ מעברים",
    "🧮 השוואת מחירים",
    "🔄 קבועים",
    "📊 סטטיסטיקות"
])

# ----------------------------------------------------
# 1. רשימת קניות פעילה
# ----------------------------------------------------
with tab1:
    # פס בחירת חנות ומצב כהה מהיר בראש העמוד (במקום סרגל צד)
    col_top1, col_top2 = st.columns([2, 1])
    with col_top1:
        store_list = list(st.session_state.stores.keys())
        selected_store = st.selectbox("🏪 בחר חנות:", store_list, index=store_list.index(st.session_state.active_store))
        if selected_store != st.session_state.active_store:
            st.session_state.active_store = selected_store
            save_data()
            st.rerun()
    with col_top2:
        dark_toggle = st.toggle("🌙 כהה", value=st.session_state.dark_mode)
        if dark_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_toggle
            save_data()
            st.rerun()

    st.title(f"🛒 רשימה עבור: {st.session_state.active_store}")
    
    total_cost = sum(item['quantity'] * item['estimated_price'] for item in current_shopping_list if not item['checked'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2:
        remaining_items = len([i for i in current_shopping_list if not i['checked']])
        st.metric(label="📦 פריטים שנותרו", value=remaining_items)

    if st.session_state.budget > 0:
        budget_ratio = min(total_cost / st.session_state.budget, 1.0)
        st.write(f"תקציב מוגדר: ₪{st.session_state.budget}")
        st.progress(budget_ratio)
        if total_cost > st.session_state.budget:
            st.error("⚠️ שימו לב! עברתם את תקציב הקניות שהוגדר!")

    st.markdown("---")

    if not current_shopping_list:
        st.info("💡 רשימת הקניות ריקה לחלוטין! הוסף פריטים דרך לשונית 'הוספה חכמה' או 'מועדפים'.")
    else:
        active_items = [i for i in current_shopping_list if not i['checked']]
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))
        
        col_search, col_filter = st.columns([1.5, 2])
        with col_search:
            search_query = st.text_input("🔍 חיפוש מהיר:", "", placeholder="הקלד שם מוצר...")
        with col_filter:
            selected_category_filter = st.selectbox("📂 סינון לפי מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        st.subheader("לקנות עכשיו:")
        
        for idx, item in enumerate(current_shopping_list):
            if not item['checked']:
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
                    continue
                if search_query.strip() and search_query.strip().lower() not in item['name'].lower():
                    continue

                icon, card_color = get_product_icon_and_color(item['category'])

                with st.container():
                    st.markdown(f"""
                    <div class="product-card" style="border-right: 6px solid {card_color};">
                        <span style="font-size: 26px; margin-left: 12px;">{icon}</span>
                        <div style="flex-grow: 1;">
                            <span class="product-name">{item['name']}</span> &nbsp;|&nbsp; <b>כמות: {item['quantity']}</b><br>
                            <span class="product-details">מחיר משוער: <b>₪{item['quantity'] * item['estimated_price']:.2f}</b> &nbsp;&bull;&nbsp; קטגוריה: {item['category']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_buy, col_minus, col_plus, col_mis, col_del = st.columns([1.2, 0.7, 0.7, 1, 1])
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
                    with col_mis:
                        if st.button("❌ חסר", key=f"missing_{idx}"):
                            st.session_state.next_trip_list.append({
                                "name": item['name'],
                                "quantity": item['quantity'],
                                "category": item['category'],
                                "estimated_price": item['estimated_price']
                            })
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ מחק", key=f"delete_{idx}"):
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

        checked_items = [i for i in current_shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שסומנו כנקנו:")
            for idx, item in enumerate(current_shopping_list):
                if item['checked']:
                    col_chk_name, col_chk_return, col_chk_del = st.columns([3, 1.2, 1])
                    with col_chk_name:
                        st.write(f"~~{item['name']} (כמות: {item['quantity']})~~")
                    with col_chk_return:
                        if st.button("↩️ החזר", key=f"return_{idx}"):
                            current_shopping_list[idx]['checked'] = False
                            save_data()
                            st.rerun()
                    with col_chk_del:
                        if st.button("🗑️ מחק", key=f"del_checked_{idx}"):
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏁 סיים קנייה ושמור קבלה", type="primary"):
                trip_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                trip_total = sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                st.session_state.purchase_history.append({
                    "date": trip_date,
                    "store": st.session_state.active_store,
                    "items_count": len(checked_items),
                    "total_cost": trip_total
                })
                st.session_state.stores[st.session_state.active_store] = [i for i in current_shopping_list if not i['checked']]
                save_data()
                st.success("הקנייה נשמרה בהצלחה בהיסטוריית הקבלות!")
                st.rerun()

# ----------------------------------------------------
# 2. הוספת פריטים חכמה
# ----------------------------------------------------
with tab2:
    st.title("➕ הוספת פריט חדש")
    with st.form("add_item_form"):
        item_name = st.text_input("שם הפריט (למשל: מלפפונים, קורנפלקס)")
        item_qty = st.number_input("כמות", min_value=1, value=1, step=1)
        submit_btn = st.form_submit_button("הוסף לרשימה 🛒", type="primary")
        if submit_btn:
            if item_name.strip():
                category, estimated_price = ai_smart_categorize_and_price(item_name.strip())
                current_shopping_list.append({"name": item_name.strip(), "quantity": item_qty, "category": category, "estimated_price": estimated_price, "checked": False})
                save_data()
                st.success(f"הפריט '{item_name}' נוסף בהצלחה!")
            else:
                st.warning("נא להזין שם פריט תקין.")

# ----------------------------------------------------
# 3. מוצרים מועדפים
# ----------------------------------------------------
with tab3:
    st.title("⭐ מוצרים קבועים ומועדפים")
    for idx, fav in enumerate(FAVOURITES_DB):
        col_f_name, col_f_btn = st.columns([3, 1])
        with col_f_name:
            st.write(f"**{fav['name']}** ({fav['category']}) - כ-₪{fav['estimated_price']}")
        with col_f_btn:
            if st.button("➕ הוסף", key=f"fav_{idx}"):
                current_shopping_list.append({"name": fav['name'], "quantity": 1, "category": fav['category'], "estimated_price": fav['estimated_price'], "checked": False})
                save_data()
                st.success(f"הפריט {fav['name']} נוסף!")

# ----------------------------------------------------
# 4. סידור לפי מעברים
# ----------------------------------------------------
with tab4:
    st.title("🗺️ סידור הרשימה לפי מעברי הסופר")
    active_items = [i for i in current_shopping_list if not i['checked']]
    sorted_items = sorted(active_items, key=lambda x: AISLE_ORDER.get(x['category'], 99))
    for item in sorted_items:
        icon, _ = get_product_icon_and_color(item['category'])
        st.markdown(f"• {icon} **{item['name']}** (כמות: {item['quantity']}) — מחלקה: *{item['category']}*")

# ----------------------------------------------------
# 5. השוואת מחירים (ליחידה)
# ----------------------------------------------------
with tab5:
    st.title("🧮 מחשבון השוואת מחירים")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("אריזה א'")
        price_a = st.number_input("מחיר אריזה א' (₪):", min_value=0.0, value=10.0, key="pa")
        amount_a = st.number_input("כמות (גרם/מ\"ל/יחידות):", min_value=0.1, value=500.0, key="aa")
    with col_b:
        st.subheader("אריזה ב'")
        price_b = st.number_input("מחיר אריזה ב' (₪):", min_value=0.0, value=18.0, key="pb")
        amount_b = st.number_input("כמות (גרם/מ\"ל/יחידות):", min_value=0.1, value=1000.0, key="ab")
        
    if amount_a > 0 and amount_b > 0:
        unit_a = price_a / amount_a
        unit_b = price_b / amount_b
        st.markdown("---")
        if unit_a < unit_b:
            st.success("🏆 **אריזה א' משתלמת יותר!**")
        elif unit_b < unit_a:
            st.success("🏆 **אריזה ב' משתלמת יותר!**")
        else:
            st.info("🤝 שתי האריזות בעלות מחיר זהה ליחידת מידה.")

# ----------------------------------------------------
# 6. פריטים קבועים
# ----------------------------------------------------
with tab6:
    st.title("🔄 ניהול פריטים קבועים")
    new_rec = st.text_input("הוסף פריט קבוע רשימה (למשל: נייר טואלט):")
    if st.button("שמור כפריט קבוע"):
        if new_rec.strip() and new_rec not in st.session_state.recurring_items:
            st.session_state.recurring_items.append(new_rec.strip())
            save_data()
            st.success("הפריט נוסף!")
    for idx, rec in enumerate(st.session_state.recurring_items):
        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            st.write(f"• {rec}")
        with col_r2:
            if st.button("➕ הוסף לסל", key=f"add_rec_{idx}"):
                cat, price = ai_smart_categorize_and_price(rec)
                current_shopping_list.append({"name": rec, "quantity": 1, "category": cat, "estimated_price": price, "checked": False})
                save_data()
                st.success("הוסף לסל!")

# ----------------------------------------------------
# 7. סטטיסטיקות
# ----------------------------------------------------
with tab7:
    st.title("📊 סטטיסטיקות והיסטוריית קבלות")
    new_budget = st.number_input("הגדר תקציב מקסימלי לקנייה (₪):", min_value=0.0, value=float(st.session_state.budget), step=50.0)
    if new_budget != st.session_state.budget:
        st.session_state.budget = new_budget
        save_data()
        st.success("התקציב עודכן!")
    if st.session_state.purchase_history:
        st.dataframe(pd.DataFrame(st.session_state.purchase_history), use_container_width=True)
    else:
        st.info("עדיין אין היסטוריית קניות שמורה.")
