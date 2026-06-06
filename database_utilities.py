import mysql.connector
from typing import Any, Optional

from logger import logger
from typo_utils import closest_match

SYSTEM_DATABASES = {
    "mysql",
    "information_schema",
    "performance_schema",
    "sys"
}
DbRowValue = str | int | float
TableRowsResult = tuple[list[str], list[tuple[Any, ...]] | list[tuple[str, str]]]


def quote_identifier(identifier: str) -> str:
    # Escape table names safely before using them in SQL strings.
    return f"`{str(identifier).replace('`', '``')}`"


def connect_db(database: Optional[str] = None) -> Any:
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="0000",
        database=database
    )


def load_user_databases() -> list[str]:
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SHOW DATABASES")
        rows: list[tuple[str]] = cursor.fetchall()
        return [db for (db,) in rows if db not in SYSTEM_DATABASES]
    except Exception as e:
        logger.exception("load_user_databases failed")
        return [f"Database error: {e}"]
    finally:
        cursor.close()
        conn.close()


def get_tables(database: str) -> list[str]:
    conn = connect_db(database)
    cursor = conn.cursor()

    try:
        cursor.execute("SHOW TABLES")
        rows: list[tuple[str]] = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception:
        logger.exception("get_tables failed for %s", database)
        return []
    finally:
        cursor.close()
        conn.close()


def show_databases() -> str:
    dbs = load_user_databases()
    if not dbs:
        return "No user databases found."
    if len(dbs) == 1 and str(dbs[0]).startswith("Database error:"):
        return dbs[0]
    return "Databases: " + ", ".join(dbs)


def show_tables(db_name: str) -> str:
    tables = get_tables(db_name)
    if not tables:
        return f"No tables found in {db_name}."
    return f"Tables in {db_name}: " + ", ".join(tables)


def fetch_table_rows(db_name: str, table_name: str, limit: int = 25) -> TableRowsResult:
    conn = connect_db(db_name)
    cursor = conn.cursor()

    try:
        if table_name not in get_tables(db_name):
            return [], [("Database error", f"Unknown table: {table_name}")]

        cursor.execute(
            f"SELECT * FROM {quote_identifier(table_name)} LIMIT %s",
            (int(limit),)
        )
        rows: list[tuple[Any, ...]] = cursor.fetchall()
        headers = [desc[0] for desc in cursor.description] if cursor.description else []
        return headers, rows
    except Exception as e:
        logger.exception("fetch_table_rows failed for %s.%s", db_name, table_name)
        return [], [("Database error", str(e))]
    finally:
        cursor.close()
        conn.close()


def get_actions() -> list[tuple[str, str]]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT action_name, symbol FROM actions ORDER BY action_name")
        return cursor.fetchall()
    except Exception:
        logger.exception("get_actions failed")
        return []
    finally:
        cursor.close()
        conn.close()


def get_trigger_words() -> list[tuple[int, str, str, str]]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT t.trigger_id, t.trigger_word, a.action_name, a.symbol
            FROM trigger_words t
            JOIN actions a ON t.action_id = a.action_id
            ORDER BY t.trigger_word
        """)
        return cursor.fetchall()
    except Exception:
        logger.exception("get_trigger_words failed")
        return []
    finally:
        cursor.close()
        conn.close()


def ensure_trigger_word_unique_index():
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT LOWER(trigger_word), COUNT(*)
            FROM trigger_words
            GROUP BY LOWER(trigger_word)
            HAVING COUNT(*) > 1
        """)
        # Stop early if old duplicate rows would make the unique index fail.
        duplicates = cursor.fetchall()
        if duplicates:
            duplicate_names = ", ".join(word for word, _ in duplicates)
            return False, f"Remove duplicate trigger words first: {duplicate_names}"

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'trigger_words'
              AND index_name = 'unique_trigger_word'
        """)
        if cursor.fetchone()[0]:
            return True, "Trigger words already have SQL duplicate protection."

        cursor.execute("""
            ALTER TABLE trigger_words
            ADD UNIQUE KEY unique_trigger_word (trigger_word)
        """)
        conn.commit()
        return True, "SQL duplicate protection is enabled for trigger words."
    except Exception as e:
        logger.exception("ensure_trigger_word_unique_index failed")
        return False, f"Database error: {e}"
    finally:
        cursor.close()
        conn.close()


def ensure_user_memory_table():
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        # This table stores small facts the bot can remember between chats.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                memory_key VARCHAR(255) NOT NULL PRIMARY KEY,
                memory_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    except Exception:
        logger.exception("ensure_user_memory_table failed")
        return False
    finally:
        cursor.close()
        conn.close()


def ensure_saved_equations_table():
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        # Saved equations let the app reuse named formulas later.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_equations (
                equation_name VARCHAR(255) NOT NULL PRIMARY KEY,
                equation_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    except Exception:
        logger.exception("ensure_saved_equations_table failed")
        return False
    finally:
        cursor.close()
        conn.close()


def normalize_equation_text(equation_text: str) -> str:
    # Collapse extra spaces so the same formula is treated consistently.
    return " ".join(str(equation_text).strip().split())


def save_equation_to_db(equation_name: str, equation_text: str) -> tuple[bool, Optional[str]]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        normalized_name = str(equation_name).strip().lower()
        normalized_equation = normalize_equation_text(equation_text)

        cursor.execute("""
            SELECT equation_name
            FROM saved_equations
            WHERE equation_text = %s
              AND equation_name <> %s
            LIMIT 1
        """, (normalized_equation, normalized_name))
        duplicate_row = cursor.fetchone()
        if duplicate_row:
            return False, f'That equation is already saved as "{duplicate_row[0]}".'

        cursor.execute("""
            INSERT INTO saved_equations (equation_name, equation_text)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE equation_text = VALUES(equation_text)
        """, (normalized_name, normalized_equation))
        conn.commit()
        return True, None
    except Exception:
        logger.exception("save_equation_to_db failed")
        return False, "I tried to save that equation, but the database was unavailable."
    finally:
        cursor.close()
        conn.close()


def load_saved_equation(equation_name: str) -> Optional[str]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT equation_text
            FROM saved_equations
            WHERE equation_name = %s
        """, (str(equation_name).strip().lower(),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        logger.exception("load_saved_equation failed")
        return None
    finally:
        cursor.close()
        conn.close()


def get_saved_equations() -> list[tuple[str, str]]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT equation_name, equation_text
            FROM saved_equations
            ORDER BY equation_name
        """)
        return cursor.fetchall()
    except Exception:
        logger.exception("get_saved_equations failed")
        return []
    finally:
        cursor.close()
        conn.close()


def save_user_memory(memory_key: str, memory_value: str) -> bool:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO user_memory (memory_key, memory_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE memory_value = VALUES(memory_value)
        """, (str(memory_key).strip().lower(), str(memory_value).strip()))
        conn.commit()
        return True
    except Exception:
        logger.exception("save_user_memory failed")
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_memory(memory_key: str) -> Optional[str]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT memory_value
            FROM user_memory
            WHERE memory_key = %s
        """, (str(memory_key).strip().lower(),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        logger.exception("get_user_memory failed")
        return None
    finally:
        cursor.close()
        conn.close()


def find_custom_command(user_input: str) -> Optional[str]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        text = user_input.lower().strip()

        cursor.execute("""
            SELECT cc.command_response
            FROM command_aliases ca
            JOIN custom_commands cc ON ca.command_id = cc.command_id
            WHERE LOWER(ca.alias_text) = %s
        """, (text,))
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute("""
            SELECT command_response
            FROM custom_commands
            WHERE LOWER(command_name) = %s
        """, (text,))
        row = cursor.fetchone()
        if row:
            return row[0]

        return None
    except Exception:
        logger.exception("find_custom_command failed")
        return None
    finally:
        cursor.close()
        conn.close()


def save_variable_to_db(name: str, value: Any) -> None:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        # Store values as text so the rest of the app can format them flexibly.
        cursor.execute("""
            INSERT INTO saved_variables (variable_name, variable_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE variable_value = VALUES(variable_value)
        """, (name, str(value)))
        conn.commit()
    except Exception:
        logger.exception("save_variable_to_db failed")
    finally:
        cursor.close()
        conn.close()


def load_saved_variables() -> dict[str, DbRowValue]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT variable_name, variable_value FROM saved_variables")
        rows: list[tuple[str, str]] = cursor.fetchall()
        result: dict[str, DbRowValue] = {}
        for name, value in rows:
            try:
                result[name] = float(value) if "." in value else int(value)
            except Exception:
                result[name] = value
        return result
    except Exception:
        logger.exception("load_saved_variables failed")
        return {}
    finally:
        cursor.close()
        conn.close()


def insert_trigger_word(word: str, action_name: str) -> tuple[bool, str]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        action_name = str(action_name).lower().strip()
        cursor.execute(
            "SELECT action_id FROM actions WHERE LOWER(action_name) = %s OR symbol = %s",
            (action_name, action_name)
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT action_id, action_name, symbol FROM actions")
            actions = cursor.fetchall()
            action_choices = [name.lower() for _, name, _ in actions]
            symbol_choices = [symbol for _, _, symbol in actions]
            corrected_action = (
                closest_match(action_name, action_choices, threshold=0.78)
                or closest_match(action_name, symbol_choices, threshold=0.9)
            )

            if not corrected_action:
                return False, "That action is not valid."

            row = next(
                (action_id, name)
                for action_id, name, symbol in actions
                if name.lower() == corrected_action or symbol == corrected_action
            )
            action_id = row[0]
            action_name = row[1]
        else:
            action_id = row[0]

        cursor.execute("""
            SELECT a.action_name
            FROM trigger_words t
            JOIN actions a ON t.action_id = a.action_id
            WHERE LOWER(t.trigger_word) = %s
        """, (word.lower(),))
        existing = cursor.fetchone()
        if existing:
            return False, f'"{word}" is already stored for "{existing[0]}".'

        cursor.execute("""
            INSERT INTO trigger_words (trigger_word, action_id)
            VALUES (%s, %s)
        """, (word.lower(), action_id))
        conn.commit()
        return True, f'Added "{word}" to action "{action_name}".'
    except Exception as e:
        logger.exception("insert_trigger_word failed")
        return False, f"Database error: {e}"
    finally:
        cursor.close()
        conn.close()


def delete_trigger_word(trigger_id: int) -> tuple[bool, str]:
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT trigger_word FROM trigger_words WHERE trigger_id = %s",
            (trigger_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False, "That trigger word was not found."

        word = row[0]
        cursor.execute(
            "DELETE FROM trigger_words WHERE trigger_id = %s",
            (trigger_id,)
        )
        conn.commit()
        return True, f'Removed trigger word "{word}" from the SQL database.'
    except Exception as e:
        logger.exception("delete_trigger_word failed")
        return False, f"Database error: {e}"
    finally:
        cursor.close()
        conn.close()
