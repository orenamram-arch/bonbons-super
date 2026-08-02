import streamlit as st
import pandas as pd
import json
import os
from supabase import create_client, Client

# הגדרת תצורת העמוד (חייב להיות ראשון)
st.set_page_config(page_title="רשימת קניות חכמה", page_icon="🛒", layout="wide")

# ==========================================
# חיבור ל-Supabase בענן
# ==========================================
SUPABASE_URL = "https://vobzhjutimeowgsjhgyt.supabase.co"
SUPABASE_KEY = "sb_publishable_OC3UKQ-UdO3ba4yHgvt9RQ_-AZdenBv"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# יצירת החיבור קודם כל!
supabase = init_supabase()

# ==========================================
# פונקציות טעינה ושמירה מהענן
# ==========================================
def load_data():
    try:
        # שימוש במפתח ייחודי לאפליקציית הקניות
        response = supabase.table("app_data").select("content").eq("key", "shopping_list_main_data").execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["content"]
    except Exception as e:
        st.error(f"שגיאה בטעינת הנתונים מ-Supabase: {e}")
    return None

def save_data(data):
    try:
        supabase.table("app_data").upsert(
            {"key": "shopping_list_main_data", "content": data},
            on_conflict="key"
        ).execute()
        st.toast("💾 נשמר בהצלחה בענן Supabase!", icon="✅")
    except Exception as e:
        st.error(f"שגיאה בשמירת הנתונים ב-Supabase: {e}")

# טעינת נתונים קיימים מ-Supabase
saved_data = load_data()

# אתחול Session State עם הנתונים מהענן או ערכי ברירת מחדל
if 'shopping_items' not in st.session_state:
    if saved_data and "shopping_items" in saved_data:
        st.session_state.shopping_items = saved_data["shopping_items"]
    else:
        st.session_state.shopping_items = [
            {"id": 1, "name": "חלב", "category": "מוצרי חלב", "quantity": 2, "checked": False},
            {"id": 2, "name": "לחם", "category": "מאפים", "quantity": 1, "checked": False},
            {"id": 3, "name": "עגבניות", "category": "פירות וירקות", "quantity": 5, "checked": True}
        ]

def persist_all():
    """שומר את רשימת הקניות המעודכנת לענן לצמיתות"""
    data = {
        "shopping_items": st.session_state.shopping_items
    }
    save_data(data)

# ==========================================
# עיצוב מותאם אישית (RTL)
# ==========================================
st.markdown("""
<style>
    .block-container { direction: rtl; text-align: right; }
    div[data-testid="metric-container"] { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important; border: 1px solid #dee2e6; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; border-right: 5px solid #007bff; }
    div[data-testid="metric-container"] label, div[data-testid="metric-container"] div { color: #111111 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🛒 אפליקציית רשימת הקניות שלי")
st.markdown("ניהול רשימת קניות חכמה, מסונכרנת לענן בזמן אמת.")

st.markdown("---")

# ==========================================
# הוספת פריט חדש
# ==========================================
st.subheader("➕ הוסף פריט חדש לרשימה")
with st.form("add_item_form", clear_on_submit=True):
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        item_name = st.text_input("שם המוצר:")
    with col_f2:
        item_category = st.selectbox("קטגוריה:", ["פירות וירקות", "מוצרי חלב", "מאפים", "בשר ודגים", "חומרי ניקוי", "שונות"])
    with col_f3:
        item_qty = st.number_input("כמות:", min_value=1, value=1, step=1)
        
    submitted = st.form_submit_button("הוסף לרשימה")
    if submitted and item_name.strip():
        new_id = max([item.get("id", 0) for item in st.session_state.shopping_items], default=0) + 1
        st.session_state.shopping_items.append({
            "id": new_id,
            "name": item_name.strip(),
            "category": item_category,
            "quantity": item_qty,
            "checked": False
        })
        persist_all()
        st.success("המוצר נוסף בהצלחה!")
        st.rerun()

st.markdown("---")

# ==========================================
# הצגת רשימת הקניות
# ==========================================
st.subheader("📋 רשימת הקניות הפעילה")

if not st.session_state.shopping_items:
    st.info("רשימת הקניות ריקה כרגע. הוסף פריטים למעלה!")
else:
    items_changed = False
    
    # הצגה לפי קטגוריות או רשימה נקייה
    for idx, item in enumerate(st.session_state.shopping_items):
        col_c1, col_c2, col_c3 = st.columns([4, 2, 1])
        
        with col_c1:
            new_checked = st.checkbox(
                f"**{item['name']}** (כמות: {item['quantity']}) — *{item['category']}*",
                value=item["checked"],
                key=f"check_{item.get('id', idx)}"
            )
            if new_checked != item["checked"]:
                st.session_state.shopping_items[idx]["checked"] = new_checked
                items_changed = True
                
        with col_c2:
            st.markdown(f"<span style='color: gray;'>קטגוריה: {item['category']}</span>", unsafe_allow_html=True)
            
        with col_c3:
            if st.button("🗑️", key=f"del_{item.get('id', idx)}"):
                st.session_state.shopping_items.pop(idx)
                persist_all()
                st.success("המוצר הוסר!")
                st.rerun()

    if items_changed:
        persist_all()
        st.rerun()

    st.markdown("---")
    
    # כפתורי פעולה מהירים
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🧹 נקה פריטים שסומנו כנקנו"):
            st.session_state.shopping_items = [item for item in st.session_state.shopping_items if not item["checked"]]
            persist_all()
            st.success("הפריטים שנקנו הוסרו מהרשימה!")
            st.rerun()
            
    with col_b2:
        if st.button("🗑️ אפס את כל הרשימה"):
            st.session_state.shopping_items = []
            persist_all()
            st.success("הודפס איפוס לרשימה!")
            st.rerun()
