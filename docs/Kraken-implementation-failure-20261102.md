# Kraken implementation failure — 2026-11-02

This verification records a failed implementation. No Kraken decoder, package
writer, or engine path was added. Production is unchanged.

## Disposition

The implementation is failed and closed. It is not adopted. This is not a new
console measurement and does not show that hardware decoding is absent.

The earlier CPU entropy comparison remains the measured result: lossless, and
about 97% slower in total delivery. That candidate stays rejected. See
[AMPR-Kraken-revalidation-20261102.md](AMPR-Kraken-revalidation-20261102.md).
Hardware Kraken was not submitted in that campaign, and it was not submitted
here.

## What was checked

External reports and source were read for a procedure that could be
implemented. The checked material does not supply one.

- [drakmor/ampr_emu](https://github.com/drakmor/ampr_emu) replaces APR in
  software and packs with LZ4. It does not call a hardware decoder.
- [ps5-payload-dev/sdk](https://github.com/ps5-payload-dev/sdk) has APR stubs
  and no Kraken sample.
- [EchoStretch/kstuff-lite](https://github.com/EchoStretch/kstuff-lite) and
  [Viktorious-x/ps5-bdjb-modified-ISOs](https://github.com/Viktorious-x/ps5-bdjb-modified-ISOs)
  do not contain a Kraken implementation.
- The 2026-06-25 GameGaz report, and the posts it cites, describe PHU A53
  native loading. The published artifact is `a53.elf`, a binary. No source
  repository for a decoder was linked. That binary was not fetched or
  disassembled for this record.
- Public zlib bindings are `sceZlibInitialize`, `sceZlibInflate`,
  `sceZlibWaitForDone`, and `sceZlibGetResult`, with a 64 KiB output limit.
  They are not a Kraken implementation. No Kraken stream was sent to zlib.

RAD's public description is that a game issues a read and the I/O path writes
decompressed bytes. That description was not turned into code.

## What did not run

No title launch, APR read, hardware Kraken request, GPU call, mount change,
initializer, driver change, or CI run was made for this record. Consumed cases
were not replayed. Draft PR85 stays outside production.

## Consequence

Do not add a Kraken implementation from this verification. Do not treat the
missing implementation as a hardware timing result. The qualified production
placement and driver `872cc126` / cumulative-idle remain in force. Persistent
caches stay disabled.
