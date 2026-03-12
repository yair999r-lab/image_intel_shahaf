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