📖 Quran & Hadith Verifier

An AI-powered Chrome Extension that reads Arabic text from an image and finds its exact source in the Quran and the major Hadith collections — with Urdu and English translation.

The Quran & Hadith Verifier helps you identify Quranic verses and Hadith that appear in images, screenshots and posters. Instead of typing Arabic text by hand and searching for it, simply capture a photo or upload an image. The app uses OCR (Optical Character Recognition) to read the text, searches the Quran and six Hadith collections, and shows the matching reference together with its translation.


✨ Features

📷 Image Capture

Take a photo of a Quranic verse or Hadith directly with your laptop webcam or phone camera.

🖼️ Image Upload

Choose an image from your device, or simply drag and drop it into the extension.

🔍 Arabic OCR

Uses EasyOCR (Arabic + English) to read text from the image, and tries several enhanced versions of the picture (enlarged, higher contrast, sharpened) to get the best result.

📖 Quran Verification

The extracted text is matched against the full Quran (Uthmani script) using the QuranCloud API, and the result shows the Surah name and Ayah number.

📚 Hadith Verification

The text is searched across six major Hadith collections:

Collection

Sahih al-Bukhari	

Sunan Abu Dawud

Sahih Muslim	

Jami at-Tirmidhi

Sunan Ibn Majah

Sunan an-Nasa'i

The result shows the book name and Hadith number. Matching tolerates common OCR mistakes such as merged or split words, and it works even when only part of a Hadith is in the image.

🌍 Urdu & English Translation

Every result includes a one-tap switch between اردو and English translation.


⚡ FastAPI Backend

A Python FastAPI backend receives the image, runs OCR, and performs the Quran and Hadith search.

🧩 Chrome Extension

Packaged as a Manifest V3 Chrome Extension with a simple, user-friendly popup.

🛠️ Technologies
Backend: Python, FastAPI, Uvicorn
OCR: EasyOCR, Pillow, NumPy
Data sources: QuranCloud API, Hadith API
Frontend: HTML, CSS, JavaScript
Platform: Chrome Extension (Manifest V3)

🙏 Acknowledgements

QuranCloud for the Quran text and translations

fawazahmed0/hadith-api for the Hadith collections and translations

EasyOCR for text recognition

🎬 Demo


https://github.com/user-attachments/assets/e3df06af-ed4b-4601-9ced-3e3d6e680081

