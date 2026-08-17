"""
AWS RDS MySQL Database Inspector Utility (Zero Extra Dependencies)
Usage:
    python "CTS Hackathon/inspect_db.py"
    python "CTS Hackathon/inspect_db.py" --table users
    python "CTS Hackathon/inspect_db.py" --table search_history
    python "CTS Hackathon/inspect_db.py" --table comparison_history
    python "CTS Hackathon/inspect_db.py" --table recommendation_history
    python "CTS Hackathon/inspect_db.py" --table products
    python "CTS Hackathon/inspect_db.py" --query "SELECT * FROM users LIMIT 5"
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Auto-detect and switch to virtual environment python if needed
_venv_py = Path(__file__).parent.parent / "backend" / "venv" / "bin" / "python"
if not _venv_py.exists():
    _venv_py = Path(__file__).parent.parent / ".venv" / "bin" / "python"
if _venv_py.exists() and ("backend/venv" not in sys.executable and ".venv" not in sys.executable):
    try:
        import mysql.connector
    except ImportError:
        os.execv(str(_venv_py), [str(_venv_py)] + sys.argv)

# Ensure db module is loaded
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_db_connection, get_db_cursor, DB_HOST, DB_NAME, DB_USER

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def format_table(headers: List[str], rows: List[List[Any]]) -> str:
    """Format headers and rows into an ASCII table without external dependencies."""
    if not headers and not rows:
        return "No data."

    str_rows = [[str(val) if val is not None else "NULL" for val in row] for row in rows]
    col_widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, val in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(val))

    separator = "+-" + "-+-".join(["-" * w for w in col_widths]) + "-+"
    header_line = "| " + " | ".join([h.ljust(col_widths[i]) for i, h in enumerate(headers)]) + " |"

    output_lines = [separator, header_line, separator]
    for row in str_rows:
        row_line = "| " + " | ".join([row[i].ljust(col_widths[i]) if i < len(row) else "".ljust(col_widths[i]) for i in range(len(col_widths))]) + " |"
        output_lines.append(row_line)
    output_lines.append(separator)

    return "\n".join(output_lines)


def print_banner():
    print(f"\n{CYAN}{BOLD}{'=' * 75}")
    print(f" AWS RDS MySQL Database Inspector: `{DB_NAME}`")
    print(f" Host: {DB_HOST} | User: {DB_USER}")
    print(f"{'=' * 75}{RESET}\n")


def show_database_summary():
    print_banner()
    print(f"{YELLOW}{BOLD}📊 Table Record Counts:{RESET}")
    with get_db_cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]

        table_stats = []
        for tbl in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{tbl}`")
                count = cursor.fetchone()[0]
                table_stats.append([tbl, f"{count:,}"])
            except Exception as e:
                table_stats.append([tbl, f"Error: {e}"])

    print(format_table(["Table Name", "Total Records"], table_stats))

    print(f"\n{GREEN}{BOLD}🔍 Quick View Commands:{RESET}")
    print('  python "CTS Hackathon/inspect_db.py" --table users')
    print('  python "CTS Hackathon/inspect_db.py" --table search_history')
    print('  python "CTS Hackathon/inspect_db.py" --table comparison_history')
    print('  python "CTS Hackathon/inspect_db.py" --table recommendation_history')
    print('  python "CTS Hackathon/inspect_db.py" --table products')
    print('  python "CTS Hackathon/inspect_db.py" --query "SELECT * FROM users LIMIT 5"\n')


def inspect_table(table_name: str, limit: int = 10):
    print_banner()
    print(f"{YELLOW}{BOLD}📋 Inspecting Table `{table_name}` (First {limit} records):{RESET}\n")
    try:
        with get_db_cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT %s", (limit,))
            rows = cursor.fetchall()

        if not rows:
            print(f"Table `{table_name}` is currently empty.")
            return

        headers = list(rows[0].keys())
        table_data = []
        for r in rows:
            row_data = []
            for h in headers:
                val = r.get(h)
                val_str = str(val) if val is not None else "NULL"
                if len(val_str) > 35:
                    val_str = val_str[:32] + "..."
                row_data.append(val_str)
            table_data.append(row_data)

        print(format_table(headers, table_data))
    except Exception as e:
        print(f"Error reading table `{table_name}`: {e}")


def execute_custom_query(sql: str):
    print_banner()
    print(f"{CYAN}{BOLD}Executing SQL Query:{RESET} {sql}\n")
    try:
        with get_db_cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            if cursor.description:
                rows = cursor.fetchall()
                if rows:
                    headers = list(rows[0].keys())
                    table_data = []
                    for r in rows:
                        row_data = []
                        for h in headers:
                            val = r.get(h)
                            val_str = str(val) if val is not None else "NULL"
                            if len(val_str) > 40:
                                val_str = val_str[:37] + "..."
                            row_data.append(val_str)
                        table_data.append(row_data)
                    print(format_table(headers, table_data))
                    print(f"\n{GREEN}Total Rows Returned: {len(rows)}{RESET}\n")
                else:
                    print("Query executed successfully. 0 rows returned.")
            else:
                print(f"{GREEN}Query executed successfully. Affected Rows: {cursor.rowcount}{RESET}")
    except Exception as e:
        print(f"Query Execution Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS RDS MySQL Database Inspector")
    parser.add_argument("--table", "-t", type=str, help="Name of table to inspect")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of records to show (default: 10)")
    parser.add_argument("--query", "-q", type=str, help="Custom SQL query to execute")

    args = parser.parse_args()

    if args.query:
        execute_custom_query(args.query)
    elif args.table:
        inspect_table(args.table, limit=args.limit)
    else:
        show_database_summary()
