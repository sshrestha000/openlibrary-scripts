#!/usr/bin/env python
# coding: utf-8

import requests
import json
import time
import os
import logging


BASE_URL="https://openlibrary.org/works/"


WORKS=[
    "OL15626917W",
    "OL4772214W",
    "OL19963111W",
    "OL15110516W",
    "OL66554W"
]


OUTPUT_FOLDER=os.path.join("..", "..", "data", "works")
DELAY_BETWEEN_REQUESTS=0.5
LOG_FOLDER=os.path.join("..","logs")
LOG_FILE = os.path.join(LOG_FOLDER,"fetch_openlibrary_works.log")


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


def fetch_works(work_id):
    url = f"{BASE_URL}{work_id}.json"
    try:
        response=requests.get(url,timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptopns.RequestEsceptopn as error:
        logger.error(f"Error fetching '{work_id}':{error}")
        return None 


def save_to_json_file(data,base_folder,work_id):
    os.makedirs(base_folder, exist_ok=True)
    filepath = os.path.join(base_folder, f"{work_id}.json")  
    with open(filepath,"w",encoding="utf-8") as file:
        json.dump(data,file,indent=2,ensure_ascii=False)
    logger.info(f"saved to {filepath}")


def run():
    logger.info("starting data download")
    for work_id in WORKS:
        logger.info(f"searching for:'{work_id}'")
        data=fetch_works(work_id)
        if data is not None:
            save_to_json_file(data,OUTPUT_FOLDER,work_id)
        logger.info(f"completed")


if __name__=="__main__":
    run()

