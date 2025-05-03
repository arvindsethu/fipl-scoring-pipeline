import json
import os
from typing import Dict, Any, Tuple

def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load and return JSON file contents"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found - {filepath}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file - {filepath}")
        exit(1)

def get_player_role(player_name: str, players_data: Dict[str, Any]) -> str:
    """Get player role from players.json"""
    for player in players_data["players"]:
        if player["name"] == player_name:
            return player["role"]
    return "Unknown"

def calculate_runs_conceded(overs: float, economy: float) -> int:
    """Calculate runs conceded from overs and economy rate"""
    # Convert overs to balls (e.g., 2.3 overs = 15 balls)
    balls = int(overs * 6)
    # Calculate runs and round up to nearest integer
    runs = (economy * balls) / 6
    return int(runs + 0.999)  # Round up by adding 0.999 before converting to int

def format_overs(overs: float) -> str:
    """Format overs as string (e.g., 2.3)"""
    return f"{int(overs)}.{int((overs % 1) * 6)}"

def analyze_strike_rate_differential(player_stats: Dict[str, Any], rules: Dict[str, Any], player_role: str) -> Tuple[str, int]:
    """Analyze strike rate differential and return highest/lowest qualifying category and points"""
    if player_stats.get("did_not_bat") == "Yes":
        return None, 0
        
    balls_faced = player_stats.get("balls_faced", 0)
    runs_scored = player_stats.get("runs_scored", 0)
    sr_differential = player_stats.get("sr_differential", 0)
    
    # Check higher differentials (positive)
    if runs_scored >= 20 and sr_differential > 0:  # Minimum runs requirement and positive differential
        if sr_differential >= 200 and balls_faced >= 10:
            return "SR Diff Higher 200_plus", rules["strike_rate_differential"]["higher"]["200_plus"][player_role]
        elif sr_differential >= 100 and balls_faced >= 10:
            return "SR Diff Higher 100_to_199.99", rules["strike_rate_differential"]["higher"]["100_to_199.99"][player_role]
        elif sr_differential >= 75 and balls_faced >= 10:
            return "SR Diff Higher 75_to_99.99", rules["strike_rate_differential"]["higher"]["75_to_99.99"][player_role]
        elif sr_differential >= 50 and balls_faced >= 12:
            return "SR Diff Higher 50_to_74.99", rules["strike_rate_differential"]["higher"]["50_to_74.99"][player_role]
        elif sr_differential >= 30 and balls_faced >= 15:
            return "SR Diff Higher 30_to_49.99", rules["strike_rate_differential"]["higher"]["30_to_49.99"][player_role]
        elif sr_differential >= 20 and balls_faced >= 15:
            return "SR Diff Higher 20_to_29.99", rules["strike_rate_differential"]["higher"]["20_to_29.99"][player_role]
    
    # Check lower differentials (negative)
    if balls_faced >= 10 and sr_differential < 0:  # Minimum balls requirement and negative differential
        sr_diff_abs = abs(sr_differential)
        if sr_diff_abs >= 70:
            return "SR Diff Lower 70_plus", rules["strike_rate_differential"]["lower"]["70_plus"][player_role]
        elif sr_diff_abs >= 60:
            return "SR Diff Lower 60_to_69.99", rules["strike_rate_differential"]["lower"]["60_to_69.99"][player_role]
        elif sr_diff_abs >= 50:
            return "SR Diff Lower 50_to_59.99", rules["strike_rate_differential"]["lower"]["50_to_59.99"][player_role]
        elif sr_diff_abs >= 40 and balls_faced >= 12:
            return "SR Diff Lower 40_to_49.99", rules["strike_rate_differential"]["lower"]["40_to_49.99"][player_role]
        elif sr_diff_abs >= 30 and balls_faced >= 15:
            return "SR Diff Lower 30_to_39.99", rules["strike_rate_differential"]["lower"]["30_to_39.99"][player_role]
        elif sr_diff_abs >= 20 and balls_faced >= 15:
            return "SR Diff Lower 20_to_29.99", rules["strike_rate_differential"]["lower"]["20_to_29.99"][player_role]
    
    return None, 0

def analyze_economy_differential(player_stats: Dict[str, Any], rules: Dict[str, Any], player_role: str) -> Tuple[str, int]:
    """Analyze economy rate differential and return highest/lowest qualifying category and points"""
    if player_stats.get("overs", 0) < 2.1:  # Minimum overs requirement
        return None, 0
        
    econ_differential = player_stats.get("economy_differential", 0)
    
    # Check higher differentials (positive)
    if econ_differential > 0:
        if econ_differential >= 70:
            return "Econ Diff Higher 70_plus", rules["economy_rate_differential"]["higher"]["70_plus"][player_role]
        elif econ_differential >= 60:
            return "Econ Diff Higher 60_to_69.99", rules["economy_rate_differential"]["higher"]["60_to_69.99"][player_role]
        elif econ_differential >= 50:
            return "Econ Diff Higher 50_to_59.99", rules["economy_rate_differential"]["higher"]["50_to_59.99"][player_role]
        elif econ_differential >= 40:
            return "Econ Diff Higher 40_to_49.99", rules["economy_rate_differential"]["higher"]["40_to_49.99"][player_role]
        elif econ_differential >= 30:
            return "Econ Diff Higher 30_to_39.99", rules["economy_rate_differential"]["higher"]["30_to_39.99"][player_role]
        elif econ_differential >= 20:
            return "Econ Diff Higher 20_to_29.99", rules["economy_rate_differential"]["higher"]["20_to_29.99"][player_role]
    
    # Check lower differentials (negative)
    else:
        eco_diff_abs = abs(econ_differential)
        if eco_diff_abs >= 70:
            return "Econ Diff Lower 70_plus", rules["economy_rate_differential"]["lower"]["70_plus"][player_role]
        elif eco_diff_abs >= 60:
            return "Econ Diff Lower 60_to_69.99", rules["economy_rate_differential"]["lower"]["60_to_69.99"][player_role]
        elif eco_diff_abs >= 50:
            return "Econ Diff Lower 50_to_59.99", rules["economy_rate_differential"]["lower"]["50_to_59.99"][player_role]
        elif eco_diff_abs >= 40:
            return "Econ Diff Lower 40_to_49.99", rules["economy_rate_differential"]["lower"]["40_to_49.99"][player_role]
        elif eco_diff_abs >= 30:
            return "Econ Diff Lower 30_to_39.99", rules["economy_rate_differential"]["lower"]["30_to_39.99"][player_role]
        elif eco_diff_abs >= 20:
            return "Econ Diff Lower 20_to_29.99", rules["economy_rate_differential"]["lower"]["20_to_29.99"][player_role]
    
    return None, 0

def calculate_team_averages(team_data: Dict[str, Any]) -> Tuple[float, float]:
    """Calculate team's average strike rate and economy rate"""
    total_runs = 0
    total_balls = 0
    total_runs_conceded = 0
    total_overs = 0
    
    for stats in team_data["player_stats"].values():
        if stats.get("did_not_bat") != "Yes":
            total_runs += stats.get("runs_scored", 0)
            total_balls += stats.get("balls_faced", 0)
        
        if stats.get("overs", 0) > 0:
            total_runs_conceded += calculate_runs_conceded(stats["overs"], stats["economy"])
            total_overs += stats["overs"]
    
    avg_sr = (total_runs / total_balls * 100) if total_balls > 0 else 0
    avg_econ = (total_runs_conceded / total_overs) if total_overs > 0 else 0
    
    return avg_sr, avg_econ

def main():
    # Load required files
    scorecard = load_json_file("manual_tools/outputs/scorecard.json")
    rules = load_json_file("config/scoring_rules.json")
    players_data = load_json_file("config/players.json")
    
    print("\n=== Strike Rate and Economy Differential Analysis ===")
    
    for team, team_data in scorecard.items():
        team_has_points = False
        avg_sr, avg_econ = calculate_team_averages(team_data)
        
        print(f"\n{team}")
        print(f"Team Averages - Strike Rate: {avg_sr:.1f}, Economy: {avg_econ:.1f}")
        print("-" * 50)
        
        for player, stats in team_data["player_stats"].items():
            # Skip players who didn't bat or bowl
            if stats.get("did_not_bat") == "Yes" and stats.get("overs", 0) == 0:
                continue
                
            player_role = get_player_role(player, players_data)
            has_points = False
            
            # Analyze strike rate differential
            sr_category, sr_points = analyze_strike_rate_differential(stats, rules, player_role)
            if sr_category:
                has_points = True
                runs = stats.get("runs_scored", 0)
                balls = stats.get("balls_faced", 0)
                sr = (runs / balls * 100) if balls > 0 else 0
                sr_diff = stats.get("sr_differential", 0)
                
                print(f"\nPlayer: {player} ({player_role})")
                print(f"Stats: {runs} off {balls} at {sr:.1f} (SR Diff = {sr_diff:+.1f}%) ({sr_points:d} points)")
            
            # Analyze economy differential
            econ_category, econ_points = analyze_economy_differential(stats, rules, player_role)
            if econ_category:
                if not has_points:
                    print(f"\nPlayer: {player} ({player_role})")
                overs = stats.get("overs", 0)
                wickets = stats.get("wickets", 0)
                economy = stats.get("economy", 0)
                econ_diff = stats.get("economy_differential", 0)
                runs_conceded = calculate_runs_conceded(overs, economy)
                
                print(f"Stats: {format_overs(overs)} overs, {wickets}/{runs_conceded} at {economy:.1f} (Econ Diff: {econ_diff:+.1f}%) ({econ_points:d} points)")
                has_points = True
            
            if has_points:
                team_has_points = True
        
        if not team_has_points:
            print("No players with differential points")

if __name__ == "__main__":
    main() 