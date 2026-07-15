#!/usr/bin/env python
# coding: utf-8

import os
import logging
import time
import requests
import json


BASE_URL="https://openlibrary.org/"


AUTHORS = {
    "jk_rowling": "OL23919A",
    "eliezer_yudkowsky": "OL7288845A",
    "david_colbert": "OL1399035A",
    "philip_nel": "OL622143A",
    "roger_highfield": "OL225628A",
    "john_granger": "OL1388274A",
    "elizabeth_heilman": "OL2699880A",
    "richard_abanes": "OL392226A",
    "julia_eccleshare": "OL2623174A",
    "edmund_kern": "OL1514872A",
}


OUTPUT_FOLDER=os.path.join("..", "..", "data", "Authors")
DELAY_BETWEEN_REQUESTS=0.5
LOG_FOLDER=os.path.join("..","logs")
LOG_FILE = os.path.join(LOG_FOLDER,"fetch_openlibrary_authors.log")


def setup_log():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter= logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler=logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler=logging.FileHandler(LOG_FILE,encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger=setup_log()


def fetch_author(author_id):
    url = f"{BASE_URL}/authors/{author_id}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching author '{author_id}': {error}")
        return None


def make_author_folder_name(label):
    return f"Author={label}"


def save_author_to_json_file(data, label, base_folder):
    author_folder = make_author_folder_name(label)
    folder_path = os.path.join(base_folder, author_folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, "data.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    logger.info(f"Saved to {filepath}")


def fetch_and_save_author(label, author_id, base_folder):

    logger.info(f"Fetching author: '{label}' ({author_id})...")
    data = fetch_author(author_id)

    if data is not None:
        save_author_to_json_file(data, label, base_folder)
    else:
        logger.warning(f"Skipped saving author '{label}' (request failed)")


def run():
    logger.info("Starting OpenLibrary authors download...")

    for label, author_id in AUTHORS.items():
        fetch_and_save_author(label, author_id, OUTPUT_FOLDER)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(f"Saved to '{OUTPUT_FOLDER}'.")


if __name__ == "__main__":
    run()

