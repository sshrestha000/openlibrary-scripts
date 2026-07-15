#!/usr/bin/env python
# coding: utf-8

import requests
import json
import time
import os
import logging


BASE_URL="https://openlibrary.org/search.json"


TITLES = [
    "harry potter",
    "the hobbit",
    "percy jackson",
    "lord of the rings",
    "the hunger games",
    "chronicles of narnia",
]


PAGES_PER_TITLE = 10
OUTPUT_FOLDER = os.path.join("..", "..", "data", "books", "titles")
DELAY_BETWEEN_REQUESTS = 0.5
LOG_FOLDER=os.path.join("..","logs")
LOG_FILE = os.path.join(LOG_FOLDER,"fetch_openlibrary_books.log")


def setup_logging():
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


logger = setup_logging()


def fetch_page(title, page):
    params = {
        "title": title,
        "page": page
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()  
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching '{title}' page {page}: {error}")
        return None


def make_title_folder_name(title):
    safe_title = title.lower().replace(" ", "_")
    return f"Title={safe_title}"


def make_page_folder_name(page):
    return f"Page={page:02d}"


def save_page_to_json_file(data, title, page, base_folder):
    title_folder = make_title_folder_name(title)
    page_folder = make_page_folder_name(page)
    folder_path = os.path.join(base_folder, title_folder, page_folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, "data.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    logger.info(f"Saved to {filepath}")


def fetch_and_save_all_pages_for_title(title, num_pages, base_folder):
    for page in range(1, num_pages + 1):
        logger.info(f"Fetching '{title}' - page {page}/{num_pages}...")
        data = fetch_page(title, page)

        if data is not None:
            save_page_to_json_file(data, title, page, base_folder)
        else:
            logger.warning(f"Skipped saving '{title}' page {page} (request failed)")

        time.sleep(DELAY_BETWEEN_REQUESTS)


def run():
    logger.info("Starting OpenLibrary data download...")

    for title in TITLES:
        logger.info(f"Searching for: '{title}'")

        # Fetch every page for this title, saving each one as we go
        fetch_and_save_all_pages_for_title(title, PAGES_PER_TITLE, OUTPUT_FOLDER)

    logger.info(f"Check the '{OUTPUT_FOLDER}' folder for your files.")


if __name__ == "__main__":
    run()

