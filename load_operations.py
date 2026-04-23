import re

from database_utilities import connect_db
from logger import logger

OPERATIONS = {}
ARITHMETIC_SYMBOLS = {"+", "-", "*", "/"}


def load_operations():
    global OPERATIONS

    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT a.symbol, t.trigger_word
            FROM actions a
            JOIN trigger_words t ON a.action_id = t.action_id
        """)

        rows = cursor.fetchall()
        temp = {}

        for symbol, word in rows:
            temp.setdefault(symbol, []).append(word.lower())

        OPERATIONS = temp
        return OPERATIONS

    except Exception:
        logger.exception("load_operations failed")
        OPERATIONS = {}
        return OPERATIONS

    finally:
        cursor.close()
        conn.close()


def get_operations():
    return OPERATIONS


def replace_operation_words(text):
    replacements = []

    for symbol, words in OPERATIONS.items():
        if symbol not in ARITHMETIC_SYMBOLS:
            continue

        for word in words:
            word = str(word).lower().strip()
            if word:
                replacements.append((word, symbol))

    replacements.sort(key=lambda item: len(item[0]), reverse=True)

    for word, symbol in replacements:
        pattern = r'\b' + r'\s+'.join(re.escape(part) for part in word.split()) + r'\b'
        text = re.sub(pattern, f" {symbol} ", text)

    return " ".join(text.split())
