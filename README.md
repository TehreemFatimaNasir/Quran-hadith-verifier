# 📖 Quran & Hadith Verifier

> *An AI-powered Chrome Extension that extracts Islamic text from images and verifies it from Quran and Hadith sources.*

The *Quran & Hadith Verifier* is a web-based Chrome Extension designed to help users verify Quranic verses and Hadith from images.

Instead of manually typing Arabic text and searching for its source, users can simply *capture a photo or upload an image. The application uses **OCR (Optical Character Recognition)* to extract the text and then verify

---

## ✨ Features

### 📷 Image Capture
Capture Quranic verses or Hadith directly using the device camera.

### 🖼️ Image Upload
Upload an existing image containing Quranic or Hadith text.

### 🔍 Arabic OCR
Uses *EasyOCR* to recognize Arabic text from images.

### 📖 Quran Verification
Extracted Quranic text is checked against the *QuranCloud API*.

### 📚 Hadith Verification
Hadith text is checked against trusted Hadith collections through the *Hadith API*.

### ⚡ FastAPI Backend
A Python FastAPI backend processes uploaded images, performs OCR, and handles verification.

### 🌐 Chrome Extension
The project is packaged as a *Manifest V3 Chrome Extension* with a simple and user-friendly interface.

---
## 🛠️ Technologies

- Python
- FastAPI
- EasyOCR
- HTML
- CSS
- JavaScript
- Chrome Extension Manifest V3
- QuranCloud API
- Hadith API
  
## 🚀 How to Run

### ⚙️ Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload


🌐Backend: http://127.0.0.1:8000

🧩 Chrome Extension

🌐 Open Google Chrome

🔧 Go to chrome://extensions/

🛠️ Enable Developer mode

📂 Click Load unpacked


📁 Select the extension folder
▶️ Open the extension

📷 Upload an image or capture one using the camera

✅ Click Verify Image


https://github.com/user-attachments/assets/2b090627-ae3a-4e19-8961-ba313236ec8f

