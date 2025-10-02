"""
Sport-specific configuration for stats, scoring, and game features.
This module defines what statistics and features are available for each sport.
"""

from typing import Dict, List, Any

# Sport configuration defining available stats for each sport
SPORT_CONFIGS = {
    'soccer': {
        'display_name': 'Soccer / Football',
        'player_stats': [
            {'key': 'goals', 'label': 'Goals', 'type': 'int', 'abbr': 'G', 'per_game': True},
            {'key': 'assists', 'label': 'Assists', 'type': 'int', 'abbr': 'A', 'per_game': True},
            {'key': 'shots_on_target', 'label': 'Shots on Target', 'type': 'int', 'abbr': 'SOT', 'per_game': True},
            {'key': 'shot_attempts', 'label': 'Shot Attempts', 'type': 'int', 'abbr': 'SH', 'per_game': True},
            {'key': 'passes_completed', 'label': 'Passes Completed', 'type': 'int', 'abbr': 'PC', 'per_game': True},
            {'key': 'passes_attempted', 'label': 'Passes Attempted', 'type': 'int', 'abbr': 'PA', 'per_game': True},
            {'key': 'saves', 'label': 'Saves (GK)', 'type': 'int', 'abbr': 'SV', 'per_game': True},
            {'key': 'clean_sheets', 'label': 'Clean Sheets', 'type': 'int', 'abbr': 'CS', 'per_game': False},
            {'key': 'yellow_cards', 'label': 'Yellow Cards', 'type': 'int', 'abbr': 'YC', 'per_game': False},
            {'key': 'red_cards', 'label': 'Red Cards', 'type': 'int', 'abbr': 'RC', 'per_game': False},
        ],
        'team_stats': ['goals', 'assists', 'shots_on_target', 'possession', 'fouls'],
        'game_events': ['goal', 'assist', 'yellow_card', 'red_card', 'substitution'],
        'scoring_type': 'goals',
        'standings_points': {'win': 3, 'draw': 1, 'loss': 0},
        'allows_draws': True,
    },
    'basketball': {
        'display_name': 'Basketball',
        'player_stats': [
            {'key': 'points', 'label': 'Points', 'type': 'int', 'abbr': 'PTS', 'per_game': True},
            {'key': 'assists', 'label': 'Assists', 'type': 'int', 'abbr': 'AST', 'per_game': True},
            {'key': 'rebounds', 'label': 'Rebounds', 'type': 'int', 'abbr': 'REB', 'per_game': True},
            {'key': 'steals', 'label': 'Steals', 'type': 'int', 'abbr': 'STL', 'per_game': True},
            {'key': 'blocks', 'label': 'Blocks', 'type': 'int', 'abbr': 'BLK', 'per_game': True},
            {'key': 'turnovers', 'label': 'Turnovers', 'type': 'int', 'abbr': 'TO', 'per_game': True},
            {'key': 'field_goals_made', 'label': 'Field Goals Made', 'type': 'int', 'abbr': 'FGM', 'per_game': True},
            {'key': 'field_goals_attempted', 'label': 'Field Goals Attempted', 'type': 'int', 'abbr': 'FGA', 'per_game': True},
            {'key': 'three_pointers_made', 'label': '3-Pointers Made', 'type': 'int', 'abbr': '3PM', 'per_game': True},
            {'key': 'three_pointers_attempted', 'label': '3-Pointers Attempted', 'type': 'int', 'abbr': '3PA', 'per_game': True},
            {'key': 'free_throws_made', 'label': 'Free Throws Made', 'type': 'int', 'abbr': 'FTM', 'per_game': True},
            {'key': 'free_throws_attempted', 'label': 'Free Throws Attempted', 'type': 'int', 'abbr': 'FTA', 'per_game': True},
        ],
        'team_stats': ['points', 'rebounds', 'assists', 'steals', 'blocks'],
        'game_events': ['field_goal', 'three_pointer', 'free_throw', 'rebound', 'assist', 'steal', 'block', 'turnover'],
        'scoring_type': 'points',
        'standings_points': {'win': 2, 'loss': 0},
        'allows_draws': False,
    },
    'hockey': {
        'display_name': 'Hockey (Ice/Field)',
        'player_stats': [
            {'key': 'goals', 'label': 'Goals', 'type': 'int', 'abbr': 'G', 'per_game': True},
            {'key': 'assists', 'label': 'Assists', 'type': 'int', 'abbr': 'A', 'per_game': True},
            {'key': 'points', 'label': 'Points', 'type': 'int', 'abbr': 'PTS', 'per_game': True},  # Goals + Assists
            {'key': 'shots_on_goal', 'label': 'Shots on Goal', 'type': 'int', 'abbr': 'SOG', 'per_game': True},
            {'key': 'plus_minus', 'label': 'Plus/Minus', 'type': 'int', 'abbr': '+/-', 'per_game': False},
            {'key': 'penalty_minutes', 'label': 'Penalty Minutes', 'type': 'int', 'abbr': 'PIM', 'per_game': True},
            {'key': 'power_play_goals', 'label': 'Power Play Goals', 'type': 'int', 'abbr': 'PPG', 'per_game': False},
            {'key': 'short_handed_goals', 'label': 'Short-Handed Goals', 'type': 'int', 'abbr': 'SHG', 'per_game': False},
            {'key': 'saves', 'label': 'Saves (Goalie)', 'type': 'int', 'abbr': 'SV', 'per_game': True},
            {'key': 'save_percentage', 'label': 'Save %', 'type': 'float', 'abbr': 'SV%', 'per_game': False},
        ],
        'team_stats': ['goals', 'assists', 'shots_on_goal', 'penalty_minutes'],
        'game_events': ['goal', 'assist', 'penalty', 'save'],
        'scoring_type': 'goals',
        'standings_points': {'win': 2, 'overtime_win': 2, 'overtime_loss': 1, 'loss': 0},
        'allows_draws': False,  # Uses overtime
    },
    'volleyball': {
        'display_name': 'Volleyball',
        'player_stats': [
            {'key': 'kills', 'label': 'Kills', 'type': 'int', 'abbr': 'K', 'per_game': True},
            {'key': 'assists', 'label': 'Assists', 'type': 'int', 'abbr': 'A', 'per_game': True},
            {'key': 'blocks', 'label': 'Blocks', 'type': 'int', 'abbr': 'BLK', 'per_game': True},
            {'key': 'digs', 'label': 'Digs', 'type': 'int', 'abbr': 'D', 'per_game': True},
            {'key': 'aces', 'label': 'Aces', 'type': 'int', 'abbr': 'ACE', 'per_game': True},
            {'key': 'service_errors', 'label': 'Service Errors', 'type': 'int', 'abbr': 'SE', 'per_game': True},
            {'key': 'attack_attempts', 'label': 'Attack Attempts', 'type': 'int', 'abbr': 'TA', 'per_game': True},
            {'key': 'attack_errors', 'label': 'Attack Errors', 'type': 'int', 'abbr': 'E', 'per_game': True},
        ],
        'team_stats': ['kills', 'blocks', 'aces', 'digs'],
        'game_events': ['kill', 'block', 'ace', 'dig'],
        'scoring_type': 'sets',
        'standings_points': {'win': 3, 'loss': 0},  # Can be 2 points for win depending on league
        'allows_draws': False,
    },
    'football': {
        'display_name': 'American Football / Flag Football',
        'player_stats': [
            {'key': 'passing_yards', 'label': 'Passing Yards', 'type': 'int', 'abbr': 'PYD', 'per_game': True},
            {'key': 'passing_touchdowns', 'label': 'Passing TDs', 'type': 'int', 'abbr': 'PTD', 'per_game': True},
            {'key': 'interceptions', 'label': 'Interceptions Thrown', 'type': 'int', 'abbr': 'INT', 'per_game': True},
            {'key': 'rushing_yards', 'label': 'Rushing Yards', 'type': 'int', 'abbr': 'RYD', 'per_game': True},
            {'key': 'rushing_touchdowns', 'label': 'Rushing TDs', 'type': 'int', 'abbr': 'RTD', 'per_game': True},
            {'key': 'receiving_yards', 'label': 'Receiving Yards', 'type': 'int', 'abbr': 'RCYD', 'per_game': True},
            {'key': 'receiving_touchdowns', 'label': 'Receiving TDs', 'type': 'int', 'abbr': 'RCTD', 'per_game': True},
            {'key': 'receptions', 'label': 'Receptions', 'type': 'int', 'abbr': 'REC', 'per_game': True},
            {'key': 'sacks', 'label': 'Sacks', 'type': 'float', 'abbr': 'SK', 'per_game': True},
            {'key': 'tackles', 'label': 'Tackles', 'type': 'int', 'abbr': 'TKL', 'per_game': True},
            {'key': 'interceptions_caught', 'label': 'Interceptions Caught', 'type': 'int', 'abbr': 'INT', 'per_game': True},
        ],
        'team_stats': ['passing_yards', 'rushing_yards', 'total_yards', 'touchdowns'],
        'game_events': ['touchdown', 'field_goal', 'extra_point', 'safety', 'interception', 'fumble'],
        'scoring_type': 'points',
        'standings_points': {'win': 2, 'loss': 0},
        'allows_draws': True,  # Rare but possible
    },
    'baseball': {
        'display_name': 'Baseball',
        'player_stats': [
            {'key': 'batting_average', 'label': 'Batting Average', 'type': 'float', 'abbr': 'AVG', 'per_game': False},
            {'key': 'hits', 'label': 'Hits', 'type': 'int', 'abbr': 'H', 'per_game': True},
            {'key': 'home_runs', 'label': 'Home Runs', 'type': 'int', 'abbr': 'HR', 'per_game': True},
            {'key': 'runs_batted_in', 'label': 'RBIs', 'type': 'int', 'abbr': 'RBI', 'per_game': True},
            {'key': 'runs', 'label': 'Runs', 'type': 'int', 'abbr': 'R', 'per_game': True},
            {'key': 'stolen_bases', 'label': 'Stolen Bases', 'type': 'int', 'abbr': 'SB', 'per_game': True},
            {'key': 'strikeouts_batting', 'label': 'Strikeouts', 'type': 'int', 'abbr': 'SO', 'per_game': True},
            {'key': 'walks', 'label': 'Walks', 'type': 'int', 'abbr': 'BB', 'per_game': True},
            {'key': 'earned_run_average', 'label': 'ERA', 'type': 'float', 'abbr': 'ERA', 'per_game': False},
            {'key': 'wins_pitching', 'label': 'Wins (P)', 'type': 'int', 'abbr': 'W', 'per_game': False},
            {'key': 'strikeouts_pitching', 'label': 'Strikeouts (P)', 'type': 'int', 'abbr': 'K', 'per_game': True},
        ],
        'team_stats': ['runs', 'hits', 'errors', 'home_runs'],
        'game_events': ['hit', 'home_run', 'strikeout', 'walk', 'stolen_base'],
        'scoring_type': 'runs',
        'standings_points': {'win': 1, 'loss': 0},
        'allows_draws': False,
    },
    'cricket': {
        'display_name': 'Cricket',
        'player_stats': [
            {'key': 'runs', 'label': 'Runs', 'type': 'int', 'abbr': 'R', 'per_game': True},
            {'key': 'batting_average', 'label': 'Batting Average', 'type': 'float', 'abbr': 'AVG', 'per_game': False},
            {'key': 'strike_rate', 'label': 'Strike Rate', 'type': 'float', 'abbr': 'SR', 'per_game': False},
            {'key': 'wickets', 'label': 'Wickets', 'type': 'int', 'abbr': 'W', 'per_game': True},
            {'key': 'bowling_average', 'label': 'Bowling Average', 'type': 'float', 'abbr': 'AVG', 'per_game': False},
            {'key': 'economy_rate', 'label': 'Economy Rate', 'type': 'float', 'abbr': 'ECON', 'per_game': False},
            {'key': 'catches', 'label': 'Catches', 'type': 'int', 'abbr': 'CT', 'per_game': True},
            {'key': 'stumpings', 'label': 'Stumpings', 'type': 'int', 'abbr': 'ST', 'per_game': True},
            {'key': 'fifties', 'label': '50s', 'type': 'int', 'abbr': '50', 'per_game': False},
            {'key': 'hundreds', 'label': '100s', 'type': 'int', 'abbr': '100', 'per_game': False},
        ],
        'team_stats': ['runs', 'wickets', 'overs', 'extras'],
        'game_events': ['wicket', 'boundary', 'six', 'catch'],
        'scoring_type': 'runs',
        'standings_points': {'win': 2, 'draw': 1, 'loss': 0},
        'allows_draws': True,
    },
    'rugby': {
        'display_name': 'Rugby',
        'player_stats': [
            {'key': 'tries', 'label': 'Tries', 'type': 'int', 'abbr': 'T', 'per_game': True},
            {'key': 'conversions', 'label': 'Conversions', 'type': 'int', 'abbr': 'C', 'per_game': True},
            {'key': 'penalty_goals', 'label': 'Penalty Goals', 'type': 'int', 'abbr': 'PG', 'per_game': True},
            {'key': 'drop_goals', 'label': 'Drop Goals', 'type': 'int', 'abbr': 'DG', 'per_game': True},
            {'key': 'tackles', 'label': 'Tackles', 'type': 'int', 'abbr': 'TKL', 'per_game': True},
            {'key': 'carries', 'label': 'Carries', 'type': 'int', 'abbr': 'CAR', 'per_game': True},
            {'key': 'meters_gained', 'label': 'Meters Gained', 'type': 'int', 'abbr': 'M', 'per_game': True},
            {'key': 'lineout_wins', 'label': 'Lineout Wins', 'type': 'int', 'abbr': 'LW', 'per_game': True},
            {'key': 'turnovers', 'label': 'Turnovers', 'type': 'int', 'abbr': 'TO', 'per_game': True},
        ],
        'team_stats': ['tries', 'conversions', 'penalties', 'possession'],
        'game_events': ['try', 'conversion', 'penalty_goal', 'drop_goal', 'yellow_card', 'red_card'],
        'scoring_type': 'points',
        'standings_points': {'win': 4, 'draw': 2, 'loss': 0, 'bonus_try': 1, 'bonus_losing': 1},
        'allows_draws': True,
    },
    'other': {
        'display_name': 'Other Sport',
        'player_stats': [
            {'key': 'goals', 'label': 'Goals/Points', 'type': 'int', 'abbr': 'G', 'per_game': True},
            {'key': 'assists', 'label': 'Assists', 'type': 'int', 'abbr': 'A', 'per_game': True},
            {'key': 'games_played', 'label': 'Games Played', 'type': 'int', 'abbr': 'GP', 'per_game': False},
        ],
        'team_stats': ['goals', 'assists'],
        'game_events': ['score', 'assist'],
        'scoring_type': 'points',
        'standings_points': {'win': 3, 'draw': 1, 'loss': 0},
        'allows_draws': True,
    },
}


def get_sport_config(sport: str) -> Dict[str, Any]:
    """Get the configuration for a specific sport."""
    return SPORT_CONFIGS.get(sport, SPORT_CONFIGS['other'])


def get_player_stats_for_sport(sport: str) -> List[Dict[str, Any]]:
    """Get the player stats configuration for a specific sport."""
    config = get_sport_config(sport)
    return config.get('player_stats', [])


def get_team_stats_for_sport(sport: str) -> List[str]:
    """Get the team stats for a specific sport."""
    config = get_sport_config(sport)
    return config.get('team_stats', [])


def get_game_events_for_sport(sport: str) -> List[str]:
    """Get the available game events for a specific sport."""
    config = get_sport_config(sport)
    return config.get('game_events', [])


def get_standings_points_config(sport: str) -> Dict[str, int]:
    """Get the points configuration for standings calculations."""
    config = get_sport_config(sport)
    return config.get('standings_points', {'win': 3, 'draw': 1, 'loss': 0})


def allows_draws(sport: str) -> bool:
    """Check if a sport allows draws/ties."""
    config = get_sport_config(sport)
    return config.get('allows_draws', True)


def get_sport_display_name(sport: str) -> str:
    """Get the display name for a sport."""
    config = get_sport_config(sport)
    return config.get('display_name', sport.title())


def get_primary_stat_name(sport: str) -> str:
    """Get the primary stat name for a sport (e.g., 'goals', 'points', 'runs')."""
    config = get_sport_config(sport)
    return config.get('scoring_type', 'points')


def get_all_sports() -> List[Dict[str, str]]:
    """Get a list of all available sports with their keys and display names."""
    return [
        {'key': key, 'display_name': config['display_name']}
        for key, config in SPORT_CONFIGS.items()
        if key != 'other'  # Exclude 'other' from the public list
    ]
