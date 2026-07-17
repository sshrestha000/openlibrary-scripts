#!/usr/bin/env python
# coding: utf-8

import logging
import mysql.connector
import os
import pandas as pd
import json
import argparse


from mysql.connector import Error
from db_config import DB_CONFIG
from pathlib import Path


LOG_FOLDER=os.path.join("..","logs")
LOG_FILE=os.path.join(LOG_FOLDER,"sql_schema_logfile.log")


def setup_log():
    """Configures logging handlers to mirror log outputs to both the system terminal
    and a local logfile.
    """
    os.makedirs(LOG_FOLDER, exist_ok=True)
    logger=logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    format=logging.Formatter(
        fmt="%(asctime)s[%(levelname)s] %(message)s",
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


TABLES={
    "authors":"Authors/*/data.json",
    "book_titles":"books/titles/*/*/data.json",
    "book_editions":"books/editions/*/*/data.json",
    "works":"works/*.json",
    "subjects":"subjects/*/data.json",
}

TABLE_SINGULAR={
    "authors":"author",
    "book_editions":"edition",
    "subjects":"subject",
    "works":"work",
    "book_titles":"title"

}
FOREIGN_KEY_SUFFIXES=["_key","_id"]


def clean_record(record):
    """ 
    Some fields look like {"type": "...", "value": 42} when all we
    really want is the 42. This function unwraps those.
    """
    cleaned={}
    for key,value in record.items():
        if isinstance(value,dict) and "value" in value:
            cleaned[key]=value["value"]
        else:
            cleaned[key]=value
    return cleaned


def unwrap_search_result_pages(records):
    """ 
    The book_titles files are search-result pages, not individual
    titles — each one looks like {"docs": [ {...one result...}, ... ]}.
    This pulls all the individual results out into one flat list, so
    each row in our table is one title, not one page of results.
    """
    individual_titles=[]
    for page in records:
        if isinstance(page,dict):
            docs_list=page.get("docs",[])
            for doc in docs_list:
                individual_titles.append(doc)
    return individual_titles



def make_dataframe(records):
    """ 
    turn a list of dicts into pandas dataframe.
    iterates through fields and parses multi-dimensional lists or
    dictionaries into plain string text representations..
    """
    cleaned_records=[]
    for r in records:
        if isinstance(r,dict):
            cleaned_records.append(clean_record(r))
    df=pd.DataFrame(cleaned_records)
    list_columns=set()
    for column in df.columns:
        has_nested_values=False
        for cell in df[column]:
            if isinstance(cell,(dict,list)):
                has_nested_values=True
                if isinstance(cell,list):
                    list_columns.add(column)
        if has_nested_values:
            stringified_values=[]
            for cell in df[column]:
                if isinstance(cell,(dict,list)):
                    stringified_values.append(json.dumps(cell,ensure_ascii=False))
                else:
                    stringified_values.append(cell)
            df[column]=stringified_values

    return df, list_columns


def guess_primary_key(columns):
    """
    evaluates field indices to determine which element most likely acts as
    the primary key constraint identifier for the current dataset entity block.
    """
    candidates=("key","id","work_id","author_id")
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None




def find_foreign_keys(table_name,columns,list_columns):
    foreign_keys={}
    for column in list_columns:
        if column in list_columns:
            continue
        for other_table,singular in TABLE_SINGULAR.items():
            if other_table==table_name:
                continue
            for suffix in FOREIGN_KEY_SUFFIXES:
                if column== singular+suffix:
                    foreign_keys[column]=other_table
    return foreign_keys


def identify_data_type_for_column(series):
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DATETIME"
    return "TEXT"


def create_table_sql(table_name,df,primary_key,foreign_keys,primary_keys_by_table):
    column_lines=[]
    for column in df.columns:
        sql_type=identify_data_type_for_column(df[column])
        if column==primary_key and sql_type=="TEXT":
            sql_type="VARCHAR(255)"
        line=f"   `{column}` {sql_type}"
        if column==primary_key:
            line+= " PRIMARY KEY"
        column_lines.append(line)

    for column, ref_table in foreign_keys.items():
        ref_column=primary_keys_by_table.get(ref_table,"id")
        column_lines.append(
            f"  Foreign key (`{column}`) REFERENCES `{ref_table}` (`{ref_column}`)"
        )
    body=",\n".join(column_lines)
    return f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n{body}\n);"

def build_dataframes(root):
    """ 
    scans the data folders per tables patterns and turns each table's 
    json files into a flattened pandas dataframe
    """
    dataframes = {}
    primary_keys_by_table = {}
    list_columns_by_table = {}

    for table_name, pattern in TABLES.items():
        matches = sorted(Path(root).glob(pattern))
        if not matches:
            logger.warning(f" No files found for '{table_name}' (pattern:{pattern}, skipping). ")
            continue

        records = []
        for file_path in matches[:500]:
            try:
                records.append(json.loads(file_path.read_text(encoding="utf-8")))
            except Exception as error:
                logger.warning(f"skipping unreadable file {file_path.name}: {error}")

        if table_name == "book_titles":
            records = unwrap_search_result_pages(records)
            table_name = "title_search_results"

        if not records:
            logger.warning(f" No rows found for '{table_name}', skipping.")
            continue

        df, list_columns = make_dataframe(records)  
        
        logger.info(f"'{table_name}': Inferred {len(df)} rows, {len(df.columns)} columns")

        dataframes[table_name] = df
        list_columns_by_table[table_name] = list_columns
        primary_keys_by_table[table_name] = guess_primary_key(df.columns)

    return dataframes, primary_keys_by_table, list_columns_by_table


def load_table_ddls(root):
    """ 
    analyzes raw JSON files and generates SQL table creation scripts.
    scans up to 500 JSON files per table, infers the data structure,
    automatically detects primary and foreign keys, and compiles 
    CREATE TABLE statements for database initialization.
    """
    dataframes={}
    primary_keys_by_table={}
    list_columns_by_table={}

    for table_name, pattern in TABLES.items():
        matches=sorted(Path(root).glob(pattern))
        if not matches:
            logger.warning(f" No files found for '{table_name}' (pattern:{pattern}, skipping). ")
            continue

        records=[]
        for file_path in matches[:500]:
            try:
                records.append(json.loads(file_path.read_text(encoding="utf-8")))
            except Exception as error:
                logger.warning(f"skipping unreadable file {file_path.name}: {error}")

        if table_name=="book_titles":
            records=unwrap_search_result_pages(records)
            table_name="title_search_results"

        if not records:
            logger.warning(f" No rows found for '{table_name}', skipping.")
            continue

        df,list_columns=make_dataframe(records)
        logger.info(f"'{table_name}': Inferred {len(df)} rows, {len(df.columns)} columns")

        dataframes[table_name]=df
        list_columns_by_table[table_name]=list_columns
        primary_keys_by_table[table_name]=guess_primary_key(df.columns)

    ddls={}
    for table_name , df in dataframes.items():
        primary_key=primary_keys_by_table[table_name]
        foreign_keys=find_foreign_keys(table_name,df.columns,list_columns_by_table[table_name])
        if foreign_keys:
            logger.info(f"'{table_name}': Found relationship keys {foreign_keys}")

        ddls[table_name]=create_table_sql(
            table_name, df, primary_key, foreign_keys, primary_keys_by_table
        )

    return ddls




def get_connection(with_database=True):
    config = DB_CONFIG.copy()
    if not with_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)


def create_database():
    conn = get_connection(with_database=False)
    cursor = conn.cursor()
    db_name = DB_CONFIG["database"]
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        )
        logger.info(f"Database '{db_name}' is ready.")
    finally:
        cursor.close()
        conn.close()


def create_tables(root):
    ddls=load_table_ddls(root)
    if not ddls:
        logger.warning("no tables to create, check directory parameters and file patterns")
        return

    conn= get_connection()
    cursor=conn.cursor()
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS =0;")

        for name,ddl in ddls.items():
            logger.info(f" creating table '{name}' ")
            try:
                cursor.execute(ddl)
            except Error as error:
                logger.error(f"Failed creating table '{name}': {error}")

        cursor.execute("SET FOREIGN_KEY_CHECKS =1;")
        conn.commit()

    finally:
        cursor.close()
        conn.close()

    logger.info("schema is up to date")

DEFAULT_ROOT = Path("../../data")
def run(root=None):
    root_path = Path(root) if root else DEFAULT_ROOT
    if not root_path.exists():
        logger.error(f"Directory not found: {root_path}")
        raise FileNotFoundError(root_path)

    logger.info("Connecting to MySQL")
    try:
        create_database()
        create_tables(root_path)
    except Error as error:
        logger.error(f"Could not set up schema: {error}")
        raise


if __name__ == "__main__":
    run()

