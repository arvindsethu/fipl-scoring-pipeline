import logging
from datetime import datetime, timedelta
import pytz
import json
import os
import functions_framework
from src.sheet_updater import main as update_main
from src.state_manager import StateManager

# Setup logging for Cloud Functions
logging.basicConfig(
    level=logging.INFO,  # Show all info messages
    format='%(message)s'  # Clean format without timestamps
)

# Get logger instance
logger = logging.getLogger(__name__)

# Allow essential match info through
logging.getLogger('src.scorecard_scraper').setLevel(logging.INFO)

# Disable verbose loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)

# Cloud Storage setup
BUCKET_NAME = "fipl_bucket"  # Replace with your bucket name
state_manager = StateManager(BUCKET_NAME)

def parse_datetime(datetime_str):
    """Helper function to parse datetime strings consistently"""
    if not datetime_str or datetime_str == "null":
        return None
    try:
        # First try direct parsing
        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            pass
        
        # Handle timezone format without colon
        if '+0000' in datetime_str:
            try:
                # Try converting +0000 to +00:00
                datetime_str = datetime_str[:-2] + ':' + datetime_str[-2:]
                return datetime.fromisoformat(datetime_str)
            except ValueError:
                pass
            
            try:
                # Try parsing without timezone
                base_dt = datetime.fromisoformat(datetime_str[:-5])
                return base_dt.replace(tzinfo=pytz.UTC)
            except ValueError:
                pass
        
        # Try parsing with dateutil as last resort
        from dateutil import parser
        return parser.parse(datetime_str)
        
    except Exception as e:
        logger.error(f"Error parsing datetime string '{datetime_str}': {str(e)}")
        return None

def format_datetime(dt):
    """Helper function to format datetime consistently"""
    if not dt:
        return None
    try:
        # Always format with UTC timezone and proper ISO format
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.isoformat().replace('+00:00', 'Z')
    except Exception as e:
        logger.error(f"Error formatting datetime: {str(e)}")
        return None

def get_update_frequency(match_start_time, current_time):
    """Determine update frequency based on match phase"""
    hours_elapsed = (current_time - match_start_time).total_seconds() / 3600
    
    if hours_elapsed <= 5:
        return 14  # First 5 hours: every 15 minutes
    else:
        return None  # Match should be completed

def should_process_match(match, current_time):
    """Determine if a match should be processed based on its timing and status"""
    try:
        start_time = parse_datetime(match['start_time'])
        if not start_time:
            logger.error(f"Could not parse start time for match {match.get('match_number', 'Unknown')}")
            return False, None, match.get('status', 'not_started')
            
        current_status = match.get('status', 'not_started')
        
        # If match is already completed, keep it completed
        if current_status == "completed":
            return False, None, "completed"
        
        # If match hasn't started yet
        if current_time < start_time:
            return False, None, "not_started"
        
        # Get the appropriate update frequency
        frequency = get_update_frequency(start_time, current_time)
        
        # If match should be completed (more than 5 hours elapsed)
        if frequency is None:
            return False, None, "completed"
        
        # Handle in-progress state
        last_update = parse_datetime(match.get('last_update'))
        
        # If no previous update or enough time has passed since last update
        if not last_update or (current_time - last_update).total_seconds() >= (frequency * 60):
            return True, frequency, "in_progress"
        
        return False, frequency, "in_progress"
    except Exception as e:
        logger.error(f"Error processing match {match.get('match_number', 'Unknown')}: {str(e)}")
        return False, None, match.get('status', 'not_started')

@functions_framework.http
def update_scores(request):
    """Cloud Function entry point"""
    try:
        current_time = datetime.now(pytz.UTC)
        logger.info(f"Starting match updates at {format_datetime(current_time)}")
        
        # Only run between 8 AM and 8 PM UTC
        if not (8 <= current_time.hour < 20):
            return json.dumps({
                'message': 'Outside operating hours',
                'timestamp': format_datetime(current_time)
            }), 200, {'Content-Type': 'application/json'}
        
        try:
            # Load state from Cloud Storage
            data = state_manager.load_state()
            
            # Verify state integrity
            if not state_manager.verify_state_integrity(data):
                logger.error("Invalid state data structure")
                return json.dumps({
                    'error': 'Invalid state data structure',
                    'timestamp': format_datetime(current_time)
                }), 500, {'Content-Type': 'application/json'}
                
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            return json.dumps({
                'error': f'Failed to load state: {str(e)}',
                'timestamp': format_datetime(current_time)
            }), 500, {'Content-Type': 'application/json'}
        
        matches_updated = False
        processed_matches = []
        status_changes = []
        skipped_matches = {
            "completed": [],
            "not_started": [],
            "in_progress": []  # Added to track in-progress skipped matches
        }
        
        # Process each match
        for match in data['matches']:
            match_num = match.get('match_number', 'Unknown')
            old_status = match.get('status', 'not_started')
            should_update, frequency, new_status = should_process_match(match, current_time)
            
            if old_status != new_status:
                status_changes.append({
                    'match': match_num,
                    'from': old_status,
                    'to': new_status,
                    'time': format_datetime(current_time)
                })
                match['status'] = new_status
                matches_updated = True
            
            if should_update:
                try:
                    # Pass the specific match to update_main
                    updated_match = update_main(match)
                    if updated_match:  # Only update if we got a valid match back
                        match.update(updated_match)
                        match['last_update'] = format_datetime(current_time)
                        matches_updated = True
                        processed_matches.append(match_num)
                except Exception as e:
                    if "RATE_LIMIT_EXCEEDED" in str(e):
                        logger.warning(f"Rate limit exceeded for match {match_num}, will retry in next run")
                    else:
                        logger.error(f"Error updating match {match_num}: {str(e)}")
            else:
                # Handle skipped matches
                if new_status == "completed":
                    skipped_matches["completed"].append(match_num)
                elif new_status == "not_started":
                    skipped_matches["not_started"].append(match_num)
                elif new_status == "in_progress":
                    skipped_matches["in_progress"].append(match_num)
                    # Calculate next update time for in-progress matches
                    last_update = parse_datetime(match.get('last_update'))
                    if last_update and frequency:
                        next_update = last_update + timedelta(minutes=frequency)
                        next_update_str = next_update.strftime('%H:%M UTC')
                        minutes_until = round((next_update - current_time).total_seconds() / 60)
                        logger.info(f"Skipping in-progress match {match_num} - next update in {minutes_until} minutes (at {next_update_str})")
                        
        
        # Log skipped matches by category
        if skipped_matches["completed"]:
            logger.info(f"Skipping completed matches: {', '.join(map(str, sorted(skipped_matches['completed'])))}")
        
        if skipped_matches["not_started"]:
            logger.info(f"Skipping not_started matches: {', '.join(map(str, sorted(skipped_matches['not_started'])))}")
        
        # Save updated match states if any changes were made
        if matches_updated:
            try:
                state_manager.save_state(data)
            except Exception as e:
                logger.error(f"Error saving state: {str(e)}")
                return json.dumps({
                    'error': f'Failed to save state: {str(e)}',
                    'timestamp': format_datetime(current_time)
                }), 500, {'Content-Type': 'application/json'}
        
        if processed_matches or status_changes:
            logger.info(f"Processed matches: {processed_matches}, Status changes: {status_changes}")
        
        return json.dumps({
            'message': 'Success',
            'processed_matches': processed_matches,
            'matches_updated': matches_updated,
            'status_changes': status_changes,
            'skipped_matches': skipped_matches,
            'timestamp': format_datetime(current_time)
        }), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        error_msg = f"Error during score update: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            'error': error_msg,
            'timestamp': format_datetime(datetime.now(pytz.UTC))
        }), 500, {'Content-Type': 'application/json'}

if __name__ == "__main__":
    # For local testing
    response, status_code = update_scores(None)
    print(f"\nStatus Code: {status_code}")
    print("Response:", json.dumps(response, indent=2)) 