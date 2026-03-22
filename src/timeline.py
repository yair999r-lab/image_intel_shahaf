import pandas as pd  # ספרייה חזקה לניהול ועיבוד נתונים (מסדרת לנו את המידע בטבלאות חכמות)
import \
    plotly.express as px  # 📊 פלוטלי: הספרייה שמציירת את הגרף עצמו (הופכת מספרים לאינטראקטיביות, מאפשרת ריחוף וזום בדפדפן)
import \
    base64  # 🖼️ בייס64: ספרייה ש"גורסת" קובץ תמונה והופכת אותו לטקסט ארוך. ככה התמונה נטמעת בתוך ה-HTML ולא נשברת כשמעבירים מחשב
from pathlib import \
    Path  # 📍 פאת'ליב: ה"GPS" של פייתון. יודע למצוא נתיבים אוטומטית בלי להתבלבל בין הסלאשים של ווינדוס ללינוקס

# ייבוא פונקציית החילוץ מהקובץ השני שבניתם
from extractor import extract_all

# --- הגדרות גלובליות ונתיבים ---
BASE_DIR = Path(__file__).resolve().parent  # מוצא את התיקייה שבה שמור הקובץ הנוכחי
ICONS_DIR = BASE_DIR / "icons"  # מגדיר שהלוגואים נמצאים בתיקיית "icons" ליד הקובץ שלנו

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
            return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return None


def get_logos_html(makes_list):
    """
    מקבל רשימה של יצרנים, שולף את הלוגואים ומייצר תגיות HTML תקניות.
    אלו יוצגו בחלון הצף העצמאי של ה-JS שלנו (ולא בזה של פלוטלי).
    """
    unique_makes = set(makes_list)
    html_elements = []

    for make in unique_makes:
        make_lower = str(make).lower()
        logo_key = make_lower if make_lower in LOGO_FILES_LOWER else "unknown"
        full_path = ICONS_DIR / LOGO_FILES_LOWER[logo_key]

        if full_path.exists():
            b64 = get_b64_image(full_path)
            if b64:
                # יצירת אלמנט עוטף לבן לכל לוגו שיבלוט ברקע הכהה, הצגה Side-by-Side
                img_tag = f"<div style='background-color:#ffffff; padding:4px; border-radius:6px; margin:0 4px; display:inline-block;'><img src='{b64}' style='height:30px; width:auto; display:block;'></div>"
                html_elements.append(img_tag)

    return "".join(html_elements)


def prepare_camera_data(raw_data):
    """לוקחת את המילונים מהחילוץ, מנקה, ומקבצת תמונות זהות בזמן (Clustering)"""
    df = pd.DataFrame(raw_data)

    df_clean = df.dropna(subset=['datetime']).copy()

    if df_clean.empty:
        return None

    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'], format="%Y:%m:%d %H:%M:%S")
    df_clean['datetime_minute'] = df_clean['datetime'].dt.floor('min')

    df_clean['camera_make'] = df_clean['camera_make'].fillna("Unknown")
    df_clean['camera_model'] = df_clean['camera_model'].fillna("Unknown")

    if 'city' in df_clean.columns:
        df_clean['city'] = df_clean['city'].fillna("Unknown")
    else:
        df_clean['city'] = "Unknown"

    df_clean['display_name'] = df_clean.apply(
        lambda r: r['camera_model'] if r['camera_model'] != "Unknown" else r['camera_make'], axis=1
    )

    df_clean['coords'] = df_clean.apply(
        lambda r: f"{r['latitude']:.4f}, {r['longitude']:.4f}" if pd.notnull(r['latitude']) else "No GPS", axis=1
    )

    # שלב הקיבוץ והאיחוד של רשימות היצרנים
    grouped = df_clean.groupby(['datetime_minute', 'display_name', 'camera_model', 'city']).agg(
        count=('filename', 'count'),
        filenames=('filename', lambda x: '<br>'.join(x.head(5)) + ('<br>...' if len(x) > 5 else '')),
        coords=('coords', 'first'),
        datetime=('datetime', 'first'),
        makes_list=('camera_make', list)  # אוסף את כל היצרנים באותה נקודה
    ).reset_index()

    grouped['make_model'] = grouped['makes_list'].apply(lambda x: x[0]) + " " + grouped['camera_model']
    grouped['bubble_text'] = grouped['count'].apply(lambda x: str(x) if x > 1 else "")

    # הכנת נתונים לתצוגת ה-JS העצמאית
    grouped['logos_html'] = grouped['makes_list'].apply(get_logos_html)
    grouped['formatted_date'] = grouped['datetime'].dt.strftime('%d/%m/%Y %H:%M')

    return grouped


def create_pro_scatter(df_clean):
    """מייצרת את קנבס הגרף עם הנקודות וזום אינטראקטיבי מלא"""

    num_rows = len(df_clean['display_name'].unique())
    dynamic_height = max(450, num_rows * 80)

    fig = px.scatter(
        df_clean, x='datetime', y='display_name',
        size='count',
        color='display_name',
        text='bubble_text',
        # הוספת הנתונים החדשים למערך הנסתר (אינדקסים נשמרים תואמים ל-JS בדשבורד)
        custom_data=['count', 'filenames', 'make_model', 'coords', 'city', 'logos_html', 'formatted_date'],
        color_discrete_sequence=px.colors.qualitative.Prism,
        size_max=35
    )

    # נטרול מלא של חלונית פלוטלי המקורית - אנחנו נשתמש ב-JS במקום!
    fig.update_traces(
        hoverinfo='none',
        hovertemplate=None,
        marker=dict(line=dict(width=2, color='white'), opacity=0.9),
        textposition='middle center',
        textfont=dict(size=14, color='white', family="Arial Black")
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111217", plot_bgcolor="#111217",
        font=dict(family="Assistant, Segoe UI, sans-serif", size=14),
        height=dynamic_height,
        autosize=True,
        margin=dict(l=20, r=20, t=80, b=20),
        title={'text': "<b>ציר זמן צילום - ממופה לפי מכשיר</b>", 'y': 0.96, 'x': 0.5,
               'font': {'size': 24, 'color': '#00CCFF'}},
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="ציר זמן"),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title="", tickfont={'size': 16}),
        showlegend=False,
        dragmode='pan'
    )
    return fig


def generate_camera_dashboard(raw_data):
    """מריצה את כל השלבים לפי הסדר ומוציאה HTML"""

    print("📊 מעבד ומקבץ נתונים...")
    df_ready = prepare_camera_data(raw_data)

    if df_ready is None or len(df_ready) < 1:
        print("🛑 כל התמונות סוננו (ללא זמן צילום תקין), לא נשארו נתונים לגרף.")
        return False, ""

    print("🎨 בונה גרף בועות מעוצב...")
    fig = create_pro_scatter(df_ready)

    print("✅ הגרף מוכן! מוסר בחזרה לשרת עם מנגנון Hover עצמאי.")

    html_string = fig.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        div_id='cyber_timeline',
        config={'scrollZoom': True, 'displayModeBar': True}
    )

    # === הזרקת מנוע החלון הצף העצמאי שלנו (JS) לתוך תוצר הפייתון ===
    custom_tooltip_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        var myPlot = document.getElementById('cyber_timeline');
        if(!myPlot) return;

        // יצירת החלון הצף העצמאי
        var tooltip = document.getElementById('cyber-tooltip');
        if(!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'cyber-tooltip';
            tooltip.style.position = 'fixed';
            tooltip.style.display = 'none';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '10000';
            tooltip.style.background = 'rgba(11, 31, 64, 0.95)';
            tooltip.style.border = '1px solid #39ff14';
            tooltip.style.borderRadius = '8px';
            tooltip.style.padding = '15px';
            tooltip.style.color = '#c9d1d9';
            tooltip.style.fontFamily = 'Assistant, "Segoe UI", sans-serif';
            tooltip.style.textAlign = 'right';
            tooltip.style.direction = 'rtl';
            tooltip.style.boxShadow = '0 4px 15px rgba(0,0,0,0.5)';
            tooltip.style.minWidth = '220px';
            document.body.appendChild(tooltip);
        }

        // האזנה לאירוע ריחוף של פלוטלי ובניית התוכן
        myPlot.on('plotly_hover', function(data){
            var pt = data.points[0];
            var cd = pt.customdata;
            if(!cd) return;

            // cd[0]=count, cd[1]=filenames, cd[2]=make_model, cd[3]=coords, cd[4]=city, cd[5]=logos_html, cd[6]=formatted_date
            var html = `
                <div style="display:flex; justify-content:center; margin-bottom:10px;">${cd[5]}</div>
                <div style="font-size:16px; font-weight:bold; color:#00CCFF; margin-bottom:5px;">${cd[2]}</div>
                <div style="margin-bottom:3px;">📅 ${cd[6]}</div>
                <div style="margin-bottom:3px;">📍 ${cd[3]} (${cd[4]})</div>
                <div style="margin-bottom:8px; border-bottom: 1px dashed #1a365d; padding-bottom: 8px; margin-top: 8px;">📸 <b>סך כל התמונות בנקודה זו: ${cd[0]}</b></div>
                <div style="font-size:11px; color:#8b949e; line-height:1.4;">${cd[1]}</div>
            `;
            tooltip.innerHTML = html;
            tooltip.style.display = 'block';

            // מיקום דינמי שמונע חריגה מגבולות המסך
            var tooltipRect = tooltip.getBoundingClientRect();
            var x = data.event.clientX + 15;
            var y = data.event.clientY + 15;

            if (x + tooltipRect.width > window.innerWidth) {
                x = data.event.clientX - tooltipRect.width - 15;
            }
            if (y + tooltipRect.height > window.innerHeight) {
                y = data.event.clientY - tooltipRect.height - 15;
            }

            tooltip.style.left = x + 'px';
            tooltip.style.top = y + 'px';
        });

        myPlot.on('plotly_unhover', function(data){
            tooltip.style.display = 'none';
        });
    });
    </script>
    """

    html_string += custom_tooltip_js
    return True, html_string


# ==========================================
# אזור ההפעלה
# ==========================================
if __name__ == "__main__":

    from extractor import extract_all

    MY_PHOTOS_PATH = r"C:/Intel/pycharm/pythonProject12/images"
    print("מתחיל בדיקה מקומית...")

    test_data = extract_all(MY_PHOTOS_PATH)

    success, html_result = generate_camera_dashboard(test_data)

    if success:
        print("✅ הגרף נוצר בהצלחה בזיכרון!")

        with open("test_timeline.html", "w", encoding="utf-8") as f:
            f.write(html_result)
    else:
        print("🛑 הבדיקה נכשלה או שאין מספיק נתונים (חזר False).")