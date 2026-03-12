"""
analyzer.py - מציאת דפוסים ותובנות
צוות 2, זוג B
"""
import json
from datetime import datetime
from extractor import extract_all
def detect_camera_switches(images_data):
    """
    פונקציית עזר: מזהה מתי הסוכן החליף מכשיר בין צילום לצילום.
    מקבלת: את כל רשימת התמונות.
    מחזירה: רשימה של מילונים, שכל אחד מהם מתאר "החלפה" שהתרחשה.
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
            # אם מצאנו החלפה, מוסיפים מילון עם הפרטים לרשימת התוצאות
            switches.append({
                "date": sorted_images[i]["datetime"],  # מתי קרתה ההחלפה
                "from": prev_cam,  # מאיזה מכשיר
                "to": curr_cam  # לאיזה מכשיר
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
        prev_str = sorted_images[i-1]["datetime"]
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
            gaps.append(f"פער זמן חריג: זוהה נתק של {int(diff_hours)} שעות לפני הצילום ב-{date_only} במכשיר {full_name}")
    return gaps

def analyze(images_data):
    """
    הפונקציה המרכזית (ה"מוח"): מנתחת את הנתונים ומחזירה את הדו"ח הסופי.
    """

    # --- חלק 1: חישוב סטטיסטיקות בסיסיות ---

    # בודקים כמה תמונות יש בסך הכל ברשימה שקיבלנו
    total_images = len(images_data)

    # סופרים כמה תמונות מכילות GPS (כלומר, המפתח 'has_gps' הוא True)
    # משתמשים ב-sum כדי לסכום 1 על כל פעם שהתנאי מתקיים.
    images_with_gps = sum(1 for img in images_data if img.get("has_gps"))

    # סופרים כמה תמונות מכילות תאריך (datetime קיים ולא ריק)
    images_with_datetime = sum(1 for img in images_data if img.get("datetime"))

    # --- חלק 2: מציאת מצלמות ייחודיות ---

    # משתמשים ב-set (קבוצה) כי הוא לא מאפשר כפילויות.
    unique_cameras = set()

    for img in images_data:
        # משתמשים ב- "" (מחרוזת ריקה) במקום None כדי למנוע יצירת שם כמו "None None"
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""

        # מחברים אותם למחרוזת אחת, ומורידים רווחים מיותרים מהצדדים בעזרת strip()
        full_name = f"{make} {model}".strip()

        # אם קיבלנו שם תקין (ולא סתם מחרוזת ריקה), נוסיף לקבוצה
        if full_name:
            unique_cameras.add(full_name)

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
    cam_dates_map = {}

    # רצים רק על התמונות שיש לנו בהן תאריך תקין (אם אין תאריכים, הלולאה פשוט לא תרוץ)
    for img in dated_images:
        # חולצים את שם המכשיר, ומשתמשים ב-"" במקום None כדי למנוע קריסות
        make = img.get("camera_make") or ""
        model = img.get("camera_model") or ""
        full_name = f"{make} {model}".strip()

        # מוודאים שבאמת יש לנו שם של מכשיר ביד
        if full_name:
            # אם זו פעם ראשונה שאנחנו נתקלים במכשיר הזה - נפתח לו רשימה ריקה במילון
            if full_name not in cam_dates_map:
                cam_dates_map[full_name] = []

            # מוסיפים את תאריך הצילום הספציפי הזה לרשימה של המכשיר
            cam_dates_map[full_name].append(img["datetime"])

    # 2. מילון התוצאה הסופי: יחזיק רק את תאריך ההתחלה ותאריך הסיום לכל מכשיר
    per_camera_range = {}

    # הלולאה הזו עוברת על מילון העזר שיצרנו.
    # camera = שם המכשיר, dates = רשימת כל התאריכים שלו
    for camera, dates in cam_dates_map.items():
        # ממיינים את התאריכים של המכשיר הספציפי הזה מהישן לחדש
        sorted_cam_dates = sorted(dates)

        # מכניסים למילון הסופי את התאריך הראשון (אינדקס 0) והאחרון (אינדקס 1-)
        per_camera_range[camera] = {
            # פעולת ה-split(" ") חותכת את הרווח שמפריד בין התאריך לשעה
            # ה-[0] בסוף לוקח רק את החצי הראשון (התאריך עצמו) וזורק את השעה
            "first_picture": sorted_cam_dates[0].split(" ")[0],
            "last_picture": sorted_cam_dates[-1].split(" ")[0]
        }
# --- חלק 5: יצירת התובנות (Insights) ---

    insights = []

    # תובנה על טווח השימוש של כל מכשיר
    for camera, range_info in per_camera_range.items():
        msg = f"המכשיר {camera} היה בשימוש מ-{range_info['first_picture']} עד {range_info['last_picture']}"
        insights.append(msg)

    # תובנה 1: אם ראינו יותר ממצלמה אחת, נתריע על זה
    if len(unique_cameras) > 1:
        insights.append(f"נמצאו {len(unique_cameras)} מכשירים שונים - ייתכן שהסוכן החליף מכשירים במכוון")

    # תובנה 2: מפעילים את הפונקציה שכתבנו למעלה כדי למצוא החלפות מדויקות
    switches = detect_camera_switches(images_data)
    for switch in switches:
        # לוקחים רק את התאריך מהזמן המדויק
        date_only = switch["date"].split(" ")[0]
        # מוסיפים את המשפט לרשימת התובנות
        insights.append(f"ב-{date_only} הסוכן עבר ממכשיר {switch['from']} ל-{switch['to']}")

    # תובנה 3: הוספת פערי הזמן החריגים שזיהינו
    time_gaps = detect_time_gaps(images_data)
    insights.extend(time_gaps) # extend שופך את כל הרשימה לתוך התובנות

    # --- חלק 6: החזרת התוצאה לצוות 3 ---

    # מחזירים מילון שבנוי בדיוק לפי דרישות ה-API Contract, פלוס התוספת שלך.
    # שים לב שהפכנו את קבוצת המצלמות (set) בחזרה לרשימה רגילה (list) כי ככה דרשו.
    return {
        "total_images": total_images,
        "images_with_gps": images_with_gps,
        "images_with_datetime": images_with_datetime,
        "unique_cameras": list(unique_cameras),
        "date_range": date_range,
        "per_camera_range": per_camera_range,
        "insights": insights
    }

if __name__ == "__main__":
    # --- אזור בדיקות ---
    # הבלוק הזה ירוץ רק אם נריץ את הקובץ הזה ישירות, ולא יפריע לשאר הפרויקט.
    # זה מאפשר לנו לבדוק את הקוד שלנו עם נתונים מזויפים לפני שאנחנו מחברים הכל.

    dir_path = ""
    # מדפיס את המילון שיצרנו בצורה יפה ומסודרת לטרמינל כדי שנוכל לקרוא אותו
    print(json.dumps(analyze(extract_all(dir_path)), indent=4, ensure_ascii=False))