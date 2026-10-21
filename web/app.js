/* SPDX-License-Identifier: MIT */
"use strict";
const ui = Object.fromEntries(["backend", "conversation", "compose", "prompt", "thinking", "limit", "stop", "send", "state", "metrics", "clear"].map(id => [id, document.getElementById(id)]));
let messages = [], active = null;
function busy(value) { ui.send.disabled = value; ui.stop.disabled = !value; ui.clear.disabled = value; }
function message(role, text) {
  ui.conversation.querySelector(".empty")?.remove();
  const item = document.createElement("div"), label = document.createElement("strong"), content = document.createElement("span");
  item.className = "message"; label.textContent = role; content.textContent = text;
  item.append(label, content); ui.conversation.append(item); return content;
}
function metrics(data) {
  if (!data) return;
  ui.metrics.textContent = `${data.generated_tokens} tokens · TTFT ${data.ttft_ms == null ? "—" : (data.ttft_ms / 1000).toFixed(2) + " s"} · ${data.decode_tokens_per_second == null ? "—" : data.decode_tokens_per_second.toFixed(2) + " tokens/s"}`;
}
ui.compose.addEventListener("submit", async event => {
  event.preventDefault(); if (active || !ui.prompt.value.trim()) return;
  const prompt = ui.prompt.value; ui.prompt.value = ""; message("You", prompt);
  messages.push({role: "user", content: prompt}); const output = message("Assistant", "");
  const id = crypto.randomUUID(); active = id; busy(true); ui.state.textContent = "Preparing";
  const decoder = new TextDecoder("utf-8"), networkDecoder = new TextDecoder("utf-8");
  let text = "", terminal = false;
  try {
    const response = await fetch("/api/generate", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id, messages, max_output_tokens: Number(ui.limit.value), context_tokens: 4096, enable_thinking: ui.thinking.checked})});
    if (!response.ok) throw new Error(`Request rejected (${response.status})`);
    const reader = response.body.getReader(); let buffer = "";
    for (;;) {
      const chunk = await reader.read(); buffer += networkDecoder.decode(chunk.value, {stream: !chunk.done});
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        if (!frame.startsWith("data: ")) continue;
        const data = JSON.parse(frame.slice(6)); if (data.id !== id) throw new Error("Response request ID mismatch");
        ui.state.textContent = data.state; metrics(data.metrics);
        if (data.type === "token") {
          const bytes = Uint8Array.from(atob(data.piece_b64), c => c.charCodeAt(0));
          text += decoder.decode(bytes, {stream: true}); output.textContent = text;
          ui.conversation.scrollTop = ui.conversation.scrollHeight;
        }
        if (data.type === "finished") { terminal = true; if (data.state === "failed") throw new Error(`Generation failed (${data.error})`); }
      }
      if (chunk.done) break;
    }
    if (!terminal) throw new Error("Stream ended without a completion event");
    text += decoder.decode(); output.textContent = text;
    // A stopped response is displayed but excluded from later model history.
    if (ui.state.textContent === "completed") messages.push({role: "assistant", content: text}); else messages.pop();
  } catch (error) {
    ui.state.textContent = error.message; messages.pop();
    output.textContent = text || "The request did not complete.";
    await fetch("/api/cancel", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id})}).catch(() => {});
  } finally { active = null; busy(false); }
});
ui.stop.addEventListener("click", async () => {
  if (!active) return; ui.stop.disabled = true; ui.state.textContent = "Stopping after the current backend operation…";
  try { await fetch("/api/cancel", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: active})}); }
  catch { ui.state.textContent = "Cancellation could not be delivered."; ui.stop.disabled = false; }
});
ui.clear.addEventListener("click", () => { if (active) return; messages = []; ui.conversation.replaceChildren(); ui.state.textContent = "Idle"; });
fetch("/api/status").then(response => response.json()).then(data => {
  ui.backend.textContent = data.backend === "demo" ? "DEMO BACKEND · No model is loaded. Text and timings are interface test data." : "MODEL BACKEND · Console qualification results must be checked separately.";
}).catch(() => { ui.backend.textContent = "Backend unavailable"; ui.send.disabled = true; });
