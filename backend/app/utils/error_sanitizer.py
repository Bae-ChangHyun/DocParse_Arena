"""Sanitize error messages to prevent leaking secrets or internal paths."""
import re


def sanitize_error(e: Exception) -> str:
    msg = str(e)
    # Redact known API key patterns
    msg = re.sub(r'sk-[a-zA-Z0-9_-]+', '[REDACTED]', msg)
    msg = re.sub(r'AIza[a-zA-Z0-9_-]+', '[REDACTED]', msg)
    msg = re.sub(r'key-[a-zA-Z0-9_-]+', '[REDACTED]', msg)
    # Redact internal file paths
    msg = re.sub(r'/[\w/.-]+\.py', '[internal]', msg)
    # Truncate long messages
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return msg
