#!/usr/bin/env python
# coding: utf-8

import requests   
import json      
import time      
import os         
import logging


BASE_URL = "https://openlibrary.org"


SUBJECTS = [
    "science",
    "fiction",
    "fantasy",
    "history",
    "romance",
    "biography",
    "philosophy",
    "poetry",
    "mystery",
    "art",
]


OUTPUT_FOLDER = os.path.join("..", "..", "data", "subjects")
DELAY_BETWEEN_REQUESTS = 0.5
LOG_FOLDER=os.path.join("..","logs")
LOG_FILE = os.path.join(LOG_FOLDER, "fetch_openlibrary_subjects.log")


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


def fetch_subject(subject):
    url = f"{BASE_URL}/subjects/{subject}.json"
    try:
        response = requests.get(url,timeout=10)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching subject '{subject}': {error}")
        return None


def make_subject_folder_name(subject):
    return f"Subject={subject}"


def save_subject_to_json_file(data, subject, base_folder):
    subject_folder = make_subject_folder_name(subject)
    folder_path = os.path.join(base_folder, subject_folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, "data.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    logger.info(f"Saved to {filepath}")


def fetch_and_save_subject(subject, base_folder):
    logger.info(f"Fetching subject: '{subject}'...")
    data = fetch_subject(subject)
    if data is not None:
        save_subject_to_json_file(data, subject, base_folder)
    else:
        logger.warning(f"Skipped saving subject '{subject}' (request failed)")


def run():
    logger.info("Starting OpenLibrary subjects download...")
    for subject in SUBJECTS:
        fetch_and_save_subject(subject,OUTPUT_FOLDER)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(f"Check the '{OUTPUT_FOLDER}' folder.")


if __name__ == "__main__":
    run()

