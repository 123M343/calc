from database_utilities import connect_db
from logger import logger


def show_last_10_messages():
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT sender, message_text, created_at
            FROM conversation_history
            ORDER BY created_at DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()

        if not rows:
            return "No messages found."

        rows.reverse()

        lines = ["Last 10 Messages:"]
        for sender, message_text, created_at in rows:
            lines.append(f"[{created_at}] {sender}: {message_text}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("show_last_10_messages failed")
        return f"Could not load last 10 messages: {e}"

    finally:
        cursor.close()
        conn.close()
