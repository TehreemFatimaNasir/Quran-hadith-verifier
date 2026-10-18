const API_URL = "http://127.0.0.1:8000/ocr";

const $ = (id) => document.getElementById(id);

const dropZone = $("drop");
const cameraBtn = $("cameraBtn");
const uploadBtn = $("uploadBtn");
const imageInput = $("imageInput");
const camera = $("camera");
const stage = $("stage");
const preview = $("preview");
const captureBtn = $("captureBtn");
const resetBtn = $("resetBtn");
const stepsList = $("steps");
const statusBox = $("status");
const results = $("results");
const toastBox = $("toast");

let cameraStream = null;
let isProcessing = false;
let stepTimers = [];



function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null && text !== "") {
        node.textContent = String(text);
    }
    return node;
}

function svgIcon(markup, size = 14) {
    const wrapper = document.createElement("span");
    wrapper.style.display = "inline-flex";
    wrapper.innerHTML =
        `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" ` +
        `stroke="currentColor" stroke-width="2" stroke-linecap="round" ` +
        `stroke-linejoin="round">${markup}</svg>`;
    return wrapper;
}

function showStatus(message, type = "") {
    statusBox.textContent = message;
    statusBox.className = "status" + (type ? " " + type : "");
    statusBox.hidden = false;
}

function hideStatus() {
    statusBox.hidden = true;
    statusBox.textContent = "";
}

let toastTimer = null;

function toast(message) {
    toastBox.textContent = message;
    toastBox.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastBox.classList.remove("show"), 2600);
}




const darkQuery = window.matchMedia?.("(prefers-color-scheme: dark)");

function applyTheme() {
    document.documentElement.setAttribute(
        "data-theme",
        darkQuery?.matches ? "dark" : "light"
    );
}

darkQuery?.addEventListener?.("change", applyTheme);



function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop());
        cameraStream = null;
    }

    camera.srcObject = null;
    camera.hidden = true;
    captureBtn.hidden = true;
}

async function startCamera() {
    hideStatus();

    if (!navigator.mediaDevices?.getUserMedia) {
        showStatus("Camera access is unavailable. Upload an image instead.", "error");
        return;
    }

    try {
        stopCamera();
        clearResults();

        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment" },
            audio: false,
        });

        camera.srcObject = cameraStream;
        camera.hidden = false;
        preview.hidden = true;
        stage.hidden = false;
        stage.classList.remove("scanning");
        captureBtn.hidden = false;
        resetBtn.hidden = false;

        await camera.play();
    } catch (error) {
        console.error("Camera error:", error);
        showStatus(
            "Could not open the camera. Check camera permissions or upload an image.",
            "error"
        );
        stopCamera();
        stage.hidden = true;
    }
}

captureBtn.addEventListener("click", async () => {
    if (!cameraStream || !camera.videoWidth || !camera.videoHeight) {
        showStatus("Camera is not ready yet.", "error");
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;

    const context = canvas.getContext("2d");

    if (!context) {
        showStatus("Could not capture the image.", "error");
        return;
    }

    context.drawImage(camera, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.92)
    );

    if (!blob) {
        showStatus("Could not create the captured image.", "error");
        return;
    }

    showPreview(blob);
    stopCamera();

    await sendImageToOCR(new File([blob], "camera-capture.jpg", { type: "image/jpeg" }));
});




function showPreview(fileOrBlob) {
    if (preview.src.startsWith("blob:")) URL.revokeObjectURL(preview.src);

    preview.src = URL.createObjectURL(fileOrBlob);
    preview.hidden = false;
    camera.hidden = true;
    stage.hidden = false;
    resetBtn.hidden = false;
}

async function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
        showStatus("Please select a valid image file.", "error");
        return;
    }

    stopCamera();
    showPreview(file);
    await sendImageToOCR(file);
}

uploadBtn.addEventListener("click", () => imageInput.click());

imageInput.addEventListener("change", async () => {
    const file = imageInput.files?.[0];
    await handleFile(file);
    imageInput.value = "";
});

["dragenter", "dragover"].forEach((name) =>
    dropZone.addEventListener(name, (event) => {
        event.preventDefault();
        dropZone.classList.add("dragging");
    })
);

["dragleave", "drop"].forEach((name) =>
    dropZone.addEventListener(name, (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragging");
    })
);

dropZone.addEventListener("drop", (event) => {
    handleFile(event.dataTransfer?.files?.[0]);
});




function setStep(index) {
    stepsList.querySelectorAll("li").forEach((item) => {
        const position = Number(item.dataset.step);
        item.classList.toggle("done", position < index);
        item.classList.toggle("active", position === index);
    });
}

function startScanning() {
    stage.classList.add("scanning");
    stepsList.hidden = false;
    setStep(0);

    stepTimers.forEach(clearTimeout);
    stepTimers = [
        setTimeout(() => setStep(1), 1800),
        setTimeout(() => setStep(2), 3400),
    ];
}

function stopScanning(success) {
    stepTimers.forEach(clearTimeout);
    stepTimers = [];
    stage.classList.remove("scanning");

    if (success) {
        setStep(3);
        setTimeout(() => { stepsList.hidden = true; }, 500);
    } else {
        stepsList.hidden = true;
    }
}




const CHECK_SVG =
    '<svg class="check" viewBox="0 0 36 36"><circle cx="18" cy="18" r="15"/><path d="M11 18.5l5 5 9-10"/></svg>';

function buildTranslationTabs(info) {
    const translations = info.translations || {};
    const fragment = document.createDocumentFragment();

    fragment.appendChild(el("div", "tr-title", "Translation / ترجمہ"));

    const segmented = el("div", "segmented");
    segmented.dataset.active = "ur";
    segmented.appendChild(el("span", "thumb"));

    const output = el("div", "tr-output");

    function select(key) {
        segmented.dataset.active = key;

        segmented.querySelectorAll("button").forEach((button) => {
            const active = button.dataset.key === key;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });

        const text = translations[key];

        output.className = "tr-output " + key;
        output.style.animation = "none";
        void output.offsetWidth; // restart the fade animation
        output.style.animation = "";

        if (typeof text === "string" && text.trim()) {
            output.textContent = text;
        } else {
            output.textContent =
                key === "ur"
                    ? "Urdu translation is not available for this reference."
                    : "English translation is not available for this reference.";
            output.classList.add("missing");
            output.dir = "ltr";
        }
    }

    [
        { key: "ur", label: "اردو" },
        { key: "en", label: "English" },
    ].forEach(({ key, label }) => {
        const button = el("button", "", label);
        button.type = "button";
        button.dataset.key = key;
        button.addEventListener("click", () => select(key));
        segmented.appendChild(button);
    });

    fragment.appendChild(segmented);
    fragment.appendChild(output);

    select("ur");

    return fragment;
}

function showFound(kind, info) {
    const isQuran = kind === "quran";
    const card = el("article", "result-card");

    // ----- top ribbon -----
    const top = el("div", "result-top" + (isQuran ? "" : " hadith"));
    top.insertAdjacentHTML("beforeend", CHECK_SVG);

    const label = el("div", "label");
    label.appendChild(el("small", "", isQuran ? "Quran verse found" : "Hadith found"));
    label.appendChild(
        el(
            "strong",
            "",
            isQuran
                ? `Surah ${info.surah || ""}`.trim()
                : info.book || "Hadith"
        )
    );
    top.appendChild(label);

    const number = isQuran ? info.ayah : (info.hadithNumber ?? info.number);

    if (number !== undefined && number !== null && number !== "") {
        const badge = el("div", "badge" + (String(number).length > 2 ? " wide" : ""));
        badge.textContent = isQuran ? number : `#${number}`;
        badge.title = isQuran ? `Ayah ${number}` : `Hadith ${number}`;
        top.appendChild(badge);
    }

    card.appendChild(top);

    
    const body = el("div", "result-body");
    const arabicWrap = el("div", "arabic-wrap");
    const arabic = el("p", "arabic");
    arabic.lang = "ar";
    arabic.dir = "rtl";

    const arabicText = info.text || "";

    if (isQuran) {
        arabic.appendChild(el("span", "ornament", "﴿"));
        arabic.appendChild(document.createTextNode(` ${arabicText} `));
        arabic.appendChild(el("span", "ornament", "﴾"));
    } else {
        arabic.textContent = arabicText;
    }

    arabicWrap.appendChild(arabic);
    body.appendChild(arabicWrap);

    // Long hadiths: collapse with a "Read full text" toggle
    if (!isQuran && arabicText.length > 260) {
        arabic.classList.add("clamped");

        const tools = el("div", "tools");
        const more = el("button", "chip-btn", "Read full text");
        more.type = "button";
        more.addEventListener("click", () => {
            const collapsed = arabic.classList.toggle("clamped");
            more.textContent = collapsed ? "Read full text" : "Show less";
        });

        tools.appendChild(more);
        body.appendChild(tools);
    }

    body.appendChild(buildTranslationTabs(info));
    card.appendChild(body);
    results.appendChild(card);
}

function clearResults() {
    results.replaceChildren();

}



async function sendImageToOCR(file) {
    if (isProcessing) return;

    isProcessing = true;
    hideStatus();
    clearResults();

    cameraBtn.disabled = true;
    uploadBtn.disabled = true;
    captureBtn.disabled = true;

    startScanning();

    let success = false;

    try {
        const formData = new FormData();
        formData.append("file", file); // must match the FastAPI parameter: file

        const response = await fetch(API_URL, { method: "POST", body: formData });

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error("The server returned an invalid response.");
        }

        if (!response.ok) {
            throw new Error(data.detail || `Server error (${response.status}).`);
        }

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.quran) showFound("quran", data.quran);
        if (data.hadith) showFound("hadith", data.hadith);

        if (data.quran || data.hadith) {
            success = true;

            if (data.quran && data.hadith) {
                showStatus(
                    "Possible matches found in both sources. Compare them carefully.",
                    "warning"
                );
            }
        } else if (data.text) {
            showStatus(
                "Text was extracted, but no matching reference was found. Try a clearer image.",
                "warning"
            );
        } else {
            showStatus(
                data.message || "No readable text was detected. Try another image.",
                "warning"
            );
        }
    } catch (error) {
        console.error("Verification error:", error);

        showStatus(
            `Could not verify the image. ${error.message || "Check that your FastAPI server is running."}`,
            "error"
        );
    } finally {
        stopScanning(success);

        isProcessing = false;
        cameraBtn.disabled = false;
        uploadBtn.disabled = false;
        captureBtn.disabled = false;
    }

    if (success) {
        results.firstElementChild?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}




function resetApp() {
    stopCamera();
    stopScanning(false);
    clearResults();
    hideStatus();

    if (preview.src.startsWith("blob:")) URL.revokeObjectURL(preview.src);

    preview.removeAttribute("src");
    preview.hidden = true;
    stage.hidden = true;
    resetBtn.hidden = true;
    imageInput.value = "";
}

cameraBtn.addEventListener("click", startCamera);
resetBtn.addEventListener("click", resetApp);

window.addEventListener("pagehide", () => {
    if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
});

applyTheme();
