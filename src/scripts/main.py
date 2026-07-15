import os
import logging
import time
import fetch_authors
import fetch_book_edition
import fetch_book_title
import fetch_subjects
import fetch_works

LOG_FOLDER=os.path.join("..","logs")
LOG_FILE=os.path.join(LOG_FOLDER,"main.log")

def setup_log():
    logger=logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger
    
    formatter=logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M;%S"
    )
    console_handler=logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    os.makedirs(LOG_FOLDER,exist_ok=True)
    file_handler=logging.FileHandler(LOG_FILE,encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
logger=setup_log()

def main():
    logger.info("--Starting--")
    start_time=time.time()

    steps=[
        ("fetch_authors",fetch_authors.run),
        ("fetch_book_edition", fetch_book_edition.run),
        ("fetch_book_title",fetch_book_title.run),
        ("fetch_subjects",fetch_subjects.run),
        ("fetch_works",fetch_works.run)
    ]

    for name, step in steps:
        logger.info(f"--Starting: {name}--")
        try:
            step()
            logger.info(f"--Finished: {name}")
        except Exception:
            logger.exception(f"{name} failed to execute. Stopping---")

            raise

if __name__=="__main__":
    main()
