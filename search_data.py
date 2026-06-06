from database_utilities import connect_db
from logger import logger


def search_all_data(keyword: str) -> str:
    keyword = keyword.strip()

    if not keyword:
        return "Enter a search term."

    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        results: list[str] = []

        # conversation_history
        cursor.execute("""
            SELECT sender, message_text, created_at
            FROM conversation_history
            WHERE message_text LIKE %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (f"%{keyword}%",))
        history_rows: list[tuple[str, str, str]] = cursor.fetchall()

        if history_rows:
            results.append("Conversation History:")
            for sender, message_text, created_at in history_rows:
                results.append(f"[{created_at}] {sender}: {message_text}")
            results.append("")

        # trigger_words + actions
        cursor.execute("""
            SELECT t.trigger_word, a.action_name, a.symbol
            FROM trigger_words t
            JOIN actions a ON t.action_id = a.action_id
            WHERE t.trigger_word LIKE %s
               OR a.action_name LIKE %s
               OR a.symbol LIKE %s
            ORDER BY t.trigger_word
        """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
        trigger_rows: list[tuple[str, str, str]] = cursor.fetchall()

        if trigger_rows:
            results.append("Trigger Words:")
            for trigger_word, action_name, symbol in trigger_rows:
                results.append(f"{trigger_word} -> {action_name} ({symbol})")
            results.append("")

        # custom commands
        cursor.execute("""
            SELECT command_name, command_response
            FROM custom_commands
            WHERE command_name LIKE %s
               OR command_response LIKE %s
            ORDER BY command_name
        """, (f"%{keyword}%", f"%{keyword}%"))
        command_rows: list[tuple[str, str]] = cursor.fetchall()

        if command_rows:
            results.append("Custom Commands:")
            for command_name, command_response in command_rows:
                results.append(f"{command_name} -> {command_response}")
            results.append("")

        # command aliases
        cursor.execute("""
            SELECT ca.alias_text, cc.command_name
            FROM command_aliases ca
            JOIN custom_commands cc ON ca.command_id = cc.command_id
            WHERE ca.alias_text LIKE %s
               OR cc.command_name LIKE %s
            ORDER BY ca.alias_text
        """, (f"%{keyword}%", f"%{keyword}%"))
        alias_rows: list[tuple[str, str]] = cursor.fetchall()

        if alias_rows:
            results.append("Command Aliases:")
            for alias_text, command_name in alias_rows:
                results.append(f"{alias_text} -> {command_name}")
            results.append("")

        # saved variables
        cursor.execute("""
            SELECT variable_name, variable_value
            FROM saved_variables
            WHERE variable_name LIKE %s
               OR variable_value LIKE %s
            ORDER BY variable_name
        """, (f"%{keyword}%", f"%{keyword}%"))
        variable_rows: list[tuple[str, str]] = cursor.fetchall()

        if variable_rows:
            results.append("Saved Variables:")
            for variable_name, variable_value in variable_rows:
                results.append(f"{variable_name} = {variable_value}")
            results.append("")

        if not results:
            return f'No results found for "{keyword}".'

        return "\n".join(results).strip()

    except Exception as e:
        logger.exception("search_all_data failed")
        return f"Search error: {e}"

    finally:
        cursor.close()
        conn.close()
