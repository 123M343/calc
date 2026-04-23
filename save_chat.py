from database_utilities import connect_db
from logger import logger


def save_message(sender, message):
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO conversation_history (sender, message_text)
            VALUES (%s, %s)
        """, (sender, str(message)))
        conn.commit()
    except Exception:
        logger.exception("save_message failed")
    finally:
        cursor.close()
        conn.close()
