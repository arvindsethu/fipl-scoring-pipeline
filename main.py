import logging
from datetime import datetime, timedelta
import pytz
import json
import os
import functions_framework
from src.sheet_updater import main as update_main

# Setup logging for Cloud Functions
logger = logging.getLogger()
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

def get_update_frequency(match_start_time, current_time):
    """Determine update frequency based on match phase"""
    hours_elapsed = (current_time - match_start_time).total_seconds() / 3600
    
    if hours_elapsed <= 4:
        return 15  # First 4 hours: every 15 minutes
    elif hours_elapsed <= 5:
        return 30  # Next hour: every 30 minutes
    else:
        return None  # Match should be completed

def should_process_match(match, current_time):
    """Determine if a match should be processed based on its timing and status"""
    try:
        start_time = datetime.fromisoformat(match['start_time'].replace('Z', '+00:00'))
        current_status = match.get('status', 'pending')
        
        # If match is already completed, keep it completed
        if current_status == "completed":
            return False, None, "completed"
        
        # If match hasn't started yet
        if current_time < start_time:
            return False, None, "pending"
        
        # Get the appropriate update frequency
        frequency = get_update_frequency(start_time, current_time)
        
        # If match should be completed (more than 5 hours elapsed)
        if frequency is None:
            return False, None, "completed"
        
        # Handle in-progress state
        last_update = None
        last_update_str = match.get('last_update')
        if last_update_str and last_update_str != "null":  # Handle both None and "null" string
            try:
                last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
            except ValueError as e:
                logger.warning(f"Invalid last_update format: {last_update_str}")
                last_update = None
        
        # If no previous update or enough time has passed since last update
        if not last_update or (current_time - last_update).total_seconds() >= (frequency * 60):
            return True, frequency, "in_progress"
        
        # Return current state without processing
        return False, frequency, "in_progress"
    except Exception as e:
        logger.error(f"Error in should_process_match: {str(e)}")
        return False, None, match.get('status', 'pending')

@functions_framework.http
def update_scores(request):
    """Cloud Function entry point"""
    try:
        current_time = datetime.now(pytz.UTC)
        logger.info(f"Function triggered at {current_time.isoformat()}")
        
        # Only run between 8 AM and 8 PM UTC
        if not (8 <= current_time.hour < 20):
            logger.info("Outside of operating hours (8 AM - 8 PM UTC)")
            return {'message': 'Outside operating hours'}, 200
        
        logger.info("Starting score update process...")
        
        # Load matches
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        matches_file = os.path.join(config_dir, 'demo.json')
        
        if not os.path.exists(matches_file):
            error_msg = f"Matches file not found: {matches_file}"
            logger.error(error_msg)
            return {'error': error_msg}, 500
        
        with open(matches_file, 'r') as f:
            data = json.load(f)
        
        matches_updated = False
        processed_matches = []
        status_changes = []
        skipped_matches = {"completed": [], "pending": []}  # Track skipped matches by status
        
        # Process each match
        for match in data['matches']:
            match_num = match.get('match_number', 'Unknown')
            old_status = match.get('status', 'pending')
            should_update, frequency, new_status = should_process_match(match, current_time)
            
            # Log status transition if changed
            if old_status != new_status:
                status_changes.append({
                    'match': match_num,
                    'from': old_status,
                    'to': new_status,
                    'time': current_time.isoformat()
                })
                match['status'] = new_status
                matches_updated = True
            
            if should_update:
                logger.info(f"Processing match {match_num} (updating every {frequency} minutes)")
                try:
                    update_main()
                    match['last_update'] = current_time.isoformat()
                    matches_updated = True
                    processed_matches.append(match_num)
                except Exception as e:
                    logger.error(f"Error updating match {match_num}: {str(e)}")
            else:
                # Track skipped matches by their status
                if new_status in ["completed", "pending"]:
                    skipped_matches[new_status].append(match_num)
        
        # Log skipped matches grouped by status
        for status, matches in skipped_matches.items():
            if matches:
                matches_str = ", ".join(str(m) for m in sorted(matches))
                logger.info(f"Skipping {status} matches: {matches_str}")
        
        # Save updated match states if any changes were made
        if matches_updated:
            try:
                with open(matches_file, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info("Updated match states saved")
                if status_changes:
                    logger.info("Status changes: " + json.dumps(status_changes, indent=2))
            except Exception as e:
                logger.error(f"Error saving match states: {str(e)}")
                return {'error': f'Failed to save match states: {str(e)}'}, 500
        
        return {
            'message': 'Success',
            'processed_matches': processed_matches,
            'matches_updated': matches_updated,
            'status_changes': status_changes,
            'skipped_matches': skipped_matches,
            'timestamp': current_time.isoformat()
        }, 200
        
    except Exception as e:
        error_msg = f"Error during score update: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}, 500

if __name__ == "__main__":
    # For local testing
    response, status_code = update_scores(None)
    print(f"\nStatus Code: {status_code}")
    print("Response:", json.dumps(response, indent=2)) 