#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Parse a completed read-only PS5 df capture without making a console request."""
from decimal import Decimal
import re


def human_bytes_lower_bound(value):
    """Use decimal units and subtract one displayed unit of precision.

    This is deliberately conservative for either binary or decimal human output,
    including rounding. It is disk capacity, never GPU/physical RAM capacity.
    """
    match = re.fullmatch(r"(\d{1,12}(?:\.\d{1,6})?)([KMGT]?)", value)
    if not match: raise ValueError("A bounded nonnegative df byte quantity is required")
    amount, suffix = match.groups()
    if not suffix:
        if "." in amount: raise ValueError("An unsuffixed byte count must be integral")
        return int(amount)
    precision = len(amount.partition(".")[2])
    quantum = Decimal(1).scaleb(-precision)
    lower = max(Decimal(0), Decimal(amount) - quantum)
    return int(lower * (Decimal(1000) ** ("KMGT".index(suffix) + 1)))


def data_capacity(capture):
    if not isinstance(capture, bytes) or not 0 < len(capture) <= 1 << 20:
        raise ValueError("A completed bounded CPU capacity capture is required")
    text = capture.decode("ascii", errors="strict")
    matches = [line.split() for line in text.splitlines() if line.split() and line.split()[-1] == "/data"]
    if len(matches) != 1: raise ValueError("Exactly one /data filesystem row is required")
    row = matches[0]
    if len(row) != 6 or row[0] != "/user/data" or not re.fullmatch(r"(?:\d|[1-9]\d|100)%", row[4]):
        raise ValueError("The expected complete PS5 data filesystem row is required")
    total, used, free = [human_bytes_lower_bound(value) for value in row[1:4]]
    if not total or used > total or free > total:
        raise ValueError("Inconsistent filesystem capacity")
    return dict(schema="ps5-qwen-data-capacity-parsed-v1", mount="/data",
        free_bytes_lower_bound=free, total_bytes_lower_bound=total,
        interpretation="decimal units; one displayed quantum subtracted",
        console_access=False, freshness_proven=False, capture_completion_proven=False)


def require_storage(capacity, remaining_payload_bytes, receipt_bytes):
    if type(remaining_payload_bytes) is not int or not 0 < remaining_payload_bytes <= 512 << 30:
        raise ValueError("A bounded remaining original payload is required")
    if type(receipt_bytes) is not int or not 0 < receipt_bytes <= 1 << 20:
        raise ValueError("A bounded original receipt size is required")
    required = remaining_payload_bytes + receipt_bytes + (32 << 30)
    if capacity["free_bytes_lower_bound"] < required:
        raise ValueError("Conservative storage headroom cannot admit the original transfer")
    return required
