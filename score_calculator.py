import json
from typing import Dict, Any

# Load scoring rules
with open('config/scoring_rules.json', 'r', encoding='utf-8') as f:
    scoring_rules = json.load(f)

# Load player roles
with open('config/players.json', 'r', encoding='utf-8') as f:
    players_data = json.load(f)
    # Create a dictionary for quick player role lookup
    player_roles = {player['name']: player['role'] for player in players_data['players']}

# Function to calculate batting points
def calculate_batting_points(stats: Dict[str, Any], player_name: str) -> tuple[float, float, float, float]:
    runs_points = 0
    strike_rate_points = 0
    boundaries_points = 0
    player_role = player_roles.get(player_name, "Unknown")
    
    if player_role == "Unknown":
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

# Function to calculate bowling points
def calculate_bowling_points(stats: Dict[str, Any], player_name: str) -> tuple[float, float, float, float, float, float]:
    wickets_points = 0
    maiden_points = 0
    economy_points = 0
    extras_points = 0
    dots_points = 0
    player_role = player_roles.get(player_name, "Unknown")
    
    if player_role == "Unknown":
        return (0, 0, 0, 0, 0, 0)
    
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

# Function to calculate fielding points
def calculate_fielding_points(stats: Dict[str, Any], player_name: str) -> float:
    fielding_points = 0
    player_role = player_roles.get(player_name, "Unknown")
    
    if player_role == "Unknown":
        print(f"Warning: Role not found for player {player_name}")
        return fielding_points
        
    # Points for catches, stumpings and direct run outs
    fielding_actions = stats['catches'] + stats['stumping'] + stats['run_outs']
    fielding_points += fielding_actions * scoring_rules['fielding']['catch_stumping_runout'][player_role]
    
    return fielding_points

# Function to calculate player of the match points
def calculate_potm_points(stats: Dict[str, Any], player_name: str) -> float:
    player_role = player_roles.get(player_name, "Unknown")
    
    if player_role == "Unknown":
        return 0

    return scoring_rules['miscellaneous']['player_of_match'][player_role] if stats['potm'] == 'Yes' else 0

def calculate_scores_and_update_sheet():
    # Load player statistics from scorecard.json
    with open('output/scorecard.json', 'r', encoding='utf-8') as f:
        scorecard_data = json.load(f)

    # Calculate points for each player
    for team_name, team_data in scorecard_data.items():
        if 'player_stats' in team_data:
            for player_name, stats in team_data['player_stats'].items():
                # Calculate batting points breakdown
                runs_points = 0
                strike_rate_points = 0
                boundaries_points = 0
                
                # Calculate batting points with detailed breakdown
                batting_stats = calculate_batting_points(stats, player_name)
                if isinstance(batting_stats, tuple):
                    batting_points, runs_points, strike_rate_points, boundaries_points = batting_stats
                else:
                    batting_points = batting_stats
                
                # Calculate bowling points breakdown
                wickets_points = 0
                maiden_points = 0
                economy_points = 0
                extras_points = 0
                dots_points = 0
                
                # Calculate bowling points with detailed breakdown
                bowling_stats = calculate_bowling_points(stats, player_name)
                if isinstance(bowling_stats, tuple):
                    bowling_points, wickets_points, maiden_points, economy_points, extras_points, dots_points = bowling_stats
                else:
                    bowling_points = bowling_stats
                
                # Calculate fielding points
                fielding_points = calculate_fielding_points(stats, player_name)
                potm_points = calculate_potm_points(stats, player_name)
                
                # Store all point categories - convert to int if it ends in .0
                def format_points(points):
                    return int(points) if float(points).is_integer() else float(points)
                
                # Update all point categories
                stats['runs_points'] = format_points(runs_points)
                stats['strike_rate_points'] = format_points(strike_rate_points)
                stats['boundaries_points'] = format_points(boundaries_points)
                stats['maiden_points'] = format_points(maiden_points)
                stats['potm_points'] = format_points(potm_points)
                stats['wickets_points'] = format_points(wickets_points)
                stats['dots_points'] = format_points(dots_points)
                stats['extras_points'] = format_points(extras_points)
                stats['economy_points'] = format_points(economy_points)
                stats['batting_points'] = format_points(batting_points)
                stats['bowling_points'] = format_points(bowling_points)
                stats['fielding_points'] = format_points(fielding_points)
                
                # Calculate total points as sum of all categories
                total = batting_points + bowling_points + fielding_points + potm_points
                stats['total_points'] = format_points(total)

    # Save the updated scorecard back to the file
    with open('output/scorecard.json', 'w', encoding='utf-8') as f:
        json.dump(scorecard_data, f, indent=4)

    print("Player scores calculated and saved to scorecard.json")

if __name__ == "__main__":
    calculate_scores_and_update_sheet()

