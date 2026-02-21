"""
Spotify Charts Combiner

Combines daily Spotify Charts CSV files into a single master dataset
with an added 'date' column derived from filenames.
"""

import os
import glob
import logging
from datetime import datetime
from typing import Optional, List

import pandas as pd


# =========================
# Configuration
# =========================

INPUT_FOLDER = "downloads"
OUTPUT_FILE = "spotify_charts_master.csv"


# =========================
# Logging Setup
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# Utility Functions
# =========================

def extract_date_from_filename(filepath: str) -> Optional[str]:
    """
    Extract and validate date from filename.
    Expected format: YYYY-MM-DD.csv
    """
    filename = os.path.basename(filepath)
    date_str = filename.replace(".csv", "")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


def read_csv_with_fallback(filepath: str) -> pd.DataFrame:
    """
    Read CSV using UTF-8 encoding with fallback to latin-1.
    """
    try:
        return pd.read_csv(filepath, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(filepath, encoding="latin-1")


def combine_csv_files(input_folder: str, output_file: str):

    if not os.path.exists(input_folder):
        logging.error(f"Input folder '{input_folder}' not found.")
        return

    csv_files: List[str] = sorted(
        glob.glob(os.path.join(input_folder, "*.csv"))
    )

    if not csv_files:
        logging.warning("No CSV files found.")
        return

    logging.info(f"Found {len(csv_files)} CSV files.")

    dataframes = []
    failed_files = []

    for index, filepath in enumerate(csv_files, start=1):

        date_str = extract_date_from_filename(filepath)

        if not date_str:
            logging.warning(f"Skipping invalid filename: {os.path.basename(filepath)}")
            failed_files.append(filepath)
            continue

        try:
            df = read_csv_with_fallback(filepath)
            df.insert(0, "date", date_str)
            dataframes.append(df)

        except Exception as e:
            logging.error(f"Failed to process {os.path.basename(filepath)}: {e}")
            failed_files.append(filepath)

        if index % 50 == 0:
            logging.info(f"Processed {index}/{len(csv_files)} files.")

    if not dataframes:
        logging.error("No valid CSV files processed.")
        return

    logging.info("Combining datasets...")
    master_df = pd.concat(dataframes, ignore_index=True)

    if "rank" in master_df.columns:
        master_df = master_df.sort_values(["date", "rank"]).reset_index(drop=True)
    else:
        master_df = master_df.sort_values(["date"]).reset_index(drop=True)

    logging.info("Saving master dataset...")
    master_df.to_csv(output_file, index=False, encoding="utf-8")

    logging.info("Combination complete.")
    logging.info(f"Total rows: {len(master_df):,}")
    logging.info(f"Date range: {master_df['date'].min()} to {master_df['date'].max()}")

    if failed_files:
        logging.warning(f"{len(failed_files)} files failed to process.")


# =========================
# Main
# =========================

def main():
    combine_csv_files(INPUT_FOLDER, OUTPUT_FILE)


if __name__ == "__main__":
    main()