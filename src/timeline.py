import pandas as pd              # ספרייה חזקה לניהול ועיבוד נתונים (מסדרת לנו את המידע בטבלאות חכמות)
import plotly.express as px      # 📊 פלוטלי: הספרייה שמציירת את הגרף עצמו (הופכת מספרים לאינטראקטיביות, מאפשרת ריחוף וזום בדפדפן)
import base64                    # 🖼️ בייס64: ספרייה ש"גורסת" קובץ תמונה והופכת אותו לטקסט ארוך. ככה התמונה נטמעת בתוך ה-HTML ולא נשברת כשמעבירים מחשב
from pathlib import Path         # 📍 פאת'ליב: ה"GPS" של פייתון. יודע למצוא נתיבים אוטומטית בלי להתבלבל בין הסלאשים של ווינדוס ללינוקס

# ייבוא פונקציית החילוץ מהקובץ השני שבניתם
from extractor import extract_all

# --- הגדרות גלובליות ונתיבים ---
BASE_DIR = Path(__file__).resolve().parent # מוצא את התיקייה שבה שמור הקובץ הנוכחי
ICONS_DIR = BASE_DIR / "icons"             # מגדיר שהלוגואים נמצאים בתיקיית "icons" ליד הקובץ שלנו

# מילון הלוגואים: שם היצרן מול שם הקובץ בתיקייה
LOGO_FILES = {
    "Apple": "Apple-Logo.png",
    "Samsung": "Samsung-Logo-2.png",
    "Canon": "Canon-Logo.png",
    "LG Electronics": "LG-Logo.png",
    "Xiaomi": "Xiaomi-logo.png",
    "Unknown": "purepng.com-camera-iconsymbolsiconsapple-iosiosios-8-iconsios-8-72152259602494tzv.png"
}