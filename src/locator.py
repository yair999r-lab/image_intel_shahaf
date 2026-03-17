from geopy.geocoders import Nominatim
import time

cities_cache = {}
geolocator = Nominatim(user_agent="cyber_image_intel_app_yair")


def is_in_bbox(lat, lon, bbox):
    min_lat, max_lat, min_lon, max_lon = map(float, bbox)
    return (min_lat <= lat <= max_lat) and (min_lon <= lon <= max_lon)


def get_city_and_district(lat, lon):
    # שומר השער מבוסס None
    if lat is None or lon is None:
        return None, None

    # חיפוש מהיר בזיכרון המקומי
    for city_name, data in cities_cache.items():
        if is_in_bbox(lat, lon, data['bbox']):
            return city_name, data['district']

    # הליכה לאינטרנט
    try:
        time.sleep(1)

        # התוספת שלנו! הוספנו language='he' כדי לקבל תוצאות בעברית
        location = geolocator.reverse((lat, lon), exactly_one=True, language='he', zoom=10)

        if location and location.raw.get('address'):
            address = location.raw['address']

            # אם אין עיר, זה פשוט יחזיר None ולא מחרוזת

            district = address.get('state_district') or address.get('state') or "מחוז לא ידוע"
            city = address.get('city') or address.get('town') or address.get('village') or address.get(
                'county') or f"שטח פתוח ({district})"

            bbox = location.raw.get('boundingbox')

            # שומרים בזיכרון רק אם באמת מצאנו שם של עיר
            if city and bbox:
                cities_cache[city] = {
                    "bbox": bbox,
                    "district": district
                }
                print(f"[📍 למידת מכונה] נוסף לזיכרון: {city} (מחוז {district})")

            return city, district

    except Exception as e:
        print(f"שגיאת תקשורת עם שרת המפות: {e}")
        return None, None

    # אם הכל כשל, נחזיר None כמו שביקשת
    return None, None