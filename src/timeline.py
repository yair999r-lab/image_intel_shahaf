import pandas as pd
import json
import base64
import re
from pathlib import Path

# --- הגדרות גלובליות ונתיבים ---
BASE_DIR = Path(__file__).resolve().parent
ICONS_DIR = BASE_DIR / "icons"

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
    try:
        with open(image_path, "rb") as img_file:
            return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return None


def get_logos_html(makes_list):
    """שולף את הלוגואים ומייצר חלון קטן עם רקע לבן בתוך ה-Tooltip של Vis.js"""
    unique_makes = set(makes_list)
    html_elements = []

    for make in unique_makes:
        make_lower = str(make).lower()
        logo_key = make_lower if make_lower in LOGO_FILES_LOWER else "unknown"
        full_path = ICONS_DIR / LOGO_FILES_LOWER[logo_key]

        if full_path.exists():
            b64 = get_b64_image(full_path)
            if b64:
                img_tag = f"<div style='background-color:#ffffff; padding:5px; border-radius:6px; margin:0 4px; display:inline-block;'><img src='{b64}' style='height:35px; width:auto; display:block;'></div>"
                html_elements.append(img_tag)

    return "".join(html_elements)


def hex_to_rgba(hex_color, alpha=0.1):
    """פונקציית עזר להמרת צבעי הקסדצימל ל-RGBA שקוף"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"
    return "rgba(255,255,255,0.1)"


def prepare_camera_data(raw_data):
    df = pd.DataFrame(raw_data)
    if 'datetime' not in df.columns: return None
    df_clean = df.dropna(subset=['datetime']).copy()
    if df_clean.empty: return None

    df_clean['datetime'] = pd.to_datetime(df_clean['datetime'], format="%Y:%m:%d %H:%M:%S", errors='coerce')
    df_clean = df_clean.dropna(subset=['datetime']).copy()
    df_clean['datetime_minute'] = df_clean['datetime'].dt.floor('min')

    if 'camera_make' not in df_clean.columns: df_clean['camera_make'] = "Unknown"
    if 'camera_model' not in df_clean.columns: df_clean['camera_model'] = "Unknown"
    df_clean['camera_make'] = df_clean['camera_make'].fillna("Unknown")
    df_clean['camera_model'] = df_clean['camera_model'].fillna("Unknown")

    df_clean['display_name'] = df_clean.apply(
        lambda r: r['camera_model'] if str(r['camera_model']).strip() not in ["Unknown", ""] else r['camera_make'],
        axis=1
    )

    if 'latitude' in df_clean.columns and 'longitude' in df_clean.columns:
        df_clean['coords'] = df_clean.apply(
            lambda r: f"{r['latitude']:.4f}, {r['longitude']:.4f}" if pd.notnull(r['latitude']) else "ללא GPS", axis=1
        )
    else:
        df_clean['coords'] = "ללא GPS"

    if 'city' in df_clean.columns:
        df_clean['city_display'] = df_clean['city'].fillna("לא זוהתה עיר")
    else:
        df_clean['city_display'] = "לא זוהתה עיר"

    return df_clean


def generate_camera_dashboard(raw_data):
    df_ready = prepare_camera_data(raw_data)
    if df_ready is None or df_ready.empty:
        return False, ""

    # חישוב גבולות הזמן הדינמיים (הכי ישן מול הכי חדש + שוליים של שנה)
    time_padding = pd.Timedelta(days=365)
    limit_min = (df_ready['datetime'].min() - time_padding).isoformat()
    limit_max = (df_ready['datetime'].max() + time_padding).isoformat()

    # קיבוץ הנתונים
    grouped = df_ready.groupby(['datetime_minute', 'display_name', 'city_display', 'coords']).agg(
        count=('filename', 'count'),
        makes_list=('camera_make', list),
        filenames=('filename', list),
        datetime=('datetime', 'first')
    ).reset_index()

    grouped['logos_html'] = grouped['makes_list'].apply(get_logos_html)

    groups = []
    items = []
    added_groups = set()

    CYBER_COLORS = ["#00CCFF", "#FF3366", "#39FF14", "#FFCC00", "#B026FF", "#00FFCC", "#FF9900", "#FF00FF"]
    device_colors = {}
    dynamic_css = ""

    for idx, row in grouped.iterrows():
        display_name = str(row['display_name'])
        dt = row['datetime']
        coords = row['coords']
        city = str(row['city_display'])
        count = row['count']
        logos_html = row['logos_html']

        filenames_str = " ".join(row['filenames']).lower()

        # יצירת קלאס ייחודי לשורה שלמה
        group_class = "group_" + re.sub(r'[^a-zA-Z0-9]', '_', display_name).lower()

        if display_name not in device_colors:
            color = CYBER_COLORS[len(device_colors) % len(CYBER_COLORS)]
            device_colors[display_name] = color

            # 🛑 עוקף Vis.js: העיצוב יורד ממעטפת השורה היישר אל העיגולים והאגדים שבתוכה! 🛑
            dynamic_css += f"""
            /* צבע רקע השורה ותווית המכשיר */
            .vis-group.{group_class} {{ background-color: {hex_to_rgba(color, 0.04)} !important; border-bottom: 1px solid rgba(255,255,255,0.03) !important; }}
            .vis-label.{group_class} {{ border-left: 5px solid {color} !important; background-color: {hex_to_rgba(color, 0.08)} !important; color: white !important; }}

            /* עיצוב הנקודה הבודדת (Dot) באותה השורה */
            .vis-group.{group_class} .vis-item .vis-dot {{
                border-color: {color} !important;
                background-color: {hex_to_rgba(color, 0.2)} !important;
                box-shadow: 0 0 18px {hex_to_rgba(color, 0.9)} !important;
            }}
            .vis-group.{group_class} .vis-item:hover .vis-dot {{
                box-shadow: 0 0 25px {color} !important;
            }}

            /* אנימציית נשימה/הבהוב מותאמת אישית לצבע השורה */
            @keyframes pulse_{group_class} {{
                0% {{ box-shadow: inset 0 0 5px {hex_to_rgba(color, 0.6)}, 0 0 8px {hex_to_rgba(color, 0.4)}; transform: scale(1); }}
                50% {{ box-shadow: inset 0 0 15px {color}, 0 0 20px {hex_to_rgba(color, 0.8)}; transform: scale(1.1); }}
                100% {{ box-shadow: inset 0 0 5px {hex_to_rgba(color, 0.6)}, 0 0 8px {hex_to_rgba(color, 0.4)}; transform: scale(1); }}
            }}

            /* פתרון ה"עיגולים הלבנים": עיצוב האגד (Cluster) מתבצע ע"י ירושה מהשורה - שקיפות, צבע והבהוב! */
            .vis-group.{group_class} .vis-item.vis-cluster {{
                background-color: {hex_to_rgba(color, 0.15)} !important; 
                color: {color} !important; 
                border: 1px solid {hex_to_rgba(color, 0.6)} !important; 
                animation: pulse_{group_class} 2s infinite ease-in-out !important; 
            }}
            .vis-group.{group_class} .vis-item.vis-cluster:hover {{
                background-color: {hex_to_rgba(color, 0.5)} !important; 
                color: white !important; 
                box-shadow: 0 0 25px {color} !important; 
                animation: none !important; 
                transform: scale(1.2) !important;
            }}
            """

        color = device_colors[display_name]

        if group_class not in added_groups:
            groups.append({
                "id": group_class,
                "content": f"<div style='padding: 15px 5px; min-height: 30px; display: flex; align-items: center; justify-content: center;'><b style='color: {color}; font-size: 15px; text-shadow: 0 0 8px {hex_to_rgba(color, 0.6)};'>{display_name}</b></div>",
                "className": group_class  # מגדיר את הקלאס לשורה כולה
            })
            added_groups.add(group_class)

        item_html = f"<span style='color: white; font-weight: bold; font-size: 13px; margin-left: 5px; text-shadow: 1px 1px 2px #000;'>{count} תמונות</span>" if count > 1 else ""

        hover_html = f"""
        <div class="cyber-tooltip">
            <div style="display:flex; justify-content:center; margin-bottom:12px;">{logos_html}</div>
            <div style="font-size:18px; font-weight:bold; color:#39ff14; margin-bottom: 10px; border-bottom: 1px solid #1a365d; padding-bottom: 8px;">
                {display_name}
            </div>
            <div style="margin-bottom: 8px; font-size: 16px;">📅 <b style="color:#fff;">{dt.strftime('%d/%m/%Y | %H:%M')}</b></div>
            <div style="margin-bottom: 8px; font-size: 16px;">🏙️ <b style="color:#fff;">{city}</b></div>
            <div style="font-size: 14px; color: #8b949e; margin-top: 8px;">📍 {coords}</div>
            <div style="font-size: 16px; color: #fff; margin-top: 10px; border-top: 1px dashed #1a365d; padding-top: 10px;">📸 סך כל התמונות בנקודה זו: <b>{count}</b></div>
        </div>
        """

        items.append({
            "id": idx + 1,
            "group": group_class,
            "start": dt.isoformat(),
            "content": item_html,
            "title": hover_html,
            "type": "point",
            "search_city": city,
            "search_device": display_name,
            "search_text": (filenames_str + " " + city + " " + display_name).lower(),
            "className": group_class
        })

    groups_json = json.dumps(groups)
    items_json = json.dumps(items)

    html_string = f"""
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment-with-locales.min.js"></script>
    <script type="text/javascript" src="https://unpkg.com/vis-timeline@latest/standalone/umd/vis-timeline-graph2d.min.js"></script>
    <link href="https://unpkg.com/vis-timeline@latest/styles/vis-timeline-graph2d.min.css" rel="stylesheet" type="text/css" />

    <style>
        .vis-timeline {{ border: 1px solid #1a365d; border-radius: 10px; font-family: 'Segoe UI', sans-serif; background-color: #06142e; overflow: hidden; }}
        .vis-group {{ background-image: linear-gradient(to bottom, transparent 49%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.08) 51%, transparent 52%); }}

        /* מבנה בסיס לנקודה (Dot) - הגדלנו ל-8 פיקסלים */
        .vis-item .vis-dot {{
            border-width: 8px !important;
            border-radius: 50% !important;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}

        .vis-item:hover .vis-dot {{
            transform: scale(1.4);
        }}

        /* מבנה בסיס לאגד (Cluster) - עגול, קומפקטי, ותומך ביישור אמצע למספר */
        .vis-item.vis-cluster {{ 
            font-weight: bold !important; 
            border-radius: 50% !important; 
            min-width: 32px !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 14px !important; 
            box-sizing: border-box !important;
            cursor: pointer;
            transition: transform 0.2s, background-color 0.2s;
        }}

        /* ביטול הפדינג הפנימי של הטקסט בתוך האגד כדי שהמספר יהיה ממורכז */
        .vis-item.vis-cluster .vis-item-content {{
            padding: 0 !important;
        }}

        /* חלונית הריחוף המעוצבת */
        .vis-tooltip {{ background-color: transparent !important; border: none !important; padding: 0 !important; overflow: visible !important; }}
        .cyber-tooltip {{
            direction: rtl; text-align: right; background: rgba(11, 31, 64, 0.98); 
            padding: 20px; border-radius: 10px; border: 2px solid #39ff14; color: white; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.9); width: max-content; min-width: 280px;
            max-width: 450px; white-space: normal;
        }}

        .vis-time-axis .vis-text {{ color: #8b949e; font-weight: bold; font-size: 14px; }}
        .vis-labelset .vis-label {{ color: white !important; display:flex; align-items:center; justify-content:center; }}
        .vis-time-axis .vis-grid.vis-minor {{ border-color: rgba(255, 255, 255, 0.07); }}
        .vis-time-axis .vis-grid.vis-major {{ border-color: rgba(255, 255, 255, 0.2); }}

        /* הזרקת בלוקי ה-CSS הדינמיים (אנימציות, צבעים ושקיפויות) ישירות מהפייתון! */
        {dynamic_css}
    </style>

    <div id="vis-graph-container" style="width: 100%; height: 700px; direction: ltr;"></div>

    <script>
        moment.locale('he');

        window.timelineSearchData = {{
            items: {items_json},
            groups: {groups_json}
        }};

        var groups = new vis.DataSet(window.timelineSearchData.groups);
        var items = new vis.DataSet(window.timelineSearchData.items);
        var container = document.getElementById('vis-graph-container');

        var options = {{
            locale: 'he', 
            groupOrder: 'id',
            orientation: 'top',
            editable: false,
            height: '700px', 
            margin: {{ item: 10, axis: 10 }},
            stack: false, 
            zoomMin: 1000 * 60 * 60,
            xss: {{ disabled: true }},

            min: '{limit_min}',
            max: '{limit_max}',

            tooltip: {{ followMouse: true, delay: 50 }},

            cluster: {{
                titleTemplate: "<div class='cyber-tooltip' style='min-width: auto; text-align: center; font-size: 18px; padding: 15px;'>📸 סך הכל <b>{{count}}</b> תמונות בנקודה זו</div>",
                clusterCriteria: function(firstItem, secondItem) {{
                    return firstItem.group === secondItem.group;
                }}
            }}
        }};

        var timeline = new vis.Timeline(container, items, groups, options);

        window.cyberTimeline = timeline;
        window.cyberTimelineItems = items;
        window.cyberTimelineOriginalData = window.timelineSearchData.items;

        window.applyTimelineFilterFromHeader = function(start, end) {{
            if(start && end) {{
                timeline.setWindow(start, end, {{animation: true}});
            }}
        }};

        window.resetTimelineZoomFromHeader = function() {{
            timeline.fit({{animation: true}});
        }};
    </script>
    """
    return True, html_string