# CLI Commands Documentation

This document describes the command-line interface (CLI) commands available in the Sports League Management System (SLMS).

## Setup

Ensure the Flask app environment variable is set:

```bash
export FLASK_APP=slms
# or on Windows:
set FLASK_APP=slms
```

## Organization Management

### Create Organization

Create a new organization with basic settings:

```bash
flask org:create --name "Demo League" --slug demo
```

Create organization with admin user:

```bash
flask org:create --name "Demo League" --slug demo --admin-email admin@demo.com --admin-password password123
```

Options:
- `--name`: Organization name (required)
- `--slug`: URL-friendly identifier (required)
- `--admin-email`: Admin user email (optional)
- `--admin-password`: Admin user password (optional)
- `--primary-color`: Primary brand color hex code (optional)

### List Organizations

```bash
flask org:list
```

### Organization Information

```bash
flask org:info demo
```

### Delete Organization

⚠️ **WARNING**: This permanently deletes all organization data!

```bash
flask org:delete demo
flask org:delete demo --force  # Skip confirmation
```

## Demo Data Seeding

### Seed Demo Data

Create sample data for testing and demonstration:

```bash
flask seed:demo --org demo
```

Custom seeding options:

```bash
flask seed:demo --org demo --teams 8 --players-per-team 15 --venues 2 --games 20
```

Options:
- `--org`: Organization slug (required)
- `--teams`: Number of teams (default: 6)
- `--players-per-team`: Players per team (default: 12)
- `--venues`: Number of venues (default: 1)
- `--games`: Number of games (default: 15)

**What gets created:**
- 1 Basketball league
- 1 Active season
- Teams with players
- Venues with schedules
- Games (some completed with scores)
- Sample registrations

### Clear Demo Data

⚠️ **WARNING**: This deletes all league data for the organization!

```bash
flask seed:clear --org demo
flask seed:clear --org demo --force  # Skip confirmation
```

## CSV Export

### Export Season Data

Export various types of season data to CSV files:

```bash
# Export standings
flask export:season --season <season-id> --what standings

# Export schedule
flask export:season --season <season-id> --what schedule

# Export registrations
flask export:season --season <season-id> --what registrations

# Export everything
flask export:season --season <season-id> --what all
```

Custom output directory:

```bash
flask export:season --season <season-id> --what all --output-dir ./my-exports
```

### Export Teams and Players

```bash
flask export:teams --season <season-id>
```

### List Seasons

Find season IDs for export:

```bash
flask export:list-seasons
flask export:list-seasons --org demo
```

## CSV Templates

Generate CSV templates for data imports:

```bash
# Generate teams import template
flask templates:teams

# Generate players import template
flask templates:players

# Generate venues import template
flask templates:venues

# Generate all templates
flask templates:all
```

Custom output directory:

```bash
flask templates:all --output-dir ./templates
```

## Export File Locations

By default, all exports are saved to `/tmp/exports/` with timestamps:

```
/tmp/exports/
├── demo_Spring_2024_Demo_Season_standings_20241201_143022.csv
├── demo_Spring_2024_Demo_Season_schedule_20241201_143022.csv
├── demo_Spring_2024_Demo_Season_registrations_20241201_143022.csv
├── teams_import_template.csv
├── players_import_template.csv
└── venues_import_template.csv
```

## CSV Export Formats

### Standings CSV

Contains team rankings and statistics:

- `rank`: Team ranking
- `team_name`: Team name
- `games_played`: Number of games played
- `wins`, `losses`, `ties`: Win/loss record
- `win_percentage`: Win percentage (0.000 - 1.000)
- `points_for`, `points_against`: Total points scored/allowed
- `points_differential`: Point differential (+/-)
- `points_per_game`: Average points scored
- `points_allowed_per_game`: Average points allowed
- `coach_name`, `coach_email`: Coach information

### Schedule CSV

Contains all games and results:

- `game_id`: Unique game identifier
- `date`, `time`: Game date and time
- `home_team`, `away_team`: Team names
- `venue`, `venue_address`: Venue information
- `status`: Game status (scheduled, in_progress, final, etc.)
- `home_score`, `away_score`: Final scores (if completed)
- `winner`: Winning team name
- `notes`: Game notes

### Registrations CSV

Contains player registration data:

- `registration_id`: Unique registration ID
- `name`: Full player name
- `first_name`, `last_name`: Split name fields
- `email`: Contact email
- `team_name`: Requested/assigned team
- `preferred_division`: Requested division
- `registration_date`: When registered
- `waiver_signed`: Whether waiver was signed
- `waiver_signed_date`: When waiver was signed
- `payment_status`: Payment status (paid, unpaid, waived)
- `payment_notes`: Payment notes
- `notes`: Additional notes

### Teams CSV

Contains team information:

- `team_id`: Unique team identifier
- `team_name`: Team name
- `coach_name`, `coach_email`: Coach information
- `player_count`: Number of players on team
- `created_date`: When team was created

### Players CSV

Contains player information:

- `player_id`: Unique player identifier
- `team_name`: Team assignment
- `first_name`, `last_name`: Player name
- `email`: Contact email
- `jersey_number`: Jersey number
- `birthdate`: Birth date (YYYY-MM-DD)
- `age`: Calculated age

## Example Workflow

1. **Create organization:**
   ```bash
   flask org:create --name "Demo League" --slug demo --admin-email admin@demo.com --admin-password password123
   ```

2. **Seed demo data:**
   ```bash
   flask seed:demo --org demo
   ```

3. **Find season ID:**
   ```bash
   flask export:list-seasons --org demo
   ```

4. **Export data:**
   ```bash
   flask export:season --season <season-id> --what all
   ```

5. **Access the site:**
   - Public: http://localhost:5000/demo
   - Admin: http://localhost:5000/demo/admin

## Error Handling

The CLI commands include comprehensive error handling:

- **Database errors**: Rolled back automatically
- **Validation errors**: Clear error messages
- **Missing resources**: Helpful suggestions
- **Confirmation prompts**: For destructive operations

## Development and Testing

Use the provided test script to verify all commands work:

```bash
python test_cli_commands.py
```

This script will:
1. Create a demo organization
2. Seed it with sample data
3. Export data in all formats
4. Generate CSV templates
5. Verify file creation

## Security Notes

- Admin passwords are hashed using bcrypt
- Organizations are isolated by slug
- All destructive operations require confirmation (unless `--force` is used)
- CSV exports contain only data accessible to organization admins

## Integration with Web Interface

The CLI commands complement the web interface:

- **Organization creation**: Sets up initial admin access
- **Demo seeding**: Provides immediate data for testing
- **CSV exports**: Enable data analysis and backup
- **Templates**: Support bulk imports through admin interface

The seeded demo data is immediately visible on the public site, allowing for end-to-end testing of the application.