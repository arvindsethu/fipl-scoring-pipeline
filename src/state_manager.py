import json
import logging
from google.cloud import storage
from google.api_core import retry
from config import sheets_config

# Configure logging
logger = logging.getLogger(__name__)

class StateManager:
    """Manages the state of match processing in Google Cloud Storage"""
    
    def __init__(self, bucket_name, state_file_path=None):
        """Initialize with bucket name and optional state file path"""
        self.bucket_name = bucket_name
        self.state_file_path = state_file_path or sheets_config.STATE_FILE
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    @retry.Retry(predicate=retry.if_exception_type(Exception))
    def load_state(self):
        """
        Load state from Cloud Storage with retry logic
        
        Returns:
            dict: The current state
        """
        try:
            blob = self.bucket.blob(self.state_file_path)
            content = blob.download_as_string()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading state from Cloud Storage: {str(e)}")
            # Return empty state if file doesn't exist
            return {"matches": []}

    def save_state(self, state_data):
        """
        Save state to Cloud Storage
        
        Args:
            state_data (dict): The state data to save
        """
        try:
            # Verify state before saving
            if not self.verify_state_integrity(state_data):
                raise ValueError("Invalid state data structure")

            # Save state
            blob = self.bucket.blob(self.state_file_path)
            blob.upload_from_string(
                json.dumps(state_data, indent=2),
                content_type='application/json'
            )
            logger.info("Successfully saved state to Cloud Storage")
        except Exception as e:
            logger.error(f"Error saving state to Cloud Storage: {str(e)}")
            raise

    def verify_state_integrity(self, state_data):
        """
        Verify the integrity of the state data
        
        Args:
            state_data (dict): The state data to verify
            
        Returns:
            bool: True if state is valid, False otherwise
        """
        try:
            # Check basic structure
            if not isinstance(state_data, dict):
                return False
            if 'matches' not in state_data:
                return False
            if not isinstance(state_data['matches'], list):
                return False
            
            # Check each match
            for match in state_data['matches']:
                required_fields = ['match_number', 'start_time', 'status', 'url', 'gameweek', 'teams']
                if not all(field in match for field in required_fields):
                    return False
                
                # Verify teams structure
                if not isinstance(match['teams'], dict):
                    return False
                for team_data in match['teams'].values():
                    if 'gameweek_match' not in team_data:
                        return False
            
            return True
        except Exception:
            return False 