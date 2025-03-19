import logging
from datetime import datetime, timedelta
import pytz
import json
import os
import functions_framework
from src.sheet_updater import main as update_main
from src.state_manager import StateManager

# Setup logging for Cloud Functions
logger = logging.getLogger()
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# Cloud Storage setup
BUCKET_NAME = "fipl_bucket"  # Replace with your bucket name
state_manager = StateManager(BUCKET_NAME)

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
        if last_update_str and last_update_str != "null":
            try:
                last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
            except ValueError:
                last_update = None
        
        # If no previous update or enough time has passed since last update
        if not last_update or (current_time - last_update).total_seconds() >= (frequency * 60):
            return True, frequency, "in_progress"
        
        return False, frequency, "in_progress"
    except Exception as e:
        logger.error(f"Error processing match {match.get('match_number', 'Unknown')}: {str(e)}")
        return False, None, match.get('status', 'pending')

@functions_framework.http
def update_scores(request):
    """Cloud Function entry point"""
    try:
        current_time = datetime.now(pytz.UTC)
        
        # Only run between 8 AM and 8 PM UTC
        if not (8 <= current_time.hour < 20):
            return json.dumps({
                'message': 'Outside operating hours',
                'timestamp': current_time.isoformat()
            }), 200, {'Content-Type': 'application/json'}
        
        try:
            # Load state from Cloud Storage
            data = state_manager.load_state()
            
            # Verify state integrity
            if not state_manager.verify_state_integrity(data):
                logger.error("Invalid state data structure")
                return json.dumps({
                    'error': 'Invalid state data structure',
                    'timestamp': current_time.isoformat()
                }), 500, {'Content-Type': 'application/json'}
                
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            return json.dumps({
                'error': f'Failed to load state: {str(e)}',
                'timestamp': current_time.isoformat()
            }), 500, {'Content-Type': 'application/json'}
        
        matches_updated = False
        processed_matches = []
        status_changes = []
        skipped_matches = {"completed": [], "pending": []}
        
        # Process each match
        for match in data['matches']:
            match_num = match.get('match_number', 'Unknown')
            old_status = match.get('status', 'pending')
            should_update, frequency, new_status = should_process_match(match, current_time)
            
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
                try:
                    # Pass the specific match to update_main
                    updated_match = update_main(match)
                    if updated_match:
                        match.update(updated_match)
                        match['last_update'] = current_time.isoformat()
                        matches_updated = True
                        processed_matches.append(match_num)
                except Exception as e:
                    if "RATE_LIMIT_EXCEEDED" in str(e):
                        logger.warning(f"Rate limit exceeded for match {match_num}, will retry in next run")
                    else:
                        logger.error(f"Error updating match {match_num}: {str(e)}")
            else:
                if new_status in ["completed", "pending"]:
                    skipped_matches[new_status].append(match_num)
        
        # Save updated match states if any changes were made
        if matches_updated:
            try:
                state_manager.save_state(data)
            except Exception as e:
                logger.error(f"Error saving state: {str(e)}")
                return json.dumps({
                    'error': f'Failed to save state: {str(e)}',
                    'timestamp': current_time.isoformat()
                }), 500, {'Content-Type': 'application/json'}
        
        if processed_matches or status_changes:
            logger.info(f"Processed matches: {processed_matches}, Status changes: {status_changes}")
        
        return json.dumps({
            'message': 'Success',
            'processed_matches': processed_matches,
            'matches_updated': matches_updated,
            'status_changes': status_changes,
            'skipped_matches': skipped_matches,
            'timestamp': current_time.isoformat()
        }), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        error_msg = f"Error during score update: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            'error': error_msg,
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }), 500, {'Content-Type': 'application/json'}

if __name__ == "__main__":
    # For local testing
    response, status_code = update_scores(None)
    print(f"\nStatus Code: {status_code}")
    print("Response:", json.dumps(response, indent=2)) 