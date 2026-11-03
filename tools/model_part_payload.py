#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stream bounded host windows and separate actual socket time from file reads."""
import hashlib
import socket
import time
from start_success_route import need

WINDOW = 262144


def send_payload(channel, source, expected_bytes, progress):
    channel.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    digest, sent, sends = hashlib.sha256(), 0, 0
    read_seconds = send_seconds = maximum_send_seconds = 0.0
    with source.open('rb') as stream:
        while True:
            started = time.monotonic(); block = stream.read(WINDOW)
            read_seconds += time.monotonic()-started
            if not block:
                break
            need(sent+len(block) <= expected_bytes, 'Source exceeded its declared model-part extent')
            started = time.monotonic(); channel.sendall(block); elapsed = time.monotonic()-started
            send_seconds += elapsed; maximum_send_seconds = max(maximum_send_seconds, elapsed)
            sent += len(block); sends += 1; digest.update(block); progress(sent)
    need(sent == expected_bytes, 'Source was shorter than its declared model-part extent')
    return dict(bytes=sent, sha256=digest.hexdigest(), send_calls=sends, host_window_bytes=WINDOW,
                TCP_NODELAY=True, file_read_seconds=read_seconds, socket_sendall_seconds=send_seconds,
                maximum_sendall_seconds=maximum_send_seconds)
