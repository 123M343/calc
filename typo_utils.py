import re
from difflib import SequenceMatcher
from typing import Optional


COMMAND_PHRASES = [
    "exit",
    "help",
    "clear history",
    "show databases",
    "show tables",
    "show last 10",
    "export csv",
]

PREFIX_COMMANDS = {
    "search": ["serach", "seach", "sarch"],
    "teach": ["teahc", "teech", "tech"],
}

MATH_WORDS = [
    "what",
    "is",
    "calculate",
    "solve",
    "add",
    "plus",
    "subtract",
    "minus",
    "multiply",
    "multiplied",
    "times",
    "divide",
    "divided",
    "over",
    "half",
    "split",
    "percent",
    "percentage",
    "mile",
    "miles",
    "km",
    "kilometer",
    "kilometers",
    "fahrenheit",
    "celsius",
    "kelvin",
    "ft",
    "feet",
    "foot",
    "cm",
    "meter",
    "meters",
    "binary",
    "hex",
    "hexadecimal",
    "octal",
    "decimal",
    "bitwise",
    "and",
    "or",
    "xor",
    "not",
    "weight",
    "weigh",
    "gram",
    "grams",
    "g",
    "kg",
    "kilogram",
    "kilograms",
    "pound",
    "pounds",
    "lb",
    "lbs",
    "ounce",
    "ounces",
    "oz",
    "sin",
    "cos",
    "tan",
    "log",
    "ln",
    "sqrt",
    "factorial",
    "degrees",
    "radians",
    "exp",
    "linear",
    "quadratic",
    "system",
    "systems",
    "equation",
    "equations",
    "from",
    "to",
    "by",
    "of",
    "that",
]

COMMON_FIXES = {
    "whats": "what is",
    "what's": "what is",
    "wat": "what",
    "waht": "what",
    "si": "is",
    "claculate": "calculate",
    "calcualte": "calculate",
    "slove": "solve",
    "sovle": "solve",
    "plsu": "plus",
    "pls": "plus",
    "ad": "add",
    "substract": "subtract",
    "subtact": "subtract",
    "mutiply": "multiply",
    "mulitply": "multiply",
    "multipy": "multiply",
    "multply": "multiply",
    "divde": "divide",
    "devide": "divide",
    "divied": "divide",
    "dived": "divide",
    "precent": "percent",
    "percet": "percent",
}


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def closest_match(value: str, choices: list[str], threshold: float = 0.82) -> Optional[str]:
    best: Optional[str] = None
    best_score = 0

    for choice in choices:
        score = similarity(value, choice)
        if score > best_score:
            best = choice
            best_score = score

    if best and best_score >= threshold:
        return best
    return None


def normalize_spaces(text: str) -> str:
    return " ".join(str(text).lower().strip().split())


def correct_command_text(text: str) -> str:
    text = normalize_spaces(text)
    if not text:
        return text

    for command, typos in PREFIX_COMMANDS.items():
        for typo in typos:
            if text == typo:
                return command
            if text.startswith(f"{typo} "):
                return command + text[len(typo):]

    if text.startswith("search ") or text.startswith("teach "):
        return text

    match = closest_match(text, COMMAND_PHRASES, threshold=0.78)
    return match or text


def correct_math_words(text: str) -> str:
    words: list[str] = normalize_spaces(text).split()
    corrected: list[str] = []

    for word in words:
        if word in COMMON_FIXES:
            corrected.extend(COMMON_FIXES[word].split())
            continue

        if re.search(r'\d|[+\-*/=^()]', word) or len(word) < 3:
            corrected.append(word)
            continue

        match = closest_match(word, MATH_WORDS, threshold=0.84)
        corrected.append(match or word)

    return " ".join(corrected)
