"""
analyzer.py - מציאת דפוסים ותובנות
צוות 2, זוג B
"""
import json
from datetime import datetime
from extractor import extract_all
from collections import Counter  # התוספת שלנו לספירת מכשירים וערים


def detect_camera_switches(images_data):
    """
    פונקציית עזר: מזהה מתי הסוכן החליף מכשיר בין צילום לצילום.
    מקבלת: את כל רשימת התמונות.
    מחזירה: רשימה של אובייקטים (מילונים), שכל אחד מהם מתאר "החלפה" שהתרחשה.
    """

    # שלב 1: מסננים תמונות בלי תאריך, ואז ממיינים את השאר לפי סדר כרונולוגי (מהישן לחדש).
    # הפקודה שקשורה ל-lambda אומרת לפייתון: "תמיין את הרשימה אך ורק לפי המפתח 'datetime'".
    sorted_images = sorted(
        [img for img in images_data if img.get("datetime")],
        key=lambda x: x["datetime"]
    )

    # רשימה ריקה שתשמור בתוכה את כל ההחלפות שמצאנו
    switches = []

    # שלב 2: לולאה שרצה מהתמונה השנייה (אינדקס 1) ועד הסוף.
    # אנחנו מתחילים מ-1 כדי שנוכל תמיד להשוות את התמונה הנוכחית (i) לתמונה הקודמת (i-1).
    for i in range(1, len(sorted_images)):
        # שולפים את מודל המצלמה של התמונה הקודמת והנוכחית
        prev_cam = sorted_images[i - 1].get("camera_model")
        curr_cam = sorted_images[i].get("camera_model")

        # שלב 3: התנאי להחלפה
        # בודקים שגם לקודמת יש מודל, גם לנוכחית יש מודל (הם לא None), והם שונים אחד מהשני.
        if prev_cam and curr_cam and prev_cam != curr_cam:
            date_only = sorted_images[i]["datetime"].split(" ")[0]
            curr_city = sorted_images[i].get("city")

            # אם מצאנו החלפה, מוסיפים אובייקט חכם עם תגיות לדשבורד
            switches.append({
                "type": "device_switch",
                "text": f"החלפת מכשיר: ב-{date_only} הסוכן עבר ממכשיר {prev_cam} ל-{curr_cam}",
                "devices": [prev_cam, curr_cam],
                "cities": [curr_city] if curr_city else [],
                "date": date_only
            })

    return switches


def detect_time_gaps(images_data):
    """
    פונקציית עזר: מחפשת קפיצות זמן חריגות (מעל 12 שעות) בין צילומים.
    """
    # מסננים תמונות בלי תאריך וממיינים מהישן לחדש
    sorted_images = sorted(
        [img for img in images_data if img.get("datetime")],
        key=lambda x: x["datetime"]
    )

    gaps = []

    # רצים על התמונות ומשווים כל תמונה לקודמתה
    for i in range(1, len(sorted_images)):
        prev_str = sorted_images[i - 1]["datetime"]
        curr_str = sorted_images[i]["datetime"]

        # ממירים את המחרוזת לאובייקט "זמן" שפייתון יודע לחשב
        prev_time = datetime.strptime(prev_str, "%Y:%m:%d %H:%M:%S")
        curr_time = datetime.strptime(curr_str, "%Y:%m:%d %H:%M:%S")

        # מחשבים את ההפרש והופכים אותו לשעות
        diff_hours = (curr_time - prev_time).total_seconds() / 3600

        # שליפת שם המכשיר של התמונה הנוכחית
        make = sorted_images[i].get("camera_make") or ""
        model = sorted_images[i].get("camera_model") or ""
        full_name = f"{make} {model}".strip() or "מכשיר לא ידוע"

        # אם ההפרש גדול מ-12 שעות, מצאנו פער חשוד!
        if diff_hours > 12:
            date_only = curr_str.split(" ")[0]
            curr_city = sorted_images[i].get("city")

            gaps.append({
                "type": "time_gap",
                "text": f"פער בין תמונות: זוהה נתק של {int(diff_hours)} שעות לפני הצילום ב-{date_only} במכשיר {full_name}",
                "devices": [full_name],
                "cities": [curr_city] if curr_city else [],
                "date": date_only
            })

    return gaps


def analyze(images_data):
    """
    הפונקציה המרכזית (ה"מוח"): מנתחת את הנתונים ומחזירה את הדו"ח הסופי.
    """

    # --- חלק 1: חישוב סטטיסטיקות בסיסיות ---

    # בודקים כמה תמונות יש בסך הכל ברשימה שקיבלנו
    total_images = len(images_data)

    # סופרים כמה תמונות מכילות GPS (כלומר, המפתח 'has_gps' הוא True)
    images_with_gps = sum(1 for img in images_data if img.get("has_gps"))

    # סופרים כמה תמונות מכילות תאריך (datetime קיים ולא ריק)
    images_with_datetime = sum(1 for img in images_data if img.get("datetime"))

    # --- חלק 2: מציאת מצלמות ייחודיות וספירתן ---
    all_devices = []

    for img in images_data:
        # משתמשים ב- "" (מחרוזת ריקה) במקום None כדי למנוע יצירת שם כמו "None None"
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""

        # מחברים אותם למחרוזת אחת, ומורידים רווחים מיותרים מהצדדים בעזרת strip()
        full_name = f"{make} {model}".strip()

        # אם קיבלנו שם תקין (ולא סתם מחרוזת ריקה), נוסיף לרשימה
        if full_name:
            all_devices.append(full_name)

    # משתמשים ב-Counter כדי לספור כמה תמונות צולמו בכל מכשיר
    device_counts = Counter(all_devices)
    unique_cameras = list(device_counts.keys())
    total_unique_cameras = len(unique_cameras)

    # --- חלק 3: מציאת טווח תאריכים (התחלה וסוף) ---

    # מכינים את מבנה התוצאה עם None כברירת מחדל
    date_range = {"start": None, "end": None}

    # מוציאים הצידה רק את התמונות שיש להן תאריך כדי לא לקרוס על תמונות חסרות
    dated_images = [img for img in images_data if img.get("datetime")]

    if dated_images:
        # ממיינים את התמונות לפי זמן מהישן לחדש
        sorted_dates = sorted(dated_images, key=lambda x: x["datetime"])

        # לוקחים את התמונה הראשונה [0]. התאריך נראה ככה: "08:30:00 2025-01-12".
        # פעולת split(" ") חותכת את הטקסט לפי הרווח, ו- [0] לוקח רק את החלק הראשון (התאריך בלי השעה).
        date_range["start"] = sorted_dates[0]["datetime"].split(" ")[0]

        # עושים את אותו הדבר לתמונה האחרונה ברשימה [-1] כדי למצוא את תאריך הסיום
        date_range["end"] = sorted_dates[-1]["datetime"].split(" ")[0]

    # --- חלק 4: מציאת טווח תאריכים לכל סוג מכשיר (השדרוג של צוות 2!) ---

    # 1. מילון עזר: המפתח יהיה שם המצלמה, והערך יהיה רשימה של כל התאריכים שבהם היא צילמה
    cam_data_map = {}

    # רצים רק על התמונות שיש לנו בהן תאריך תקין (אם אין תאריכים, הלולאה פשוט לא תרוץ)
    for img in dated_images:
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""
        full_name = f"{make} {model}".strip()

        if full_name:
            if full_name not in cam_data_map:
                cam_data_map[full_name] = {"dates": [], "cities": set()}

            # מוסיפים את תאריך הצילום ואת העיר
            cam_data_map[full_name]["dates"].append(img["datetime"])
            if img.get("city"):
                cam_data_map[full_name]["cities"].add(img["city"])

    # 2. מילון התוצאה הסופי: יחזיק רק את תאריך ההתחלה, הסיום, ורשימת הערים לכל מכשיר
    per_camera_range = {}

    for camera, data in cam_data_map.items():
        sorted_cam_dates = sorted(data["dates"])
        per_camera_range[camera] = {
            "first_picture": sorted_cam_dates[0].split(" ")[0],
            "last_picture": sorted_cam_dates[-1].split(" ")[0],
            "cities": list(data["cities"])
        }

    # --- חלק 5: ניתוח אזורים, מחוזות ו"אזורים חמים" דינמיים ---
    cities = [img['city'] for img in images_data if img.get('city')]
    districts = [img['district'] for img in images_data if img.get('district')]

    city_counts = Counter(cities)
    district_counts = Counter(districts)
    total_unique_cities = len(set(cities))

    def get_hottest_locations(counter_obj):
        if not counter_obj: return []
        max_count = max(counter_obj.values())
        return [loc for loc, count in counter_obj.items() if count == max_count]

    hottest_cities = get_hottest_locations(city_counts)
    hottest_districts = get_hottest_locations(district_counts)

    hot_zones = []
    total_located_images = len(cities)
    if total_located_images > 0:
        threshold = total_located_images * 0.15
        hot_zones = [city for city, count in city_counts.items() if count >= threshold]

    # --- חלק 6: יצירת התובנות (Insights) ---
    insights = []

    # תובנה על טווח השימוש של כל מכשיר
    for camera, range_info in per_camera_range.items():
        insights.append({
            "type": "usage_time",
            "text": f"זמן שימוש: המכשיר {camera} היה בשימוש מ-{range_info['first_picture']} עד {range_info['last_picture']}",
            "devices": [camera],
            "cities": range_info["cities"],
            "date": f"{range_info['first_picture']} ➔ {range_info['last_picture']}"
        })

    # מפעילים את הפונקציה שכתבנו למעלה כדי למצוא החלפות מדויקות
    switches = detect_camera_switches(images_data)
    insights.extend(switches)

    # הוספת פערי הזמן החריגים שזיהינו
    time_gaps = detect_time_gaps(images_data)
    insights.extend(time_gaps)

    # --- חלק 7: החזרת התוצאה לצוות 3 ---
    # מחזירים מילון שבנוי בדיוק לפי דרישות ה-API Contract, פלוס התוספות לדשבורד
    return {
        "total_images": total_images,
        "images_with_gps": images_with_gps,
        "images_with_datetime": images_with_datetime,
        "unique_cameras": list(unique_cameras),
        "total_unique_cameras": total_unique_cameras,
        "devices_distribution": dict(device_counts),
        "total_unique_cities": total_unique_cities,
        "date_range": date_range,
        "per_camera_range": per_camera_range,
        "insights": insights,
        "cities_distribution": dict(city_counts),
        "districts_distribution": dict(district_counts),
        "hottest_cities": hottest_cities,
        "hottest_districts": hottest_districts,
        "hot_zones": hot_zones
    }


if __name__ == "__main__":
    # --- אזור בדיקות ---
    # הבלוק הזה ירוץ רק אם נריץ את הקובץ הזה ישירות, ולא יפריע לשאר הפרויקט.
    dir_path = ""
    print(json.dumps(analyze(extract_all(dir_path)), indent=4, ensure_ascii=False))