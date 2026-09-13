/* Omni-Yomi popup: extract -> preview -> speak via local server. */
"use strict";

const $ = (id) => document.getElementById(id);

function setStatus(msg) {
  $("status").textContent = msg;
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function saveState() {
  await chrome.storage.local.set({
    text: $("text").value,
    server: $("server").value,
    speed: $("speed").value,
  });
}

async function restoreState() {
  const s = await chrome.storage.local.get(["text", "server", "speed"]);
  if (s.text) $("text").value = s.text;
  if (s.server) $("server").value = s.server;
  if (s.speed) $("speed").value = s.speed;
}

restoreState();
$("text").addEventListener("input", saveState);
$("server").addEventListener("input", saveState);
$("speed").addEventListener("input", saveState);

$("extract").addEventListener("click", async () => {
  setStatus("extracting...");
  try {
    const tab = await activeTab();
    const res = await chrome.tabs.sendMessage(tab.id, { type: "OMNI_YOMI_EXTRACT" });
    if (!res || !res.ok) {
      setStatus("extract failed: " + ((res && res.error) || "no response"));
      return;
    }
    $("text").value = res.paragraphs.join("\n");
    await saveState();
    setStatus(`extracted: ${res.title} (${res.paragraphs.length} paras)`);
  } catch (e) {
    setStatus("extract error: " + e.message);
  }
});

$("preview").addEventListener("click", async () => {
  setStatus("previewing...");
  try {
    const r = await fetch($("server").value + "/normalize/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("text").value }),
    });
    const data = await r.json();
    $("chunks").textContent = data.chunks
      .map((c) => `[${c.kind}/${c.lang}] ${c.spoken}`)
      .join("\n");
    setStatus(`preview: ${data.chunks.length} chunks`);
  } catch (e) {
    setStatus("preview error: " + e.message);
  }
});

$("speak").addEventListener("click", async () => {
  setStatus("synthesizing...");
  try {
    const r = await fetch($("server").value + "/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: $("text").value,
        speed: parseFloat($("speed").value) || 1.0,
      }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || ("HTTP " + r.status));
    }
    const blob = await r.blob();
    $("player").src = URL.createObjectURL(blob);
    await $("player").play();
    setStatus("playing");
  } catch (e) {
    setStatus("speak error: " + e.message);
  }
});
