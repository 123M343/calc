import re
from typing import Any, Optional, cast

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pytesseract  # type: ignore[import-untyped]
except ImportError:
    pytesseract = None


ALLOWED_WORDS = {
    "x", "y", "z",
    "sin", "cos", "tan",
    "log", "ln", "sqrt",
    "pi", "e",
    "plus", "minus", "times",
    "divide", "divided", "by", "over",
    "multiply", "multiplied",
    "what", "is", "solve", "find",
    "equals", "equal", "to",
}

MATH_WORD_PATTERNS = [
    r"\d+\s+(?:plus|minus|times|divide|divided|multiply|multiplied|over)\s+\d+",
    r"\d+\s+divided\s+by\s+\d+",
    r"\d+\s+to\s+\d+",
]

LEADING_PROBLEM_NUMBER_PATTERN = r"^\d+\s*[\)\.\-:]+\s*"


def ocr_dependencies_ready() -> tuple[bool, Optional[str]]:
    if cv2 is None or pytesseract is None:
        return False, "Install `opencv-python-headless` and `pytesseract` in the project virtual environment."

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False, "Install the Tesseract OCR app on your computer so image scanning can read text."

    return True, None


def normalize_ocr_text(text: str) -> str:
    cleaned = str(text)
    cleaned = cleaned.replace("×", "*")
    cleaned = cleaned.replace("÷", "/")
    cleaned = cleaned.replace("−", "-")
    cleaned = cleaned.replace("=", " = ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return "\n".join(line.strip() for line in cleaned.splitlines())


def looks_like_math_line(text: str) -> bool:
    stripped = str(text).strip()
    if not stripped:
        return False

    # Remove leading problem numbers like "1)" before checking the pattern.
    stripped = re.sub(LEADING_PROBLEM_NUMBER_PATTERN, "", stripped)
    if not stripped:
        return False

    if not re.search(r"\d|[=+\-*/^()]|[xyz]", stripped, re.IGNORECASE):
        return False

    has_symbol_math = re.search(r"[=+\-*/^()]", stripped)
    has_word_math = any(
        re.search(pattern, stripped, re.IGNORECASE)
        for pattern in MATH_WORD_PATTERNS
    )
    if not has_symbol_math and not has_word_math:
        return False

    # Reject lines with too many non-math symbols that usually come from OCR noise.
    if re.search(r"[@#%&_>{}<[\]|\\]", stripped):
        return False

    word_tokens = re.findall(r"[A-Za-z]+", stripped)
    if word_tokens:
        invalid_words = [
            token for token in word_tokens
            if token.lower() not in ALLOWED_WORDS
        ]
        if invalid_words:
            return False

    cleaned_for_ratio = re.sub(r"[0-9A-Za-z=+\-*/^(). ]", "", stripped)
    if len(cleaned_for_ratio) > 2:
        return False

    return True


def extract_math_lines(image_path: str) -> dict[str, Any]:
    ready, error_message = ocr_dependencies_ready()
    if not ready:
        raise RuntimeError(error_message)

    cv2_module = cast(Any, cv2)
    pytesseract_module = cast(Any, pytesseract)

    image = cv2_module.imread(str(image_path))
    if image is None:
        raise RuntimeError("Could not open that image.")

    # Keep preprocessing simple so handwritten and printed math both have a chance.
    grayscale = cv2_module.cvtColor(image, cv2_module.COLOR_BGR2GRAY)
    blurred = cv2_module.GaussianBlur(grayscale, (3, 3), 0)
    processed = cv2_module.adaptiveThreshold(
        blurred,
        255,
        cv2_module.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2_module.THRESH_BINARY,
        31,
        11,
    )

    raw_text = pytesseract_module.image_to_string(processed, config="--psm 6")
    normalized_text = normalize_ocr_text(raw_text)

    math_lines: list[str] = []
    for line in normalized_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Keep only lines that still look like real math after OCR cleanup.
        if not looks_like_math_line(stripped):
            continue

        stripped = re.sub(LEADING_PROBLEM_NUMBER_PATTERN, "", stripped)
        math_lines.append(stripped)

    if not math_lines:
        detail = normalized_text.strip()
        if detail:
            raise RuntimeError(
                "I could not find any math problems in that image.\n\n"
                f"OCR read this text:\n{detail}"
            )
        raise RuntimeError("I could not find any readable text in that image.")

    return {
        "raw_text": normalized_text,
        "math_lines": math_lines,
    }
