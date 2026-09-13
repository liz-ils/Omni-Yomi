/* Omni-Yomi offscreen player: owns fetch + playback so audio survives popup close. */
"use strict";

const player = new Audio();

function status(text) {
  chrome.runtime.sendMessage({ target: "popup", type: "STATUS", text }).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.target !== "offscreen") return false;
  if (msg.type === "PING") {
    sendResponse({ ok: true });
  } else if (msg.type === "PLAY") {
    void play(msg);
  } else if (msg.type === "STOP") {
    player.pause();
    player.removeAttribute("src");
    player.load();
    status("stopped");
  }
  return false;
});

async function play({ server, text, speed, voice, use_llm }) {
  try {
    player.pause();
    status("synthesizing...");
    const r = await fetch(server + "/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speed, voice, use_llm: !!use_llm }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "HTTP " + r.status);
    }
    if (player.src.startsWith("blob:")) URL.revokeObjectURL(player.src);
    player.src = URL.createObjectURL(await r.blob());
    await player.play();
    status("playing");
  } catch (e) {
    status("play error: " + e.message);
  }
}

player.addEventListener("ended", () => status("ended"));
player.addEventListener("error", () => status("player error"));
