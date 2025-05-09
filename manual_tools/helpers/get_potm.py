#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timezone

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import requests
from bs4 import BeautifulSoup
import re
import logging
import urllib3
import argparse
import json
from typing import Dict, Optional, List, Tuple

# Constants
CONFIG_DIR = os.path.join(project_root, 'config')

# Suppress SSL-related warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def clean_player_name(name: str) -> str:
    """Clean player name by removing special characters and normalizing format."""
    # Remove wicketkeeper symbol and other special characters
    cleaned = re.sub(r'\s*[(]c[)]|\s*[†](?!\w)|\s*,', '', name).replace('\u2019', "'").strip()
    return cleaned

def get_enhanced_headers():
    """Get headers that help bypass scraping protection"""
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def get_potm(soup: BeautifulSoup) -> Optional[str]:
    """Extract Player of the Match from the scorecard"""
    header = soup.find('div', class_='ds-text-eyebrow-xs ds-uppercase ds-text-typo-mid2', string='Player Of The Match')
    if not header:
        return None
        
    container = header.find_next('div')
    if not container:
        return None
        
    link = container.find('a')
    if not link:
        return None
        
    return clean_player_name(link.text.strip())

def get_cricinfo_mvp(soup: BeautifulSoup) -> Optional[str]:
    """Extract Cricinfo MVP from the scorecard"""
    # Find the MVP container with the correct class and text
    mvp_container = soup.find('div', class_='ds-text-eyebrow-xs ds-uppercase ds-text-typo-mid2', string="Cricinfo's MVP")
    if not mvp_container:
        return None
    
    # Get the next div which contains the player info
    player_div = mvp_container.find_next('div')
    if not player_div:
        return None
    
    # Find the player link within a popper wrapper
    popper_div = player_div.find('div', class_='ds-popper-wrapper')
    if not popper_div:
        return None
        
    # Get the player link
    player_link = popper_div.find('a')
    if not player_link:
        return None
    
    # Find the span with the player name
    player_span = player_link.find('span', class_='ds-text-tight-m')
    if not player_span:
        return None
        
    return clean_player_name(player_span.text.strip())

def get_match_awards(url: str) -> Dict[str, str]:
    """Extract Player of the Match and Cricinfo MVP from a cricinfo scorecard URL"""
    try:
        # Make request with enhanced headers
        response = requests.get(
            url,
            headers=get_enhanced_headers(),
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get both awards
        awards = {
            'Player of the Match': get_potm(soup) or "Not found",
            'Cricinfo MVP': get_cricinfo_mvp(soup) or "Not found"
        }
        
        return awards
        
    except requests.RequestException as e:
        return {
            'Player of the Match': f"Error fetching URL: {str(e)}",
            'Cricinfo MVP': f"Error fetching URL: {str(e)}"
        }
    except Exception as e:
        return {
            'Player of the Match': f"Error processing awards: {str(e)}",
            'Cricinfo MVP': f"Error processing awards: {str(e)}"
        }

def load_match_by_number(match_number: int) -> Dict:
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

def process_url(url: str):
    """Process a single URL"""
    print(f"\nProcessing URL: {url}")
    
    # Get and print awards
    awards = get_match_awards(url)
    print("\nMatch Awards:")
    print(f"Player of the Match: {awards['Player of the Match']}")
    print(f"Cricinfo MVP: {awards['Cricinfo MVP']}\n")

def process_match(match_number: int):
    """Process a match by number"""
    print(f"\nProcessing match number: {match_number}")
    
    try:
        # Load match data
        match_data = load_match_by_number(match_number)
        print(f"Found match: {' vs '.join(match_data['teams'].keys())}")
        
        # Get and print awards
        awards = get_match_awards(match_data['url'])
        print("\nMatch Awards:")
        print(f"Player of the Match: {awards['Player of the Match']}")
        print(f"Cricinfo MVP: {awards['Cricinfo MVP']}\n")
        
    except Exception as e:
        print(f"Error processing match: {str(e)}")
        raise

def load_all_past_matches() -> List[Dict]:
    """Load all matches from ipl_2025_matches.json that have started"""
    matches_file = os.path.join(CONFIG_DIR, 'ipl_2025_matches.json')
    current_time = datetime.now(timezone.utc)
    
    try:
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches_data = json.load(f)
            past_matches = []
            
            for match in matches_data['matches']:
                match_time = datetime.fromisoformat(match['start_time'].replace('Z', '+00:00'))
                if match_time < current_time:
                    past_matches.append(match)
                    
            return past_matches
    except Exception as e:
        print(f"Error loading match data: {str(e)}")
        raise

def process_all_past_matches():
    """Process all past matches and compare POTM with MVP"""
    print("\nAnalyzing all past matches...")
    
    past_matches = load_all_past_matches()
    total_matches = len(past_matches)
    same_awards = 0
    
    for match in past_matches:
        match_num = match['match_number']
        teams = ' vs '.join(match['teams'].keys())
        
        # Get awards
        awards = get_match_awards(match['url'])
        potm = awards['Player of the Match']
        mvp = awards['Cricinfo MVP']
        
        # Skip if either award wasn't found
        if potm == "Not found" or mvp == "Not found":
            print(f"\nMatch {match_num}: {teams}")
            print("Skipping - Could not find one or both awards")
            continue
            
        # Compare awards
        if potm != mvp:
            print(f"\nMatch {match_num}: {teams}")
            print(f"Player of the Match: {potm}")
            print(f"Cricinfo MVP: {mvp}")
        else:
            same_awards += 1
    
    # Print summary
    print("\nSummary:")
    print(f"Total matches analyzed: {total_matches}")
    print(f"Matches with same POTM and MVP: {same_awards}")
    print(f"Matches with different POTM and MVP: {total_matches - same_awards}")

def main():
    parser = argparse.ArgumentParser(description='Extract Player of the Match and Cricinfo MVP from a cricinfo scorecard')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--match-number', type=int, help='Match number from ipl_2025_matches.json')
    group.add_argument('--url', type=str, help='Direct ESPNCricinfo scorecard URL')
    group.add_argument('--all', action='store_true', help='Process all past matches and compare POTM with MVP')
    
    args = parser.parse_args()
    
    if args.match_number:
        process_match(args.match_number)
    elif args.url:
        # Strip quotes if present
        url = args.url.strip('"\'')
        process_url(url)
    else:
        process_all_past_matches()

if __name__ == "__main__":
    main() 