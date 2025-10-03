# Live Scoring System - Quick Guide

## 🎯 Overview
Comprehensive live score reporting system with real-time updates, penalty tracking, player statistics, and full audit trail.

## 🚀 Quick Access

### For Admins
1. **Admin Dashboard** → "Score Reporting" card
2. **Manage Scores Page** → Click "Live Console" button on any game
3. Direct URL: `/live-scoring/console/<game_id>`

### For Scorekeepers
- Access from manage_scores page via "Live Console" button
- Opens in new tab for dedicated scoring interface

## 📋 Features

### Live Game Console
- **Real-time Scoreboard**: Large, clear score display
- **Game Controls**: Start, Halftime, Resume, Overtime, End, Reconcile
- **Auto-refresh**: Updates every 10 seconds
- **Status Tracking**: SCHEDULED → IN_PROGRESS → HALFTIME → OVERTIME → FINAL → RECONCILED

### Score Management
- ✅ Update scores with full audit trail
- ✅ Track regulation vs overtime scores
- ✅ Period-by-period scoring
- ✅ Score validation against player stats
- ✅ Complete score history for reconciliation

### Events & Penalties
- ✅ Game events (goals, timeouts, substitutions)
- ✅ Penalty tracking (fouls, cards, ejections)
- ✅ Player-specific events
- ✅ Timestamped event log

### Player Statistics
- ✅ Points, rebounds, assists (basketball)
- ✅ Goals, saves, cards (soccer)
- ✅ Goals, assists, penalty minutes (hockey)
- ✅ Real-time stat updates
- ✅ Team-by-team breakdown

### Reconciliation
- ✅ Final score confirmation
- ✅ Score validation (checks vs player stats)
- ✅ Audit trail review
- ✅ Admin-only reconciliation

### Notifications
- ✅ Updates ticker/scoreboard cache
- ✅ Invalidates standings on score changes
- ✅ Webhook support for external systems
- ✅ Event-based notifications (game_start, game_end, overtime)

## 🔌 API Endpoints

### Game Control
```
POST /live-scoring/api/games/<id>/start        # Start game
POST /live-scoring/api/games/<id>/score        # Update score
POST /live-scoring/api/games/<id>/halftime     # Set halftime
POST /live-scoring/api/games/<id>/resume       # Resume from halftime
POST /live-scoring/api/games/<id>/overtime     # Start overtime
POST /live-scoring/api/games/<id>/end          # End game
```

### Events & Stats
```
POST /live-scoring/api/games/<id>/events       # Add event
GET  /live-scoring/api/games/<id>/events       # List events
POST /live-scoring/api/games/<id>/penalties    # Add penalty
GET  /live-scoring/api/games/<id>/penalties    # List penalties
POST /live-scoring/api/games/<id>/stats        # Update stat
GET  /live-scoring/api/games/<id>/stats        # List stats
```

### Reconciliation
```
POST /live-scoring/api/games/<id>/reconcile    # Reconcile game
GET  /live-scoring/api/games/<id>/validate     # Validate score
GET  /live-scoring/api/games/<id>/score-history # Score audit trail
```

### Live Data (for tickers/scoreboards)
```
GET  /live-scoring/api/games/<id>/live         # Real-time game data
```

## 📊 Database Schema

### Enhanced Game Model
- `went_to_overtime`, `overtime_periods`
- `home_score_regulation`, `away_score_regulation`
- `period_scores` (JSON)
- `is_reconciled`, `reconciled_at`, `reconciled_by_user_id`
- `current_period`, `game_clock`, `last_score_update`

### New Tables
- **game_event**: All game events with timestamps
- **player_game_stat**: Individual player statistics
- **penalty**: Fouls/penalties with severity tracking
- **score_update**: Complete audit trail of score changes

## 🎮 Usage Workflow

### 1. Start Game
```
Admin → Manage Scores → Live Console → Start Game
```

### 2. Live Updates
```
- Update scores in real-time
- Add events (goals, timeouts)
- Record penalties/fouls
- Track player stats
```

### 3. Game Transitions
```
- Set halftime when first half ends
- Resume for second half
- Start overtime if tied
- End game when complete
```

### 4. Reconciliation
```
- Validate score
- Review history
- Confirm final score
- System notifies all surfaces
```

## 🔔 Notification Flow

1. **Score Update** → Ticker cache updated → Standings invalidated → Webhooks sent
2. **Game Start** → Live game notification → Ticker shows "LIVE"
3. **Game End** → Final score notification → Standings recalculated
4. **Overtime** → Special notification → Ticker shows "OT"
5. **Reconciliation** → Confirmation notification → Score locked

## 🔒 Security & Permissions

- **Scorekeeper+**: Can update scores, add events/penalties/stats
- **Admin+**: Can reconcile games, view full history
- **Owner**: Full access to all features
- All actions logged to audit trail

## 🚦 Game Status Flow

```
SCHEDULED
    ↓ (Start Game)
IN_PROGRESS
    ↓ (Set Halftime)
HALFTIME
    ↓ (Resume)
IN_PROGRESS
    ↓ (Tie? Start Overtime)
OVERTIME
    ↓ (End Game)
FINAL
    ↓ (Reconcile - Admin only)
RECONCILED ✅
```

## 📱 Integration Points

### Ticker/Scoreboard
- Auto-updates from live console
- Shows current period, clock, scores
- Live indicator for in-progress games

### Standings
- Auto-recalculates on game completion
- Cache invalidated on score changes
- Respects overtime rules

### APIs
- RESTful endpoints for external systems
- Webhook notifications
- Real-time data access

## 🛠️ Technical Stack

- **Backend**: Flask + SQLAlchemy
- **Frontend**: Bootstrap 5 + Vanilla JS
- **Real-time**: Auto-refresh (10s interval)
- **Storage**: PostgreSQL with JSONB
- **Audit**: Complete change tracking

## 📝 Notes

- Migration required: `scoring_system_enhancement.py`
- All stat types configurable per sport
- Timezone-aware timestamps
- Support for multiple overtime periods
- Flexible event system via JSON details
