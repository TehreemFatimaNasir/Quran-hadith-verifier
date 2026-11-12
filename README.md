# Quran-hadith-verifier

# 📖 Quran & Hadith Verifier

> *A Chrome Extension that finds the exact source of Arabic and Urdu text — from an image, or from text you highlight on any webpage — and shows the reference with Urdu and English translation.*

Quran & Hadith Verifier helps you identify verses of the **Quran** and narrations from the **six major Hadith collections**. Upload or capture a picture, or simply **highlight text on any website**. The extension reads the text, searches the sources and shows the **Surah / Ayah** or the **Hadith book and number**, together with its translation.

---


---

## ✨ Features

### 🖱️ Select & Search on Any Webpage
Turn on **Select & Search** in the popup, then **highlight Arabic or Urdu text on any website**. A small card appears next to your selection with the matching verse or Hadith, its reference and the translation — no screenshot needed.

- **Search in:** choose **Auto**, **Quran** or **Hadith** to tell the extension where to look.
- **Verify against a reference (optional):** type a pointer such as `67:15`, `Bukhari 2731` or `Muslim 1600b`. After you highlight text, the card tells you whether the text really belongs to that reference — **✓ Verified** or **✗ Does not match**.

### 📷 Image Capture & Upload
Take a photo with your webcam or phone camera, upload an image, or **drag and drop** it into the popup.

### 🔍 Arabic & Urdu OCR
Uses **EasyOCR** to read the text. Several enhanced versions of the picture (enlarged, higher contrast, sharpened) are tried to get the best result. The Urdu reader is loaded only when it is needed.

### 📖 Quran Verification
Text is matched against the full Quran (Uthmani script) from the **QuranCloud API**. The result shows the **Surah name and Ayah number**.

### 📚 Hadith Verification
Text is searched across six collections:

| Collection | Collection |
|---|---|
| Sahih al-Bukhari | Sunan Abu Dawud |
| Sahih Muslim | Jami at-Tirmidhi |
| Sunan Ibn Majah | Sunan an-Nasa'i |

Matching tolerates common OCR mistakes and merged or split words, and works even when only part of a Hadith is selected. Numbers follow the style used on websites such as Sunnah.com (for example Sahih Muslim **1511a**).

###  Search from Urdu Text
If the image or selected text is an **Urdu translation**, the extension searches Urdu translations of the Quran and the Hadith collections and returns the matching Arabic text with its reference.

### 🌍 Urdu & English Translation
Every result has a one-tap switch between **اردو** and **English**.

### 🎯 Highlighted Reference
The source (for example *Surah Al-Mulk* or *Sahih Bukhari*) and its **Ayah / Hadith number** are highlighted in a Reference card directly under the matched text, so the result is clear at a glance.

### 🎨 Clean, Modern Interface
- Elegant **denim** colour theme with its own toolbar icon
- Smooth scan animation with a step-by-step progress indicator
- Arabic typography (Amiri) and Urdu Nastaliq
- Long Hadith texts are collapsed with a **Read full text** option
- Follows your device's **light / dark mode**




                                             


1. **Input** — an image goes through OCR; selected webpage text is sent directly.
2. **Normalise** — diacritics and letter variants are removed so small differences do not matter.
3. **Search** — the text is compared with the Quran and the Hadith index; if nothing is found in Arabic, the Urdu translation index is tried.
4. **Verify** — if a reference was typed, the text is compared with exactly that Ayah or Hadith.
5. **Show** — the popup or the page card displays the source, number and translation.



## 🛠️ Technologies

- **Backend:** Python, FastAPI, Uvicorn
- **OCR:** EasyOCR, Pillow, NumPy
- **Data sources:** [QuranCloud API](https://alquran.cloud/api), [Hadith API](https://github.com/fawazahmed0/hadith-api)
- **Frontend:** HTML, CSS, JavaScript
- **Platform:** Chrome Extension (Manifest V3: popup, content script, service worker)






### 🧩 2. Chrome Extension

1. Open **Google Chrome** and go to `chrome://extensions/`
2. Turn on **Developer mode**
3. Click **Load unpacked** and select the `extension` folder
4. Click the puzzle-piece button and **pin** the extension
5. Keep the backend running while you use it

### 🖱️ 3. Use Select & Search

1. Open the popup and turn on **Select & Search**
2. Choose **Auto**, **Quran** or **Hadith**, and optionally type a reference
3. Open any webpage (reload tabs that were already open) and **highlight Arabic or Urdu text**
4. The result card appears next to your selection. Press `Esc` to close it






## 🙏 Acknowledgements

- [QuranCloud](https://alquran.cloud/) for the Quran text and translations
- [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) for the Hadith collections and translations
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) for text recognition

Demo:


https://github.com/user-attachments/assets/f4928b4c-b2b5-49c4-819c-4674a2191e41


