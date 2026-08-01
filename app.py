import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import time

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
        "learned_categories": {},
        "all_purchased_items": [],
        "budget": 300.0,
        "dark_mode": False
    }

def save_data():
    data = {
        "stores": st.session_state.stores,
        "active_store": st.session_state.active_store,
        "next_trip_list": st.session_state.next_trip_list,
        "purchase_history": st.session_state.purchase_history,
        "recurring_items": st.session_state.recurring_items,
        "learned_categories": st.session_state.learned_categories,
        "all_purchased_items": st.session_state.all_purchased_items,
        "budget": st.session_state.budget,
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
if 'learned_categories' not in st.session_state: st.session_state.learned_categories = saved_data.get("learned_categories", {})
if 'all_purchased_items' not in st.session_state: st.session_state.all_purchased_items = saved_data.get("all_purchased_items", [])
if 'budget' not in st.session_state: st.session_state.budget = saved_data.get("budget", 300.0)
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
    clean_name = item_name.strip().lower()
    
    if clean_name in st.session_state.learned_categories:
        return st.session_state.learned_categories[clean_name], 12.0

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
            return cat, price
    return "שונות", 12.0

current_shopping_list = st.session_state.stores[st.session_state.active_store]

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🛒 רשימה", 
    "➕ הוספה", 
    "⭐ מועדפים",
    "🗺️ סידור",
    "🧮 השוואה",
    "🔄 קבועים",
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
        
        selected_category_filter = st.selectbox("📂 סינון מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        for idx, item in enumerate(current_shopping_list):
            if not item['checked']:
                if selected_category_filter != "הכל (ללא סינון)" and item['category'] != selected_category_filter:
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
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ מחק", key=f"delete_{idx}"):
                            current_shopping_list.pop(idx)
                            save_data()
                            st.rerun()

                if st.session_state.get(f"show_edit_shop_{idx}", False):
                    with st.container():
                        with st.form(f"form_edit_item_{idx}"):
                            e_name = st.text_input("שם הפריט:", value=item['name'])
                            e_price = st.number_input("מחיר משוער ליחידה (₪):", value=float(item['estimated_price']))
                            current_cat_index = CATEGORIES.index(item['category']) if item['category'] in CATEGORIES else 7
                            e_category = st.selectbox("תקן קטגוריה (המערכת תלמד ותשמור לפעמים הבאות):", CATEGORIES, index=current_cat_index)
                            
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
                st.success("הקנייה נשמרה בהצלחה!")
                st.rerun()

# ----------------------------------------------------
# 2. הוספת פריט ידנית (עם מחיקת הודעה אוטומטית אחרי 3 שניות)
# ----------------------------------------------------
with tab2:
    st.subheader("➕ הוספת פריט ידנית")
    
    # הצגת אינדיקציה זמנית אם קיימת
    if st.session_state.get('last_added_item'):
        last = st.session_state.last_added_item
        st.success(f"✅ נוסף בהצלחה: **{last['name']}** (כמות: {last['qty']}) | מחלקה: {last['cat']} | מחיר משוער: ₪{last['price']:.2f}")
        
        # השהייה של 3 שניות ואז איפוס ההודעה כדי שלא תישארא קבועה
        time.sleep(3)
        st.session_state.pop('last_added_item', None)
        st.rerun()

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
                
                # שמירת האינדיקציה הזמנית
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
        col_f.write(f"**{fav['name']}** (₪{fav['estimated_price']})")
        if col_btn.button("➕ הוסף", key=f"fav_{idx}"):
            current_shopping_list.append({
                "name": fav['name'], 
                "quantity": 1, 
                "category": fav['category'], 
                "estimated_price": fav['estimated_price'], 
                "checked": False
            })
            if fav['name'] not in st.session_state.all_purchased_items:
                st.session_state.all_purchased_items.append(fav['name'])
            save_data()
            st.success(f"נוסף בהצלחה: {fav['name']}!")

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
    st.subheader("🧮 השוואת מחירים (מה משתלם יותר?)")
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
        if (pa/aa) < (pb/ab): st.success("אריזה א' זולה יותר ליחידה!")
        elif (pb/ab) < (pa/aa): st.success("אריזה ב' זולה יותר ליחידה!")
        else: st.info("המחיר ליחידה זהה.")

# ----------------------------------------------------
# 6. מוצרים קבועים
# ----------------------------------------------------
with tab6:
    st.subheader("🔄 מוצרים קבועים בבית")
    new_rec = st.text_input("הוסף פריט קבוע:")
    if st.button("שמור"):
        if new_rec.strip() and new_rec not in st.session_state.recurring_items:
            st.session_state.recurring_items.append(new_rec.strip())
            save_data()
    for idx, rec in enumerate(st.session_state.recurring_items):
        c1, c2 = st.columns([3, 1])
        c1.write(f"• {rec}")
        if c2.button("➕ לסל", key=f"r_{idx}"):
            cat, price = ai_smart_categorize_and_price(rec)
            current_shopping_list.append({"name": rec, "quantity": 1, "category": cat, "estimated_price": price, "checked": False})
            if rec not in st.session_state.all_purchased_items:
                st.session_state.all_purchased_items.append(rec)
            save_data()
            st.success(f"הפריט '{rec}' נוסף לסל!")

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
        st.dataframe(pd.DataFrame(st.session_state.purchase_history), use_container_width=True)

# ----------------------------------------------------
# 8. ניהול חנויות והגדרות
# ----------------------------------------------------
with tab8:
    st.title("🏪 חנויות והגדרות")
    
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
    st.subheader("🗑️ מחיקת חנות קיימת")
    store_to_delete = st.selectbox("בחר חנות למחיקה:", list(st.session_state.stores.keys()))
    if st.button("🗑️ מחק חנות זו לצמיתות"):
        if len(st.session_state.stores) > 1:
            del st.session_state.stores[store_to_delete]
            if st.session_state.active_store == store_to_delete:
                st.session_state.active_store = list(st.session_state.stores.keys())[0]
            save_data()
            st.success("החנות נמחקה!")
            st.rerun()
        else:
            st.error("חייבת להישאר לפחות חנות אחת פעילה באפליקציה.")

    st.markdown("---")
    st.subheader("🌙 תצוגה ועיצוב")
    dark_toggle = st.toggle("הפעל מצב כהה (Dark Mode)", value=st.session_state.dark_mode)
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        save_data()
        st.rerun()
