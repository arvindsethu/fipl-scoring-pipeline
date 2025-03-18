import json

def update_json():
    # Read the existing JSON file
    with open('ipl_2025_matches.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process each match
    for match in data['matches']:
        # Update URL with base URL
        base_url = "https://www.espncricinfo.com"
        match['url'] = f"{base_url}{match['url']}"
        
        # Create teams structure using existing data
        team1, team2 = match['team1'], match['team2']
        match['teams'] = {
            team1: {"gameweek_match": match[team1]},
            team2: {"gameweek_match": match[team2]}
        }
        
        # Remove the old team number fields and team1/team2 fields
        del match[team1]
        del match[team2]
        del match['team1']
        del match['team2']
    
    # Save the updated JSON
    with open('ipl_2025_matches.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Successfully updated ipl_2025_matches.json with new structure")

if __name__ == "__main__":
    update_json()