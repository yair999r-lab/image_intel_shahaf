from PIL import Image
from PIL.ExifTags import TAGS
from pathlib import Path
import os
import random
from datetime import datetime
from locator import get_city_and_district

"""
extractor.py - שליפת EXIF מתמונות
צוות 1, זוג A
"""

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    print("Warning: pillow-heif is not installed. iPhone HEIC images will fail.")


def has_gps(data: dict):
    return 'GPSInfo' in data


def latitude(data: dict):
    if 'GPSInfo' in data and data['GPSInfo']:
        if 1 in data['GPSInfo'] and 2 in data['GPSInfo']:
            lat = data['GPSInfo'][2]
            decimal_lat = float(lat[0]) + (float(lat[1]) / 60) + (float(lat[2]) / 3600)

            if data['GPSInfo'][1] == 'N':
                return decimal_lat
            elif data['GPSInfo'][1] == 'S':
                return -decimal_lat
            return decimal_lat
    return None


def longitude(data: dict):
    if 'GPSInfo' in data and data['GPSInfo']:
        if 3 in data['GPSInfo'] and 4 in data['GPSInfo']:
            lon = data['GPSInfo'][4]
            decimal_lon = float(lon[0]) + (float(lon[1]) / 60) + (float(lon[2]) / 3600)

            if data['GPSInfo'][3] == 'E':
                return decimal_lon
            elif data['GPSInfo'][3] == 'W':
                return -decimal_lon
            return decimal_lon
    return None


def datatime(data: dict):
    raw_date = None
    if "DateTimeOriginal" in data:
        raw_date = data["DateTimeOriginal"]
    elif "DateTimeDigitized" in data:
        raw_date = data["DateTimeDigitized"]
    elif "DateTime" in data:
        raw_date = data["DateTime"]

    if raw_date:
        clean_date = str(raw_date).strip()
        clean_date = clean_date.replace("-", ":").replace(".", ":").replace("T", " ")
        if len(clean_date) <= 10:
            clean_date += " 00:00:00"
        return clean_date
    return None


def camera_make(data: dict):
    if "Make" in data:
        return data["Make"].strip("\x00")


def camera_model(data: dict):
    if "Model" in data:
        return data["Model"].strip("\x00")


def extract_metadata(image_path):
    path = Path(image_path)

    try:
        file_size_kb = round(os.path.getsize(image_path) / 1024, 2)
        file_mtime = os.path.getmtime(image_path)
        modified_date = datetime.fromtimestamp(file_mtime).strftime("%Y:%m:%d %H:%M:%S")
    except Exception:
        file_size_kb = 0.0
        modified_date = None

    file_ext = path.suffix.lower()
    ai_score = random.randint(1, 100)

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
            "city": None,
            "district": None,
            "camera_make": None,
            "camera_model": None,
            "has_gps": False,
            "size_kb": file_size_kb,
            "ai_score": ai_score,
            "file_ext": file_ext,
            "modified_date": modified_date
        }

    data = {}
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        data[tag] = value

    lat = latitude(data)
    lon = longitude(data)

    if lat is not None and lon is not None:
        city, district = get_city_and_district(round(lat, 3), round(lon, 3))
    else:
        city, district = get_city_and_district(lat, lon)

    exif_dict = {
        "filename": path.name,
        "datetime": datatime(data) or modified_date,
        "latitude": lat,
        "longitude": lon,
        "city": city,
        "district": district,
        "camera_make": camera_make(data),
        "camera_model": camera_model(data),
        "has_gps": has_gps(data),
        "size_kb": file_size_kb,
        "ai_score": ai_score,
        "file_ext": file_ext,
        "modified_date": modified_date
    }
    return exif_dict


def extract_all(folder_path):
    results = []
    dir_path = Path(folder_path)

    if not dir_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory.")
        return results

    for file_path in dir_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.heic', '.heif']:
            metadata = extract_metadata(str(file_path))
            results.append(metadata)

    return results