import os
import re
import io
import json
import pathlib
import threading
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
                    "surahNumber": surah.get("number"),
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
    old_cache = []

    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                if data and "arabicnumber" in data[0]:
                    return data
                old_cache = data  # older cache without Sunnah.com numbers: refresh once
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
                {"hadithnumber": h.get("hadithnumber", ""), "arabicnumber": h.get("arabicnumber"), "text": h.get("text", "")}
                for h in hadiths
            ]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(slim, f, ensure_ascii=False)

            print(f"[HADITH] Downloaded {len(slim)} from {edition}")
            return slim
        except Exception as e:
            print(f"[HADITH] Error loading {edition}:", e)

    print(f"[HADITH] FAILED to load {edition}")
    return old_cache


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
                "arabic": h.get("arabicnumber"),
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




# ==================================================
# TRANSLATIONS (Urdu + English) for the matched result
# ==================================================

QURAN_TRANSLATION_EDITIONS = {"en": "en.sahih", "ur": "ur.jalandhry"}

_quran_translation_cache = {}
_hadith_translation_lookup = {}


def get_quran_translations(surah_number, ayah_number) -> dict:
    """English + Urdu translation of one ayah."""
    translations = {}
    if not surah_number or not ayah_number:
        return translations

    for language, edition in QURAN_TRANSLATION_EDITIONS.items():
        key = (surah_number, ayah_number, edition)

        if key in _quran_translation_cache:
            translations[language] = _quran_translation_cache[key]
            continue

        try:
            response = requests.get(
                f"https://api.alquran.cloud/v1/ayah/{surah_number}:{ayah_number}/{edition}",
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") == 200:
                text = payload["data"]["text"]
                _quran_translation_cache[key] = text
                translations[language] = text
        except Exception as e:
            print(f"[QURAN] {language} translation error:", e)

    return translations


def _hadith_translation_book(edition: str) -> dict:
    """{hadith number: text} for one translated book (downloaded once, then cached)."""
    if edition not in _hadith_translation_lookup:
        records = load_hadith_collection(edition)
        _hadith_translation_lookup[edition] = {
            str(h.get("hadithnumber", "")).strip(): h.get("text", "")
            for h in records
        }
    return _hadith_translation_lookup[edition]


def get_hadith_translations(book_name, hadith_number) -> dict:
    """English + Urdu translation of one hadith."""
    translations = {}
    arabic_edition = HADITH_COLLECTIONS.get(book_name)
    if not arabic_edition or hadith_number in (None, ""):
        return translations

    # "ara-bukhari1" -> "bukhari"
    name = arabic_edition.replace("ara-", "", 1)
    if name.endswith("1"):
        name = name[:-1]

    for language, prefix in (("en", "eng-"), ("ur", "urd-")):
        try:
            book = _hadith_translation_book(prefix + name)
            text = book.get(str(hadith_number).strip())
            if text:
                translations[language] = text
        except Exception as e:
            print(f"[HADITH] {language} translation error:", e)

    return translations


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




# ==================================================
# URDU IMAGE SUPPORT
#
# Runs ONLY when the normal (Arabic) search finds nothing.
# The Urdu text is read with a second OCR reader and searched in the
# Urdu translations of the Quran and the six Hadith books. The result
# shows the original ARABIC text plus its reference, like always.
# ==================================================

# (alquran.cloud edition, GitHub fallback edition)
URDU_QURAN_SOURCES = [
    ("ur.jalandhry", "urd-fatehmuhammadja"),
    ("ur.maududi", "urd-abulaalamaududi"),
    ("ur.junagarhi", "urd-muhammadjunagar"),
    ("ur.ahmedali", "urd-ahmedali"),
]

URDU_CACHE_DIR = pathlib.Path("urdu_data")
URDU_CACHE_DIR.mkdir(exist_ok=True)

URDU_MIN_SCORE = 0.62      # minimum score to accept an Urdu match

_urdu_reader = None
_urdu_index = []
_urdu_index_ready = False
_urdu_lock = threading.Lock()
_quran_lookup = None
_hadith_arabic_lookup = None


# Letters that OCR often confuses (or that Urdu writes differently from
# Arabic) are folded together, so small OCR mistakes don't break matching.
_URDU_FOLD = str.maketrans({
    "ي": "ی", "ى": "ی", "ې": "ی", "ے": "ی", "ۓ": "ی", "ئ": "ی",
    "ك": "ک", "ڪ": "ک", "گ": "ک",
    "ه": "ہ", "ھ": "ہ", "ۃ": "ہ", "ۂ": "ہ", "ة": "ہ", "ە": "ہ",
    "ٹ": "ت", "ڈ": "د", "ڑ": "ر", "ں": "ن", "ژ": "ز",
    "چ": "ج", "پ": "ب",
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "و",
})


def urdu_skeleton(text) -> str:
    """Letters only (no spaces, marks, digits or punctuation), folded."""
    text = re.sub(
        r"[ؐ-ًؚ-ٰٟۖ-ۭ]", "", str(text or "")
    )
    text = text.replace("ـ", "").translate(_URDU_FOLD)
    return "".join(c for c in text if "ء" <= c <= "ۓ" and c.isalpha())


def get_urdu_reader():
    """Second OCR reader for Urdu (created the first time it is needed)."""
    global _urdu_reader
    if _urdu_reader is None:
        print("[URDU] Loading Urdu OCR reader...")
        _urdu_reader = easyocr.Reader(["ur", "en"], gpu=False)
        print("[URDU] Urdu OCR reader ready.")
    return _urdu_reader


def run_urdu_ocr(image: Image.Image) -> str:
    results = get_urdu_reader().readtext(np.array(image))
    return " ".join(r[1] for r in results if len(r) >= 2 and r[1])


def _load_urdu_quran_edition(alquran_edition: str, github_edition: str) -> list:
    """[[surah, ayah, text], ...] for one Urdu Quran translation."""
    cache_file = URDU_CACHE_DIR / f"{github_edition}.json"

    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass

    verses = []

    try:
        response = requests.get(
            f"https://api.alquran.cloud/v1/quran/{alquran_edition}", timeout=60
        )
        response.raise_for_status()
        for surah in response.json()["data"]["surahs"]:
            for ayah in surah.get("ayahs", []):
                verses.append(
                    [surah["number"], ayah["numberInSurah"], ayah["text"]]
                )
    except Exception as e:
        print(f"[URDU] {alquran_edition} from alquran.cloud failed:", e)
        verses = []

    if not verses:
        try:
            response = requests.get(
                "https://raw.githubusercontent.com/fawazahmed0/quran-api/1/"
                f"editions/{github_edition}.json",
                timeout=60,
            )
            response.raise_for_status()
            for v in response.json().get("quran", []):
                verses.append([v["chapter"], v["verse"], v["text"]])
        except Exception as e:
            print(f"[URDU] {github_edition} from GitHub failed:", e)

    if verses:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(verses, f, ensure_ascii=False)

    return verses


def build_urdu_index() -> list:
    """Loads all Urdu translations once (Quran + Hadith) and indexes them."""
    global _urdu_index, _urdu_index_ready

    with _urdu_lock:
        if _urdu_index_ready:
            return _urdu_index

        print("[URDU] Building Urdu index...")
        index = []

        for alquran_edition, github_edition in URDU_QURAN_SOURCES:
            for surah, ayah, text in _load_urdu_quran_edition(
                alquran_edition, github_edition
            ):
                skel = urdu_skeleton(text)
                if skel:
                    index.append({
                        "kind": "quran", "surah": surah,
                        "ayah": ayah, "skel": skel,
                    })

        for book_name, arabic_edition in HADITH_COLLECTIONS.items():
            name = arabic_edition.replace("ara-", "", 1)
            if name.endswith("1"):
                name = name[:-1]

            for h in load_hadith_collection("urd-" + name):
                skel = urdu_skeleton(h.get("text", ""))
                if skel:
                    index.append({
                        "kind": "hadith", "book": book_name,
                        "number": h.get("hadithnumber", ""), "skel": skel,
                    })

        _urdu_index = index
        _urdu_index_ready = len(index) > 0
        print(f"[URDU] Urdu index ready: {len(index)} texts")
        return _urdu_index


def _arabic_quran_lookup() -> dict:
    """{(surah, ayah): (surah English name, Arabic text)}"""
    global _quran_lookup
    if _quran_lookup is None:
        lookup = {}
        for surah in load_quran():
            for ayah in surah.get("ayahs", []):
                lookup[(surah.get("number"), ayah.get("numberInSurah"))] = (
                    surah.get("englishName", ""), ayah.get("text", ""),
                )
        _quran_lookup = lookup
    return _quran_lookup


def _arabic_hadith_lookup() -> dict:
    """{(book, hadith number): Arabic text}"""
    global _hadith_arabic_lookup
    if _hadith_arabic_lookup is None:
        _hadith_arabic_lookup = {
            (h["book"], str(h["number"]).strip()): h["text"]
            for h in build_hadith_index()
        }
    return _hadith_arabic_lookup


def search_urdu(urdu_text: str):
    """Best Urdu-translation match -> {"quran":..., "hadith":...} or None."""
    print("\n========== URDU SEARCH ==========")

    index = build_urdu_index()
    query = urdu_skeleton(urdu_text)

    if not index or len(query) < 12:
        print("[URDU] Index empty or too little text.")
        return None

    grams = list({query[i:i + 4] for i in range(len(query) - 3)})

    # a spread-out sample of the query is enough to shortlist candidates
    if len(grams) > 30:
        step = len(grams) / 30
        sample = [grams[int(i * step)] for i in range(30)]
    else:
        sample = grams

    candidates = []
    for entry in index:
        if query in entry["skel"]:
            candidates.append((10 ** 6, entry))
            continue
        shared = sum(1 for g in sample if g in entry["skel"])
        if shared >= 0.3 * len(sample):
            candidates.append((shared, entry))

    candidates.sort(key=lambda pair: pair[0], reverse=True)

    best, best_score = None, 0.0
    for _, entry in candidates[:1500]:
        if query in entry["skel"]:
            # an exact match always beats a partial one; between several
            # exact matches prefer the text closest in length to what was read
            score = 1.0 + len(query) / len(entry["skel"])
        else:
            scores = _best_window_score(entry["skel"], query, grams)
            if not isinstance(scores, tuple):
                continue
            rough_match, exact_match = scores
            if rough_match < 0.3:
                continue
            score = rough_match * 0.5 + exact_match * 0.5

        if score > best_score:
            best_score, best = score, entry

    print("[URDU] Best score:", round(best_score * 100, 1))

    if not best or best_score < URDU_MIN_SCORE:
        print("[URDU] No reliable match found.")
        return None

    confidence = round(min(best_score * 100, 100), 1)

    if best["kind"] == "quran":
        name, arabic = _arabic_quran_lookup().get(
            (best["surah"], best["ayah"]), (f"Surah {best['surah']}", "")
        )
        print("[URDU] QURAN MATCH:", name, best["ayah"])
        return {
            "quran": {
                "surah": name or f"Surah {best['surah']}",
                "surahNumber": best["surah"],
                "ayah": best["ayah"],
                "text": arabic,
                "confidence": confidence,
            },
            "hadith": None,
        }

    arabic = _arabic_hadith_lookup().get(
        (best["book"], str(best["number"]).strip()), ""
    )
    print("[URDU] HADITH MATCH:", best["book"], best["number"])
    return {
        "quran": None,
        "hadith": {
            "book": best["book"],
            "hadithNumber": best["number"],
            "status": "Found in collection",
            "text": arabic,
            "confidence": confidence,
        },
    }


def verify_urdu_image(image: Image.Image):
    """Reads Urdu text from the image and searches it.
    Returns (urdu_text, {"quran":..., "hadith":...}) or None. Never raises."""
    try:
        variants = prepare_images(image)
        best = None  # (confidence, text, result)

        for img in (variants[0], variants[2]):
            text = run_urdu_ocr(img)
            if not text:
                continue

            found = search_urdu(text)
            if not found:
                continue

            hit = found["quran"] or found["hadith"]
            if best is None or hit["confidence"] > best[0]:
                best = (hit["confidence"], text, found)

        if best:
            return best[1], best[2]

    except Exception as e:
        print("[URDU] Urdu search error:", e)

    return None


@app.on_event("startup")
def preload_urdu_index():
    # in the background, so the server starts quickly
    threading.Thread(target=build_urdu_index, daemon=True).start()




@app.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        
        texts = [run_ocr(img) for img in prepare_images(image)]
        final_text = max([t for t in texts if t], key=len, default="")

        result = verify_text(final_text)
        language = "ar"

        # Nothing found with the Arabic search -> try Urdu text in the image
        if not result["quran"] and not result["hadith"]:
            urdu = verify_urdu_image(image)
            if urdu:
                final_text, result = urdu
                language = "ur"

        if result["quran"]:
            result["quran"]["translations"] = get_quran_translations(
                result["quran"].get("surahNumber"),
                result["quran"].get("ayah"),
            )

        if result["hadith"]:
            result["hadith"]["translations"] = get_hadith_translations(
                result["hadith"].get("book"),
                result["hadith"].get("hadithNumber"),
            )

        return {
            "filename": file.filename,
            "text": final_text,
            "language": language,
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



# ==================================================
# SELECTED TEXT (highlight on any webpage) + reference check
# ==================================================

from pydantic import BaseModel
import re as _re

URDU_ONLY_LETTERS = set("ٹڈڑںےگچپژھۓ")

HADITH_ALIASES = {
    "bukhari": "Sahih Bukhari",
    "muslim": "Sahih Muslim",
    "abu dawud": "Sunan Abu Dawud", "abudawud": "Sunan Abu Dawud", "dawud": "Sunan Abu Dawud", "daud": "Sunan Abu Dawud",
    "tirmidhi": "Jami At-Tirmidhi", "tirmizi": "Jami At-Tirmidhi",
    "ibn majah": "Sunan Ibn Majah", "ibnmajah": "Sunan Ibn Majah", "majah": "Sunan Ibn Majah",
    "nasai": "Sunan an-Nasai", "nasa'i": "Sunan an-Nasai", "nasa": "Sunan an-Nasai",
}


class SelectedText(BaseModel):
    text: str
    source: str = "auto"       # auto | quran | hadith
    reference: str = ""        # optional pointer, e.g. "67:15" or "Bukhari 2731"


def parse_reference(ref: str):
    """'67:15' -> ('quran', 67, 15); 'Bukhari 2731' -> ('hadith', book, 2731); else None."""
    ref = (ref or "").strip().lower()
    if not ref:
        return None
    m = _re.match(r"^(\d{1,3})\s*[:/.\-]\s*(\d{1,3})$", ref)
    if m:
        return ("quran", int(m.group(1)), int(m.group(2)))
    for alias, book in sorted(HADITH_ALIASES.items(), key=lambda kv: -len(kv[0])):
        m = _re.match(rf"^(?:sahih\s+|sunan\s+|jami\s+)?(?:al[-\s]|at[-\s]|an[-\s])?{_re.escape(alias)}\D*?(\d+)\s*([a-z])?$", ref)
        if m:
            return ("hadith", book, int(m.group(1)), m.group(2))
    return None


def check_reference(text: str, ref: str) -> dict:
    """Does the selected text really belong to the pointer the user gave?"""
    parsed = parse_reference(ref)
    if not parsed:
        return {"input": ref, "verdict": "invalid",
                "message": "Use a format like 67:15 (Quran) or Bukhari 2731 (Hadith)."}

    if parsed[0] == "quran":
        _, sno, ayno = parsed
        for surah in load_quran():
            if surah.get("number") == sno:
                for ayah in surah.get("ayahs", []):
                    if ayah.get("numberInSurah") == ayno:
                        words = normalize_arabic(text).split()
                        awords = normalize_arabic(ayah["text"]).split()
                        if not words or not awords:
                            break
                        hit = sum(1 for w in words if max(_word_match_score(w, a) for a in awords) >= 0.75)
                        cov = hit / len(words)
                        label = f"{surah.get('englishName', '')} {sno}:{ayno}"
                        return {"input": ref, "verdict": "verified" if cov >= 0.75 else "mismatch",
                                "score": round(cov * 100, 1), "label": label, "kind": "quran",
                                "text": ayah["text"]}
        return {"input": ref, "verdict": "invalid", "message": "That Surah/Ayah number does not exist."}

    _, book, number, suffix = parsed
    q = skeleton(text)
    if len(q) < 8:
        return {"input": ref, "verdict": "invalid", "message": "Selected text is too short."}
    grams = {q[i:i + 4] for i in range(len(q) - 3)}

    def sunnah_match(h) -> bool:
        a = h.get("arabic")
        try:
            a = float(a)
        except (TypeError, ValueError):
            return False
        if int(a) != number:
            return False
        if not suffix:
            return True
        return round((a - int(a)) * 100) == ord(suffix) - 96

    candidates = []
    for h in build_hadith_index():
        if h["book"] != book:
            continue
        # the book's own number (only when no letter like 1600b was typed) or the Sunnah.com number
        if (not suffix and str(h["number"]).strip() == str(number)) or sunnah_match(h):
            candidates.append(h)

    best = None
    for h in candidates:
        cov = sum(1 for g in grams if g in h["skel"]) / max(len(grams), 1)
        if best is None or cov > best[0]:
            best = (cov, h)
    if best:
        cov, h = best
        return {"input": ref, "verdict": "verified" if cov >= 0.7 else "mismatch",
                "score": round(cov * 100, 1), "label": f"{book} {number}{suffix or ''}", "kind": "hadith",
                "text": h["text"]}
    return {"input": ref, "verdict": "invalid", "message": "That Hadith number was not found in this book."}


@app.post("/search-text")
def search_selected_text(body: SelectedText):
    try:
        text = " ".join((body.text or "").split())[:3000]
        source = (body.source or "auto").lower()
        if len(text) < 6:
            return {"text": text, "language": "ar", "quran": None, "hadith": None,
                    "error": "Select a little more text."}

        language = "ar"
        if source == "quran":
            result = {"quran": search_quran(text), "hadith": None}
        elif source == "hadith":
            result = {"quran": None, "hadith": search_hadith(text)}
        else:
            result = verify_text(text)

        # Urdu text selected on a page
        if not result["quran"] and not result["hadith"] and (set(text) & URDU_ONLY_LETTERS or len(normalize_arabic(text)) > 0):
            found = search_urdu(text)
            if found:
                if source == "quran" and not found["quran"]:
                    found = None
                elif source == "hadith" and not found["hadith"]:
                    found = None
            if found:
                result, language = found, "ur"

        if result["quran"]:
            result["quran"]["translations"] = get_quran_translations(
                result["quran"].get("surahNumber"), result["quran"].get("ayah"))
        if result["hadith"]:
            result["hadith"]["translations"] = get_hadith_translations(
                result["hadith"].get("book"), result["hadith"].get("hadithNumber"))

        out = {"text": text, "language": language,
               "quran": result["quran"], "hadith": result["hadith"]}
        if (body.reference or "").strip():
            out["reference"] = check_reference(text, body.reference)
        return out

    except Exception as e:
        print("SEARCH-TEXT ERROR:", e)
        return {"text": body.text, "quran": None, "hadith": None, "error": str(e)}


@app.get("/")
def home():
    return {"message": "Quran & Hadith Verifier API is running"}