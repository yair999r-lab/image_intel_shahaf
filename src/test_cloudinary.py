import os
from werkzeug.datastructures import FileStorage
from image_manager_natan import process_and_upload_image


def run_test():
    # שים לב: ודא שיש לך תמונה אמיתית בשם test.jpg באותה תיקייה של הפרויקט
    image_path = "test.jpg"

    if not os.path.exists(image_path):
        print(f"❌ שגיאה: לא מצאתי קובץ בשם '{image_path}'.")
        print("אנא העתק תמונה כלשהי לתיקיית הפרויקט, קרא לה 'test.jpg' והרץ שוב.")
        return

    print("🚀 מתחיל העלאה לענן של נתן, תחזיק אצבעות...")

    # פותחים את התמונה ומדמים את האובייקט ש-Flask מייצר כשמעלים קובץ מאתר
    with open(image_path, "rb") as f:
        file_storage = FileStorage(f, filename="test.jpg")

        # שולחים לפונקציה שלך!
        result = process_and_upload_image(file_storage)

    print("\n--- 📊 תוצאות הבדיקה ---")
    if result.get('success'):
        print("✅ הכל עובד מושלם! ה-API מחובר.")
        print(f"🔑 טביעת אצבע (Hash) שנוצרה: {result['hash']}")
        print(f"🔗 לינק מאובטח בענן: {result['url']}")
        print("\n👉 תעתיק את הלינק הזה, תדביק בדפדפן, ותראה את התמונה שלך יושבת בשרתי Cloudinary!")
    else:
        print("❌ משהו השתבש בהעלאה:")
        print(result)


if __name__ == "__main__":
    run_test()