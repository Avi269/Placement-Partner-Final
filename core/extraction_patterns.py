"""Centralized regex patterns for data extraction"""

import re


EMAIL_PATTERNS = [
    r"(?:email|e-mail|mail|contact)[\s:]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
]

PHONE_PATTERNS = [
    r"\+91[\s-]?\d{5}[\s-]?\d{5}",  # Indian format
    r"\+\d{1,3}[\s-]?\(?\d{3,5}\)?[\s-]?\d{3,5}[\s-]?\d{4}",  # International
    r"\d{5}[\s-]\d{5}",  # Hyphenated 10-digit
    r"\d{3}[-.\s]\d{3}[-.\s]\d{4}"  # US format
]

EDUCATION_PATTERNS = [
    r"(Bachelor|Master|B\.?Tech|M\.?Tech|MCA|BCA|BSc|MSc|MBA|PhD|Diploma).*"
]

def extract_email(text: str) -> str:
    """Extract email using centralized patterns"""
    for pattern in EMAIL_PATTERNS:
        match = re.search(pattern, text, re.I | re.M)
        if match:
            return match.group(1 if '(' in pattern else 0).lower().strip()
    return ""

def extract_phone(text: str) -> str:
    """Extract phone using centralized patterns"""
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""