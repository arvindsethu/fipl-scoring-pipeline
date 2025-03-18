import json
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from scorecard_scraper import scrape_scorecard
from score_calculator import calculate_scores_and_update_sheet
from sheets_config import SPREADSHEET_ID, SCOPES

def load_config():
    """Load configuration files"""
    with open('config/sheet_mappings.json', 'r') as f:
        sheet_mappings = json.load(f)
    with open('config/field_mappings.json', 'r') as f:
        field_mappings = json.load(f)
    return sheet_mappings, field_mappings

def get_sheet_service():
    """Initialize Google Sheets service"""
    creds = Credentials.from_service_account_file(
        'config/service-account.json', scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()

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
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    values = result.get('values', [])
    
    for idx, row in enumerate(values, start=4):
        if row and row[0] == player_name:
            return idx
    return None

def should_update_match(match_data):
    """
    Determine if a match should be updated based on its status and timing
    Returns: (should_update, new_status)
    """
    current_time = datetime.utcnow()
    start_time = datetime.fromisoformat(match_data['start_time'].replace('Z', '+00:00'))
    
    # For pending matches
    if match_data['status'] == 'pending':
        if current_time >= start_time:
            return True, 'active'
        return False, 'pending'
    
    # For active matches
    if match_data['status'] == 'active':
        time_since_start = current_time - start_time
        
        # If match has run for more than 5 hours, mark as completed
        if time_since_start > timedelta(hours=5):
            return False, 'completed'
        
        # Get time since last update
        last_update = datetime.fromisoformat(match_data['last_update'].replace('Z', '+00:00')) if match_data['last_update'] else start_time
        time_since_update = current_time - last_update
        
        # First 4 hours: update every 15 minutes
        if time_since_start <= timedelta(hours=4):
            return time_since_update >= timedelta(minutes=15), 'active'
        
        # Next hour: update every 30 minutes
        return time_since_update >= timedelta(minutes=30), 'active'
    
    # Completed matches don't need updates
    return False, 'completed'

def update_match_status(match_data, new_status):
    """Update match status and last_update time"""
    match_data['status'] = new_status
    if new_status == 'active':
        match_data['last_update'] = datetime.utcnow().isoformat() + 'Z'
    return match_data

def save_matches_state(matches_data):
    """Save updated matches data back to demo.json"""
    with open('config/demo.json', 'w', encoding='utf-8') as f:
        json.dump(matches_data, f, indent=2)

def update_sheet_for_match(match_data):
    """Process a single match and update the sheet"""
    # Initialize Google Sheets
    sheet_service = get_sheet_service()
    sheet_mappings, field_mappings = load_config()
    
    try:
        # Scrape match data
        print(f"Scraping match {match_data['match_number']}...")
        scorecard_data = scrape_scorecard(match_data['url'])
        
        # Calculate points
        print("Calculating points...")
        with open('output/scorecard.json', 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=4)
        calculate_scores_and_update_sheet()
        
        # Read the updated scorecard with points
        with open('output/scorecard.json', 'r', encoding='utf-8') as f:
            scorecard_data = json.load(f)
        
        # Process each team
        for team_name, team_info in match_data['teams'].items():
            gameweek = match_data['gameweek']
            match_num = team_info['gameweek_match']
            
            # Get column ranges
            columns = get_column_range(sheet_mappings, gameweek, match_num)
            print(f"\nProcessing {team_name} (Gameweek {gameweek}, Match {match_num})")
            print(f"Columns: {columns['played']} (Played), {columns['start']}-{columns['end']} (Stats)")
            
            # Process each player
            if team_name in scorecard_data:
                for player_name, stats in scorecard_data[team_name]['player_stats'].items():
                    # Find player's row
                    row_num = find_player_row(sheet_service, player_name)
                    if row_num is None:
                        print(f"Player not found: {player_name}")
                        continue
                    
                    # Update "Played" column
                    played_range = f"{columns['played']}{row_num}"
                    sheet_service.values().update(
                        spreadsheetId=SPREADSHEET_ID,
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
                        spreadsheetId=SPREADSHEET_ID,
                        range=stats_range,
                        valueInputOption='RAW',
                        body={'values': [ordered_stats]}
                    ).execute()
                    
                    print(f"Updated {player_name} in row {row_num}")
        
        return True
    except Exception as e:
        print(f"Error updating match {match_data['match_number']}: {str(e)}")
        return False

def main():
    """Main function to process matches"""
    print(f"Starting match updates at {datetime.utcnow().isoformat()}Z")
    
    # Load matches
    with open('config/demo.json', 'r') as f:
        data = json.load(f)
    
    # Process each match
    for match in data['matches']:
        should_update, new_status = should_update_match(match)
        
        if should_update:
            print(f"\nProcessing match {match['match_number']} ({match['status']} -> {new_status})")
            if update_sheet_for_match(match):
                match = update_match_status(match, new_status)
        else:
            print(f"\nSkipping match {match['match_number']} (status: {match['status']})")
    
    # Save updated match states
    save_matches_state(data)
    print(f"\nCompleted updates at {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    main() 