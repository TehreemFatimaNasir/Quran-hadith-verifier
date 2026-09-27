

const API_URL = "http://127.0.0.1:8000/ocr";




const cameraBtn = document.getElementById("cameraBtn");
const uploadBtn = document.getElementById("uploadBtn");
const imageInput = document.getElementById("imageInput");
const camera = document.getElementById("camera");
const captureBtn = document.getElementById("captureBtn");
const preview = document.getElementById("preview");

const result = document.getElementById("result");
const resultCard = document.getElementById("resultCard");
const resetBtn = document.getElementById("resetBtn");

let stream = null;

const isCameraPage =
    new URLSearchParams(window.location.search).get("camera") === "1";



function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function chip(key, value) {
    const c = el("div", "chip");
    c.appendChild(el("div", "k", key));
    c.appendChild(el("div", "v", String(value)));
    return c;
}



function showResultArea() {
    result.style.display = "block";
    resultCard.innerHTML = "";
}

function showLoading() {
    showResultArea();
    resetBtn.classList.add("hidden");

    const box = el("div", "loading");
    box.appendChild(el("div", "spinner"));
    box.appendChild(el("p", "", "Reading text and searching..."));
    resultCard.appendChild(box);
}

function showError(message) {
    showResultArea();
    resetBtn.classList.remove("hidden");

    const head = el("div", "card-head error");
    head.appendChild(el("div", "title", " Could not connect"));
    resultCard.appendChild(head);

    const body = el("div", "card-body");
    const msg = el("div", "message");
    msg.appendChild(el("div", "", message));

    const list = el("ul");
    list.appendChild(el("li", "", "Make sure the FastAPI server is running."));
    list.appendChild(el("li", "", "Check that it is at " + API_URL));
    msg.appendChild(list);

    body.appendChild(msg);
    resultCard.appendChild(body);
}

function showNoMatch(extractedText) {
    showResultArea();
    resetBtn.classList.remove("hidden");

    const head = el("div", "card-head none");
    head.appendChild(el("div", "title", "No Matching Quran or Hadith Found"));
    resultCard.appendChild(head);

    const body = el("div", "card-body");
    const msg = el("div", "message");
    msg.appendChild(el("div", "", "Try again with a clearer image:"));

    const list = el("ul");
    list.appendChild(el("li", "", "Crop so only the Arabic text is visible."));
    list.appendChild(el("li", "", "Use good lighting and hold the camera steady."));
    list.appendChild(el("li", "", "Include at least one full line of text."));
    msg.appendChild(list);
    body.appendChild(msg);

    resultCard.appendChild(body);
}

function buildArabicBox(text) {
    const box = el("div", "arabic", text);
    const wrap = el("div");
    wrap.appendChild(box);

    const isLong = text.length > 220;
    if (isLong) box.classList.add("clamped");

    const actions = el("div", "actions");

    if (isLong) {
        const toggle = el("button", "", "Show full text");
        toggle.addEventListener("click", () => {
            const expanded = box.classList.toggle("expanded");
            box.classList.toggle("clamped", !expanded);
            toggle.textContent = expanded ? "Show less" : "Show full text";
        });
        actions.appendChild(toggle);
    }

    const copy = el("button", "", "📋 Copy");
    copy.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(text);
            copy.textContent = " Copied";
        } catch (e) {
            copy.textContent = "Copy failed";
        }
        setTimeout(() => (copy.textContent = "📋 Copy"), 1500);
    });
    actions.appendChild(copy);

    wrap.appendChild(actions);
    return wrap;
}

function showFound(kind, info, extractedText) {
    showResultArea();
    resetBtn.classList.remove("hidden");

    // header
    const head = el("div", "card-head ok");
    head.appendChild(
        el("div", "title", kind === "quran" ? "📖 Quran Found ✓" : "📜 Hadith Found ✓")
    );
    resultCard.appendChild(head);

    
    const body = el("div", "card-body");

    const chips = el("div", "chips");
    if (kind === "quran") {
        chips.appendChild(chip("Surah", info.surah));
        chips.appendChild(chip("Ayah", info.ayah));
    } else {
        chips.appendChild(chip("Book", info.book));
        chips.appendChild(chip("Hadith No.", info.hadithNumber));
    }
    body.appendChild(chips);

    body.appendChild(buildArabicBox(info.text || ""));

    if (kind === "hadith") {
        body.appendChild(
            el(
                "div",
                "note",
                "The same hadith can appear in several books. " +
                "Matching is based on text similarity, so always confirm " +
                "with a trusted source."
            )
        );
    }

    resultCard.appendChild(body);
}



async function sendImageToOCR(imageBlob) {
    showLoading();

    const formData = new FormData();
    formData.append("file", imageBlob, "quran-hadith-image.png");

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Server returned " + response.status);
        }

        const data = await response.json();
        console.log("OCR response:", data);

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.quran) {
            showFound("quran", data.quran, data.text);
        } else if (data.hadith) {
            showFound("hadith", data.hadith, data.text);
        } else {
            showNoMatch(data.text);
        }

    } catch (error) {
        console.error("OCR request failed:", error);
        showError(error.message);
    }
}



uploadBtn.addEventListener("click", () => imageInput.click());

imageInput.addEventListener("change", async () => {
    const file = imageInput.files[0];
    if (!file) return;

    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";

    await sendImageToOCR(file);
    imageInput.value = "";   // allow choosing the same file again
});




cameraBtn.addEventListener("click", (e) => {
    e.preventDefault();
    chrome.tabs.create({
        url: chrome.runtime.getURL("index.html?camera=1")
    });
    window.close();
});

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1920 },
                height: { ideal: 1080 },
                facingMode: "environment"
            },
            audio: false
        });

        camera.srcObject = stream;
        camera.style.display = "block";

        camera.onloadedmetadata = async () => {
            try {
                await camera.play();
                captureBtn.style.display = "block";
            } catch (error) {
                console.error("Video play error:", error);
                alert("Camera opened but video could not play.");
            }
        };

    } catch (error) {
        console.error("Camera error:", error);
        alert("Unable to access camera.\n\nError: " + error.name);
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
    }
    camera.srcObject = null;
    camera.style.display = "none";
    captureBtn.style.display = "none";
}

captureBtn.addEventListener("click", () => {
    if (!camera.videoWidth || !camera.videoHeight) {
        alert("Camera is not ready yet.");
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;
    canvas.getContext("2d").drawImage(camera, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
        if (!blob) {
            alert("Could not capture image.");
            return;
        }

        preview.src = URL.createObjectURL(blob);
        preview.style.display = "block";

        await sendImageToOCR(blob);
    }, "image/png", 0.95);

    stopCamera();
});



resetBtn.addEventListener("click", () => {
    result.style.display = "none";
    resultCard.innerHTML = "";
    resetBtn.classList.add("hidden");
    preview.style.display = "none";
    preview.removeAttribute("src");

    if (isCameraPage) {
        startCamera();
    }
});



if (isCameraPage) {
    startCamera();
}