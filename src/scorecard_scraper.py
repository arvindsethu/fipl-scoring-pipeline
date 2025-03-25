import os
import json
import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import random
import urllib3
import sys

# Suppress SSL-related warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants for Cloud Function environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
TMP_DIR = '/tmp'

# Configure logging
logger = logging.getLogger(__name__)

def clean_player_name(name: str) -> Tuple[str, bool]:
    """Clean player name by removing special characters and normalizing format.
    Returns a tuple of (cleaned_name, is_wicketkeeper)"""
    is_wicketkeeper = '†' in name
    if is_wicketkeeper:
        name = re.sub(r'†', '', name)

    cleaned = re.sub(r'\s*[(]c[)]|\s*[†](?!\w)|\s*,', '', name).replace('\u2019', "'").strip()
    return cleaned, is_wicketkeeper

def create_default_player_stats() -> Dict[str, Any]:
    """Create a dictionary with default player statistics"""
    return {
        "runs_scored": 0,
        "balls_faced": 0,
        "fours": 0,
        "sixes": 0,
        "strike_rate": 0,
        "sr_differential": 0.0,
        "overs": 0,
        "economy": 0,
        "economy_differential": 0.0,
        "wickets": 0,
        "dots": 0,
        "wides": 0,
        "no_balls": 0,
        "catches": 0,
        "run_outs": 0,
        "did_not_bat": "Yes",
        "stumping": 0,
        "maiden": 0,
        "potm": "No",
        "is_sub": False,
        "runs_points": 0,
        "strike_rate_points": 0,
        "boundaries_points": 0,
        "maiden_points": 0,
        "potm_points": 0,
        "wickets_points": 0,
        "dots_points": 0,
        "extras_points": 0,
        "economy_points": 0,
        "batting_points": 0,
        "bowling_points": 0,
        "fielding_points": 0,
        "total_points": 0
    }

def normalize_team_name(team_name: str) -> str:
    """Normalize team name to handle variations"""
    team_name = team_name.lower()
    
    # Handle known variations
    if "chennai" in team_name:
        return "Chennai Superkings"  # Will match both Super Kings and Superkings
    elif "lucknow" in team_name:
        return "Lucknow Supergiants"  # Will match both Super Giants and Supergiants
    elif any(x in team_name for x in ["rcb", "royal challengers", "bengaluru", "bangalore"]):
        return "Royal Challengers Bengaluru"
    
    # For other teams, just capitalize words
    return ' '.join(word.capitalize() for word in team_name.split())

def find_matching_player(name: str, team_name: str, existing_players: List[str], players_data: Dict[str, Any], is_wicketkeeper: bool = False) -> Tuple[Optional[str], bool, Optional[str]]:
    """Find matching player from players.json data"""
    logger = logging.getLogger(__name__)
    
    # Parse name
    name = name.lower()
    name_parts = name.split()
    last_name = name_parts[-1] if name_parts else ''
    first_name = name_parts[0] if len(name_parts) > 1 else ''
    first_letter = first_name[0] if first_name else ''
    has_multiple_parts = len(name_parts) > 1
    
    # Load and filter players from config
    try:
        with open(os.path.join(CONFIG_DIR, 'players.json')) as f:
            all_players = json.load(f)['players']
    except Exception as e:
        logger.error("Failed to load players.json: %s", str(e))
        return None, False, f"Failed to load players.json: {str(e)}"
    
    # Filter players by team
    normalized_team = normalize_team_name(team_name)
    team_players = [p['name'] for p in all_players if normalize_team_name(p['team']) == normalized_team]
    if not team_players:
        logger.warning("No players found for team: %s", team_name)
        return None, False, f"No players found for team: {team_name}"
    
    # Find matches
    last_name_matches = []
    first_name_matches = []
    
    for player in team_players:
        player_lower = player.lower()
        player_parts = player_lower.split()
        player_last = player_parts[-1] if player_parts else ''
        player_first = player_parts[0] if player_parts else ''
        
        # Try exact match first
        if player_lower == name:
            return player, False, None
        
        if player_last == last_name:
            last_name_matches.append(player)
            
        if player_first == first_name:
            first_name_matches.append(player)
    
    # Single last name match
    if len(last_name_matches) == 1:
        return last_name_matches[0], False, None
    
    # Multiple last name matches - try to resolve
    if len(last_name_matches) > 1:        
        # Only try first letter match if the original name has multiple parts
        if has_multiple_parts:
            first_letter_matches = [p for p in last_name_matches if p.lower()[0] == first_letter]
            if len(first_letter_matches) == 1:
                logger.info(f"Resolved multiple match for '{name}' using first letter match: {first_letter_matches[0]}")
                return first_letter_matches[0], False, None
            
        # Try existing players
        if existing_players:
            matches_in_existing = [p for p in last_name_matches if p in existing_players]
            if len(matches_in_existing) == 1:
                logger.info(f"Resolved multiple match for '{name}' using existing player match: {matches_in_existing[0]}")
                return matches_in_existing[0], False, None
        
        # Try keeper status matching
        if is_wicketkeeper is not None:  # Only try if we know the keeper status
            # Get roles for all matching players
            matching_players_with_roles = [
                (p, next((pl['role'] for pl in all_players if pl['name'] == p), None))
                for p in last_name_matches
            ]
            
            if is_wicketkeeper:
                # Look for keepers
                keeper_matches = [p for p, role in matching_players_with_roles if role == 'Keeper']
                if len(keeper_matches) == 1:
                    logger.info(f"Resolved multiple match for '{name}' using keeper status match: {keeper_matches[0]}")
                    return keeper_matches[0], False, None
                elif not keeper_matches:
                    logger.warning(f"WARNING: Unexpected: Player marked as keeper but no keeper matches found for '{name}'")
            else:
                # Look for non-keepers
                non_keeper_matches = [p for p, role in matching_players_with_roles if role != 'Keeper']
                if len(non_keeper_matches) == 1:
                    logger.info(f"Resolved multiple match for '{name}' using non-keeper status match: {non_keeper_matches[0]}")
                    return non_keeper_matches[0], False, None
                elif not non_keeper_matches:
                    logger.warning(f"WARNING: Unexpected: Player not marked as keeper but all matches are keepers for '{name}'")
        
        return None, False, f"Multiple unresolved last name matches: {last_name_matches}"
    
    logger.warning("No matches found for '%s' in %s", name, team_name)
    return None, False, f"No match found for: {name}"

def parse_dismissal_text(dismissal_text: str) -> List[Tuple[str, bool]]:
    """Parse dismissal text and return list of (fielder_name, is_wicketkeeper) tuples"""
    if not dismissal_text:
        return []
    
    fielders = []
    
    # Handle caught and bowled
    if 'c & b' in dismissal_text:
        bowler = clean_player_name(dismissal_text.split('c & b')[1].strip())
        return [bowler]

    # Handle stumpings
    if dismissal_text.startswith('st '):
        if 'sub (' in dismissal_text:
            sub_match = re.search(r'sub\s*\(([^)]+)\)', dismissal_text)
            keeper_name = sub_match.group(1) if sub_match else None
        else:
            keeper_name = dismissal_text.split(' b ')[0][3:].strip()
        
        if keeper_name:
            return [clean_player_name(keeper_name)]

    # Handle catches
    catch_match = re.match(r'c\s+(?:sub\s*\([^)]+\)|†?[^b]+)b', dismissal_text)
    if catch_match:
        if 'sub (' in dismissal_text:
            sub_match = re.search(r'sub\s*\(([^)]+)\)', dismissal_text)
            catcher = sub_match.group(1) if sub_match else None
        else:
            # Extract the catcher name with the † symbol if present
            catcher = dismissal_text.split(' b ')[0][2:].strip()
        
        if catcher:
            return [clean_player_name(catcher)]

    # Handle run outs
    if 'run out' in dismissal_text:
        fielders_match = re.search(r'\((.*?)\)', dismissal_text)
        if fielders_match:
            fielders_text = fielders_match.group(1)
            fielders = fielders_text.split('/')
            
            cleaned_fielders = []
            for fielder in fielders:
                fielder = re.sub(r'sub\s*\[(.*?)\]', r'\1', fielder)
                cleaned = clean_player_name(fielder)
                if cleaned[0]:  # Only add if name is not empty
                    cleaned_fielders.append(cleaned)
            
            return cleaned_fielders

    return fielders

def extract_run_rate(innings_html: str) -> Optional[float]:
    """Extract run rate from innings HTML content"""
    soup = BeautifulSoup(innings_html, 'html.parser')
    spans = soup.find_all('span', class_='ds-text-tight-s')
    
    for span in spans:
        text = ''.join(span.stripped_strings)
        if '(RR:' in text:
            try:
                return float(text.replace('(RR:', '').replace(')', '').strip())
            except ValueError:
                logger.warning("Could not convert run rate to float")
                return None
    return None

def get_enhanced_headers():
    """Get enhanced headers that successfully bypass scraping protection"""
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Referer': 'https://www.espncricinfo.com/',
        'Origin': 'https://www.espncricinfo.com'
    }

def scrape_scorecard(url: str) -> Dict[str, Any]:
    """Scrape cricket scorecard data from ESPNCricinfo URL"""
    logger = logging.getLogger(__name__)
    
    # Try up to 3 times with different headers
    max_retries = 3
    for attempt in range(max_retries):
        try:
            headers = get_enhanced_headers()  # This will get a random user agent each time
            
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                verify=False
            )
            
            # Extract Safari version from the user agent that was used
            safari_version = headers['User-Agent'].split('Version/')[1].split()[0]
            logger.info(f"Attempt {attempt + 1}/{max_retries} to fetch scorecard with Safari {safari_version}")
            
            if response.status_code == 403:
                logger.error(f"Access denied (403) on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    logger.info("Retrying with different headers...")
                    continue
                else:
                    logger.error("All retry attempts failed with 403 errors")
                    return {"error": "Access denied (403) - All retry attempts failed"}
            
            response.raise_for_status()
            break  # If we get here, the request was successful
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch URL on attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                logger.info("Retrying with different headers...")
                continue
            else:
                logger.error("All retry attempts failed")
                return {"error": f"Failed to fetch URL after {max_retries} attempts: {str(e)}"}

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        scorecard_data: Dict[str, Any] = {}

        # Extract team names and initialize data structure
        innings_divs = soup.find_all('div', class_='ds-rounded-lg')
        team_names = []
        
        # First try to get teams from match header
        match_header = soup.find('div', class_='ds-text-tight-m ds-font-regular ds-text-typo-mid3')
        if match_header:
            teams_text = match_header.text.strip()
            vs_split = teams_text.split(' vs ')
            if len(vs_split) == 2:
                team1 = vs_split[0].strip()
                team2 = vs_split[1].split(' in ')[0].strip()
                team_names = [team1, team2]
                
                for team in team_names:
                    scorecard_data[team] = {
                        "average_economy": 0,
                        "average_strike_rate": 0,
                        "player_stats": {}
                    }
        
        # If we don't have both teams, try to get them from innings headers
        if len(team_names) < 2:
            team_names = []
            for innings in innings_divs:
                team_header = innings.find('span', class_='ds-text-title-xs ds-font-bold ds-capitalize')
                if team_header:
                    team_name = team_header.text.strip()
                    if team_name not in team_names:
                        team_names.append(team_name)
                        scorecard_data[team_name] = {
                            "average_economy": 0,
                            "average_strike_rate": 0,
                            "player_stats": {}
                        }

        if not team_names:
            logger.error("No teams found in scorecard")
            return {"error": "No teams found in scorecard"}

        logger.info("Teams found: %s", team_names)
        
        # Store dismissals for later processing
        dismissal_records = []
        
        # Process innings
        for innings_num, innings in enumerate(innings_divs):
            team_header = innings.find('span', class_='ds-text-title-xs ds-font-bold ds-capitalize')
            if not team_header:
                continue
                
            batting_team = team_header.text.strip()
            logger.info("Processing %s innings", batting_team)
            
            # Find bowling team - it's the other team in the match
            bowling_team = None
            for team in team_names:
                if team != batting_team:
                    bowling_team = team
                    break
            
            # Extract and process run rate
            run_rate = extract_run_rate(str(innings))
            if run_rate:
                avg_strike_rate = float(f"{(run_rate * 100) / 6:.2f}")
                avg_economy = float(f"{run_rate:.2f}")
                
                scorecard_data[batting_team]["average_strike_rate"] = avg_strike_rate
                if bowling_team:
                    scorecard_data[bowling_team]["average_economy"] = avg_economy
                
                logger.info("Updated %s avg SR: %.2f", batting_team, avg_strike_rate)
                if bowling_team:
                    logger.info("Updated %s avg economy: %.2f", bowling_team, avg_economy)
            
            # Process batting
            batting_table = innings.find('table', class_='ci-scorecard-table')
            if batting_table:
                player_cells = batting_table.find_all('td', class_=['ds-w-0 ds-whitespace-nowrap ds-min-w-max', 
                    'ds-w-0 ds-whitespace-nowrap ds-min-w-max ds-border-line-primary ci-scorecard-player-notout'])
                logger.info("Batting players found: %d", len(player_cells))
                
                for player_cell in player_cells:
                    try:
                        player_link = player_cell.find('a')
                        if not player_link:
                            continue
                            
                        player_name, is_wicketkeeper = clean_player_name(player_link.text.strip())
                        logger.debug(f"Processing batting player: {player_name}")
                        
                        if player_name not in scorecard_data[batting_team]["player_stats"]:
                            scorecard_data[batting_team]["player_stats"][player_name] = create_default_player_stats()
                        
                        row = player_cell.find_parent('tr')
                        if row:
                            cells = row.find_all('td')
                            if len(cells) >= 8:
                                dismissal_info = cells[1].text.strip()
                                if bowling_team and dismissal_info and dismissal_info != 'not out':
                                    dismissal_records.append({
                                        'batsman': player_name,
                                        'dismissal_text': dismissal_info,
                                        'batting_team': batting_team,
                                        'bowling_team': bowling_team
                                    })
                                
                                strike_rate_text = cells[7].text.strip()
                                strike_rate = float(f"{float(strike_rate_text) if strike_rate_text != '-' else 0:.2f}")
                                avg_sr = scorecard_data[batting_team]["average_strike_rate"]
                                sr_differential = float(f"{((strike_rate - avg_sr) / avg_sr * 100) if avg_sr > 0 else 0.0:.1f}")
                                
                                # Get runs scored before deciding did_not_bat status
                                runs_scored = int(cells[2].text.strip() or 0)
                                
                                # Set did_not_bat to "Yes" if player is not out and has 0 runs
                                did_not_bat = "Yes" if runs_scored == 0 and dismissal_info == "not out" else "No"
                                
                                scorecard_data[batting_team]["player_stats"][player_name].update({
                                    "runs_scored": runs_scored,
                                    "balls_faced": int(cells[3].text.strip() or 0),
                                    "fours": int(cells[5].text.strip() or 0),
                                    "sixes": int(cells[6].text.strip() or 0),
                                    "strike_rate": strike_rate,
                                    "sr_differential": sr_differential,
                                    "did_not_bat": did_not_bat
                                })
                    except Exception as e:
                        logger.error(f"Error processing batting player: {str(e)}")
                        continue

                # Process did not bat
                dnb_row = batting_table.find('tr', class_='!ds-border-b-0')
                if dnb_row:
                    dnb_div = dnb_row.find('div', class_='ds-text-tight-m')
                    if dnb_div and 'bat' in dnb_div.text:
                        dnb_players = dnb_div.find_all('a')
                        for player in dnb_players:
                            try:
                                player_name, _ = clean_player_name(player.text.strip())
                                logger.debug(f"Processing DNB player: {player_name}")
                                if player_name not in scorecard_data[batting_team]["player_stats"]:
                                    scorecard_data[batting_team]["player_stats"][player_name] = create_default_player_stats()
                            except Exception as e:
                                logger.error(f"Error processing DNB player: {str(e)}")
                                continue

            # Process bowling - only if we have a bowling team
            if bowling_team:
                bowling_table = innings.find('table', class_='ds-w-full ds-table ds-table-md ds-table-auto')
                if bowling_table:
                    bowling_rows = bowling_table.find_all('tr')
                    for row in bowling_rows:
                        try:
                            cells = row.find_all('td')
                            if not (cells and len(cells) >= 11):
                                continue
                                
                            player_link = cells[0].find('a')
                            if not player_link:
                                continue
                                
                            player_name, _ = clean_player_name(player_link.text.strip())
                            logger.debug(f"Processing bowling player: {player_name}")
                            
                            if player_name not in scorecard_data[bowling_team]["player_stats"]:
                                scorecard_data[bowling_team]["player_stats"][player_name] = create_default_player_stats()
                            
                            economy = float(f"{float(cells[5].text.strip() or 0):.2f}")
                            avg_econ = float(f"{scorecard_data[bowling_team]['average_economy']:.2f}")
                            econ_differential = float(f"{((economy - avg_econ) / avg_econ * 100) if avg_econ > 0 else 0.0:.1f}")
                            
                            bowling_stats = {
                                "overs": float(cells[1].text.strip() or 0),
                                "maiden": int(cells[2].text.strip() or 0),
                                "wickets": int(cells[4].text.strip() or 0),
                                "dots": int(cells[6].text.strip() or 0),
                                "wides": int(cells[9].text.strip() or 0),
                                "no_balls": int(cells[10].text.strip() or 0),
                                "economy": float(f"{economy:.2f}"),
                                "economy_differential": econ_differential
                            }
                            
                            scorecard_data[bowling_team]["player_stats"][player_name].update(bowling_stats)
                        except Exception as e:
                            logger.error(f"Error processing bowling player: {str(e)}")
                            continue

        # Process dismissals - only if we have bowling team records
        for record in dismissal_records:
            try:
                if record['bowling_team'] not in scorecard_data:
                    continue
                    
                fielders = parse_dismissal_text(record['dismissal_text'])
                bowling_team_players = list(scorecard_data[record['bowling_team']]["player_stats"].keys())
                
                for fielder_name, is_wicketkeeper in fielders:
                    try:
                        is_sub = ('sub' in record['dismissal_text'] and fielder_name in record['dismissal_text'].split('sub')[1])
                        logger.debug(f"Processing fielder: {fielder_name} in dismissal: {record['dismissal_text']}")
                        matched_name, is_new, error_msg = find_matching_player(
                            fielder_name, 
                            record['bowling_team'],
                            bowling_team_players,
                            scorecard_data[record['bowling_team']]["player_stats"],
                            is_wicketkeeper
                        )
                        
                        if matched_name:
                            # Initialize player stats if they don't exist (especially for subs)
                            if matched_name not in scorecard_data[record['bowling_team']]["player_stats"]:
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name] = create_default_player_stats()
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name]["is_sub"] = True
                            
                            if "c & b" in record['dismissal_text']:
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name]["catches"] += 1
                            elif record['dismissal_text'].startswith("st "):
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name]["stumping"] += 1
                            elif record['dismissal_text'].startswith("c "):
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name]["catches"] += 1
                            elif "run out" in record['dismissal_text']:
                                points_per_fielder = 1.0 / len(fielders) if fielders else 0
                                scorecard_data[record['bowling_team']]["player_stats"][matched_name]["run_outs"] += points_per_fielder
                        else:
                            error_context = f" in dismissal: {record['dismissal_text']}"
                            if len(fielders) > 1:
                                error_context += f" (multi-fielder dismissal with: {[f for f in fielders if f != fielder_name]})"
                            logger.warning(f"WARNING: Failed to match '{fielder_name}': {error_msg}{error_context}\n")
                    except Exception as e:
                        logger.error(f"Error processing fielder {fielder_name}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Error processing dismissal record: {str(e)}")
                continue

        # Player of the Match
        try:
            potm_header = soup.find('div', class_='ds-text-eyebrow-xs ds-uppercase ds-text-typo-mid2', string='Player Of The Match')
            if potm_header:
                potm_container = potm_header.find_next('div')
                if potm_container and (potm_link := potm_container.find('a')):
                    potm_name, _ = clean_player_name(potm_link.text.strip())
                    logger.debug(f"Processing POTM: {potm_name}")
                    for team in team_names:
                        if potm_name in scorecard_data[team]["player_stats"]:
                            scorecard_data[team]["player_stats"][potm_name]["potm"] = "Yes"
                            logger.info(f"Player of the Match found: {potm_name}")
                            break
        except Exception as e:
            logger.error(f"Error processing Player of the Match: {str(e)}")

        # Format floating point values
        for team in scorecard_data:
            scorecard_data[team]["average_economy"] = float(f"{scorecard_data[team]['average_economy']:.2f}")
            scorecard_data[team]["average_strike_rate"] = float(f"{scorecard_data[team]['average_strike_rate']:.2f}")
            
            for player in scorecard_data[team]["player_stats"]:
                try:
                    stats = scorecard_data[team]["player_stats"][player]
                    formatted_stats = {
                        "strike_rate": float(f"{stats['strike_rate']:.2f}"),
                        "sr_differential": float(f"{stats['sr_differential']:.1f}"),
                        "economy": float(f"{stats['economy']:.2f}"),
                        "economy_differential": float(f"{stats['economy_differential']:.1f}")
                    }
                    stats.update(formatted_stats)
                except Exception as e:
                    logger.error(f"Error formatting stats for player {player}: {str(e)}")
                    continue

        return scorecard_data

    except Exception as e:
        logger.error(f"Critical error processing scorecard: {str(e)}")
        return {"error": "Failed to process scorecard"}

def test_player_matching():
    """Test function to verify player matching logic"""
    logger.setLevel(logging.DEBUG)
    
    # Test team name normalization
    print("\nTesting team name normalization:")
    test_teams = [
        "Royal Challengers Bangalore",
        "Royal Challengers Bengaluru",
        "RCB",
        "Chennai Super Kings",
        "Chennai Superkings",
        "CSK",
        "Lucknow Super Giants",
        "Lucknow Supergiants",
        "LSG"
    ]
    for team in test_teams:
        normalized = normalize_team_name(team)
        print(f"'{team}' -> '{normalized}'")
    
    # Test the Jitesh/Suyash Sharma case
    print("\nTesting Sharma matching:")
    result = find_matching_player(
        "Sharma",  # As it would come from dismissal text after cleaning
        {},  # Empty player stats
        False,  # Not a sub
        [],  # No bowling team players yet
        "Royal Challengers Bengaluru"  # The team they play for
    )
    
    print(f"\nTest result for 'Sharma':")
    print(f"Matched name: {result}")

if __name__ == "__main__":
    # Setup basic logging for local testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        try:
            result = scrape_scorecard(url)
            print(json.dumps(result, indent=2))
        except Exception as e:
            logger.error(f"Failed to scrape scorecard: {str(e)}")
            sys.exit(1)
    else:
        # Run test if no URL provided
        test_player_matching()


