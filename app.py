import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import time
import sqlite3

# הגדרת עמוד האפליקציה (חייב להיות ראשון)
st.set_page_config(page_title="ניהול קניות אולטימטיבי", page_icon="🛒", layout="centered")

JSON_FILE = "shopping_data.json"
DB_FILE = "shopping_data.db"
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

def load_data():
    """טוען נתונים ממסד הנתונים SQLite. אם לא קיים, מבצע מיגרציה מקובץ ה-JSON הישן."""
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        data = {
            "stores": {}, "active_store": "סופרמרקט מרכזי", "next_trip_list": [],
            "purchase_history": [], "learned_categories": {}, "all_purchased_items": [], "budget": 300.0
        }
        try:
            # טעינת הגדרות
            c.execute("SELECT key, value FROM settings")
            for row in c.fetchall():
                if row[0] == 'active_store': data['active_store'] = row[1]
                elif row[0] == 'budget': data['budget'] = float(row[1])
                elif row[0] == 'all_purchased_items': data['all_purchased_items'] = json.loads(row[1])

            # טעינת פריטים
            c.execute("SELECT store, list_type, name, quantity, category, estimated_price, checked FROM items")
            for row in c.fetchall():
                store, list_type, name, qty, cat, price, checked = row
                item = {"name": name, "quantity": qty, "category": cat, "estimated_price": price, "checked": bool(checked)}
                if list_type == 'active':
                    if store not in data['stores']: data['stores'][store] = []
                    data['stores'][store].append(item)
                elif list_type == 'next_trip':
                    data['next_trip_list'].append(item)

            # טעינת היסטוריה
            c.execute("SELECT date, store, items_count, total_cost FROM history")
            for row in c.fetchall():
                data['purchase_history'].append({"date": row[0], "store": row[1], "items_count": row[2], "total_cost": row[3]})

            # טעינת קטגוריות שנלמדו
            c.execute("SELECT name, category FROM learned_categories")
            for row in c.fetchall():
                data['learned_categories'][row[0]] = row[1]

        except sqlite3.Error:
            pass
        finally:
            conn.close()

        # וידוא שחנות פעילה קיימת במילון
        if not data['stores']: data['stores'][data['active_store']] = []
        return data

    # מנגנון הגנה ומיגרציה מקובץ ה-JSON הקיים (אם מסד הנתונים עדיין לא נוצר)
    elif os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "shopping_list" in data and "stores" not in data:
                    old_list = data["shopping_list"]
                    data["stores"] = {"סופרמרקט מרכזי": old_list}
                    data["active_store"] = "סופרמרקט מרכזי"
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            pass
            
    # מצב ברירת מחדל לאפליקציה חדשה לחלוטין
    return {
        "stores": {"סופרמרקט מרכזי": []}, "active_store": "סופרמרקט מרכזי",
        "next_trip_list": [], "purchase_history": [], "learned_categories": {},
        "all_purchased_items": [], "budget": 300.0
    }

def save_data():
    """שומר את הנתונים הנוכחיים מ-Session State לתוך מסד נתונים SQLite."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # טבלאות ושמירת הגדרות
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ('active_store', st.session_state.active_store))
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ('budget', str(st.session_state.budget)))
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ('all_purchased_items', json.dumps(st.session_state.all_purchased_items)))

    # שמירת פריטים (אקטיביים וחסרים)
    c.execute("CREATE TABLE IF NOT EXISTS items (store TEXT, list_type TEXT, name TEXT, quantity INTEGER, category TEXT, estimated_price REAL, checked BOOLEAN)")
    c.execute("DELETE FROM items")
    for store, items in st.session_state.stores.items():
        for item in items:
            c.execute("INSERT INTO items VALUES (?, 'active', ?, ?, ?, ?, ?)",
                      (store, item['name'], item['quantity'], item['category'], item['estimated_price'], item['checked']))

    for item in st.session_state.next_trip_list:
         c.execute("INSERT INTO items VALUES ('ALL', 'next_trip', ?, ?, ?, ?, ?)",
                      (item['name'], item['quantity'], item['category'], item['estimated_price'], item.get('checked', False)))

    # שמירת קטגוריות שנלמדו
    c.execute("CREATE TABLE IF NOT EXISTS learned_categories (name TEXT PRIMARY KEY, category TEXT)")
    c.execute("DELETE FROM learned_categories")
    for name, cat in st.session_state.learned_categories.items():
        c.execute("INSERT INTO learned_categories VALUES (?, ?)", (name, cat))

    # שמירת היסטוריית רכישות
    c.execute("CREATE TABLE IF NOT EXISTS history (date TEXT, store TEXT, items_count INTEGER, total_cost REAL)")
    c.execute("DELETE FROM history")
    for h in st.session_state.purchase_history:
        c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (h['date'], h['store'], h['items_count'], h['total_cost']))

    conn.commit()
    conn.close()

# טעינה ואתחול session_state
saved_data = load_data()
if 'stores' not in st.session_state: st.session_state.stores = saved_data.get("stores", {"סופרמרקט מרכזי": []})
if 'active_store' not in st.session_state: st.session_state.active_store = saved_data.get("active_store", "סופרמרקט מרכזי")
if 'next_trip_list' not in st.session_state: st.session_state.next_trip_list = saved_data.get("next_trip_list", [])
if 'purchase_history' not in st.session_state: st.session_state.purchase_history = saved_data.get("purchase_history", [])
if 'learned_categories' not in st.session_state: st.session_state.learned_categories = saved_data.get("learned_categories", {})
if 'all_purchased_items' not in st.session_state: st.session_state.all_purchased_items = saved_data.get("all_purchased_items", [])
if 'budget' not in st.session_state: st.session_state.budget = saved_data.get("budget", 300.0)

if st.session_state.active_store not in st.session_state.stores:
    st.session_state.stores[st.session_state.active_store] = []

current_shopping_list = st.session_state.stores[st.session_state.active_store]

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

    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] { display: none !important; }
    body, .stApp, .stTextInput, .stMarkdown, .stButton>button, .stSelectbox {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif !important; color: var(--app-text) !important;
    }
    .stApp { background-color: var(--app-bg); }
    h1, h2, h3 { color: var(--app-text) !important; font-weight: 800 !important; }

    div[data-testid="metric-container"] {
        background: var(--card-bg); border: 1px solid var(--app-border); padding: 12px 15px;
        border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); text-align: center; border-right: 5px solid #3b82f6;
    }
    div[data-testid="metric-container"] label { color: var(--sub-text) !important; font-size: 14px !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: var(--app-text) !important; font-size: 22px !important; font-weight: 700 !important; }

    .product-card {
        background-color: var(--card-bg); border: 1px solid var(--app-border); padding: 14px 16px;
        border-radius: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 6px; display: flex; align-items: center;
    }
    .product-name { font-size: 18px !important; font-weight: 700 !important; color: var(--app-text); }
    .product-details { font-size: 13px; color: var(--sub-text); }
    .stButton>button { border-radius: 10px; font-weight: 600; transition: all 0.2s; width: 100%; }
</style>
""", unsafe_allow_html=True)

def get_product_icon_and_color(category):
    icons = {
        "ירקות ופירות": ("🥗", "#10b981"), "מוצרי חלב": ("🥛", "#0ea5e9"), "בשר ודגים": ("🥩", "#ef4444"),
        "מאפים": ("🍞", "#f59e0b"), "חומרי ניקוי": ("🧻", "#8b5cf6"), "חטיפים וממתקים": ("🍫", "#ec4899"),
        "שימורים ויבשים": ("☕", "#6366f1")
    }
    return icons.get(category, ("🛒", "#64748b"))

def ai_smart_categorize_and_price(item_name):
    clean_name = item_name.strip().lower()
    if clean_name in st.session_state.learned_categories:
        return st.session_state.learned_categories[clean_name], 12.0

    smart_db = {
        "מלפפון": ("ירקות ופירות", 10.0), "עגבנייה": ("ירקות ופירות", 12.0), "תפוח": ("ירקות ופירות", 14.0),
        "חלב": ("מוצרי חלב", 7.2), "ביצים": ("מוצרי חלב", 14.0), "קוטג'": ("מוצרי חלב", 6.8),
        "עוף": ("בשר ודגים", 35.0), "לחם": ("מאפים", 8.5), "שמפו": ("חומרי ניקוי", 18.0),
        "אורז": ("שימורים ויבשים", 10.0), "שוקולד": ("חטיפים וממתקים", 6.5)
    }
    for key, (cat, price) in smart_db.items():
        if key in clean_name:
            return cat, price
    return "שונות", 12.0

def add_item_with_check(item_name, item_qty, category, price):
    """פונקציה חכמה שבודקת אם המוצר כבר קיים ומטפלת בו בהתאם."""
    existing_item = next((i for i in current_shopping_list if i['name'] == item_name), None)
    
    if existing_item:
        if existing_item['checked']:
            existing_item['checked'] = False
            existing_item['quantity'] = item_qty
            save_data()
            st.success(f"✅ הפריט '{item_name}' היה מסומן כנקנה והוחזר אוטומטית לרשימה הפעילה!")
        else:
            st.error(f"⚠️ הפריט '{item_name}' כבר קיים ברשימת הקניות הפעילה!")
        return False
        
    current_shopping_list.append({
        "name": item_name, "quantity": item_qty, "category": category, 
        "estimated_price": price, "checked": False
    })
    if item_name not in st.session_state.all_purchased_items:
        st.session_state.all_purchased_items.append(item_name)
    save_data()
    return True

def render_product_card(idx, item):
    """פונקציה נפרדת המרכזת את כל בניית כרטיסיית המוצר (Refactoring)"""
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
                st.session_state[f"show_edit_shop_{idx}"] = not st.session_state.get(f"show_edit_shop_{idx}", False)
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
            with st.form(f"form_edit_item_{idx}"):
                e_name = st.text_input("שם הפריט:", value=item['name'])
                e_price = st.number_input("מחיר משוער (₪):", value=float(item['estimated_price']))
                current_cat_index = CATEGORIES.index(item['category']) if item['category'] in CATEGORIES else 7
                e_category = st.selectbox("תקן קטגוריה:", CATEGORIES, index=current_cat_index)
                
                if st.form_submit_button("שמור שינויים", type="primary"):
                    new_name = e_name.strip()
                    current_shopping_list[idx].update({'name': new_name, 'estimated_price': e_price, 'category': e_category})
                    st.session_state.learned_categories[new_name.lower()] = e_category
                    st.session_state[f"show_edit_shop_{idx}"] = False
                    save_data() 
                    st.rerun()
    st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)


# --- מסך הניווט (Tabs) ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🛒 רשימה", "➕ הוספה", "⭐ מועדפים", "🗺️ סידור", "🧮 השוואה", "🛍️ לבאה", "📊 היסטוריה", "🏪 חנויות"
])

with tab1:
    store_list = list(st.session_state.stores.keys())
    selected_store = st.selectbox("🏪 חנות פעילה כרגע:", store_list, index=store_list.index(st.session_state.active_store))
    if selected_store != st.session_state.active_store:
        st.session_state.active_store = selected_store
        save_data()
        st.rerun()

    st.markdown("---")
    active_items = [i for i in current_shopping_list if not i['checked']]
    total_cost = sum(i['quantity'] * i['estimated_price'] for i in active_items)
    
    col1, col2 = st.columns(2)
    with col1: st.metric(label="💰 עלות סל נוכחי", value=f"₪{total_cost:.2f}")
    with col2: st.metric(label="📦 פריטים שנותרו", value=len(active_items))

    if st.session_state.budget > 0:
        st.progress(min(total_cost / st.session_state.budget, 1.0))
        if total_cost > st.session_state.budget:
            st.error("⚠️ עברתם את התקציב שהוגדר!")

    st.markdown("---")

    if not active_items:
        st.info("💡 רשימת הקניות ריקה לגמרי!")
    else:
        categories_in_list = sorted(list(set(i['category'] for i in active_items)))
        selected_category_filter = st.selectbox("📂 סינון מחלקה:", ["הכל (ללא סינון)"] + categories_in_list)

        for idx, item in enumerate(current_shopping_list):
            if not item['checked']:
                if selected_category_filter == "הכל (ללא סינון)" or item['category'] == selected_category_filter:
                    render_product_card(idx, item)

        checked_items = [i for i in current_shopping_list if i['checked']]
        if checked_items:
            st.markdown("---")
            st.subheader("✅ פריטים שנקנו:")
            for idx, item in enumerate(current_shopping_list):
                if item['checked']:
                    c1, c2 = st.columns([4, 1.2])
                    c1.write(f"~~{item['name']} (כמות: {item['quantity']})~~")
                    if c2.button("↩️ החזר", key=f"return_{idx}"):
                        current_shopping_list[idx]['checked'] = False
                        save_data()
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏁 סיים קנייה ושמור קבלה", type="primary"):
                st.session_state.purchase_history.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "store": st.session_state.active_store,
                    "items_count": len(checked_items),
                    "total_cost": sum(i['quantity'] * i['estimated_price'] for i in checked_items)
                })
                st.session_state.stores[st.session_state.active_store] = active_items
                save_data()
                st.success("הקנייה נשמרה בהצלחה!")
                st.rerun()

with tab2:
    st.subheader("➕ הוספת פריט ידנית")
    if st.session_state.get('last_added_item'):
        last = st.session_state.last_added_item
        st.success(f"✅ נוסף בהצלחה: **{last['name']}**")
        time.sleep(2)
        st.session_state.pop('last_added_item', None)
        st.rerun()

    with st.form("add_item_form"):
        known_items = sorted(list(set(st.session_state.all_purchased_items)))
        selected_known_item = st.selectbox("היסטוריה:", ["-- בחר --"] + known_items)
        manual_item_name = st.text_input("או פריט חדש:")
        item_qty = st.number_input("כמות", min_value=1, value=1)
        
        if st.form_submit_button("הוסף לרשימה 🛒", type="primary"):
            final_name = manual_item_name.strip() if manual_item_name.strip() else (selected_known_item if selected_known_item != "-- בחר --" else "")
            
            if final_name:
                category, price = ai_smart_categorize_and_price(final_name)
                success = add_item_with_check(final_name, item_qty, category, price)
                
                if success:
                    st.session_state.last_added_item = {"name": final_name}
                    st.rerun()
            else:
                st.warning("נא להזין שם פריט.")

with tab3:
    st.subheader("⭐ הוספה מהירה ממועדפים")
    for idx, fav in enumerate(FAVOURITES_DB):
        col_f, col_btn = st.columns([3, 1])
        col_f.write(f"**{fav['name']}** (₪{fav['estimated_price']})")
        if col_btn.button("➕ הוסף", key=f"fav_{idx}"):
            success = add_item_with_check(fav['name'], 1, fav['category'], fav['estimated_price'])
            if success: st.rerun()

with tab4:
    st.subheader("🗺️ מסלול הליכה חכם")
    sorted_items = sorted([i for i in current_shopping_list if not i['checked']], key=lambda x: AISLE_ORDER.get(x['category'], 99))
    for item in sorted_items:
        icon, _ = get_product_icon_and_color(item['category'])
        st.write(f"• {icon} **{item['name']}** ({item['category']})")

with tab5:
    st.subheader("🧮 מה משתלם יותר?")
    c_a, c_b = st.columns(2)
    with c_a:
        pa = st.number_input("מחיר א'", value=10.0, key="pa")
        aa = st.number_input("כמות א'", value=500.0, key="aa")
    with c_b:
        pb = st.number_input("מחיר ב'", value=18.0, key="pb")
        ab = st.number_input("כמות ב'", value=1000.0, key="ab")
    if aa > 0 and ab > 0:
        if (pa/aa) < (pb/ab): st.success("א' משתלם יותר!")
        elif (pb/ab) < (pa/aa): st.success("ב' משתלם יותר!")
        else: st.info("זהה.")

with tab6:
    st.subheader("🛍️ פריטים חסרים (לקנייה הבאה)")
    if not st.session_state.next_trip_list: st.info("אין חסרים.")
    for idx, item in enumerate(st.session_state.next_trip_list):
        c_n, c_a, c_r = st.columns([3, 1.2, 1])
        c_n.write(f"• **{item['name']}**")
        if c_a.button("➕ לסל", key=f"ab_{idx}"):
            current_shopping_list.append(item)
            st.session_state.next_trip_list.pop(idx)
            save_data(); st.rerun()
        if c_r.button("🗑️ הסר", key=f"rn_{idx}"):
            st.session_state.next_trip_list.pop(idx)
            save_data(); st.rerun()

with tab7:
    st.subheader("📊 היסטוריה ותקציב")
    new_budget = st.number_input("תקציב (₪):", value=float(st.session_state.budget))
    if new_budget != st.session_state.budget:
        st.session_state.budget = new_budget
        save_data()
    if st.session_state.purchase_history:
        st.dataframe(pd.DataFrame(st.session_state.purchase_history), use_container_width=True)

with tab8:
    st.subheader("🏪 ניהול חנויות")
    selected_type = st.selectbox("סוג:", ["סופרמרקט", "פארם", "ירקניה", "אחר"])
    new_store = st.text_input("שם חנות חדשה:", value=f"{selected_type} חדש")
    if st.button("צור חנות ✅", type="primary"):
        if new_store.strip() and new_store.strip() not in st.session_state.stores:
            st.session_state.stores[new_store.strip()] = []
            st.session_state.active_store = new_store.strip()
            save_data(); st.rerun()
    st.markdown("---")
    store_to_del = st.selectbox("מחיקת חנות:", list(st.session_state.stores.keys()))
    if st.button("🗑️ מחק לצמיתות") and len(st.session_state.stores) > 1:
        del st.session_state.stores[store_to_del]
        st.session_state.active_store = list(st.session_state.stores.keys())[0]
        save_data(); st.rerun()
