from PIL import Image
from PIL.ExifTags import TAGS
from pathlib import Path
import os
from locator import get_city_and_district  # *** תוספת: ייבוא המנוע הגיאוגרפי החדש שלנו ***

"""
extractor.py - שליפת EXIF מתמונות
צוות 1, זוג A

ראו docs/api_contract.md לפורמט המדויק של הפלט.

"""
# === התוספת הקריטית לאייפונים! ===
# אנחנו מנסים לטעון את התוסף שמאפשר קריאת קבצי HEIC
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("Warning: pillow-heif is not installed. iPhone HEIC images will fail.")
# ================================

def has_gps(data: dict):
    return 'GPSInfo' in data


def latitude(data: dict):
    if 'GPSInfo' in data and data['GPSInfo']:
        # קו רוחב תמיד יושב על מפתחות 1 (Ref) ו-2 (Data)
        if 1 in data['GPSInfo'] and 2 in data['GPSInfo']:
            lat = data['GPSInfo'][2]
            decimal_lat = float(lat[0]) + (float(lat[1]) / 60) + (float(lat[2]) / 3600)

            # בדיקה רגילה: צפון
            if data['GPSInfo'][1] == 'N':
                return decimal_lat
            # הפולבק: דרום (באותם מפתחות בדיוק)
            elif data['GPSInfo'][1] == 'S':
                return -decimal_lat

            # מקרה קצה (אם חסרה האות אבל יש נתונים)
            return decimal_lat

    return None


def longitude(data: dict):
    if 'GPSInfo' in data and data['GPSInfo']:
        # קו אורך תמיד יושב על מפתחות 3 (Ref) ו-4 (Data)
        if 3 in data['GPSInfo'] and 4 in data['GPSInfo']:
            lon = data['GPSInfo'][4]
            decimal_lon = float(lon[0]) + (float(lon[1]) / 60) + (float(lon[2]) / 3600)

            # בדיקה רגילה: מזרח
            if data['GPSInfo'][3] == 'E':
                return decimal_lon
            # הפולבק: מערב (באותם מפתחות בדיוק)
            elif data['GPSInfo'][3] == 'W':
                return -decimal_lon

            # מקרה קצה
            return decimal_lon

    return None
'''
הוספת לוגיקה לחישוב קו אורך עשרוני
'''

def datatime(data: dict):
    aw_date = None

    # מנסים למצוא את התאריך באחד מהשדות האפשריים
    if "DateTimeOriginal" in data:
        raw_date = data["DateTimeOriginal"]
    elif "DateTimeDigitized" in data:
        raw_date = data["DateTimeDigitized"]
    elif "DateTime" in data:
        raw_date = data["DateTime"]

    if raw_date:
        # הופכים למחרוזת ומנקים רווחים מיותרים
        clean_date = str(raw_date).strip()

        # מתקנים תאריכים שמגיעים עם מקפים, נקודות או האות T לאותה תבנית סטנדרטית
        # דוגמה: "2024-03-17T14-00-00" יהפוך ל- "2024:03:17 14:00:00"
        clean_date = clean_date.replace("-", ":").replace(".", ":").replace("T", " ")

        # יש מצלמות ששומרות "2024:03:17" בלי שעה. נוסיף להן שעת אפס כדי שהקוד לא יקרוס
        if len(clean_date) <= 10:
            clean_date += " 00:00:00"

        return clean_date

    return None
'''
הוספת פונקציה לשליפת זמן יצירת התמונה
'''


def camera_make(data: dict):
    if "Make" in data:
        return data["Make"].strip("\x00")


def camera_model(data: dict):
    if "Model" in data:
        return data["Model"].strip("\x00")
'''
שני הפונקציות האחרונות אחראיים לשליפת יצרן ודגם המצלמה
'''

def extract_metadata(image_path):
    """
    שולף EXIF מתמונה בודדת.

    Args:
        image_path: נתיב לקובץ תמונה

    Returns:
        dict עם: filename, datetime, latitude, longitude,
              city, district, camera_make, camera_model, has_gps
    """
    path = Path(image_path)

    # תיקון: טיפול בתמונה בלי EXIF - בלי זה, exif.items() נופל עם AttributeError
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
    except Exception:
        exif = None

    if exif is None:
        return {
            "filename": path.name,
            "datetime": None,
            "latitude": None,
            "longitude": None,
            "city": None,          # *** תוספת: מקרה קצה לתמונה בלי נתונים ***
            "district": None,      # *** תוספת: מקרה קצה לתמונה בלי נתונים ***
            "camera_make": None,
            "camera_model": None,
            "has_gps": False
        }

    data = {}
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        data[tag] = value

    # *** תוספת: חילוץ נתוני ה-GPS למשתנים, ושליחתם למנוע הגיאוגרפי לקבלת עיר ומחוז ***
    lat = latitude(data)
    lon = longitude(data)
    city, district = get_city_and_district(lat, lon)

    exif_dict = {
        "filename": path.name,
        "datetime": datatime(data),
        "latitude": lat,
        "longitude": lon,
        "city": city,              # *** תוספת: הכנסת העיר למילון הסופי ***
        "district": district,      # *** תוספת: הכנסת המחוז למילון הסופי ***
        "camera_make": camera_make(data),
        "camera_model": camera_model(data),
        "has_gps": has_gps(data)
    }
    return exif_dict


def extract_all(folder_path):
    """
    שולף EXIF מכל התמונות בתיקייה.

    Args:
        folder_path: נתיב לתיקייה

    Returns:
        list של dicts (כמו extract_metadata)
    """
    results = []
    dir_path = Path(folder_path)

    if not dir_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory.")
        return results

    # שימוש ב-rglob('*') כדי לסרוק גם תתי-תיקיות בצורה ריקורסיבית
    for file_path in dir_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.heic', '.heif']:
            metadata = extract_metadata(str(file_path))
            results.append(metadata)

    return results

'''
ביצוע סריקה לתיקיית תמונות
'''

#=========================================================================================#

'''
הוספת הדפסה סופית להדפסה כולל עיצוב שורות
'''
#Example = extract_all("C:/Intel/pycharm/pythonProject12/images")
#print(*Example, sep='\n')