# Automated Cricket Score Updates

Automatically updates cricket match scores and points in Google Sheets.

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Sheets:
   - Place your `service-account.json` in the `config` directory
   - Update `sheets_config.py` with your spreadsheet ID

4. Configure matches:
   - Update `config/demo.json` with match details
   - Each match needs:
     - start_time (ISO 8601 format)
     - status ("pending", "active", or "completed")
     - gameweek and team information

## GitHub Actions Setup

1. Add your Google service account JSON as a secret:
   - Go to your repository settings
   - Under "Secrets and variables" -> "Actions"
   - Add new secret named `GOOGLE_SERVICE_ACCOUNT`
   - Paste your entire service-account.json content

2. The workflow will:
   - Run every 5 minutes
   - Check for matches that need updates
   - Update the Google Sheet accordingly

## Local Testing

Run the script manually:
```bash
python test_sheet_update.py
```

## Match Update Logic

- Pending matches start updating when their start time is reached
- Active matches are updated:
  - Every 15 minutes for the first 4 hours
  - Every 30 minutes for the next hour
- Matches are marked completed after 5 hours 