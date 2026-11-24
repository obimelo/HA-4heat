"""Shared socket and reply helpers for 4Heat's local protocol."""

import socket

from .const import SOCKET_BUFFER, SOCKET_TIMEOUT, TCP_PORT


def exchange(host: str, payload: bytes) -> str:
    """Perform one blocking TCP exchange; callers must use an executor."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((host, TCP_PORT))
        sock.sendall(payload)
        return sock.recv(SOCKET_BUFFER).decode()


def reply_tokens(reply: str) -> list[str]:
    """Split the module's bracketed, comma-separated reply."""
    return [
        token.strip()
        for token in reply.replace("[", "").replace("]", "").replace('"', "").split(",")
    ]


def is_reading_token(token: str) -> bool:
    """Check for a marker, five-digit ID and integer value."""
    if len(token) < 8 or not token[0].isascii() or not token[0].isalpha():
        return False
    reading_id = token[1:6]
    if not reading_id.isascii() or not reading_id.isdigit():
        return False
    try:
        int(token[7:])
    except ValueError:
        return False
    return True
