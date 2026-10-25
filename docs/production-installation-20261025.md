# Qualified application production placement

The owner explicitly authorized production placement on 2026-10-25. The exact
qualified fastest SELF and selected performance policy now occupy the registered
title's actual startup path. The original MOSS executable remains a fully verified
rollback artifact; it was **not restored over Qwen after successful deployment**.
See the [sanitized installation record](../config/production-installation.json).

## Installed provenance

- Application source: `db01f30df6a440a53604751b17cc93fe1cbcaa35`.
- SELF: `ed4b360bbe88c691c02f1bc90cc5249c00d8e6ab75f8d89783a03d0699d1669d` (28,017,271 bytes).
- Driver source: `akiba-tokyo-jp/PS5-Vulkan-Inference`, revision
  `872cc1264ad8ba5d6b888b092968fa5858a38c58`, profile `cumulative-idle`.
- Linked driver archive: `b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925`.
- Persistent shader/pipeline caches remain disabled. No driver or model rebuild,
  conversion, retransfer, quantization, expert pruning or CI was performed.
- Original BF16/F32 weights, F32 KV, 711 physical parts at most 512 MiB, 53 active
  Expert cache slots, 512 MiB cache and 8 MiB source window remain unchanged.
- BF16 indexed-vector decode and owned padded-bank reads match the
  [qualified profile](qualified-performance-20261025.md). Non-temporal copies remain disabled.

## Verification after placement

The new deployment used a distinct run binding and one ordinary PS5 title launch.
Arithmetic passed. Both external requests returned 22 tokens with output bytes and
token IDs exactly equal to the previously qualified selected case.

| Request | Prompt tokens | Generated tokens | Decode tokens/s | TTFT |
| --- | ---: | ---: | ---: | ---: |
| 1 | 30 | 22 | 0.391093 | 50.130 s |
| 2 | 30 | 22 | 0.398430 | 49.280 s |

These are deployment checks, not a new matched speedup comparison. Both actual
1920x1080 native scanout-source frames were viewed. They show CPU/GPU identity,
synchronized UTC, 22 generated tokens and rounded 0.39/0.40 tokens/s. Utilization
counters remain unavailable and are displayed as `--`.

Source-worker completion, GPU/model retirement and ordinary OS shutdown passed.
Fresh idle CPU/session observation then passed. Complete raw readback verified
the installed Qwen SELF, all installed application configuration/assets and the
preserved original rollback SELF. No native owner, gateway or loaded model remains.

## Preserved refusal and operating scope

The first distinct attempt refused before publication or GPU/title launch:
6,266-6,270 free kernel pages versus an unchanged 10,142-page prelaunch requirement.
Its evidence is preserved and the consumed attempt was not replayed. A separately
qualified CPU-only Direct reader positively verified the complete original SELF;
its observed free count changed from 6,181 to 12,768 pages. This observation does
not establish proprietary cache behavior. A new distinct case then passed the
same current prelaunch threshold and every native startup guard.

This installs the currently qualified **finite application**, not a continuously
running arbitrary-prompt service. Its completed binding is consumed; another
launch requires a fresh case, fresh idle/headroom/session checks and fresh output
paths. Do not replay the completed launch or weaken those gates. Committed global
execution defaults and GitHub Actions remain disabled. The exact fastest binary
remains installed while the normally closed title waits for a separately admitted
run. Longer contexts, unrestricted requests and sustained service need separate
implementation and qualification.

Private records retain exact remote paths, sessions, run IDs, full controller
inputs, ordinary-close evidence and restoration instructions outside Git.
