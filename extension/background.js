// Talks to the FastAPI backend on behalf of the page (content scripts cannot call http://127.0.0.1 from https pages)
const SEARCH_URL = "http://127.0.0.1:8000/search-text";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "search-selection") return;

    (async () => {
        try {
            const settings = await chrome.storage.local.get({ source: "auto", reference: "" });
            const response = await fetch(SEARCH_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: message.text,
                    source: settings.source,
                    reference: settings.reference,
                }),
            });
            if (!response.ok) throw new Error("Server error " + response.status);
            sendResponse({ ok: true, data: await response.json() });
        } catch (error) {
            sendResponse({ ok: false, error: String(error.message || error) });
        }
    })();

    return true; // keep the channel open for the async answer
});