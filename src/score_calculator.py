import os
import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Constants for Cloud Function environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
TMP_DIR = '/tmp'

# Set to keep track of players with unknown roles
unknown_role_players = set()

def get_player_role(player_name: str) -> str:
    """Get player role and log warning only once if role is unknown"""
    role = player_roles.get(player_name, "Unknown")
    if role == "Unknown" and player_name not in unknown_role_players:
        logger.error(f"Invalid or missing player role for {player_name}")
        unknown_role_players.add(player_name)
    return role

def load_config_files():
    """Load configuration files with proper error handling"""
    try:
        # Load scoring rules
        with open(os.path.join(CONFIG_DIR, 'scoring_rules.json'), 'r', encoding='utf-8') as f:
            scoring_rules = json.load(f)

        # Load player roles
        with open(os.path.join(CONFIG_DIR, 'players.json'), 'r', encoding='utf-8') as f:
            players_data = json.load(f)
            player_roles = {player['name']: player['role'] for player in players_data['players']}
            
        return scoring_rules, player_roles
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Configuration file not found: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {str(e)}")

# Load configuration files
scoring_rules, player_roles = load_config_files()

# Function to calculate batting points
def calculate_batting_points(stats: Dict[str, Any], player_name: str) -> tuple[float, float, float, float]:
    runs_points = 0
    strike_rate_points = 0
    boundaries_points = 0
    player_role = get_player_role(player_name)
    
    if player_role == "Unknown":
        return (0, 0, 0, 0)

    try:
        # Validate numerical values
        if not isinstance(stats['runs_scored'], (int, float)) or stats['runs_scored'] < 0:
            logger.error(f"Invalid runs_scored value for {player_name}: {stats['runs_scored']}")
            return (0, 0, 0, 0)
        if not isinstance(stats['balls_faced'], (int, float)) or stats['balls_faced'] < 0:
            logger.error(f"Invalid balls_faced value for {player_name}: {stats['balls_faced']}")
            return (0, 0, 0, 0)
        if not isinstance(stats['fours'], (int, float)) or stats['fours'] < 0:
            logger.error(f"Invalid fours value for {player_name}: {stats['fours']}")
            return (0, 0, 0, 0)
        if not isinstance(stats['sixes'], (int, float)) or stats['sixes'] < 0:
            logger.error(f"Invalid sixes value for {player_name}: {stats['sixes']}")
            return (0, 0, 0, 0)

        # Basic run scoring points    
        runs_points += stats['runs_scored'] * scoring_rules['run_scoring']['run'][player_role]
        boundaries_points += stats['fours'] * scoring_rules['run_scoring']['four'][player_role]
        boundaries_points += stats['sixes'] * scoring_rules['run_scoring']['six'][player_role]
        
        # Duck penalty
        if stats['runs_scored'] == 0 and stats['did_not_bat'] == "No":
            runs_points += scoring_rules['run_scoring']['duck'][player_role]
        
        # Run milestones
        if stats['runs_scored'] >= 150:
            runs_points += scoring_rules['run_scoring']['milestone_150'][player_role]
        elif stats['runs_scored'] >= 100:
            runs_points += scoring_rules['run_scoring']['milestone_100'][player_role]
        elif stats['runs_scored'] >= 75:
            runs_points += scoring_rules['run_scoring']['milestone_75'][player_role]
        elif stats['runs_scored'] >= 50:
            runs_points += scoring_rules['run_scoring']['milestone_50'][player_role]
        elif stats['runs_scored'] >= 30:
            runs_points += scoring_rules['run_scoring']['milestone_30'][player_role]
        
        # Strike rate bonuses (minimum 20 runs)
        if stats['runs_scored'] >= 20:
            sr = stats['strike_rate']
            if sr >= 300:
                strike_rate_points += scoring_rules['strike_rate']['above_300'][player_role]
            elif sr >= 250:
                strike_rate_points += scoring_rules['strike_rate']['above_250'][player_role]
            elif sr >= 200:
                strike_rate_points += scoring_rules['strike_rate']['above_200'][player_role]
            elif sr >= 170:
                strike_rate_points += scoring_rules['strike_rate']['above_170'][player_role]
            elif sr >= 150:
                strike_rate_points += scoring_rules['strike_rate']['above_150'][player_role]
        
        # Strike rate penalties (minimum 15 balls)
        if stats['balls_faced'] >= 15:
            sr = stats['strike_rate']
            if sr < 70:
                strike_rate_points += scoring_rules['strike_rate']['below_70'][player_role]
            elif sr < 90:
                strike_rate_points += scoring_rules['strike_rate']['below_90'][player_role]
        
        # Strike rate differential points
        sr_diff = stats['sr_differential']  # This is already in percentage form
        
        # Lower than innings SR
        if sr_diff < 0:
            sr_diff_abs = abs(sr_diff)
            if sr_diff_abs >= 70 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['70_plus'][player_role]
            elif sr_diff_abs >= 60 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['60_to_69.99'][player_role]
            elif sr_diff_abs >= 50 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['50_to_59.99'][player_role]
            elif sr_diff_abs >= 40 and stats['balls_faced'] >= 12:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['40_to_49.99'][player_role]
            elif sr_diff_abs >= 30 and stats['balls_faced'] >= 15:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['30_to_39.99'][player_role]
            elif sr_diff_abs >= 20 and stats['balls_faced'] >= 15:
                strike_rate_points += scoring_rules['strike_rate_differential']['lower']['20_to_29.99'][player_role]
        
        # Higher than innings SR
        else:
            if sr_diff >= 200 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['200_plus'][player_role]
            elif sr_diff >= 100 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['100_to_199.99'][player_role]
            elif sr_diff >= 75 and stats['balls_faced'] >= 10:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['75_to_99.99'][player_role]
            elif sr_diff >= 50 and stats['balls_faced'] >= 12:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['50_to_74.99'][player_role]
            elif sr_diff >= 30 and stats['balls_faced'] >= 15:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['30_to_49.99'][player_role]
            elif sr_diff >= 20 and stats['balls_faced'] >= 15:
                strike_rate_points += scoring_rules['strike_rate_differential']['higher']['20_to_29.99'][player_role]
        
        batting_points = runs_points + strike_rate_points + boundaries_points
        return (batting_points, runs_points, strike_rate_points, boundaries_points)

    except (TypeError, ValueError) as e:
        logger.error(f"Error calculating batting points for {player_name}: {str(e)}")
        return (0, 0, 0, 0)
    except KeyError as e:
        logger.error(f"Missing required stat for {player_name}: {str(e)}")
        return (0, 0, 0, 0)

# Function to calculate bowling points
def calculate_bowling_points(stats: Dict[str, Any], player_name: str) -> tuple[float, float, float, float, float, float]:
    wickets_points = 0
    maiden_points = 0
    economy_points = 0
    extras_points = 0
    dots_points = 0
    player_role = get_player_role(player_name)
    
    if player_role == "Unknown":
        return (0, 0, 0, 0, 0, 0)

    try:
        # Validate numerical values
        if not isinstance(stats['overs'], (int, float)) or stats['overs'] < 0:
            logger.error(f"Invalid overs value for {player_name}: {stats['overs']}")
            return (0, 0, 0, 0, 0, 0)
        if not isinstance(stats['wickets'], (int, float)) or stats['wickets'] < 0:
            logger.error(f"Invalid wickets value for {player_name}: {stats['wickets']}")
            return (0, 0, 0, 0, 0, 0)
        if not isinstance(stats['dots'], (int, float)) or stats['dots'] < 0:
            logger.error(f"Invalid dots value for {player_name}: {stats['dots']}")
            return (0, 0, 0, 0, 0, 0)
        if not isinstance(stats['maiden'], (int, float)) or stats['maiden'] < 0:
            logger.error(f"Invalid maiden value for {player_name}: {stats['maiden']}")
            return (0, 0, 0, 0, 0, 0)

        # Handle division by zero for run outs
        if 'fielders' in stats and len(stats.get('fielders', [])) > 0:
            try:
                points_per_fielder = 1.0 / len(stats['fielders'])
            except ZeroDivisionError:
                logger.error(f"Division by zero error calculating fielder points for {player_name}")
                points_per_fielder = 0
        
        # Points for wickets
        wickets_points += stats['wickets'] * scoring_rules['wickets']['per_wicket'][player_role]
        
        # Wicket milestones
        if stats['wickets'] >= 6:
            wickets_points += scoring_rules['wickets']['milestone_6_plus'][player_role]
        elif stats['wickets'] >= 5:
            wickets_points += scoring_rules['wickets']['milestone_5'][player_role]
        elif stats['wickets'] >= 4:
            wickets_points += scoring_rules['wickets']['milestone_4'][player_role]
        elif stats['wickets'] >= 3:
            wickets_points += scoring_rules['wickets']['milestone_3'][player_role]
        
        # Other bowling points
        maiden_points += stats['maiden'] * scoring_rules['bowling_other']['maiden_over'][player_role]
        dots_points += stats['dots'] * scoring_rules['bowling_other']['dot_ball'][player_role]
        extras_points += stats['no_balls'] * scoring_rules['bowling_other']['no_ball'][player_role]
        extras_points += stats['wides'] * scoring_rules['bowling_other']['wide'][player_role]
        
        # Economy rate points
        overs = stats['overs']
        economy = stats['economy']
        
        if overs >= 1:
            # 1 over minimum rules
            if economy >= 18:
                economy_points += scoring_rules['economy_rate']['one_over']['above_18'][player_role]
        
        if overs > 1 and overs <= 2:
            # 1-2 over rules
            if 15 <= economy < 18:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['15_to_17.99'][player_role]
            elif 13 <= economy < 15:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['13_to_14.99'][player_role]
            elif 12 <= economy < 13:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['12_to_12.99'][player_role]
            elif 11 <= economy < 12:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['11_to_11.99'][player_role]
            elif 7 <= economy < 8:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['7_to_7.99'][player_role]
            elif 6 <= economy < 7:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['6_to_6.99'][player_role]
            elif 5 <= economy < 6:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['5_to_5.99'][player_role]
            elif 4 <= economy < 5:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['4_to_4.99'][player_role]
            elif 3 <= economy < 4:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['3_to_3.99'][player_role]
            elif 2 <= economy < 3:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['2_to_2.99'][player_role]
            elif economy < 2:
                economy_points += scoring_rules['economy_rate']['one_to_two_overs']['below_2'][player_role]
        
        if overs > 2.1:
            # 2.1+ overs rules
            if 15 <= economy < 18:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['15_to_17.99'][player_role]
            elif 13 <= economy < 15:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['13_to_14.99'][player_role]
            elif 12 <= economy < 13:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['12_to_12.99'][player_role]
            elif 11 <= economy < 12:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['11_to_11.99'][player_role]
            elif 7 <= economy < 8:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['7_to_7.99'][player_role]
            elif 6 <= economy < 7:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['6_to_6.99'][player_role]
            elif 5 <= economy < 6:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['5_to_5.99'][player_role]
            elif 4 <= economy < 5:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['4_to_4.99'][player_role]
            elif 3 <= economy < 4:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['3_to_3.99'][player_role]
            elif 2 <= economy < 3:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['2_to_2.99'][player_role]
            elif economy < 2:
                economy_points += scoring_rules['economy_rate']['min_2.1_overs']['below_2'][player_role]
            
            # Economy rate differential points (only for 2.1+ overs)
            eco_diff = stats['economy_differential']  # This is already in percentage form
            
            # Higher than innings economy
            if eco_diff > 0:
                if eco_diff >= 70:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['70_plus'][player_role]
                elif eco_diff >= 60:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['60_to_69.99'][player_role]
                elif eco_diff >= 50:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['50_to_59.99'][player_role]
                elif eco_diff >= 40:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['40_to_49.99'][player_role]
                elif eco_diff >= 30:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['30_to_39.99'][player_role]
                elif eco_diff >= 20:
                    economy_points += scoring_rules['economy_rate_differential']['higher']['20_to_29.99'][player_role]
            
            # Lower than innings economy
            else:
                eco_diff_abs = abs(eco_diff)
                if eco_diff_abs >= 70:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['70_plus'][player_role]
                elif eco_diff_abs >= 60:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['60_to_69.99'][player_role]
                elif eco_diff_abs >= 50:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['50_to_59.99'][player_role]
                elif eco_diff_abs >= 40:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['40_to_49.99'][player_role]
                elif eco_diff_abs >= 30:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['30_to_39.99'][player_role]
                elif eco_diff_abs >= 20:
                    economy_points += scoring_rules['economy_rate_differential']['lower']['20_to_29.99'][player_role]
        
        bowling_points = wickets_points + maiden_points + economy_points + extras_points + dots_points
        return (bowling_points, wickets_points, maiden_points, economy_points, extras_points, dots_points)

    except (TypeError, ValueError) as e:
        logger.error(f"Error calculating bowling points for {player_name}: {str(e)}")
        return (0, 0, 0, 0, 0, 0)
    except KeyError as e:
        logger.error(f"Missing required stat for {player_name}: {str(e)}")
        return (0, 0, 0, 0, 0, 0)

# Function to calculate fielding points
def calculate_fielding_points(stats: Dict[str, Any], player_name: str) -> float:
    fielding_points = 0
    player_role = get_player_role(player_name)
    
    if player_role == "Unknown":
        return fielding_points

    try:
        # Validate numerical values
        if not isinstance(stats['catches'], (int, float)) or stats['catches'] < 0:
            logger.error(f"Invalid catches value for {player_name}: {stats['catches']}")
            return 0
        if not isinstance(stats['stumping'], (int, float)) or stats['stumping'] < 0:
            logger.error(f"Invalid stumping value for {player_name}: {stats['stumping']}")
            return 0
        if not isinstance(stats['run_outs'], (int, float)) or stats['run_outs'] < 0:
            logger.error(f"Invalid run_outs value for {player_name}: {stats['run_outs']}")
            return 0

        # Points for catches, stumpings and direct run outs
        fielding_actions = stats['catches'] + stats['stumping'] + stats['run_outs']
        fielding_points += fielding_actions * scoring_rules['fielding']['catch_stumping_runout'][player_role]
        
    except (TypeError, ValueError) as e:
        logger.error(f"Error calculating fielding points for {player_name}: {str(e)}")
        return 0
    except KeyError as e:
        logger.error(f"Missing required stat for {player_name}: {str(e)}")
        return 0
        
    return fielding_points

# Function to calculate player of the match points
def calculate_potm_points(stats: Dict[str, Any], player_name: str) -> float:
    player_role = get_player_role(player_name)
    
    if player_role == "Unknown":
        return 0

    return scoring_rules['miscellaneous']['player_of_match'][player_role] if stats['potm'] == 'Yes' else 0

def calculate_scores_and_update_sheet(scorecard_path):
    """Calculate scores for all players in a match"""
    try:
        # Load scorecard data
        with open(scorecard_path, 'r', encoding='utf-8') as f:
            scorecard_data = json.load(f)
        
        # Process each team
        for team_name, team_data in scorecard_data.items():
            if 'player_stats' not in team_data:
                continue
                
            for player_name, stats in team_data['player_stats'].items():
                # Calculate batting points
                batting_points, runs_points, sr_points, boundaries_points = calculate_batting_points(stats, player_name)
                
                # Calculate bowling points
                bowling_points, wickets_points, maiden_points, economy_points, extras_points, dots_points = calculate_bowling_points(stats, player_name)
                
                # Calculate fielding points
                fielding_points = calculate_fielding_points(stats, player_name)
                
                # Calculate POTM points
                potm_points = calculate_potm_points(stats, player_name)
                
                # Update stats with points
                stats.update({
                    'batting_points': round(batting_points, 2),
                    'runs_points': round(runs_points, 2),
                    'strike_rate_points': round(sr_points, 2),
                    'boundaries_points': round(boundaries_points, 2),
                    'bowling_points': round(bowling_points, 2),
                    'wickets_points': round(wickets_points, 2),
                    'maiden_points': round(maiden_points, 2),
                    'economy_points': round(economy_points, 2),
                    'extras_points': round(extras_points, 2),
                    'dots_points': round(dots_points, 2),
                    'fielding_points': round(fielding_points, 2),
                    'potm_points': round(potm_points, 2),
                    'total_points': round(batting_points + bowling_points + fielding_points + potm_points, 2)
                })
        
        # Save updated scorecard
        with open(scorecard_path, 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=4)
            
    except Exception as e:
        logger.error(f"Error calculating scores: {str(e)}")
        raise

if __name__ == "__main__":
    calculate_scores_and_update_sheet()

