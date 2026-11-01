# Service overhead and GPU kernel verification

The owner requested the previously identified five improvements in order:1/2 first,3 next, then4/5. The common control is normal47100/placement47200, SELF8858dd5e, driver872cc126/cumulative-idle with persistent shader/pipeline caches disabled. Reboot is unavailable. No CI, agents, learned host inference, precision/cache/budget changes or replay of consumed native cases.

1. Compare a bounded append-only per-request token ledger against per-token files. Every token is still synchronously persisted before publication; complete token IDs/piece bytes and all records must be read back after positive completion.
2. Compare one precisely scoped durable stage pair: the completed llama synchronization followed by the existing before-device-idle marker. Keep both records and all memory observations; write/sync them together before device idle. Never defer a before-operation record, enable this during memory-attribution probes, or leave a pending record at a request boundary.
3. Verify same-device, same-submission-generation completion reuse in the application frontend. Hold the queue lock, check actual completed worker epochs, retain owner/accounting validation and invalidate on every new submission. No counter by itself proves completion. Unknown completion retains resources for ordinary close.
4. With adopted CPU changes, test a bounded HC-path optimization derived from measured current shapes, preserving required graph dependencies and weight precision.
5. Then test a bounded Q4 small-row kernel choice on the actual decode shapes, retaining an independent unchanged control.

Use fresh14-request matched cohorts with common current math, node256/divisor40, tail batching enabled in both arms, Top2 decode and complete target F32/routes/tokens plus four fixed semantic tasks. Measure cold and retained requests separately. Adopt only repeatable whole-request improvement beyond measured A/A spread, no unresolved correctness/completion issue, and a final normal API/native display qualification. Preserve negative results as tested outcomes. Partial GPU ranges do not establish total application gains. The known prefix counting error remains separately disclosed.

Each scope ordinarily closes and restores the exact8858dd5e program/settings. Final verified production placement preserves it as rollback and checks both programs/five settings each natively. Host build failures are preserved without treating them as PS5 launches or physical impossibility.
