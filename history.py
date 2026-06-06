from database_utilities import connect_db
from bot_response import get_bot_response
from logger import logger


def clear_history() -> str:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        # This clears saved chat messages only, not formulas or memory.
        cursor.execute("DELETE FROM conversation_history")
        conn.commit()
        return get_bot_response("history_cleared")
    except Exception as e:
        logger.exception("clear_history failed")
        return f"Could not clear history: {e}"
    finally:
        cursor.close()
        conn.close()
