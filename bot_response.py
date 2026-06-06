import random
from typing import Any

from database_utilities import connect_db
from logger import logger


def get_bot_response(response_key: str, **kwargs: Any) -> str:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        if response_key == "greeting":
            cursor.execute("""
                SELECT response_text
                FROM bot_responses
                WHERE response_key LIKE 'greeting%'
            """)
            rows: list[tuple[str]] = cursor.fetchall()
            response = random.choice(rows)[0] if rows else "Hello! I am your math chatbot."
        else:
            cursor.execute(
                "SELECT response_text FROM bot_responses WHERE response_key = %s",
                (response_key,)
            )
            row: tuple[str] | None = cursor.fetchone()
            response = row[0] if row else f"Missing response: {response_key}"

        for key, value in kwargs.items():
            response = response.replace("{" + key + "}", str(value))

        return response

    except Exception:
        logger.exception("get_bot_response failed")
        return "I had trouble loading a response."
    finally:
        cursor.close()
        conn.close()
