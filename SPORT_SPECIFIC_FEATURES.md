# Sport-Specific Features - Implementation Guide

## ✅ What's Been Implemented

### 1. Database
- Added `sport` column to the `leagues` table
- Supports: soccer, basketball, hockey, volleyball, football, baseball, cricket, rugby, other

### 2. League Management UI
**File**: `slms/templates/manage_leagues.html`
- Added sport dropdown selector when creating/editing leagues
- Shows helpful text explaining that sport determines available statistics
- JavaScript updated to handle sport field in edit mode

### 3. Backend Route Updates
**File**: `slms/blueprints/admin/routes.py`
- `manage_leagues()` route now saves and loads sport field
- `player_stats()` route now includes sport configuration data
- Imported sport_config functions

### 4. Sport Configuration System
**File**: `slms/services/sport_config.py`

This is a comprehensive configuration system that defines for each sport:

#### Soccer/Football
- **Stats**: Goals, Assists, Shots on Target, Passes, Saves, Clean Sheets, Cards
- **Scoring**: Goals
- **Standings**: Win=3pts, Draw=1pt, Loss=0pts
- **Allows Draws**: Yes

#### Basketball
- **Stats**: Points (PTS), Assists (AST), Rebounds (REB), Steals (STL), Blocks (BLK), Turnovers, FG%, 3P%, FT%
- **Scoring**: Points
- **Standings**: Win=2pts, Loss=0pts
- **Allows Draws**: No

#### Hockey
- **Stats**: Goals, Assists, Points (G+A), Shots, Plus/Minus, Penalty Minutes, Power Play Goals, Saves, Save %
- **Scoring**: Goals
- **Standings**: Win=2pts, OT Win=2pts, OT Loss=1pt, Loss=0pts
- **Allows Draws**: No (uses overtime)

#### Volleyball
- **Stats**: Kills, Assists, Blocks, Digs, Aces, Service Errors, Attack Attempts
- **Scoring**: Sets won
- **Standings**: Win=3pts, Loss=0pts
- **Allows Draws**: No

#### American Football
- **Stats**: Passing Yards, Passing TDs, INTs, Rushing Yards, Rushing TDs, Receiving Yards, Receptions, Sacks, Tackles
- **Scoring**: Points (Touchdowns, Field Goals, etc.)
- **Standings**: Win=2pts, Loss=0pts
- **Allows Draws**: Yes (rare)

#### Baseball
- **Stats**: Batting Average, Hits, Home Runs, RBIs, Runs, Stolen Bases, Strikeouts, Walks, ERA, Wins (Pitcher)
- **Scoring**: Runs
- **Standings**: Win=1pt, Loss=0pt
- **Allows Draws**: No

#### Cricket
- **Stats**: Runs, Batting Average, Strike Rate, Wickets, Bowling Average, Economy Rate, Catches, Stumpings
- **Scoring**: Runs
- **Standings**: Win=2pts, Draw=1pt, Loss=0pts
- **Allows Draws**: Yes

#### Rugby
- **Stats**: Tries, Conversions, Penalty Goals, Drop Goals, Tackles, Carries, Meters Gained
- **Scoring**: Points
- **Standings**: Win=4pts, Draw=2pts, Loss=0pts, Bonus Try=1pt, Bonus Losing=1pt
- **Allows Draws**: Yes

### 5. Helper Functions Available

```python
from slms.services.sport_config import (
    get_sport_config,           # Get full config for a sport
    get_player_stats_for_sport, # Get player stat definitions
    get_team_stats_for_sport,   # Get team stat names
    get_game_events_for_sport,  # Get possible game events
    get_standings_points_config, # Get points system
    allows_draws,               # Check if draws are possible
    get_sport_display_name,     # Get friendly name
    get_primary_stat_name,      # Get main stat (goals/points/runs)
    get_all_sports              # List all sports
)
```

## 📋 What Still Needs to Be Done

### Phase 1: Player Stats Page (Current Page)
**File**: `slms/templates/player_stats.html`

**Current State**: Page uses soccer-specific terminology (Goals, Assists, etc.)

**What's Needed**:
1. Make table headers dynamic based on league's sport
2. Update "Add Player Stats" modal to show sport-specific fields
3. Add sport indicator badge showing which stat system is being used
4. Filter display to only show relevant stats for each sport

**Implementation Approach**:
- Add JavaScript that reads league selection and shows/hides stat columns
- Use the `sport_configs` passed from backend (already available!)
- Add data attributes to stat columns indicating which sports they apply to
- Example: `<th data-sports="soccer,hockey">Goals</th>`

### Phase 2: Scoring/Game Management
**Files**:
- `slms/templates/admin/score_game.html`
- `slms/templates/manage_scores.html`
- `slms/blueprints/admin/routes.py` (score_game route)

**What's Needed**:
1. When scoring a game, show sport-specific stat entry fields
   - Basketball: Points, Rebounds, Assists, etc.
   - Soccer: Goals, Assists, Yellow/Red Cards
   - Baseball: Hits, Runs, RBIs, etc.
2. Validate stat entries based on sport rules
3. Store stats in appropriate format

**Implementation Approach**:
- Load league's sport when loading game
- Dynamically generate stat entry form using sport_config
- Use custom_metrics JSON field for sport-specific stats

### Phase 3: Public-Facing Displays
**Files**:
- `slms/templates/portal/player_profile.html`
- `slms/templates/portal/team_profile.html`
- `slms/templates/portal/leaderboard.html`
- Any public stats pages

**What's Needed**:
1. Display correct stat names and abbreviations
2. Show relevant stats for each league's sport
3. Calculate per-game averages correctly (PPG for basketball, GPG for soccer)
4. Use sport-appropriate terminology throughout

### Phase 4: Standings Calculations
**Files**:
- `slms/blueprints/admin/routes.py` (recalculate_standings)
- Standings calculation logic

**What's Needed**:
1. Use sport-specific points system from config
2. Handle draws appropriately (some sports don't have draws)
3. Apply bonus points where applicable (Rugby bonus try, etc.)
4. Sort standings by sport-appropriate tie-breakers

**Implementation Approach**:
```python
sport_config = get_sport_config(league_sport)
points_config = sport_config['standings_points']
# Apply: Win = points_config['win'], Draw = points_config.get('draw', 0), etc.
```

### Phase 5: Database Schema Enhancement
**Current**: The `scorers` table uses soccer-centric fields (goals, assists, penalties)

**Future**: Consider adding:
1. Generic `stat_type` and `stat_value` table for flexible sport stats
2. Or expand `custom_metrics` JSON field usage
3. Create sport-specific stat tables if needed

**Recommendation**: Use the existing `custom_metrics` JSON field in `scorer_metrics` table for now. It's already there and flexible!

## 🎯 Quick Wins (Easiest to Implement First)

### 1. Add Sport Badge to Stats Page
Show which sport's stats are being displayed:

```html
<!-- In player_stats.html, near the league filter -->
<span class="badge bg-primary" id="sportIndicator"></span>

<script>
document.getElementById('filterLeague').addEventListener('change', function() {
    const leagueId = this.value;
    const league = {{ leagues|tojson }}.find(l => l.id == leagueId);
    if (league) {
        const sportName = league.sport || 'soccer';
        document.getElementById('sportIndicator').textContent =
            'Sport: ' + sportName.charAt(0).toUpperCase() + sportName.slice(1);
    }
});
</script>
```

### 2. Add Help Text in Stats Modal
Tell users what stats are expected for the league:

```html
<!-- In basicStatsModal, after league selection -->
<div class="col-12">
    <div class="alert alert-info" id="sportHelpText" style="display:none;">
        <strong>This league tracks:</strong> <span id="sportStatsList"></span>
    </div>
</div>

<script>
document.getElementById('basicLeague').addEventListener('change', function() {
    const leagueId = this.value;
    const league = {{ leagues|tojson }}.find(l => l.id == leagueId);
    const sportConfigs = {{ sport_configs|tojson }};

    if (league && sportConfigs[leagueId]) {
        const stats = sportConfigs[leagueId].player_stats
            .map(s => s.label).join(', ');
        document.getElementById('sportStatsList').textContent = stats;
        document.getElementById('sportHelpText').style.display = 'block';
    }
});
</script>
```

### 3. Update Terminology Dynamically
Change "Goals" to "Points" for basketball leagues:

```javascript
const sportConfig = {{ sport_configs|tojson }};
const primaryStatName = sportConfig[leagueId].scoring_type; // 'goals', 'points', 'runs'

// Update labels
if (primaryStatName === 'points') {
    document.querySelector('[for="basicGoals"]').textContent = 'Points';
} else if (primaryStatName === 'runs') {
    document.querySelector('[for="basicGoals"]').textContent = 'Runs';
}
```

## 🔧 Testing the Implementation

### 1. Test League Creation
1. Go to `/admin` → Manage Leagues
2. Create a new league
3. Select "Basketball" as sport
4. Save and verify sport is stored

### 2. Test Sport Data is Available
1. Go to Player Stats page
2. Open browser console
3. Type: `console.log({{ sport_configs|tojson|safe }})`
4. Verify sport configurations are present

### 3. Test Different Sports
1. Create leagues for different sports
2. Verify each has appropriate sport field
3. Check that sport_config returns correct data

## 📚 Code Examples

### Example 1: Get Basketball Stats in a Template
```jinja2
{% set basketball_config = get_sport_config('basketball') %}
{% for stat in basketball_config.player_stats %}
    <th>{{ stat.label }} ({{ stat.abbr }})</th>
{% endfor %}
```

### Example 2: Check if Draws are Allowed
```python
from slms.services.sport_config import allows_draws

league_sport = 'basketball'
if allows_draws(league_sport):
    # Show draw option in scoring
    pass
else:
    # Force winner selection
    pass
```

### Example 3: Calculate Standings Points
```python
from slms.services.sport_config import get_standings_points_config

points_config = get_standings_points_config('rugby')
# points_config = {'win': 4, 'draw': 2, 'loss': 0, 'bonus_try': 1, 'bonus_losing': 1}

team_points = 0
team_points += wins * points_config['win']
team_points += draws * points_config.get('draw', 0)
team_points += try_bonuses * points_config.get('bonus_try', 0)
```

## 🎉 Summary

**Foundation Complete**: The sport-specific system is now in place with:
- Database field for sport selection
- Comprehensive configuration system for 9 sports
- UI for league sport selection
- Backend integration with player stats route

**Next Steps**: The remaining work involves using this foundation to:
- Make UI elements dynamic based on sport
- Update stat entry forms
- Adjust calculations (standings, averages)
- Update public-facing displays

**The Hard Part is Done**: The configuration system handles all the complexity. Now it's just a matter of reading from it and applying the appropriate settings throughout the application.
