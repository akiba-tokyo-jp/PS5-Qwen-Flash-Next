# SPDX-License-Identifier: MIT
"""Independent host deadline for an opaque native virtual-source admission."""
class NativeSourceDeadline:
    def __init__(self):
        self.started = None
        self.completed = False

    def observe(self, lines, elapsed):
        if any("model_mapping_before_public_mmap" in line for line in lines):
            raise ValueError("The unqualified file-backed model mmap path is prohibited")
        if any(line.startswith("model_validation_completed GPU_not_started=1 model_loaded=0") for line in lines):
            self.completed = True
        if self.completed:
            return
        if self.started is None and any(line.startswith(("source_virtual_", "model_mapping_")) for line in lines):
            self.started = elapsed
        if self.started is not None and elapsed - self.started > 65:
            raise ValueError("Native virtual-source admission exceeded its independent 65-second observation bound; no further requests")
