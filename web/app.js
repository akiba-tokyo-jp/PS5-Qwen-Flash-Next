/* SPDX-License-Identifier: MIT */
"use strict";
const byId = id => document.getElementById(id);
let offset = 0, samples = [], lastRequest = null, polling = false;
const number = value => typeof value === "number" && Number.isFinite(value);
const show = (id, text) => { byId(id).textContent = text; };
const bytes = value => !number(value) ? "—" : value >= 2 ** 30 ? (value / 2 ** 30).toFixed(2) + " GiB" : (value / 2 ** 20).toFixed(1) + " MiB";
function tick() {
  const date = new Date(Date.now() + offset);
  show("clock", new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "medium"}).format(date));
  show("timezone", "Server clock · " + Intl.DateTimeFormat().resolvedOptions().timeZone);
}
function chart() {
  const canvas = byId("chart"), ratio = devicePixelRatio || 1;
  const width = canvas.clientWidth || 300, height = 90;
  canvas.width = width * ratio; canvas.height = height * ratio;
  const context = canvas.getContext("2d"); context.scale(ratio, ratio);
  const maximum = Math.max(1, ...samples.filter(number));
  context.strokeStyle = "#334539"; context.lineWidth = 1;
  context.beginPath(); context.moveTo(0, height - 1); context.lineTo(width, height - 1); context.stroke();
  context.strokeStyle = "#c7db9d"; context.lineWidth = 2; context.beginPath();
  let connected = false;
  samples.forEach((value, index) => {
    if (!number(value)) { connected = false; return; }
    const x = index * width / 59, y = height - 5 - value / maximum * (height - 10);
    connected ? context.lineTo(x, y) : context.moveTo(x, y); connected = true;
  });
  context.stroke();
}
async function poll() {
  if (polling) return; polling = true;
  try {
    const response = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error("Telemetry unavailable");
    const data = await response.json(), request = data.request || {}, metrics = request.metrics || {};
    if (number(data.server_epoch_ms)) offset = data.server_epoch_ms - Date.now();
    show("backend", data.backend === "demo" ? "DEMO TELEMETRY · No model or PS5 hardware is sampled. Generation counters come only from external demo requests."
      : data.model_loaded ? "MODEL TELEMETRY · Missing hardware counters are shown as unavailable."
      : "MONITOR ONLY · No model loaded. Inference rates remain unavailable.");
    if (request.id !== lastRequest) { samples = []; lastRequest = request.id; }
    const rate = data.busy ? request.live_tokens_per_second : metrics.decode_tokens_per_second;
    show("rate", number(rate) ? rate.toFixed(2) : "—");
    show("rate-label", data.busy ? "Generation rate · last 5 seconds" : "Last session · decode average");
    samples.push(number(rate) ? rate : null); if (samples.length > 60) samples.shift(); chart();
    show("tokens", (metrics.generated_tokens || 0).toLocaleString());
    show("ttft", number(metrics.ttft_ms) ? (metrics.ttft_ms / 1000).toFixed(2) + " s" : "—");
    show("elapsed", number(request.elapsed_ms) ? (request.elapsed_ms / 1000).toFixed(1) + " s" : "—");
    show("state", data.quarantined ? "Backend quarantined" : request.state || "Idle");
    const cpu = data.hardware?.cpu || {}, gpu = data.hardware?.gpu || {};
    show("cpu-name", cpu.name || "Not sampled"); show("cpu-threads", cpu.logical_threads || "—");
    show("cpu-usage", number(cpu.app_usage_percent) ? cpu.app_usage_percent.toFixed(1) + "%" : "—");
    show("gpu-name", gpu.name || "Not sampled");
    show("gpu-usage", number(gpu.usage_percent) ? gpu.usage_percent.toFixed(1) + "%" : "Unavailable");
    show("gpu-memory", bytes(gpu.total_bytes) + " / " + bytes(gpu.free_bytes));
    const cache = data.expert_cache || {};
    const total = (cache.hits || 0) + (cache.misses || 0);
    show("cache-hit", total ? (100 * cache.hits / total).toFixed(1) + "%" : "—");
    show("cache-bytes", bytes(cache.uploaded_bytes)); show("prefetch-bytes", bytes(cache.prefetch_advice_bytes));
    show("connection", "Telemetry connected · 1 s refresh");
    show("request", request.id ? "Request " + request.id : "No active request");
    tick();
  } catch { show("connection", "Telemetry disconnected · last values retained"); }
  finally { polling = false; }
}
tick(); poll(); setInterval(tick, 1000); setInterval(poll, 1000); addEventListener("resize", chart);
