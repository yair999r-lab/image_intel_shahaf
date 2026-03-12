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
LOGO_FILES_LOWER = {key.lower(): value for key, value in LOGO_FILES.items()}

def get_b64_image(image_path):
    """מקבלת נתיב לתמונה ומחזירה אותה כמחרוזת טקסט (Base64)"""
    try:
        with open(image_path, "rb") as img_file:
            # הקידוד המיוחד שאומר לדפדפן: "זו תמונה, תציג אותה"
            return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return None


def prepare_camera_data(raw_data):
    """לוקחת את המילונים מהחילוץ, מנקה אותם ומכינה טבלה לגרף"""
    df = pd.DataFrame(raw_data)

    # מסננים החוצה תמונות שאין להן זמן צילום (אי אפשר למקם על ציר הזמן)
    df_clean = df.dropna(subset=['datetime']).copy()

    # בדיקת בטיחות: אם אחרי הסינון לא נשארו תמונות - נעצור
    if df_clean.empty:
        return None

    # הופכים את עמודת הזמן מסתם טקסט לפורמט שפלוטלי מבין
    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'], format="%Y:%m:%d %H:%M:%S")

    # סותמים "חורים" (None) במילה Unknown כדי שהקוד לא יקרוס
    df_clean['camera_make'] = df_clean['camera_make'].fillna("Unknown")
    df_clean['camera_model'] = df_clean['camera_model'].fillna("Unknown")

    # קביעת שם הקומה (Y): נותנים עדיפות לדגם המכשיר, ואם אין - ליצרן
    df_clean['display_name'] = df_clean.apply(
        lambda r: r['camera_model'] if r['camera_model'] != "Unknown" else r['camera_make'], axis=1
    )

    # מכינים מחרוזות יפות לחלונית הריחוף (כדי שלא נצטרך לחשב את זה בתוך פלוטלי)
    df_clean['make_model'] = df_clean['camera_make'] + " " + df_clean['camera_model']
    df_clean['coords'] = df_clean.apply(
        lambda r: f"{r['latitude']:.4f}, {r['longitude']:.4f}" if pd.notnull(r['latitude']) else "No GPS", axis=1
    )

    # הטקסט שיופיע ליד העיגול (לפני שנדביק את הלוגו)
    df_clean['marker_text'] = df_clean['camera_model']

    return df_clean


def create_pro_scatter(df_clean):
    """מייצרת את קנבס הגרף עם הנקודות והעיצוב המקצועי"""

    # חישוב גובה: ככל שיש יותר מכשירים (קומות), הגרף ימתח כדי שלא יהיה צפוף
    num_rows = len(df_clean['display_name'].unique())
    dynamic_height = max(450, num_rows * 80)

    # פקודת הציור המרכזית של פלוטלי
    fig = px.scatter(
        df_clean, x='datetime', y='display_name',
        color='display_name',  # בוחר צבע שונה לכל קומה
        text='marker_text',
        # מכניסים בסתר נתונים נוספים שישמשו את חלונית הריחוף
        custom_data=['filename', 'make_model', 'coords'],
        color_discrete_sequence=px.colors.qualitative.Prism
    )

    # עיצוב מותאם אישית לחלונית הריחוף (עם שילוב HTML לאימוג'ים וצבעים)
    fig.update_traces(
        hovertemplate="""
        <span style="font-size:16px; font-weight:bold; color:#00CCFF;">%{customdata[0]}</span><br>
        📅 %{x|%d/%m/%Y %H:%M}<br>
        📍 %{customdata[2]}<br>
        📸 %{customdata[1]}
        <extra></extra>
        """,
        marker=dict(size=35, line=dict(width=2, color='white'), opacity=0.9),
        textposition='bottom center',
        textfont=dict(size=12, color='white')
    )

    # עיצוב חלון האפליקציה: רקעים כהים וטקסטים בעברית/אנגלית
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111217", plot_bgcolor="#111217",
        font=dict(family="Assistant, Segoe UI, sans-serif", size=14),
        height=dynamic_height,
        margin=dict(l=20, r=20, t=80, b=20),
        title={'text': "<b>ציר זמן צילום - ממופה לפי מכשיר</b>", 'y': 0.96, 'x': 0.5,
               'font': {'size': 24, 'color': '#00CCFF'}},
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="ציר זמן"),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title="", tickfont={'size': 16}),
        showlegend=False
    )
    return fig