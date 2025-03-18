import argparse
from scorecard_scraper import scrape_scorecard
from score_calculator import calculate_scores_and_update_sheet
import logging
import json
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('output/cricket_scores.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Cricket Match Score Calculator')
    parser.add_argument('--url', type=str, required=True, 
                       help='ESPNCricinfo scorecard URL')
    parser.add_argument('--output', type=str, default='output/scorecard.json',
                       help='Output JSON file path (default: scorecard.json)')
    args = parser.parse_args()

    logger = setup_logging()
    
    try:
        # Step 1: Scrape scorecard
        logger.info(f"Scraping scorecard from: {args.url}")
        scorecard_data = scrape_scorecard(args.url)
        
        if not scorecard_data:
            logger.error("Failed to scrape scorecard data")
            return 1
            
        # Step 2: Save raw scorecard data
        logger.info(f"Saving scorecard data to {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(scorecard_data, f, indent=4)
            
        # Step 3: Calculate scores
        logger.info("Calculating player scores")
        calculate_scores_and_update_sheet()
        
        # Step 4: Print summary
        logger.info("Score calculation complete. Summary:")
        with open(args.output, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
            for team, team_data in final_data.items():
                logger.info(f"\nTeam: {team}")
                logger.info(f"Average Economy: {team_data['average_economy']}")
                logger.info(f"Average Strike Rate: {team_data['average_strike_rate']}")
        
        logger.info("\nProcess completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in processing: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
