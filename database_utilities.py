import mysql.connector
from logger import logger

SYSTEM_DATABASES = {
    "mysql",
    "information_schema",
    "performance_schema",
    "sys"
}


def connect_db(database=None):
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="0000",
        database=database
    )


def load_user_databases():
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SHOW DATABASES")
        rows = cursor.fetchall()
        return [db for (db,) in rows if db not in SYSTEM_DATABASES]
    except Exception as e:
        logger.exception("load_user_databases failed")
        return [f"Database error: {e}"]
    finally:
        cursor.close()
        conn.close()


def get_tables(database):
    conn = connect_db(database)
    cursor = conn.cursor()

    try:
        cursor.execute("SHOW TABLES")
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        logger.exception("get_tables failed for %s", database)
        return []
    finally:
        cursor.close()
        conn.close()


def show_databases():
    dbs = load_user_databases()
    if not dbs:
        return "No user databases found."
    if len(dbs) == 1 and str(dbs[0]).startswith("Database error:"):
        return dbs[0]
    return "Databases: " + ", ".join(dbs)


def show_tables(db_name):
    tables = get_tables(db_name)
    if not tables:
        return f"No tables found in {db_name}."
    return f"Tables in {db_name}: " + ", ".join(tables)


def fetch_table_rows(db_name, table_name, limit=25):
    conn = connect_db(db_name)
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {int(limit)}")
        rows = cursor.fetchall()
        headers = [desc[0] for desc in cursor.description] if cursor.description else []
        return headers, rows
    except Exception as e:
        logger.exception("fetch_table_rows failed for %s.%s", db_name, table_name)
        return [], [("Database error", str(e))]
    finally:
        cursor.close()
        conn.close()


def get_actions():
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


def find_custom_command(user_input):
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


def save_variable_to_db(name, value):
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
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


def load_saved_variables():
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT variable_name, variable_value FROM saved_variables")
        rows = cursor.fetchall()
        result = {}
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


def insert_trigger_word(word, action_name):
    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT action_id FROM actions WHERE LOWER(action_name) = %s OR symbol = %s",
            (action_name.lower(), action_name)
        )
        row = cursor.fetchone()
        if not row:
            return False, "That action is not valid."

        action_id = row[0]

        cursor.execute("""
            SELECT trigger_id
            FROM trigger_words
            WHERE LOWER(trigger_word) = %s AND action_id = %s
        """, (word.lower(), action_id))
        if cursor.fetchone():
            return False, f'"{word}" is already stored for "{action_name}".'

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
