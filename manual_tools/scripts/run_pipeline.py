import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import json
import argparse
import tempfile
import logging
from src.scorecard_scraper import scrape_scorecard
from src.score_calculator import calculate_scores_and_update_sheet
from src.sheet_updater import update_sheet_for_match

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Show all info messages
    format='%(message)s'  # Clean format without timestamps
)

# Get logger instance
logger = logging.getLogger('src.scorecard_scraper')
logger.setLevel(logging.INFO)

# Disable verbose loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)

# Constants
CONFIG_DIR = os.path.join(project_root, 'config')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'outputs')

def load_match_by_number(match_number):
    """Load match data from ipl_2025_matches.json by match number"""
    matches_file = os.path.join(CONFIG_DIR, 'ipl_2025_matches.json')
    try:
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches_data = json.load(f)
            for match in matches_data['matches']:
                if match['match_number'] == match_number:
                    return match
    except Exception as e:
        print(f"Error loading match data: {str(e)}")
        raise
    
    raise ValueError(f"Match number {match_number} not found")

def process_url(url):
    """Process a single URL without sheet updates"""
    try:
        # Scrape scorecard
        scorecard_data = scrape_scorecard(url)
        
        if "error" in scorecard_data:
            print(f"Error: {scorecard_data['error']}")
            return
            
        # Save to temporary file for score calculation
        temp_file = os.path.join(OUTPUT_DIR, 'scorecard.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=2)
        
        # Calculate scores
        calculate_scores_and_update_sheet(temp_file)
        
        print(f"Success! Output saved to: {temp_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def process_match(match_number, dry_run=False):
    """Process a match by number with full pipeline including sheet updates"""
    print(f"\nProcessing match number: {match_number}")
    print("Mode: Full pipeline (including sheet updates)")
    if dry_run:
        print("DRY RUN: Sheet updates will be skipped")
    
    try:
        # Load match data
        match_data = load_match_by_number(match_number)
        print(f"Found match: {match_data['teams'].keys()}")
        
        # Scrape scorecard
        print("\nScraping scorecard...")
        scorecard_data = scrape_scorecard(match_data['url'])
        
        # Save to temporary file for score calculation
        temp_file = os.path.join(OUTPUT_DIR, 'scorecard.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=2)
        
        # Calculate scores
        print("Calculating scores...")
        calculate_scores_and_update_sheet(temp_file)
        
        # Read the updated scorecard with points
        with open(temp_file, 'r', encoding='utf-8') as f:
            scorecard_data = json.load(f)
        
        # Update sheet only if not in dry run mode
        if not dry_run:
            print("Updating sheet...")
            update_sheet_for_match(match_data, scorecard_data)
        else:
            print("Skipping sheet update (dry run)")
        
        print(f"\nSuccess! Output saved to: {temp_file}")
        
    except Exception as e:
        print(f"Error processing match: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Manual run tool for FIPL scoring pipeline')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--match-number', type=int, help='Match number from ipl_2025_matches.json')
    group.add_argument('--url', type=str, help='Direct ESPNCricinfo scorecard URL')
    
    # Add dry run flag
    parser.add_argument('--dry', action='store_true', help='Run in dry mode (skip sheet updates)')
    
    args = parser.parse_args()
    
    # Create outputs directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if args.match_number:
        process_match(args.match_number, dry_run=args.dry)
    else:
        # Strip quotes if present
        url = args.url.strip('"\'')
        process_url(url)

if __name__ == "__main__":
    main() 