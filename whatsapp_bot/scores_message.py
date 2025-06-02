import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient import errors
from google.cloud import storage
from config import sheets_config

# Set up paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, 'credentials.json')

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_sheet_service():
    """Get Google Sheets API service"""
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return build('sheets', 'v4', credentials=creds).spreadsheets()
    except Exception as e:
        logger.error(f"Error initializing Google Sheets service: {str(e)}")
        raise

def read_single_cell(service, spreadsheet_id, sheet_name, cell):
    """Read a single cell value from the specified sheet"""
    range_str = f"{sheet_name}!{cell}"
    try:
        result = service.values().get(spreadsheetId=spreadsheet_id, range=range_str).execute()
        value = result.get('values', [['']])[0][0]  # Safe fallback
        return value
    except errors.HttpError as e:
        logger.error(f"HTTP error reading cell {cell} from {sheet_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"General error reading cell {cell}: {str(e)}")
        raise

def read_json_from_gcs(bucket_name, blob_path):
    """Reads and parses a JSON file from a GCS bucket"""
    try:
        client = storage.Client.from_service_account_json(CREDENTIALS_PATH)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_text()
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error reading JSON from GCS: {str(e)}")
        raise

def get_last_update_for_match(matches_data, match_number):
    """Get the last_update value for a specific match number"""
    for match in matches_data.get('matches', []):
        if match.get('match_number') == match_number:
            return match.get('last_update')
    return None

def main():
    logger.info("Reading cell A162 from 'Scores and League Table'")
    sheet_service = get_sheet_service()

    try:
        cell_value = read_single_cell(sheet_service, sheets_config.MAIN_SHEET_ID, 'Scores and League Table', 'A162')
        print(f"A162 → {cell_value}")
    except Exception as e:
        logger.error(f"Failed to read cell A162: {str(e)}")

    # GCS JSON access
    try:
        bucket_name = "fipl_bucket"
        blob_path = "match_states/ipl_2025_matches.json"
        matches_data = read_json_from_gcs(bucket_name, blob_path)
        last_update = get_last_update_for_match(matches_data, 72)

        if last_update:
            print(f"Match 72 last_update → {last_update}")
        else:
            print("Match 72 not found in the JSON.")
    except Exception as e:
        logger.error(f"Failed to load or parse match JSON: {str(e)}")

if __name__ == "__main__":
    main()
