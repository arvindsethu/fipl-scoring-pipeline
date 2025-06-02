import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime
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

def read_cell_range(service, spreadsheet_id, sheet_name, cell_range):
    """Read a range of cells from the specified sheet"""
    range_str = f"{sheet_name}!{cell_range}"
    try:
        result = service.values().get(spreadsheetId=spreadsheet_id, range=range_str).execute()
        return result.get('values', [])
    except errors.HttpError as e:
        logger.error(f"HTTP error reading range {cell_range} from {sheet_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"General error reading range {cell_range}: {str(e)}")
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

def get_match_data(matches_data, match_number):
    """Get all match data for a specific match number"""
    for match in matches_data.get('matches', []):
        if match.get('match_number') == match_number:
            return match
    return None

def format_time(timestamp_str):
    """Format timestamp string to HH:MM format"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M')
    except Exception as e:
        logger.error(f"Error formatting timestamp: {str(e)}")
        return "Time unavailable"

def format_output(match_data, points_data):
    """Format the output in the requested format"""
    if not match_data:
        return "Match data not available"

    # Sort teams by points - keep as float for both sorting and display
    teams_points = [(row[0], float(row[1])) for row in points_data if len(row) >= 2]
    teams_points.sort(key=lambda x: x[1], reverse=True)

    # Create the message as a single string with \n for line breaks
    message = "*FIPL SCORES UPDATE*\n"
    message += "━━━━━━━━━━━━━━━\n"
    message += f"Last update at: *{format_time(match_data.get('last_update', ''))}*\n"
    message += f"_{match_data.get('scores', 'Scores not available')}_\n"
    message += "━━━━━━━━━━━━━━━\n"

    # Add sorted teams and points
    for idx, (team, points) in enumerate(teams_points, 1):
        message += f"{idx}) *{team}* - {points}\n"

    # Remove the last newline character
    return message.rstrip()

def get_scores_message():
    """Function to get the formatted scores message - can be imported by other scripts"""
    try:
        sheet_service = get_sheet_service()
        points_range = read_cell_range(
            sheet_service, 
            sheets_config.MAIN_SHEET_ID, 
            'Scores and League Table', 
            'A162:B165'
        )

        bucket_name = "fipl_bucket"
        blob_path = "match_states/ipl_2025_matches.json"
        matches_data = read_json_from_gcs(bucket_name, blob_path)
        match_data = get_match_data(matches_data, 73)

        return format_output(match_data, points_range)
    except Exception as e:
        logger.error(f"Error generating scores message: {str(e)}")
        return "Error fetching scores update. Please try again later."

def main():
    """Main function for standalone execution"""
    logger.info("Starting data retrieval...")
    try:
        message = get_scores_message()
        print(message)
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()
