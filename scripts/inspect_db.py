#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
if not backend_dir.exists():
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Attempt to load tabulate if installed, otherwise provide simple text fallback
try:
    from tabulate import tabulate
    has_tabulate = True
except ImportError:
    has_tabulate = False

    def tabulate(rows, headers=None, tablefmt=None):
        if not rows and not headers:
            return ""
        all_rows = [headers] + list(rows) if headers else list(rows)
        # Compute column widths
        num_cols = max(len(r) for r in all_rows)
        col_widths = [0] * num_cols
        for r in all_rows:
            for i, val in enumerate(r):
                col_widths[i] = max(col_widths[i], len(str(val)))
        
        sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
        lines = [sep]
        if headers:
            hdr_str = "| " + " | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(headers)) + " |"
            lines.append(hdr_str)
            lines.append(sep)
        for r in rows:
            row_str = "| " + " | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(r)) + " |"
            lines.append(row_str)
        lines.append(sep)
        return "\n".join(lines)

from sqlalchemy import text, inspect
from database import engine

def get_dialect():
    return engine.dialect.name

def list_all_tables():
    dialect = get_dialect()
    db_desc = "AWS RDS MySQL" if dialect == "mysql" else f"Local Database ({dialect})"
    print("\n" + "="*60)
    print(f" {db_desc} Tables & Record Counts")
    print("="*60)
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    data = []
    with engine.connect() as conn:
        for tbl in table_names:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM `{tbl}`" if dialect == "mysql" else f'SELECT COUNT(*) FROM "{tbl}"')).scalar()
                data.append([tbl, cnt])
            except Exception as e:
                data.append([tbl, f"Error: {e}"])
                
    print(tabulate(data, headers=["Table Name", "Total Rows"]))
    print()

def inspect_table(table_name: str, limit: int = 10):
    dialect = get_dialect()
    print("\n" + "="*60)
    print(f" Inspecting Table: `{table_name}` ({dialect})")
    print("="*60)
    
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    if not columns:
        print(f"Table `{table_name}` not found or has no columns.")
        return
        
    pk_constraint = inspector.get_pk_constraint(table_name)
    pks = set(pk_constraint.get("constrained_columns", []))
    
    schema_data = []
    for col in columns:
        col_name = col.get("name")
        col_type = str(col.get("type"))
        is_null = "YES" if col.get("nullable", True) else "NO"
        is_pk = "PRI" if col_name in pks else ""
        default_val = str(col.get("default", "None"))
        schema_data.append([col_name, col_type, is_null, is_pk, default_val])
        
    print("\n[SCHEMA / COLUMNS]")
    print(tabulate(schema_data, headers=["Field", "Type", "Null", "Key", "Default"]))
    
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`" if dialect == "mysql" else f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        print(f"\n[TOTAL ROW COUNT]: {count} rows")
        
        if count > 0:
            print(f"\n[SAMPLE DATA (Top {min(limit, count)} rows)]")
            rows_res = conn.execute(text(f"SELECT * FROM `{table_name}` LIMIT {limit}" if dialect == "mysql" else f'SELECT * FROM "{table_name}" LIMIT {limit}'))
            col_names = list(rows_res.keys())
            rows = rows_res.fetchall()
            
            # Truncate very long column values for clean display
            formatted_rows = []
            for r in rows:
                row_list = []
                for val in r:
                    val_str = str(val) if val is not None else "NULL"
                    if len(val_str) > 40:
                        val_str = val_str[:37] + "..."
                    row_list.append(val_str)
                formatted_rows.append(row_list)
                
            print(tabulate(formatted_rows, headers=col_names))
        else:
            print("Table is currently empty.")
        print()

def execute_custom_query(query: str, limit: int = 50):
    print("\n" + "="*60)
    print(f" Executing SQL Query: {query}")
    print("="*60)
    
    with engine.connect() as conn:
        res = conn.execute(text(query))
        if res.returns_rows:
            col_names = list(res.keys())
            rows = res.fetchmany(limit)
            formatted_rows = []
            for r in rows:
                row_list = []
                for val in r:
                    val_str = str(val) if val is not None else "NULL"
                    if len(val_str) > 40:
                        val_str = val_str[:37] + "..."
                    row_list.append(val_str)
                formatted_rows.append(row_list)
            print(tabulate(formatted_rows, headers=col_names))
            print(f"\nReturned {len(formatted_rows)} row(s).")
        else:
            conn.commit()
            print("Query executed successfully (no rows returned).")
        print()

def main():
    parser = argparse.ArgumentParser(description="Inspect Database Tables and Records.")
    parser.add_argument("--table", "-t", type=str, help="Name of the table to inspect (e.g. users, products, categories).")
    parser.add_argument("--tables", "--list", "-l", action="store_true", help="List all tables and row counts.")
    parser.add_argument("--query", "-q", type=str, help="Custom SQL query to execute.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of rows to display (default: 10).")
    
    args = parser.parse_args()
    
    if args.query:
        execute_custom_query(args.query, args.limit)
    elif args.table:
        inspect_table(args.table, args.limit)
    else:
        list_all_tables()

if __name__ == "__main__":
    main()
