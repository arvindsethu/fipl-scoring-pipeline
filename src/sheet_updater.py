import os
import json
import logging
from datetime import datetime
import pytz
import tempfile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from .scorecard_scraper import scrape_scorecard
from .score_calculator import calculate_scores_and_update_sheet
import sheets_config

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
TMP_DIR = tempfile.gettempdir()  # This will get the correct temp directory for any OS

# Configure logging
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration files"""
    with open(os.path.join(CONFIG_DIR, 'sheet_mappings.json'), 'r') as f:
        sheet_mappings = json.load(f)
    with open(os.path.join(CONFIG_DIR, 'field_mappings.json'), 'r') as f:
        field_mappings = json.load(f)
    return sheet_mappings, field_mappings

def get_sheet_service():
    """Initialize Google Sheets service"""
    creds = Credentials.from_service_account_file(
        os.path.join(CONFIG_DIR, 'service-account.json'), 
        scopes=sheets_config.SCOPES
    )
    return build('sheets', 'v4', credentials=creds).spreadsheets()

def get_column_range(sheet_mappings, gameweek, match_num):
    """Get column range for a specific gameweek and match number"""
    gameweek_data = sheet_mappings['gameweeks'][str(gameweek)]
    match_key = f'match{match_num}'
    return {
        'played': gameweek_data['played'],
        'start': gameweek_data[match_key]['start'],
        'end': gameweek_data[match_key]['end']
    }

def find_player_row(sheet_service, player_name):
    """Find row number for a player"""
    range_name = f'A4:A240'  # Player names column
    result = sheet_service.values().get(
        spreadsheetId=sheets_config.SPREADSHEET_ID,
        range=range_name
    ).execute()
    values = result.get('values', [])
    
    for idx, row in enumerate(values, start=4):
        if row and row[0] == player_name:
            return idx
    return None

def should_update_match(match_data):
    """Determine if a match should be updated based on its status and time"""
    current_time = datetime.now(pytz.UTC)
    start_time = datetime.fromisoformat(match_data['start_time'].replace('Z', '+00:00'))
    
    # If match is pending and start time has passed
    if match_data['status'] == 'pending' and current_time >= start_time:
        return True, 'in_progress'
    
    # If match is in progress
    if match_data['status'] == 'in_progress':
        return True, 'in_progress'
    
    return False, match_data['status']

def update_match_status(match_data, new_status):
    """Update match status and last update time"""
    match_data['status'] = new_status
    match_data['last_update'] = datetime.now(pytz.UTC).isoformat()
    return match_data

def save_matches_state(matches_data):
    """Save updated matches data back to demo.json in config directory"""
    output_path = os.path.join(CONFIG_DIR, 'demo.json')
    with open(output_path, 'w') as f:
        json.dump(matches_data, f, indent=2)

def update_sheet_for_match(match_data):
    """Process a single match and update the sheet"""
    # Initialize Google Sheets
    sheet_service = get_sheet_service()
    sheet_mappings, field_mappings = load_config()
    
    try:
        # Scrape match data
        logger.info(f"Scraping match {match_data['match_number']}...")
        scorecard_data = scrape_scorecard(match_data['url'])
        
        # Save scorecard data to temp file
        scorecard_path = os.path.join(TMP_DIR, f"scorecard_{match_data['match_number']}.json")
        logger.info(f"Saving scorecard data to: {scorecard_path}")
        os.makedirs(TMP_DIR, exist_ok=True)  # Ensure temp directory exists
        
        with open(scorecard_path, 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=4)
        
        # Calculate points
        logger.info("Calculating points...")
        calculate_scores_and_update_sheet(scorecard_path)  # Pass the scorecard path
        
        # Read the updated scorecard with points
        with open(scorecard_path, 'r', encoding='utf-8') as f:
            scorecard_data = json.load(f)
        
        # Process each team
        for team_name, team_info in match_data['teams'].items():
            gameweek = match_data['gameweek']
            match_num = team_info['gameweek_match']
            
            # Get column ranges
            columns = get_column_range(sheet_mappings, gameweek, match_num)
            logger.info(f"\nProcessing {team_name} (Gameweek {gameweek}, Match {match_num})")
            logger.info(f"Columns: {columns['played']} (Played), {columns['start']}-{columns['end']} (Stats)")
            
            # Process each player
            if team_name in scorecard_data:
                for player_name, stats in scorecard_data[team_name]['player_stats'].items():
                    # Find player's row
                    row_num = find_player_row(sheet_service, player_name)
                    if row_num is None:
                        logger.info(f"Player not found: {player_name}")
                        continue
                    
                    # Update "Played" column
                    played_range = f"{columns['played']}{row_num}"
                    sheet_service.values().update(
                        spreadsheetId=sheets_config.SPREADSHEET_ID,
                        range=played_range,
                        valueInputOption='RAW',
                        body={'values': [['Yes']]}
                    ).execute()
                    
                    # Prepare player stats in correct order
                    ordered_stats = []
                    for field, sheet_col in field_mappings['scorecard_to_sheet'].items():
                        ordered_stats.append(stats.get(field, 0))
                    
                    # Update stats columns
                    stats_range = f"{columns['start']}{row_num}:{columns['end']}{row_num}"
                    sheet_service.values().update(
                        spreadsheetId=sheets_config.SPREADSHEET_ID,
                        range=stats_range,
                        valueInputOption='RAW',
                        body={'values': [ordered_stats]}
                    ).execute()
                    
                    logger.info(f"Updated {player_name} in row {row_num}")
        
        # Clean up temp file
        try:
            os.remove(scorecard_path)
            logger.info(f"Cleaned up temporary file: {scorecard_path}")
        except Exception as e:
            logger.warning(f"Could not remove temporary file: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating match {match_data['match_number']}: {str(e)}")
        return False

def main():
    """Main function to process matches"""
    logger.info(f"Starting match updates at {datetime.now(pytz.UTC).isoformat()}Z")
    
    try:
        # Load matches
        matches_file = os.path.join(CONFIG_DIR, 'demo.json')
        logger.info(f"Loading matches from: {matches_file}")
        with open(matches_file, 'r') as f:
            data = json.load(f)
        
        # Process each match
        for match in data['matches']:
            should_update, new_status = should_update_match(match)
            
            if should_update:
                logger.info(f"\nProcessing match {match['match_number']} ({match['status']} -> {new_status})")
                try:
                    # Update sheet for this match
                    if update_sheet_for_match(match):
                        # Only update status if sheet update was successful
                        match = update_match_status(match, new_status)
                except Exception as e:
                    logger.error(f"Error processing match {match['match_number']}: {str(e)}")
            else:
                logger.info(f"\nSkipping match {match['match_number']} (status: {match['status']})")
        
        # Save updated match states back to config directory
        save_matches_state(data)
        logger.info(f"\nCompleted updates at {datetime.now(pytz.UTC).isoformat()}Z")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    main() 