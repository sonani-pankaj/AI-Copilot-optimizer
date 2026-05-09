# See: specs/OVERVIEW.md — Input Sanitization (Security)
import re
from typing import List, Tuple

# Each tuple: (compiled regex, replacement string)
_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Passwords
    (re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[\w!@#$%^&*()\-+=\[\]{};:\'",.<>/?\\|`~]+["\']?'),
     r'\1=<REDACTED>'),
    # API keys
    (re.compile(r'(?i)(api[_\-]?key|apikey)\s*[=:]\s*["\']?[\w\-]+["\']?'),
     r'\1=<REDACTED>'),
    # Generic secrets / tokens
    (re.compile(r'(?i)(secret|token|credential|auth)\s*[=:]\s*["\']?[\w\-\.]+["\']?'),
     r'\1=<REDACTED>'),
    # AWS access keys
    (re.compile(r'AKIA[0-9A-Z]{16}'),
     '<AWS_KEY_REDACTED>'),
    # JWT tokens (three base64url segments)
    (re.compile(r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'),
     '<JWT_REDACTED>'),
    # PEM private key blocks
    (re.compile(r'-----BEGIN [A-Z ]+ KEY-----.*?-----END [A-Z ]+ KEY-----', re.DOTALL),
     '<PRIVATE_KEY_REDACTED>'),
    # JDBC / connection strings with embedded credentials
    (re.compile(r'(?i)(jdbc:|mongodb(\+srv)?:|postgresql:|mysql:)//[^:@\s]+:[^@\s]+@'),
     r'\1//<REDACTED>@'),
    # Authorization header values
    (re.compile(r'(?i)(Authorization\s*:\s*(?:Bearer|Basic)\s+)[\w\-\.=+/]+'),
     r'\1<TOKEN_REDACTED>'),
]


def sanitize(text: str) -> str:
    """Strip secrets from *text* before embedding or storing.

    Applies all patterns in order. Returns the sanitized string.
    Never raises — if something unexpected happens the original text is returned.
    """
    try:
        for pattern, replacement in _PATTERNS:
            text = pattern.sub(replacement, text)
    except Exception:
        pass  # sanitization failure must never break the main flow
    return text
