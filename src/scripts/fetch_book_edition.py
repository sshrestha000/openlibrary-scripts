#!/usr/bin/env python
# coding: utf-8

import os
import logging
import time
import requests
import json


BASE_URL="https://openlibrary.org/"


BOOKS = {
    "pride_and_prejudice": "OL205681W",
    "1984": "OL2064553W", 
    "dune": "OL24871618W",
    "to_kill_a_mockingbird": "OL2654143W",
    "the_great_gatsby": "OL468431W", 
    "the_hobbit": "OL27482W",         
    "the_catcher_in_the_rye": "OL466465W",
    "the_hunger_games": "OL25815995W",
    "the_kite_runner": "OL11537334W",
    "sapiens": "OL22088918W",
}


OUTPUT_FOLDER = os.path.join("..", "..", "data", "books", "editions")
DELAY_BETWEEN_REQUESTS = 0.5
LOG_FOLDER=os.path.join("..","logs")
LOG_FILE = os.path.join(LOG_FOLDER,"fetch_openlibrary_editions.log")
EDITIONS_PER_BOOK = 10


def setup_log():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
  
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_log()


def get_edition_ids_for_work(work_id,limit):
    url = f"{BASE_URL}/works/{work_id}/editions.json" 
    params = {"limit": limit}
    try:
        response = requests.get(url,params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching edition list for '{work_id}': {error}")
        return []

    edition_ids = []
    for entry in data.get("entries", []):
        key = entry.get("key", "")
        edition_id = key.split("/")[-1]
        if edition_id:
            edition_ids.append(edition_id)

    return edition_ids


def fetch_edition_details(edition_id):
    url = f"{BASE_URL}/books/{edition_id}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching edition '{edition_id}': {error}")
        return None


def make_book_folder_name(book_label):
    return f"Book={book_label}"


def make_edition_folder_name(edition_number):
    return f"Edition={edition_number:02d}"


def save_edition_to_json_file(data, book_label, edition_number, base_folder):

    book_folder = make_book_folder_name(book_label)
    edition_folder = make_edition_folder_name(edition_number)
    folder_path = os.path.join(base_folder, book_folder, edition_folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, "data.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    logger.info(f"Saved to {filepath}")



def fetch_and_save_editions_for_book(book_label, work_id, num_editions, base_folder):

    logger.info(f"Looking up edition list for '{book_label}' ({work_id})...")
    edition_ids = get_edition_ids_for_work(work_id,num_editions)

    if not edition_ids:
        logger.warning(f"No editions found for '{book_label}' - skipping")
        return

    for i, edition_id in enumerate(edition_ids, start=1):
        logger.info(f"Fetching '{book_label}' - edition {i}/{len(edition_ids)} ({edition_id})...")
        data = fetch_edition_details(edition_id)

        if data is not None:
            save_edition_to_json_file(data, book_label, i, base_folder)
        else:
            logger.warning(f"Skipped saving '{book_label}' edition {i} (request failed)")

        time.sleep(DELAY_BETWEEN_REQUESTS)


def run():
    logger.info("Starting OpenLibrary editions download...")

    for book_label, work_id in BOOKS.items():
        fetch_and_save_editions_for_book(book_label, work_id,EDITIONS_PER_BOOK, OUTPUT_FOLDER)

    logger.info(f"Saved to '{OUTPUT_FOLDER}'.")


if __name__ == "__main__":
    run()

