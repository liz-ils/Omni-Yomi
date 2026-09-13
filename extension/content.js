/* Omni-Yomi content script: extract novel body text.
 * Narou (#novel_honbun / #honbun) and Kakuyomu (.widget-episodeBody).
 * Ruby is kept as base(reading) for the server-side pipeline.
 */
"use strict";

function rubyToText(root) {
  root.querySelectorAll("ruby").forEach((ruby) => {
    const base = [];
    const readings = [];
    ruby.childNodes.forEach((node) => {
      if (node.nodeName === "RT" || node.nodeName === "RP") {
        if (node.nodeName === "RT") readings.push(node.textContent);
      } else {
        base.push(node.textContent);
      }
    });
    const text = readings.length > 0 ? `${base.join("")}(${readings.join("")})` : base.join("");
    ruby.replaceWith(document.createTextNode(text));
  });
}

function extractParagraphs(root) {
  rubyToText(root);
  const out = [];
  root.querySelectorAll("p").forEach((p) => {
    const t = p.innerText.trim();
    if (t) out.push(t);
  });
  if (out.length === 0) {
    const t = root.innerText.trim();
    if (t) out.push(t);
  }
  return out;
}

function extractNovel() {
  const selectors = ["#novel_honbun", "#honbun", ".widget-episodeBody"];
  for (const sel of selectors) {
    const root = document.querySelector(sel);
    if (root) {
      const title = (document.querySelector(".novel_title, #novel_title, .widget-episodeTitle") || {})
        .textContent;
      return {
        ok: true,
        title: (title || document.title).trim(),
        paragraphs: extractParagraphs(root.cloneNode(true)),
      };
    }
  }
  return { ok: false, error: "novel body not found" };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "OMNI_YOMI_EXTRACT") {
    sendResponse(extractNovel());
  }
  return false;
});
