import os
import json
import logging
from datetime import datetime
import pytz
import tempfile
import re
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient import errors
from .scorecard_scraper import scrape_scorecard
from .score_calculator import calculate_scores_and_update_sheet
import sheets_config

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
TMP_DIR = tempfile.gettempdir()  # This will get the correct temp directory for any OS

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Ensure we see important sheet updates

class SheetUpdateError(Exception):
    """Custom exception for sheet update errors"""
    pass

def save_matches_data(matches_data):
    """Save updated matches data back to matches file in config directory"""
    try:
        with open(sheets_config.MATCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches_data, f, indent=2)
        logger.info(f"Successfully saved matches data to {sheets_config.MATCHES_FILE}")
    except Exception as e:
        logger.error(f"Error saving matches data: {str(e)}")
        raise

def load_config():
    """Load configuration files"""
    try:
        # Load sheet mappings
        sheet_mappings_path = os.path.join(CONFIG_DIR, 'sheet_mappings.json')
        with open(sheet_mappings_path, 'r', encoding='utf-8') as f:
            sheet_mappings = json.load(f)
            
        # Load field mappings
        field_mappings_path = os.path.join(CONFIG_DIR, 'field_mappings.json')
        with open(field_mappings_path, 'r', encoding='utf-8') as f:
            field_mappings = json.load(f)
            
        return sheet_mappings, field_mappings
        
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

def get_sheet_service():
    """Get Google Sheets service"""
    try:
        creds_path = os.path.join(CONFIG_DIR, 'credentials.json')
        creds = Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return build('sheets', 'v4', credentials=creds).spreadsheets()
    except Exception as e:
        logger.error(f"Error getting sheet service: {str(e)}")
        raise

def load_matches():
    """Load matches data from config file"""
    try:
        with open(sheets_config.MATCHES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading matches data: {str(e)}")
        raise

def validate_column_format(column: str) -> bool:
    """Validate if column format is correct (A-Z, AA-ZZ, or AAA-ZZZ)"""
    return bool(re.match(r'^[A-Z]{1,3}$', column))

def get_column_range(sheet_mappings, gameweek, match_num):
    """Get column range for a specific gameweek and match number with validation"""
    try:
        gameweek_data = sheet_mappings['gameweeks'].get(str(gameweek))
        if not gameweek_data:
            raise ValueError(f"Invalid gameweek: {gameweek}")
            
        match_key = f'match{match_num}'
        if match_key not in gameweek_data:
            raise ValueError(f"Invalid match number {match_num} for gameweek {gameweek}")
            
        column_range = {
            'played': gameweek_data['played'],
            'start': gameweek_data[match_key]['start'],
            'end': gameweek_data[match_key]['end']
        }
        
        # Validate column format
        for key, value in column_range.items():
            if not validate_column_format(value):
                raise ValueError(f"Invalid column format for {key}: {value}")
                
        return column_range
        
    except KeyError as e:
        logger.error(f"Missing required mapping in sheet_mappings.json: {str(e)}")
        raise SheetUpdateError(f"Configuration error: {str(e)}")

def find_player_row(sheet_service, player_name):
    """Find row number for a player"""
    range_name = f'A4:A255'  # Player names column
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
    
    # If match is not_started and start time has passed
    if match_data['status'] == 'not_started' and current_time >= start_time:
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

def update_sheet_with_retry(service, spreadsheet_id, range_name, values, value_input_option='RAW'):
    """Update sheet with single retry after 1 minute if quota is exceeded"""
    try:
        return service.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body={'values': values}
        ).execute()
    except errors.HttpError as e:
        if e.resp.status in [429, 503]:  # Quota exceeded or backend error
            logger.warning(f"Sheet API quota exceeded, waiting 60 seconds before retry")
            time.sleep(60)  # Wait for 1 minute
            try:
                return service.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body={'values': values}
                ).execute()
            except errors.HttpError as retry_error:
                logger.error(f"Sheet update failed after retry: {str(retry_error)}")
                raise SheetUpdateError(f"Failed to update sheet after retry: {str(retry_error)}")
        else:
            logger.error(f"Sheet update failed: {str(e)}")
            raise SheetUpdateError(f"Failed to update sheet: {str(e)}")

def update_team_stats(sheet_service, sheet_mappings, match_data, scorecard_data):
    """Update team stats (SR and Economy) for a match"""
    try:
        # Calculate target row based on match number
        target_row = sheet_mappings['team_stats']['start_row'] + match_data['match_number'] - 1
        
        # Get team stats columns
        columns = sheet_mappings['team_stats']['columns']
        
        # Get teams in order from match_data
        teams = list(match_data['teams'].keys())
        if len(teams) != 2:
            logger.warning(f"Expected 2 teams in match_data, found {len(teams)}")
            return
            
        # Update team1 stats if available
        if teams[0] in scorecard_data:
            team1_values = [
                scorecard_data[teams[0]]['average_strike_rate'],
                scorecard_data[teams[0]]['average_economy']
            ]
            team1_range = f"{columns['team1_sr']}{target_row}:{columns['team1_economy']}{target_row}"
            update_sheet_with_retry(
                sheet_service,
                sheets_config.SPREADSHEET_ID,
                team1_range,
                [team1_values]
            )
        
        # Update team2 stats if available
        if teams[1] in scorecard_data:
            team2_values = [
                scorecard_data[teams[1]]['average_strike_rate'],
                scorecard_data[teams[1]]['average_economy']
            ]
            team2_range = f"{columns['team2_sr']}{target_row}:{columns['team2_economy']}{target_row}"
            update_sheet_with_retry(
                sheet_service,
                sheets_config.SPREADSHEET_ID,
                team2_range,
                [team2_values]
            )
        
        if teams[0] in scorecard_data or teams[1] in scorecard_data:
            logger.info(f"Updated team stats for match {match_data['match_number']}")
        
    except Exception as e:
        logger.error(f"Error updating team stats: {str(e)}")

def update_sheet_for_match(match_data, scorecard_data=None):
    """Process a single match and update the sheet with improved error handling"""
    sheet_service = get_sheet_service()
    sheet_mappings, field_mappings = load_config()
    updated_players = []

    try:
        # If scorecard_data not provided, scrape and calculate
        if scorecard_data is None:
            # Scrape match data
            scorecard_data = scrape_scorecard(match_data['url'])
            
            # If scraping failed after all retries, return False immediately
            if isinstance(scorecard_data, dict) and 'error' in scorecard_data:
                logger.error(f"Failed to scrape match {match_data['match_number']} after all retries")
                return False, scorecard_data.get('error', 'Unknown error')
            
            # Save scorecard data to temp file
            scorecard_path = os.path.join(TMP_DIR, f"scorecard_{match_data['match_number']}.json")
            os.makedirs(TMP_DIR, exist_ok=True)
            
            with open(scorecard_path, 'w', encoding='utf-8') as f:
                json.dump(scorecard_data, f, indent=4)
            
            # Calculate points and get updated scorecard data
            calculate_scores_and_update_sheet(scorecard_path)
            
            # Read the updated scorecard with points
            with open(scorecard_path, 'r', encoding='utf-8') as f:
                scorecard_data = json.load(f)
        
        # Update team stats
        update_team_stats(sheet_service, sheet_mappings, match_data, scorecard_data)
        
        # Process each team
        for team_name, team_info in match_data['teams'].items():
            gameweek = match_data['gameweek']
            match_num = team_info['gameweek_match']
            
            try:
                # Get and validate column ranges
                columns = get_column_range(sheet_mappings, gameweek, match_num)
            except (ValueError, SheetUpdateError) as e:
                logger.error(f"Invalid column range for gameweek {gameweek}, match {match_num}: {str(e)}")
                continue
            
            if team_name in scorecard_data:
                for player_name, stats in scorecard_data[team_name]['player_stats'].items():
                    # Find player's row
                    row_num = find_player_row(sheet_service, player_name)
                    if row_num is None:
                        logger.warning(f"Player not found in sheet: {player_name}")
                        continue
                    
                    try:
                        # Update "Played" column
                        played_range = f"{columns['played']}{row_num}"
                        update_sheet_with_retry(
                            sheet_service,
                            sheets_config.SPREADSHEET_ID,
                            played_range,
                            [['Yes']]
                        )
                        
                        # Prepare player stats in correct order
                        ordered_stats = []
                        for field, sheet_col in field_mappings['scorecard_to_sheet'].items():
                            ordered_stats.append(stats.get(field, 0))
                        
                        # Update stats columns
                        stats_range = f"{columns['start']}{row_num}:{columns['end']}{row_num}"
                        update_sheet_with_retry(
                            sheet_service,
                            sheets_config.SPREADSHEET_ID,
                            stats_range,
                            [ordered_stats]
                        )
                        
                        updated_players.append(player_name)
                        
                    except SheetUpdateError as e:
                        logger.error(f"Failed to update sheet for player {player_name}: {str(e)}")
                        continue
        
        # Log summary of updates
        if updated_players:
            logger.info(f"Updated {len(updated_players)} players in sheet")
        
        # Clean up temp file if we created it
        if scorecard_data is None:
            try:
                os.remove(scorecard_path)
                logger.info(f"Cleaned up temporary file: {scorecard_path}")
            except Exception as e:
                logger.warning(f"Could not remove temporary file: {str(e)}")
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error updating match {match_data['match_number']}: {str(e)}")
        return False, str(e)

def main(match_data=None):
    """Main function to process a specific match or all matches"""
    logger.info(f"Starting match updates at {datetime.now(pytz.UTC).isoformat()}Z")
    
    try:
        if match_data:
            # Process single match
            should_update, new_status = should_update_match(match_data)
            if should_update:
                logger.info(f"Processing match {match_data['match_number']} ({match_data['status']} -> {new_status})")
                try:
                    success, error = update_sheet_for_match(match_data)
                    if success:
                        match_data = update_match_status(match_data, new_status)
                        return match_data
                    return None  # Return None on failure
                except Exception as e:
                    logger.error(f"Error processing match {match_data['match_number']}: {str(e)}")
                    raise
            return match_data
        else:
            # Process all matches (for manual runs)
            matches_file = sheets_config.MATCHES_FILE
            with open(matches_file, 'r') as f:
                data = json.load(f)
            
            for match in data['matches']:
                should_update, new_status = should_update_match(match)
                if should_update:
                    logger.info(f"Processing match {match['match_number']} ({match['status']} -> {new_status})")
                    try:
                        success, error = update_sheet_for_match(match)
                        if success:
                            match = update_match_status(match, new_status)
                    except Exception as e:
                        logger.error(f"Error processing match {match['match_number']}: {str(e)}")
            
            save_matches_data(data)
            logger.info(f"Completed updates at {datetime.now(pytz.UTC).isoformat()}Z")
            return data
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    main() 