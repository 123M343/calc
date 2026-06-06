import re
from typing import Optional

from database_utilities import connect_db
from logger import logger
from typo_utils import closest_match

OPERATIONS: dict[str, list[str]] = {}
ARITHMETIC_SYMBOLS = {"+", "-", "*", "/"}


def load_operations() -> dict[str, list[str]]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT a.symbol, t.trigger_word
            FROM actions a
            JOIN trigger_words t ON a.action_id = t.action_id
        """)

        rows: list[tuple[str, str]] = cursor.fetchall()
        temp: dict[str, list[str]] = {}

        for symbol, word in rows:
            temp.setdefault(symbol, []).append(word.lower())

        OPERATIONS.clear()
        OPERATIONS.update(temp)
        return OPERATIONS

    except Exception:
        logger.exception("load_operations failed")
        OPERATIONS.clear()
        return OPERATIONS

    finally:
        cursor.close()
        conn.close()


def get_operations() -> dict[str, list[str]]:
    return OPERATIONS


def replace_operation_words(text: str) -> str:
    replacements: list[tuple[str, str]] = []
    operation_words: list[str] = []

    for symbol, words in OPERATIONS.items():
        if symbol not in ARITHMETIC_SYMBOLS:
            continue

        for word in words:
            word = str(word).lower().strip()
            if word:
                replacements.append((word, symbol))
                operation_words.append(word)

    replacements.sort(key=lambda item: len(item[0]), reverse=True)

    for word, symbol in replacements:
        pattern = r'\b' + r'\s+'.join(re.escape(part) for part in word.split()) + r'\b'
        text = re.sub(pattern, f" {symbol} ", text)

    words: list[str] = text.split()
    for index, word in enumerate(words):
        if re.search(r'\d|[+\-*/=^()]', word) or len(word) < 3:
            continue

        match: Optional[str] = closest_match(word.lower(), operation_words, threshold=0.84)
        if match and " " not in match:
            for operation_word, symbol in replacements:
                if operation_word == match:
                    words[index] = symbol
                    break

    text = " ".join(words)
    return " ".join(text.split())
