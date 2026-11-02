/* SPDX-License-Identifier: MIT
 * A separate non-LTO provider keeps the ordinary main path linked while the
 * measurement executable always takes its early CPU-only completion path.
 */
int qwen_cpu_startup_memory_only(void) { return 1; }
