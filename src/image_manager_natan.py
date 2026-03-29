import os
import hashlib
import cloudinary
import cloudinary.uploader
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# טעינת משתני הסביבה מהקובץ .env
load_dotenv()

# הגדרת החיבור ל-Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# הגדרת תיקייה זמנית (Temp)
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def generate_image_hash(file_path):
    """
    מייצר 'טביעת אצבע' (Hash) ייחודית לתמונה באמצעות אלגוריתם SHA-256.
    קריטי למניעת כפילויות.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # קריאת הקובץ במנות קטנות (Chunks) למקרה שמדובר בקובץ גדול מאוד
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def process_and_upload_image(file_object):
    """
    מנהל את התהליך המלא: שמירה זמנית, יצירת Hash, העלאה לענן ומחיקה.
    מחזיר מילון עם נתוני התמונה או שגיאה.
    """
    if not file_object or file_object.filename == '':
        return {"error": "לא נבחר קובץ"}

    # 1. אבטחת שם הקובץ ויצירת נתיב זמני
    filename = secure_filename(file_object.filename)
    temp_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        # 2. שמירת הקובץ באופן זמני (התפוח הלוהט)
        file_object.save(temp_path)

        # 3. יצירת טביעת אצבע (Hash)
        image_hash = generate_image_hash(temp_path)

        # --- כאן תיכנס הלוגיקה של יאיר: בדיקה האם ה-Hash כבר קיים במסד הנתונים ---
        # (כרגע נניח שהוא לא קיים ונמשיך)
        # if yair_check_hash_exists(image_hash):
        #    os.remove(temp_path)
        #    return {"error": "התמונה כבר קיימת במערכת", "hash": image_hash}

        # --- כאן יתבצע חילוץ נתוני ה-GPS וה-EXIF מהקובץ הזמני ---
        # exif_data = extract_exif(temp_path)

        # 4. העלאה ל-Cloudinary
        # הוספנו את angle="auto" כדי ש-Cloudinary תסובב את התמונה אוטומטית לפי ה-EXIF!
        upload_result = cloudinary.uploader.upload(temp_path, angle="exif")

        # 5. חילוץ ה-URL המאובטח מהתשובה של Cloudinary
        secure_url = upload_result.get('secure_url')

        # 6. מחיקת הקובץ הזמני ("ניקוי השרת")
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return {
            "success": True,
            "hash": image_hash,
            "url": secure_url,
            # "exif": exif_data # (יוחזר במידה וחילצתם)
        }

    except Exception as e:
        # במקרה של שגיאה, מוודאים שהקובץ הזמני נמחק כדי לא לסתום את השרת
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return {"error": str(e)}

# דוגמה לשימוש (החלק שישולב בראוט של העלאת הקבצים ב-app.py)
# if 'image' in request.files:
#     result = process_and_upload_image(request.files['image'])
#     if result.get("success"):
#         # העבר את result['hash'] ואת result['url'] ליאיר (למסד הנתונים) ולנהוראי (ל-AI)
#         print(f"Uploaded! URL: {result['url']}, Hash: {result['hash']}")