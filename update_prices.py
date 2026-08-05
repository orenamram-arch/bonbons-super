import os
from datetime import datetime
from supabase import create_client, Client

# חיבור ל-Supabase
SUPABASE_URL = "https://vobzhjutimeowgsjhgyt.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # נמשוך ממשתני סביבה לאבטחה
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_daily_prices():
    # כאן תהיה הלוגיקה שפונה ל-API חיצוני (למשל Apify או Pricez)
    # נדמה קבלת נתונים עדכניים:
    daily_data = [
        {"item_name": "חלב תנובה 3%", "rami_levy_price": 6.80, "shufersal_price": 7.20, "yohananof_price": 6.90},
        {"item_name": "קוטג' תנובה", "rami_levy_price": 5.90, "shufersal_price": 6.50, "yohananof_price": 6.00},
        # ... שאר המוצרים הבסיסיים
    ]
    return daily_data

def update_database():
    prices = fetch_daily_prices()
    now = datetime.now().isoformat()
    
    for item in prices:
        item["last_updated"] = now
        # Upsert: יעדכן את המחיר אם המוצר קיים, ויוסיף שורה אם הוא חדש
        supabase.table("supermarket_prices").upsert(item).execute()
        
    print(f"✅ Successfully updated {len(prices)} items in Supabase.")

if __name__ == "__main__":
    update_database()