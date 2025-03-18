import requests
from bs4 import BeautifulSoup
import json
import re

def clean_player_name(name):
    return re.sub(r'\s*[(]c[)]|\s*[†](?!\w)|\s*,', '', name).replace('\u2019', "'").strip()

def create_default_player_stats():
    return {
        "runs_scored": 0,
        "balls_faced": 0,
        "fours": 0,
        "sixes": 0,
        "strike_rate": 0,
        "sr_differential": 0.0,  # Will be stored as percentage difference from average
        "overs": 0,
        "economy": 0,
        "economy_differential": 0.0,  # Will be stored as percentage difference from average
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

def find_matching_player(name, player_stats, is_sub=False, bowling_team_players=None):
    """
    Single-pass player matching with prioritized matching strategy
    Args:
        name: Name to match
        player_stats: Full player stats dictionary
        is_sub: Whether this is a substitute player
        bowling_team_players: Optional list of players from bowling team to restrict search
    """
    # Store original name for returning
    original_name = name
    # Convert to lower for comparison
    name = name.lower()
    name_parts = name.split()
    last_name = name_parts[-1]
    first_name = name_parts[0]
    first_letter = first_name[0] if first_name else ''
    
    # Determine which players to search through
    search_players = bowling_team_players if bowling_team_players else player_stats
    
    # Handle existing sub player first
    if is_sub and original_name in search_players and player_stats[original_name]["is_sub"]:
        return (original_name, False)
    
    # Single pass through players with prioritized matching
    last_name_matches = []
    first_name_matches = []
    
    for player in search_players:
        player_lower = player.lower()
        
        # Exact match (highest priority)
        if player_lower == name or player_lower.replace('-', ' ') == name:
            return (player, False)
            
        # Store potential matches for fallback
        player_parts = player_lower.split()
        if player_parts[-1] == last_name:
            last_name_matches.append(player)
        # Only match first name if it's more than just an initial
        elif len(first_name) > 1 and player_parts[0].startswith(first_name):
            first_name_matches.append(player)
    
    # Check last name matches
    if len(last_name_matches) == 1:
        return (last_name_matches[0], False)
    elif len(last_name_matches) > 1:
        # Secondary check: Try to match first letter among last name matches
        if first_letter:
            first_letter_matches = [p for p in last_name_matches if p.split()[0][0].lower() == first_letter]
            if len(first_letter_matches) == 1:
                return (first_letter_matches[0], False)
        
        print(f"Warning: Multiple unresolved last name matches for '{original_name}': {last_name_matches}")
        return (None, False)
    
    # First name match
    if len(first_name_matches) == 1:
        return (first_name_matches[0], False)
    elif len(first_name_matches) > 1:
        print(f"Warning: Multiple unresolved first name matches for '{original_name}': {first_name_matches}")
        return (None, False)
    
    # New sub player
    if is_sub:
        return (original_name, True)
    
    return (None, False)

def parse_dismissal_text(dismissal_text):
    """Parse dismissal text and return fielder names involved"""
    if not dismissal_text:
        return []
    
    # Handle caught and bowled
    if 'c & b' in dismissal_text:
        bowler = dismissal_text.split('c & b')[1].strip()
        bowler = clean_player_name(bowler)
        return [bowler]

    # Handle stumpings
    if dismissal_text.startswith('st '):
        if 'sub (' in dismissal_text:
            sub_match = re.search(r'sub\s*\(([^)]+)\)', dismissal_text)
            keeper_name = sub_match.group(1) if sub_match else None
        else:
            keeper_name = dismissal_text.split(' b ')[0][3:].strip()
            keeper_name = re.sub(r'†', '', keeper_name)
        
        if keeper_name:
            keeper_name = clean_player_name(keeper_name)
            return [keeper_name]

    # Handle catches
    catch_match = re.match(r'c\s+(?:sub\s*\([^)]+\)|†?[^b]+)b', dismissal_text)
    if catch_match:
        if 'sub (' in dismissal_text:
            sub_match = re.search(r'sub\s*\(([^)]+)\)', dismissal_text)
            catcher = sub_match.group(1) if sub_match else None
        else:
            catcher = dismissal_text.split(' b ')[0][2:].strip()
            catcher = re.sub(r'†', '', catcher)
        
        if catcher:
            catcher = clean_player_name(catcher)
            return [catcher]

    # Handle run outs
    if 'run out' in dismissal_text:
        fielders_match = re.search(r'\((.*?)\)', dismissal_text)
        if fielders_match:
            fielders_text = fielders_match.group(1)
            fielders = fielders_text.split('/')
            
            cleaned_fielders = []
            for fielder in fielders:
                fielder = re.sub(r'sub\s*\[(.*?)\]', r'\1', fielder)
                fielder = re.sub(r'†', '', fielder)
                fielder = clean_player_name(fielder)
                if fielder:
                    cleaned_fielders.append(fielder)
            
            return cleaned_fielders

    return []

def extract_run_rate(innings_html):
    """Extract run rate from innings HTML content."""
    soup = BeautifulSoup(innings_html, 'html.parser')
    # Find all spans with the specific class
    spans = soup.find_all('span', class_='ds-text-tight-s')
    for span in spans:
        # Get text content including any nested text
        text = ''.join(span.stripped_strings)
        if '(RR:' in text:
            try:
                run_rate = float(text.replace('(RR:', '').replace(')', '').strip())
                return run_rate
            except ValueError:
                print("Could not convert run rate to float")
                return None
    return None

def scrape_scorecard(url):
    print(f"Fetching: {url}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return {}
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Initialize basic structure
    scorecard_data = {}

    # Extract team names from innings headers and match header
    innings_divs = soup.find_all('div', class_='ds-rounded-lg')[:2]  # Get only first two innings
    team_names = []
    
    # First try to get both team names from the match header
    match_header = soup.find('div', class_='ds-text-tight-m ds-font-regular ds-text-typo-mid3')
    if match_header:
        teams_text = match_header.text.strip()
        vs_split = teams_text.split(' vs ')
        if len(vs_split) == 2:
            team1 = vs_split[0].strip()
            team2 = vs_split[1].split(' in ')[0].strip()
            team_names = [team1, team2]
            # Initialize data structure for both teams
            for team in team_names:
                scorecard_data[team] = {
                    "average_economy": 0,
                    "average_strike_rate": 0,
                    "player_stats": {}
                }
                print(f"Initialized team structure for: {team}")
    
    # If we couldn't get both teams from header, get what we can from innings
    if len(team_names) < 2:
        team_names = []  # Reset team names
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
                    print(f"Initialized team structure for: {team_name}")

    if not team_names:
        print("Error: No teams found")
        return {}

    print(f"\nTeams found: {team_names}")
    
    # Store dismissals for later processing
    dismissal_records = []
    
    # Process innings
    for innings_num, innings in enumerate(innings_divs, 1):
        print(f"\nProcessing innings {innings_num}")
        
        # Get batting team name
        team_header = innings.find('span', class_='ds-text-title-xs ds-font-bold ds-capitalize')
        if not team_header:
            continue
            
        batting_team = team_header.text.strip()
        # Handle case where we don't have second team yet
        if len(team_names) == 1:
            bowling_team = None
        else:
            bowling_team = team_names[1] if batting_team == team_names[0] else team_names[0]
        
        print(f"Batting team: {batting_team}")
        print(f"Bowling team: {bowling_team if bowling_team else 'Unknown'}")
        
        # Extract run rate for this innings
        run_rate = extract_run_rate(str(innings))
        if run_rate:
            # Calculate and store averages
            avg_strike_rate = float(f"{(run_rate * 100) / 6:.2f}")
            avg_economy = float(f"{run_rate:.2f}")
            
            # Update team stats
            scorecard_data[batting_team]["average_strike_rate"] = avg_strike_rate
            if bowling_team:  # Only update bowling team stats if we know who they are
                scorecard_data[bowling_team]["average_economy"] = avg_economy
            
            print(f"Updated {batting_team} avg SR: {avg_strike_rate:.2f}")
            if bowling_team:
                print(f"Updated {bowling_team} avg economy: {avg_economy:.2f}")
        else:
            print(f"Could not find run rate for innings {innings_num}")
        
        # Process batting
        batting_table = innings.find('table', class_='ci-scorecard-table')
        if batting_table:
            # Get all player cells in one go
            player_cells = batting_table.find_all('td', class_=['ds-w-0 ds-whitespace-nowrap ds-min-w-max', 
                'ds-w-0 ds-whitespace-nowrap ds-min-w-max ds-border-line-primary ci-scorecard-player-notout'])
            print(f"Batting players found: {len(player_cells)}")
            
            for player_cell in player_cells:
                player_link = player_cell.find('a')
                if not player_link:
                    continue
                    
                player_name = clean_player_name(player_link.text.strip())
                if player_name not in scorecard_data[batting_team]["player_stats"]:
                    scorecard_data[batting_team]["player_stats"][player_name] = create_default_player_stats()
                
                row = player_cell.find_parent('tr')
                if row:
                    cells = row.find_all('td')
                    if len(cells) >= 8:
                        # Store dismissal for later processing only if we know the bowling team
                        dismissal_info = cells[1].text.strip()
                        if bowling_team and dismissal_info and dismissal_info != 'not out':
                            dismissal_records.append({
                                'batsman': player_name,
                                'dismissal_text': dismissal_info,
                                'batting_team': batting_team,
                                'bowling_team': bowling_team
                            })
                        
                        # Update batting stats
                        strike_rate_text = cells[7].text.strip()
                        strike_rate = float(f"{float(strike_rate_text) if strike_rate_text != '-' else 0:.2f}")
                        # Calculate SR differential as percentage difference from average
                        avg_sr = scorecard_data[batting_team]["average_strike_rate"]
                        # Calculate percentage difference and round to 1 decimal place
                        sr_differential = float(f"{((strike_rate - avg_sr) / avg_sr * 100) if avg_sr > 0 else 0.0:.1f}")
                        
                        scorecard_data[batting_team]["player_stats"][player_name].update({
                            "runs_scored": int(cells[2].text.strip() or 0),
                            "balls_faced": int(cells[3].text.strip() or 0),
                            "fours": int(cells[5].text.strip() or 0),
                            "sixes": int(cells[6].text.strip() or 0),
                            "strike_rate": strike_rate,
                            "sr_differential": sr_differential,
                            "did_not_bat": "No"
                        })

            # Process did not bat - only if we found a batting table
            dnb_row = batting_table.find('tr', class_='!ds-border-b-0')
            if dnb_row:
                dnb_div = dnb_row.find('div', class_='ds-text-tight-m')
                if dnb_div and 'bat' in dnb_div.text:
                    dnb_players = dnb_div.find_all('a')
                    for player in dnb_players:
                        player_name = clean_player_name(player.text.strip())
                        if player_name not in scorecard_data[batting_team]["player_stats"]:
                            scorecard_data[batting_team]["player_stats"][player_name] = create_default_player_stats()

        # Process bowling - only if we know the bowling team
        if bowling_team:
            bowling_table = innings.find('table', class_='ds-w-full ds-table ds-table-md ds-table-auto')
            if bowling_table:
                bowling_rows = bowling_table.find_all('tr')
                for row in bowling_rows:
                    cells = row.find_all('td')
                    if not (cells and len(cells) >= 11):
                        continue
                        
                    player_link = cells[0].find('a')
                    if not player_link:
                        continue
                        
                    player_name = clean_player_name(player_link.text.strip())
                    if player_name not in scorecard_data[bowling_team]["player_stats"]:
                        scorecard_data[bowling_team]["player_stats"][player_name] = create_default_player_stats()
                    
                    # Extract bowling stats
                    economy = float(f"{float(cells[5].text.strip() or 0):.2f}")
                    # Calculate economy differential as percentage difference from average
                    avg_econ = float(f"{scorecard_data[bowling_team]['average_economy']:.2f}")
                    # Calculate percentage difference and round to 1 decimal place
                    econ_differential = float(f"{((economy - avg_econ) / avg_econ * 100) if avg_econ > 0 else 0.0:.1f}")
                    
                    # Create a temporary dictionary with all the values to ensure consistent formatting
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

    # Process dismissals
    print("\nProcessing dismissals...")
    for record in dismissal_records:
        fielders = parse_dismissal_text(record['dismissal_text'])
        
        # Get bowling team players for restricted search
        bowling_team_players = list(scorecard_data[record['bowling_team']]["player_stats"].keys())
        
        for fielder_name in fielders:
            is_sub = ('sub' in record['dismissal_text'] and fielder_name in record['dismissal_text'].split('sub')[1])
            matched_name, is_new = find_matching_player(
                fielder_name, 
                scorecard_data[record['bowling_team']]["player_stats"], 
                is_sub,
                bowling_team_players
            )
            
            if matched_name:
                if is_new:
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name] = create_default_player_stats()
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name]["is_sub"] = True
                
                # Update fielding stats based on dismissal type
                if "c & b" in record['dismissal_text']:
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name]["catches"] += 1
                elif record['dismissal_text'].startswith("st "):
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name]["stumping"] += 1
                elif record['dismissal_text'].startswith("c "):
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name]["catches"] += 1
                elif "run out" in record['dismissal_text']:
                    # Calculate run out points based on number of fielders involved
                    points_per_fielder = 1.0 / len(fielders) if fielders else 0
                    scorecard_data[record['bowling_team']]["player_stats"][matched_name]["run_outs"] += points_per_fielder

    # Player of the Match
    potm_header = soup.find('div', class_='ds-text-eyebrow-xs ds-uppercase ds-text-typo-mid2', string='Player Of The Match')
    if potm_header:
        potm_container = potm_header.find_next('div')
        if potm_container and (potm_link := potm_container.find('a')):
            potm_name = clean_player_name(potm_link.text.strip())
            # Search for POTM in both teams
            for team in team_names:
                if potm_name in scorecard_data[team]["player_stats"]:
                    scorecard_data[team]["player_stats"][potm_name]["potm"] = "Yes"
                    break

    # Print summary for both teams
    for team in team_names:
        print(f"\nTeam: {team}")
        print(f"Total players: {len(scorecard_data[team]['player_stats'])}")
        print("Player names:", ", ".join(sorted(scorecard_data[team]["player_stats"].keys())))

    # Before returning the data, ensure all floating point values have correct decimal places
    for team in scorecard_data:
        # Format team averages
        scorecard_data[team]["average_economy"] = float(f"{scorecard_data[team]['average_economy']:.2f}")
        scorecard_data[team]["average_strike_rate"] = float(f"{scorecard_data[team]['average_strike_rate']:.2f}")
        
        # Format player stats
        for player in scorecard_data[team]["player_stats"]:
            stats = scorecard_data[team]["player_stats"][player]
            # Create a temporary dictionary with formatted values
            formatted_stats = {
                "strike_rate": float(f"{stats['strike_rate']:.2f}"),
                "sr_differential": float(f"{stats['sr_differential']:.1f}"),
                "economy": float(f"{stats['economy']:.2f}"),
                "economy_differential": float(f"{stats['economy_differential']:.1f}")
            }
            # Update the stats with formatted values
            stats.update(formatted_stats)

    # Check and report any sub players
    for team in team_names:
        sub_players = [player for player in scorecard_data[team]["player_stats"].keys() 
                      if scorecard_data[team]["player_stats"][player]["is_sub"]]
        if sub_players:
            print(f"\nSub players for {team}: {', '.join(sub_players)}")

    return scorecard_data


