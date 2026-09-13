/* Omni-Yomi popup: extract -> preview -> offscreen playback.
 * Playback runs in the offscreen document so closing the popup keeps audio alive.
 */
"use strict";

const $ = (id) => document.getElementById(id);

function setStatus(msg) {
  $("status").textContent = msg;
}

function base() {
  return $("server").value.replace(/\/$/, "");
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
    voice: $("voice").value,
    model: $("model").value,
  });
}

async function restoreState() {
  const s = await chrome.storage.local.get(["text", "server", "speed", "voice", "model"]);
  if (s.text) $("text").value = s.text;
  if (s.server) $("server").value = s.server;
  if (s.speed) $("speed").value = s.speed;
  if (s.voice) $("voice").value = s.voice;
  if (s.model) $("model").dataset.saved = s.model;
}

async function ensureOffscreen() {
  if (chrome.offscreen.hasDocument && (await chrome.offscreen.hasDocument())) return;
  await chrome.offscreen.createDocument({
    url: "offscreen.html",
    reasons: ["AUDIO_PLAYBACK"],
    justification: "Keep novel narration playing after the popup closes.",
  });
}

async function refreshVoices() {
  try {
    const data = await (await fetch(base() + "/voices")).json();
    const sel = $("voice");
    const cur = sel.value;
    sel.innerHTML = "";
    data.voices.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
    const saved = (await chrome.storage.local.get(["voice"])).voice;
    if (saved && data.voices.includes(saved)) sel.value = saved;
    else if (data.voices.includes(cur)) sel.value = cur;
  } catch (e) {
    setStatus("voices error: " + e.message);
  }
}

async function refreshModels() {
  try {
    const data = await (await fetch(base() + "/llm/models")).json();
    const sel = $("model");
    sel.innerHTML = "";
    data.available.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m.split("/").pop();
      sel.appendChild(opt);
    });
    const saved = $("model").dataset.saved;
    sel.value = saved && data.available.includes(saved) ? saved : data.active;
  } catch (e) {
    setStatus("models error: " + e.message);
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.target === "popup" && msg.type === "STATUS") {
    setStatus(msg.text);
    if (["ended", "stopped"].includes(msg.text) || msg.text.startsWith("play error")) {
      $("speak").disabled = false;
    }
  }
  return false;
});

document.addEventListener("DOMContentLoaded", async () => {
  await restoreState();
  await refreshVoices();
  await refreshModels();
  ["text", "server", "speed"].forEach((id) => $(id).addEventListener("input", saveState));
  $("voice").addEventListener("change", saveState);
  $("model").addEventListener("change", async () => {
    await saveState();
    try {
      const r = await fetch(base() + "/llm/model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: $("model").value }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || r.statusText);
      setStatus(data.status);
    } catch (e) {
      setStatus("model error: " + e.message);
    }
  });
});

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
    const r = await fetch(base() + "/normalize/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("text").value }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || r.statusText);
    $("chunks").textContent = data.chunks
      .map((c) => `[${c.kind}/${c.lang}] ${c.spoken}`)
      .join("\n");
    setStatus(`preview: ${data.chunks.length} chunks`);
  } catch (e) {
    setStatus("preview error: " + e.message);
  }
});

$("speak").addEventListener("click", async () => {
  $("speak").disabled = true;
  try {
    await ensureOffscreen();
    await chrome.runtime.sendMessage({
      target: "offscreen",
      type: "PLAY",
      server: base(),
      text: $("text").value,
      speed: parseFloat($("speed").value) || 1.0,
      voice: $("voice").value,
    });
    setStatus("sent to player...");
  } catch (e) {
    setStatus("speak error: " + e.message);
    $("speak").disabled = false;
  }
});

$("stop").addEventListener("click", async () => {
  try {
    await chrome.runtime.sendMessage({ target: "offscreen", type: "STOP" });
  } catch (e) {
    setStatus("stop error: " + e.message);
  }
});

$("register").addEventListener("click", async () => {
  setStatus("registering...");
  try {
    const file = $("ref_audio").files[0];
    if (!file) throw new Error("audio file required");
    if (!$("ref_text").value.trim()) throw new Error("ref_text required");
    const form = new FormData();
    form.append("ref_audio", file);
    form.append("ref_text", $("ref_text").value.trim());
    const r = await fetch(base() + "/voices/register", { method: "POST", body: form });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || r.statusText);
    await refreshVoices();
    $("voice").value = data.voice;
    await saveState();
    setStatus("registered: " + data.voice);
  } catch (e) {
    setStatus("register error: " + e.message);
  }
});
