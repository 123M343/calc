import csv
from pathlib import Path
from typing import Any

from database_utilities import connect_db, get_tables, quote_identifier
from logger import logger


EXPORT_DIR = Path(__file__).with_name("exports")


def export_table_to_csv(cursor: Any, table_name: str, output_path: Path) -> int:
    cursor.execute(f"SELECT * FROM {quote_identifier(table_name)}")
    rows: list[tuple[Any, ...]] = cursor.fetchall()
    headers: list[str] = [str(desc[0]) for desc in cursor.description] if cursor.description else []

    # Write one table per file so exports stay easy to inspect.
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)

    return len(rows)


def export_all_data_to_csv() -> str:
    EXPORT_DIR.mkdir(exist_ok=True)

    conn = connect_db("Chat_Bot_DB")
    cursor = conn.cursor()

    try:
        tables = get_tables("Chat_Bot_DB")
        if not tables:
            return "No tables found to export."

        exported: list[str] = []

        for table_name in tables:
            output_path = EXPORT_DIR / f"{table_name}.csv"
            row_count = export_table_to_csv(cursor, table_name, output_path)
            exported.append(f"{table_name}.csv ({row_count} rows)")

        return (
            "Export complete.\n"
            f"Folder: {EXPORT_DIR}\n"
            "Files:\n" + "\n".join(exported)
        )

    except Exception as e:
        logger.exception("export_all_data_to_csv failed")
        return f"Export error: {e}"

    finally:
        cursor.close()
        conn.close()
