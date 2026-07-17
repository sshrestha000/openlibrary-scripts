#!/usr/bin/env python
# coding: utf-8

import json
import logging
import os
import time
import requests
import create_schema
import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG
from pathlib import Path


from create_schema import (
    TABLES,
    build_dataframes,
    get_connection,
    logger,
)


LOG_FOLDER=os.path.join("..","logs")
LOG_FILE=os.path.join(LOG_FOLDER,"sql_log_file.log")


def setup_log():
    logger=logging.getLogger(__name__)
    if logger.handlers:
        logger.handlers.clear()
    logger.setLevel(logging.INFO)
    format=logging.Formatter(
        fmt="%(asctime)s[%(levelname)s]%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler=logging.StreamHandler()
    console_handler.setFormatter(format)
    logger.addHandler(console_handler)

    file_handler=logging.FileHandler(LOG_FILE,encoding="utf-8")
    file_handler.setFormatter(format)
    logger.addHandler(file_handler)

    return logger


logger=setup_log()


BATCH_SIZE=500


TABLE_LOAD_ORDER=["authors", "works", "subjects", "title_search_results","book_editions"]


def order_tables(table_names):
    """Sorts discovered table identifiers to prevent constraint insert dependency loops.
    Ensures primary parent metrics (like authors) populate first before downstream 
    relational dependents link to them.
    """
    ordered=[]
    for t in TABLE_LOAD_ORDER:
        if t in table_names:
            ordered.append(t)

    remaining=[]
    for t in table_names:
        if t not in TABLE_LOAD_ORDER:
            remaining.append(t)
    return ordered+remaining


def insert_sql( table_name,columns, primary_key):
    escaped_columns = []
    for c in columns:
        escaped_columns.append(f"`{c}`")
    col_list = ", ".join(escaped_columns)

    placeholders_list = []
    for i in range(len(columns)):
        placeholders_list.append("%s")
    placeholders = ", ".join(placeholders_list)

    sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"

    if primary_key:
        update_cols = []
        for c in columns:
            if c != primary_key:
                update_cols.append(c)

        if update_cols:
            update_assignments = []
            for c in update_cols:
                update_assignments.append(f"`{c}` = VALUES(`{c}`)")
            update_clause = ", ".join(update_assignments)
            sql += f" ON DUPLICATE KEY UPDATE {update_clause}"

    return sql


def dataframe_to_rows(df):
    """Transforms Pandas structural DataFrames into standard Python tuples.
    Safely converts missing NaN/NaT indices into clean database 'None' elements 
    to guarantee flawless NULL insertion behavior during server processing blocks.
    """
    clean_df = df.astype(object).where(df.notnull(), None)

    rows_list = []
    for row in clean_df.itertuples(index=False, name=None):
        rows_list.append(tuple(row))

    return rows_list


def insert_dataframe(cursor, table_name, df, primary_key):
    """Processes DataFrame rows in distinct batch groupings for performance safety.
    Routes data blocks to execute via batch array commands and prints status logs 
    tracking overall row injection metrics.
    """
    if df.empty:
        logger.warning(f"'{table_name}': No rows found to insert, skipping.")
        return 0

    sql = insert_sql(table_name, list(df.columns), primary_key)
    rows = dataframe_to_rows(df)

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        cursor.executemany(sql, batch)

    if primary_key:
        mode = "upserted"
    else:
        mode = "inserted (no primary key detected -- reruns will duplicate these rows)"

    logger.info(f"'{table_name}': Successfully {mode} {len(rows)} row(s).")
    return len(rows)


def load_data(root):
    """Coordinates parsing of source JSON directories.
    Maps structures using dataframes, opens a secure transaction connection, sorts 
    ingestion pipelines sequentially, and saves record arrays cleanly to MySQL.
    """
    dataframes, primary_keys_by_table, _ = build_dataframes(root)

    if not dataframes:
        logger.warning("No data found to insert — check directory parameters and file patterns.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sorted_tables = order_tables(list(dataframes.keys()))
        for table_name in sorted_tables:
            df = dataframes[table_name]
            primary_key = primary_keys_by_table.get(table_name)

            try:
                insert_dataframe(cursor, table_name, df, primary_key)
                conn.commit()
            except Error as error:
                logger.error(f"Failed inserting into '{table_name}': {error}")
                conn.rollback()
    finally:
        cursor.close()
        conn.close()

    logger.info("Data load complete.")

DEFAULT_ROOT = Path("../../data")
def run(root=None):
    root_path = Path(root) if root else DEFAULT_ROOT
    if not root_path.exists():
        logger.error(f"Directory specification target layout not found: {root_path}")
        raise FileNotFoundError(root_path)

    logger.info("Connecting to MySQL...")
    load_data(root_path)


if __name__ == "__main__":
    run()

