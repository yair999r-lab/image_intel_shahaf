"""
analyzer.py - מציאת דפוסים ותובנות
צוות 2, זוג B
"""
import json
from datetime import datetime
from extractor import extract_all
from collections import Counter


def detect_camera_switches(images_data):
    """
    פונקציית עזר: מזהה מתי הסוכן החליף מכשיר בין צילום לצילום.
    מקבלת: את כל רשימת התמונות.
    ** שינוי: מחזירה רשימה של אובייקטי-תובנה (מילונים עם תגיות) **
    """
    sorted_images = sorted(
        [img for img in images_data if img.get("datetime")],
        key=lambda x: x["datetime"]
    )

    switches = []

    for i in range(1, len(sorted_images)):
        prev_cam = sorted_images[i - 1].get("camera_model")
        curr_cam = sorted_images[i].get("camera_model")

        if prev_cam and curr_cam and prev_cam != curr_cam:
            date_only = sorted_images[i]["datetime"].split(" ")[0]
            # ** תוספת: שולפים את העיר שבה קרתה ההחלפה (העיר של התמונה החדשה) **
            curr_city = sorted_images[i].get("city")

            # ** תוספת: יצירת חבילת המידע העשירה במקום סתם טקסט **
            switches.append({
                "type": "device_switch",
                "text": f"החלפת מכשיר: ב-{date_only} הסוכן עבר ממכשיר {prev_cam} ל-{curr_cam}",
                "devices": [prev_cam, curr_cam],  # תגיות של שני המכשירים המעורבים
                "cities": [curr_city] if curr_city else []  # תגית של העיר בה צץ המכשיר החדש
            })

    return switches


def detect_time_gaps(images_data):
    """
    פונקציית עזר: מחפשת קפיצות זמן חריגות (מעל 12 שעות) בין צילומים.
    ** שינוי: מחזירה רשימה של אובייקטי-תובנה (מילונים עם תגיות) **
    """
    sorted_images = sorted(
        [img for img in images_data if img.get("datetime")],
        key=lambda x: x["datetime"]
    )

    gaps = []

    for i in range(1, len(sorted_images)):
        prev_str = sorted_images[i - 1]["datetime"]
        curr_str = sorted_images[i]["datetime"]

        prev_time = datetime.strptime(prev_str, "%Y:%m:%d %H:%M:%S")
        curr_time = datetime.strptime(curr_str, "%Y:%m:%d %H:%M:%S")

        diff_hours = (curr_time - prev_time).total_seconds() / 3600
        make = sorted_images[i].get("camera_make") or ""
        model = sorted_images[i].get("camera_model") or ""
        full_name = f"{make} {model}".strip() or "מכשיר לא ידוע"

        if diff_hours > 12:
            date_only = curr_str.split(" ")[0]
            # ** תוספת: שולפים את העיר שבה הסוכן הופיע מחדש לאחר הנתק **
            curr_city = sorted_images[i].get("city")

            # ** תוספת: יצירת חבילת המידע העשירה **
            gaps.append({
                "type": "time_gap",
                "text": f"פער בין תמונות: זוהה נתק של {int(diff_hours)} שעות לפני הצילום ב-{date_only} במכשיר {full_name}",
                "devices": [full_name],
                "cities": [curr_city] if curr_city else []
            })

    return gaps


def analyze(images_data):
    """
    הפונקציה המרכזית (ה"מוח"): מנתחת את הנתונים ומחזירה את הדו"ח הסופי.
    """

    # --- חלק 1: חישוב סטטיסטיקות בסיסיות ---
    total_images = len(images_data)
    images_with_gps = sum(1 for img in images_data if img.get("latitude") and img.get("longitude"))
    images_with_datetime = sum(1 for img in images_data if img.get("datetime"))

    # --- חלק 2: מציאת מצלמות ייחודיות ---
    unique_cameras = set()
    for img in images_data:
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""
        full_name = f"{make} {model}".strip()
        if full_name:
            unique_cameras.add(full_name)

    # --- חלק 3: מציאת טווח תאריכים (התחלה וסוף) ---
    date_range = {"start": None, "end": None}
    dated_images = [img for img in images_data if img.get("datetime")]

    if dated_images:
        sorted_dates = sorted(dated_images, key=lambda x: x["datetime"])
        date_range["start"] = sorted_dates[0]["datetime"].split(" ")[0]
        date_range["end"] = sorted_dates[-1]["datetime"].split(" ")[0]

    # --- חלק 4: מציאת טווח תאריכים וערי ביקור לכל סוג מכשיר ---

    # ** שינוי: המילון עכשיו שומר גם תאריכים וגם את הערים (ב-set כדי למנוע כפילויות) **
    cam_data_map = {}

    for img in dated_images:
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""
        full_name = f"{make} {model}".strip()

        if full_name:
            if full_name not in cam_data_map:
                # ** פותחים רשימת תאריכים וסט לערים **
                cam_data_map[full_name] = {"dates": [], "cities": set()}

            cam_data_map[full_name]["dates"].append(img["datetime"])
            # ** מוסיפים את העיר לסט של המכשיר הזה (אם קיימת עיר) **
            if img.get("city"):
                cam_data_map[full_name]["cities"].add(img["city"])

    per_camera_range = {}

    for camera, data in cam_data_map.items():
        sorted_cam_dates = sorted(data["dates"])
        per_camera_range[camera] = {
            "first_picture": sorted_cam_dates[0].split(" ")[0],
            "last_picture": sorted_cam_dates[-1].split(" ")[0],
            # ** תוספת: הופכים את הסט של הערים חזרה לרשימה רגילה ושומרים **
            "cities": list(data["cities"])
        }

    # --- חלק 5: ניתוח אזורים, מחוזות ו"אזורים חמים" דינמיים ---
    cities = [img['city'] for img in images_data if img.get('city')]
    districts = [img['district'] for img in images_data if img.get('district')]

    # ** התוספת שלך: חישוב כמות הערים הייחודיות (set מסנן כפילויות) **
    total_unique_cities = len(set(cities))

    city_counts = Counter(cities)
    district_counts = Counter(districts)

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

    # --- חלק 6: יצירת התובנות (Insights) כאובייקטים חכמים ---
    insights = []

    for camera, range_info in per_camera_range.items():
        # ** שינוי: יצירת אובייקט חכם עם תגיות המכשיר וכל הערים בהן הוא ביקר **
        insights.append({
            "type": "usage_time",
            "text": f"זמן שימוש: המכשיר {camera} היה בשימוש מ-{range_info['first_picture']} עד {range_info['last_picture']}",
            "devices": [camera],
            "cities": range_info["cities"]
        })

    if len(unique_cameras) > 1:
        # ** שינוי: יצירת אובייקט חכם עם תגיות של כל המכשירים וכל הערים שנמצאו **
        all_cities = list(set([img.get("city") for img in images_data if img.get("city")]))
        insights.append({
            "type": "multiple_devices",
            "text": f"החלפת מכשיר: נמצאו {len(unique_cameras)} מכשירים שונים - ייתכן שהסוכן החליף מכשירים במכוון",
            "devices": list(unique_cameras),
            "cities": all_cities
        })

    # ** שינוי: הפונקציות האלה כבר מחזירות רשימות של אובייקטים, אז פשוט נשפוך אותן פנימה **
    switches = detect_camera_switches(images_data)
    insights.extend(switches)

    time_gaps = detect_time_gaps(images_data)
    insights.extend(time_gaps)

    # --- חלק 7: החזרת התוצאה לדשבורד ---
    return {
        "total_images": total_images,
        "images_with_gps": images_with_gps,
        "images_with_datetime": images_with_datetime,
        "unique_cameras": list(unique_cameras),
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
    dir_path = "C:\\Intel\\pycharm\\pythonProject12\\"
    print(json.dumps(analyze(extract_all(dir_path)), indent=4, ensure_ascii=False))