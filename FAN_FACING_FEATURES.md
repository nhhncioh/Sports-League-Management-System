# Fan-Facing Dynamic Pages - Implementation Guide

## Overview

This document outlines the dynamic fan-facing pages implemented for the Sports League Management System. These pages provide real-time engagement for fans, including live score tracking, standings, stat leaderboards, detailed match information, and rich media integration.

## Features Implemented

### 1. Live Ticker Component
**Location:** `slms/templates/components/live_ticker.html`

A reusable component that displays live games with real-time score updates.

**Features:**
- Auto-refreshes every 10 seconds
- Displays live games with status (Live, Halftime, Overtime)
- Shows current scores, period, and game clock
- Venue information
- Clickable to navigate to game detail page
- Animated with pulsing live indicator
- Beautiful gradient design

**Usage:**
```jinja2
{% include 'components/live_ticker.html' %}
```

**API Endpoint:** `GET /api/games/live`

---

### 2. Standings Page
**Route:** `/standings`
**Template:** `slms/templates/public_standings.html`
**Handler:** `slms/blueprints/public/routes.py::standings()`

Dynamic standings table with filtering capabilities.

**Features:**
- Filter by season
- Filter by division
- Sortable columns
- Team logos/placeholders
- Color-coded statistics (wins in green, losses in red)
- Goal difference with +/- indicators
- Clickable rows navigate to team profile
- Responsive design
- Legend explaining abbreviations

**Query Parameters:**
- `season_id` - Filter by specific season
- `division` - Filter by division

**Columns Displayed:**
- Position (Pos)
- Team name with logo
- Games Played (GP)
- Wins (W)
- Losses (L)
- Ties (T)
- Points (Pts)
- Goals For (GF)
- Goals Against (GA)
- Goal Difference (GD)

---

### 3. Statistical Leaderboards
**Route:** `/leaderboards`
**Template:** `slms/templates/public_leaderboards.html`
**Handler:** `slms/blueprints/public/routes.py::leaderboards()`

Showcase top performers across multiple statistical categories.

**Features:**
- Multiple stat categories (Points, Goals, Assists, Rebounds, Steals, Blocks)
- Tab-based category selection
- Medal icons for top 3 positions
- Filter by season
- Displays games played (GP)
- Card-based layout for easy scanning
- Gradient highlighting
- Clickable cards navigate to player profile

**Query Parameters:**
- `season_id` - Filter by specific season
- `stat_type` - Category to display (points, goals, assists, rebounds, steals, blocks)

**API Endpoint:** `GET /api/stats/leaders?season_id=&stat_type=&limit=`

---

### 4. Game Detail Page with Timeline
**Route:** `/games/<game_id>`
**Template:** `slms/templates/public_game_detail.html`
**Handler:** `slms/blueprints/public/routes.py::game_detail_public()`

Comprehensive game detail view with live updates and event timeline.

**Features:**
- Live status indicator for in-progress games
- Large scoreboard with team logos
- Period-by-period score breakdown
- Live game clock and period indicator
- Event timeline with chronological play-by-play
- Commentary section
- Game information sidebar (venue, date/time, season)
- Overtime indicator
- Auto-refresh for live games (every 10 seconds)
- Beautiful gradient header
- Responsive design

**Timeline Features:**
- Event type badges
- Game clock timestamps
- Event descriptions
- Visual timeline with markers
- Scrollable for long games

**API Endpoint:** `GET /api/games/<game_id>`

---

### 5. Enhanced Team Profile with Media
**Route:** `/teams/<team_id>`
**Template:** `slms/templates/team_profile.html`

Team profile page enhanced with dynamic media gallery.

**Enhancements:**
- Team media gallery (photos/videos)
- Loads team-specific media from API
- Grid layout for media items
- Click to view full size
- "View All" button if more than 6 items
- Loading spinner during fetch
- Graceful error handling
- Existing features: roster, recent games, team stats

**Media Category:** `team_<team_id>`

**JavaScript Functions:**
- `loadTeamMedia()` - Fetches and displays media
- `viewMedia(url, type)` - Opens media in new tab

---

### 6. Enhanced Player Profile with Highlights
**Route:** `/players/<player_id>`
**Template:** `slms/templates/player_profile.html`

Player profile page enhanced with highlight reel gallery.

**Enhancements:**
- Player highlights gallery
- Video thumbnails with play icon overlay
- Photo galleries
- 16:9 aspect ratio for video previews
- Click to view full highlight
- "View All" button for extensive galleries
- Loading spinner during fetch
- Graceful error handling
- Existing features: player info, season stats, team card

**Media Category:** `player_<player_id>`

**JavaScript Functions:**
- `loadPlayerHighlights()` - Fetches and displays highlights
- `viewMedia(url, type)` - Opens highlight in new tab

---

## API Endpoints Reference

### Live Games
```
GET /api/games/live
```
Returns all currently in-progress games with scores and status.

**Response:**
```json
{
  "items": [
    {
      "id": "game-uuid",
      "home_team": {"id": "team-uuid", "name": "Team A"},
      "away_team": {"id": "team-uuid", "name": "Team B"},
      "home_score": 75,
      "away_score": 68,
      "status": "in_progress",
      "current_period": 3,
      "game_clock": "5:23",
      "last_update": "2025-10-03T19:30:00Z",
      "venue": "Main Arena"
    }
  ]
}
```

### Game Detail
```
GET /api/games/<game_id>
```
Returns comprehensive game information including events timeline.

**Response:**
```json
{
  "game": {
    "id": "game-uuid",
    "season_id": "season-uuid",
    "home_team": {"id": "team-uuid", "name": "Team A"},
    "away_team": {"id": "team-uuid", "name": "Team B"},
    "venue": {"id": "venue-uuid", "name": "Main Arena", "address": "123 Street"},
    "start_time": "2025-10-03T19:00:00Z",
    "status": "in_progress",
    "home_score": 75,
    "away_score": 68,
    "current_period": 3,
    "game_clock": "5:23",
    "period_scores": [
      {"period": 1, "home": 20, "away": 18},
      {"period": 2, "home": 25, "away": 22}
    ],
    "went_to_overtime": false
  },
  "events": [
    {
      "id": "event-uuid",
      "event_type": "goal",
      "period": 1,
      "game_clock": "8:45",
      "event_time": "2025-10-03T19:15:00Z",
      "description": "John Doe scores from 25 feet",
      "player_id": "player-uuid"
    }
  ]
}
```

### Standings
```
GET /api/standings?season_id=&division=
```
Returns standings with optional filters.

**Response:**
```json
{
  "items": [
    {
      "position": 1,
      "team": {"id": "team-uuid", "name": "Team A"},
      "games_played": 20,
      "wins": 15,
      "losses": 5,
      "ties": 0,
      "points": 45,
      "goals_for": 85,
      "goals_against": 60,
      "goal_difference": 25
    }
  ]
}
```

### Stat Leaders
```
GET /api/stats/leaders?season_id=&stat_type=&limit=
```
Returns top performers for a specific stat category.

**Response:**
```json
{
  "items": [
    {
      "player": {
        "id": "player-uuid",
        "name": "John Doe",
        "team_id": "team-uuid"
      },
      "value": 450,
      "games_played": 20
    }
  ],
  "stat_type": "points"
}
```

### Media Assets
```
GET /api/media-assets?category=&media_type=
```
Returns media assets filtered by category and type.

**Response:**
```json
{
  "items": [
    {
      "id": "media-uuid",
      "media_id": "media-uuid",
      "title": "Game Highlight",
      "description": "Amazing dunk",
      "url": "https://example.com/media.mp4",
      "media_type": "video",
      "category": "player_uuid",
      "created_at": "2025-10-03T12:00:00Z"
    }
  ]
}
```

---

## Integration Points

### Adding Live Ticker to Any Page
Simply include the component in your template:
```jinja2
{% include 'components/live_ticker.html' %}
```

The component will:
1. Automatically initialize on page load
2. Fetch live games from API
3. Refresh every 10 seconds
4. Hide itself if no live games

### Navigation Links
Add these routes to your navigation menu:
- `/standings` - League Standings
- `/leaderboards` - Stat Leaders
- `/games/<game_id>` - Game Details
- `/teams/<team_id>` - Team Profiles
- `/players/<player_id>` - Player Profiles

---

## Styling & Design

### Color Scheme
- Primary gradient: `#667eea` to `#764ba2`
- Success (wins): `#28a745`
- Danger (losses): `#dc3545`
- Muted text: `#6c757d`
- Background: `#f8f9fa`

### Key CSS Classes
- `.live-ticker` - Main ticker container
- `.ticker-game` - Individual game card in ticker
- `.standings-table` - Standings table styling
- `.leader-card` - Leaderboard player card
- `.timeline` - Game event timeline
- `.media-gallery` - Grid layout for media items
- `.media-item` - Individual media thumbnail

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 992px
- Desktop: > 992px

All pages are fully responsive with mobile-first design.

---

## Performance Considerations

### Auto-Refresh Intervals
- Live ticker: 10 seconds
- Game detail (live games): 10 seconds
- Use `clearInterval` on page unload to prevent memory leaks

### Media Loading
- Media galleries load asynchronously
- Show loading spinner during fetch
- Limit displayed items to 6 by default
- Provide "View All" link for full galleries

### API Caching
Consider implementing caching for:
- Standings (cache for 5 minutes)
- Stat leaders (cache for 10 minutes)
- Media assets (cache for 30 minutes)
- Live games (no caching - real-time)

---

## Future Enhancements

### Potential Additions
1. **WebSocket Integration** - Real-time updates without polling
2. **Favorite Teams** - User can star teams for quick access
3. **Push Notifications** - Notify fans of score changes
4. **Social Sharing** - Share highlights to social media
5. **Game Predictions** - AI-powered game predictions
6. **Player Comparisons** - Side-by-side stat comparisons
7. **Heat Maps** - Shot charts and player positioning
8. **Video Streaming** - Live game streaming integration
9. **Comments/Discussion** - Fan discussion threads
10. **Fantasy Integration** - Fantasy sports integration

### Accessibility Improvements
- Add ARIA labels for screen readers
- Keyboard navigation for all interactive elements
- High contrast mode support
- Font size adjustment controls

### Analytics Integration
- Track page views for games/players
- Popular teams analytics
- User engagement metrics
- Click-through rates on media

---

## Testing Checklist

### Functional Testing
- [ ] Live ticker appears when games are in progress
- [ ] Standings filters work correctly
- [ ] Leaderboard tabs switch categories
- [ ] Game detail timeline loads events
- [ ] Media galleries load and display correctly
- [ ] All links navigate to correct pages
- [ ] Auto-refresh works for live content

### UI/UX Testing
- [ ] Responsive on mobile devices
- [ ] Smooth animations and transitions
- [ ] Loading states display correctly
- [ ] Error messages are user-friendly
- [ ] Empty states are informative
- [ ] All icons render properly

### Performance Testing
- [ ] Page load times < 3 seconds
- [ ] API responses < 500ms
- [ ] No memory leaks from intervals
- [ ] Media loads progressively
- [ ] No layout shift during load

### Cross-Browser Testing
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Edge
- [ ] Mobile browsers

---

## Troubleshooting

### Live Ticker Not Appearing
1. Check if API endpoint `/api/games/live` is accessible
2. Verify games have status `in_progress`, `halftime`, or `overtime`
3. Check browser console for JavaScript errors
4. Ensure Bootstrap and Phosphor Icons are loaded

### Media Not Loading
1. Verify `/api/media-assets` endpoint is accessible
2. Check media category format: `team_<team_id>` or `player_<player_id>`
3. Ensure CORS headers allow API access
4. Check browser console for fetch errors

### Standings/Leaderboards Empty
1. Verify database has standings/stats data
2. Check season_id parameter is valid
3. Ensure database models match API serialization
4. Test API endpoints directly in browser/Postman

### Auto-Refresh Not Working
1. Check JavaScript console for errors
2. Verify `setInterval` is being called
3. Ensure intervals are cleared on page unload
4. Test API endpoint returns current data

---

## Support & Maintenance

For issues or questions:
1. Check this documentation first
2. Review API endpoint responses
3. Check browser console for errors
4. Review server logs for API errors
5. Test with sample data

---

**Document Version:** 1.0
**Last Updated:** October 3, 2025
**Author:** Sports League Management System Team
