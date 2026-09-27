import os
import re
import io
import json
import pathlib
from difflib import SequenceMatcher

import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter
import easyocr

load_dotenv()



app = FastAPI(title="Quran & Hadith Verifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading EasyOCR...")
reader = easyocr.Reader(["ar", "en"], gpu=False)
print("EasyOCR loaded successfully.")


def normalize_arabic(text: str) -> str:
    """Cleans Arabic text for matching."""
    if not text:
        return ""
    text = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", text.strip())
    for a, b in [("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ـ", ""), ("ة", "ه")]:
        text = text.replace(a, b)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def skeleton(text: str) -> str:
    """Letters only, no spaces — survives OCR word-merging errors."""
    text = normalize_arabic(text)
    for a, b in [("ى", "ي"), ("ئ", "ي"), ("ؤ", "و"), ("ء", "")]:
        text = text.replace(a, b)
    return re.sub(r"[^\u0621-\u064A]", "", text)


def text_similarity(text1: str, text2: str) -> float:
    text1, text2 = normalize_arabic(text1), normalize_arabic(text2)
    return SequenceMatcher(None, text1, text2).ratio() if text1 and text2 else 0




_quran_data = None


def load_quran():
    """Downloads the Quran once, keeps it cached in memory."""
    global _quran_data
    if _quran_data is not None:
        return _quran_data

    print("Downloading Quran data...")
    try:
        response = requests.get(
            "https://api.alquran.cloud/v1/quran/quran-uthmani", timeout=60
        )
        response.raise_for_status()
        _quran_data = response.json()["data"]["surahs"]
        print("Quran loaded:", len(_quran_data), "surahs")
    except Exception as e:
        print("Quran API error:", e)
        _quran_data = []

    return _quran_data


def _word_match_score(ocr_word: str, ayah_word: str) -> float:
    """0-1 match score between one OCR word and one Quran word."""
    if ocr_word == ayah_word:
        return 1.0
    if ocr_word in ayah_word or ayah_word in ocr_word:
        return 0.90
    return SequenceMatcher(None, ocr_word, ayah_word).ratio()


def search_quran(text: str):
    """Best-matching ayah for the OCR text, or None."""
    print("\n========== QURAN SEARCH ==========")

    surahs = load_quran()
    ocr_words = normalize_arabic(text).split()
    if not surahs or len(ocr_words) < 2:
        return None

    best_match, best_score, best_matches = None, 0, 0

    for surah in surahs:
        for ayah in surah.get("ayahs", []):
            ayah_text = ayah.get("text", "")
            ayah_words = normalize_arabic(ayah_text).split()
            if not ayah_words:
                continue

            matched_words = sum(
                1
                for ocr_word in ocr_words
                if max(_word_match_score(ocr_word, w) for w in ayah_words) >= 0.75
            )

            word_coverage = matched_words / len(ocr_words)
            char_score = text_similarity(" ".join(ocr_words), " ".join(ayah_words))
            score = word_coverage * 0.80 + char_score * 0.20

            if score > best_score:
                best_score, best_matches = score, matched_words
                best_match = {
                    "surah": surah.get("englishName", ""),
                    "ayah": ayah.get("numberInSurah", ""),
                    "text": ayah_text,
                }

    print("Best Quran score:", round(best_score * 100, 1))
    if not best_match:
        return None

   
    word_coverage = best_matches / len(ocr_words)
    if best_matches < 2 or word_coverage < 0.50 or best_score < 0.55:
        print("Quran rejected: not confident enough.")
        return None

    print("Quran MATCH FOUND:", best_match["surah"], "Ayah:", best_match["ayah"])
    best_match["confidence"] = round(best_score * 100, 1)
    return best_match




HADITH_COLLECTIONS = {
    "Sahih Bukhari": "ara-bukhari1",
    "Sahih Muslim": "ara-muslim1",
    "Sunan Abu Dawud": "ara-abudawud1",
    "Jami At-Tirmidhi": "ara-tirmidhi1",
    "Sunan Ibn Majah": "ara-ibnmajah1",
    "Sunan an-Nasai": "ara-nasai1",
}

CACHE_DIR = pathlib.Path("hadith_data")
CACHE_DIR.mkdir(exist_ok=True)

_hadith_index = None  


def load_hadith_collection(edition: str) -> list:
    """Loads one Hadith book from local cache, or downloads it once."""
    cache_file = CACHE_DIR / f"{edition}.json"

    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass

    urls = [
        f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}.min.json",
        f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}.json",
        f"https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions/{edition}.json",
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=180)
            if response.status_code != 200:
                continue
            hadiths = response.json().get("hadiths", [])
            if not hadiths:
                continue

            slim = [
                {"hadithnumber": h.get("hadithnumber", ""), "text": h.get("text", "")}
                for h in hadiths
            ]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(slim, f, ensure_ascii=False)

            print(f"[HADITH] Downloaded {len(slim)} from {edition}")
            return slim
        except Exception as e:
            print(f"[HADITH] Error loading {edition}:", e)

    print(f"[HADITH] FAILED to load {edition}")
    return []


def build_hadith_index() -> list:
    """Loads all 6 collections into memory once, with a skeleton per hadith."""
    global _hadith_index
    if _hadith_index:
        return _hadith_index

    print("[HADITH] Building index...")
    index = []
    for book_name, edition in HADITH_COLLECTIONS.items():
        for h in load_hadith_collection(edition):
            text = h.get("text", "")
            if not text:
                continue
            index.append({
                "book": book_name,
                "number": h.get("hadithnumber", ""),
                "text": text,
                "skel": skeleton(text),
            })

    _hadith_index = index
    print(f"[HADITH] Index ready: {len(index)} hadiths")
    return index


@app.on_event("startup")
def preload_hadith_index():
    build_hadith_index()


def _best_window_score(hadith_skel: str, query: str, query_grams: list) -> float:
    """Scores only the densest matching region of a hadith, so long hadiths
    don't win just by chance."""
    positions = []
    for gram_id, gram in enumerate(query_grams):
        start = hadith_skel.find(gram)
        seen = 0
        while start != -1 and seen < 30:
            positions.append((start, gram_id))
            start = hadith_skel.find(gram, start + 1)
            seen += 1

    if not positions:
        return 0.0

    positions.sort()
    window_size = int(len(query) * 1.8)

    counts = {}
    distinct_in_window = 0
    best_distinct = 0
    best_start = 0
    left = 0

    for right, (pos, gram_id) in enumerate(positions):
        counts[gram_id] = counts.get(gram_id, 0) + 1
        if counts[gram_id] == 1:
            distinct_in_window += 1

        while pos - positions[left][0] > window_size:
            left_gram = positions[left][1]
            counts[left_gram] -= 1
            if counts[left_gram] == 0:
                distinct_in_window -= 1
            left += 1

        if distinct_in_window > best_distinct:
            best_distinct = distinct_in_window
            best_start = positions[left][0]

    rough_match = best_distinct / len(query_grams)

    window = hadith_skel[max(0, best_start - 20): best_start + window_size + 20]
    matcher = SequenceMatcher(None, query, window, autojunk=False)
    matched_chars = sum(block.size for block in matcher.get_matching_blocks())
    exact_match = matched_chars / len(query)

    return rough_match, exact_match


def search_hadith(ocr_text: str):
    """Best-matching hadith for the OCR text, or None."""
    print("\n========== HADITH SEARCH ==========")

    index = build_hadith_index()
    if not index or not ocr_text:
        print("[HADITH] Index empty or no text.")
        return None

    query = skeleton(ocr_text)
    if len(query) < 12:
        print("[HADITH] Too little text.")
        return None

    query_grams = list({query[i:i + 4] for i in range(len(query) - 3)})

    
    candidates = []
    for h in index:
        if query in h["skel"]:
            print("[HADITH] EXACT MATCH:", h["book"], h["number"])
            return {
                "book": h["book"],
                "hadithNumber": h["number"],
                "status": "Found in collection",
                "text": h["text"],
                "confidence": 100.0,
            }
        shared = sum(1 for g in query_grams if g in h["skel"])
        if shared >= 0.3 * len(query_grams):
            candidates.append((shared, h))

    candidates.sort(key=lambda pair: pair[0], reverse=True)

    
    best, best_score = None, 0
    for _, h in candidates[:2000]:
        rough_match, exact_match = _best_window_score(h["skel"], query, query_grams)
        if rough_match < 0.3:
            continue

        score = rough_match * 0.5 + exact_match * 0.5
        if score > best_score:
            best_score, best = score, h

    print("[HADITH] Best score:", round(best_score * 100, 1))

    if best and best_score >= 0.40:
        print("[HADITH] MATCH FOUND:", best["book"], best["number"])
        return {
            "book": best["book"],
            "hadithNumber": best["number"],
            "status": "Found in collection",
            "text": best["text"],
            "confidence": round(min(best_score * 100, 100), 1),
        }

    print("[HADITH] No reliable match found.")
    return None




def verify_text(text: str) -> dict:
    """Searches both Quran and Hadith, returns whichever one wins."""
    if not text:
        return {"quran": None, "hadith": None}

    quran_result = search_quran(text)
    hadith_result = search_hadith(text)

    if quran_result and hadith_result:
        if hadith_result["confidence"] >= 50 and \
           hadith_result["confidence"] + 10 >= quran_result["confidence"]:
            return {"quran": None, "hadith": hadith_result}
        return {"quran": quran_result, "hadith": None}

    return {"quran": quran_result, "hadith": hadith_result}




def run_ocr(image: Image.Image) -> str:
    """Reads text from one image using EasyOCR."""
    results = reader.readtext(np.array(image))
    return " ".join(r[1] for r in results if len(r) >= 2 and r[1])


def prepare_images(image: Image.Image) -> list:
    """Returns a few versions of the image (bigger, higher contrast, sharper) to help OCR."""
    bigger = image.resize((image.width * 2, image.height * 2))
    contrast = ImageEnhance.Contrast(bigger).enhance(1.5)
    sharper = contrast.filter(ImageFilter.SHARPEN)
    return [image, bigger, contrast, sharper]




@app.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        
        texts = [run_ocr(img) for img in prepare_images(image)]
        final_text = max([t for t in texts if t], key=len, default="")

        result = verify_text(final_text)
        return {
            "filename": file.filename,
            "text": final_text,
            "quran": result["quran"],
            "hadith": result["hadith"],
        }

    except Exception as e:
        print("OCR ERROR:", e)
        return {"filename": file.filename, 
                "text": "",
                  "quran": None, 
                  "hadith": None,
                    "error": str(e)}


@app.get("/")
def home():
    return {"message": "Quran & Hadith Verifier API is running"}