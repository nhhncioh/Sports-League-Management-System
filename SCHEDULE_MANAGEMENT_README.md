# Schedule Management System

## Overview

The Schedule Management System is a comprehensive tool for creating, reviewing, and managing fixture schedules with advanced features including drag-and-drop reordering, blackout dates, conflict detection, approval workflows, and bulk import/export capabilities.

## Features

### 1. **Schedule Plans**
- Create multiple schedule plans before committing
- Review and compare different scheduling options
- Track plan status (plan, pending approval, approved, rejected, published)
- Store generation parameters for reproducibility

### 2. **Drag-and-Drop Reordering**
- Intuitive interface for rearranging matches
- Group by matchday for easy organization
- Visual feedback during drag operations
- Save custom ordering preferences

### 3. **Blackout Dates**
- Define periods when matches cannot be scheduled
- Apply to all leagues or specific leagues
- Support for recurring blackout periods
- Automatic conflict detection for blackout violations

### 4. **Conflict Detection**
- **Blackout Date Conflicts**: Matches scheduled during blackout periods
- **Double Booking**: Teams playing multiple matches on the same day
- **Rest Period Violations**: Less than 2 days between matches for same team
- **Venue Conflicts**: Multiple matches at same venue within 4 hours
- Severity levels: Info, Warning, Error
- Auto-resolvable vs manual resolution

### 5. **Approval Workflow**
- Submit plans for approval
- Review and approve/reject with notes
- Track approval history
- Audit trail of all actions

### 6. **Bulk Import/Export**
- **Export formats**: CSV, Excel (XLSX), JSON, PDF, iCalendar (ICS)
- **Import formats**: CSV, Excel, JSON, iCalendar
- Template downloads for easy bulk uploads
- Validation during import process

## Database Schema

### Tables Created

1. **blackout_dates**: Manage unavailable dates
2. **schedule_drafts**: Store schedule plans
3. **draft_matches**: Matches within plans (draft tables)
4. **schedule_conflicts**: Detected scheduling conflicts
5. **schedule_approval_log**: Audit trail

### Enhanced Existing Tables

- **matches**: Added `display_order`, `matchday`, `venue_id`, `is_locked` columns

## Usage Guide

### Creating a Schedule Plan

1. Navigate to **Admin Dashboard** → **Schedule Management**
2. Click **New Schedule Plan**
3. Fill in the form:
   - **Plan Name**: Give it a descriptive name
   - **League & Season**: Select target league/season
   - **Start Date**: When the season begins
   - **Interval**: Days between matches (default: 7)
   - **Options**:
     - Double Round Robin (home/away)
     - Shuffle Team Order
     - Respect Blackout Dates
4. Click **Generate Plan**

### Managing Blackout Dates

1. Click **Blackout Dates** button
2. Fill in the form:
   - **League**: Specific league or all leagues
   - **Start/End Date**: Date range
   - **Reason**: Description (e.g., "International Break", "Holidays")
3. Click **Add Blackout Period**

### Reviewing and Reordering

1. Go to **Review & Reorder** tab
2. Select a plan from the dropdown
3. Drag matches to reorder within or between matchdays
4. Click **Save Changes**

### Approval Workflow

1. **Submit for Approval**: Plan creator submits when ready
2. **Review**: Approver reviews the schedule and conflicts
3. **Approve/Reject**:
   - Approve with optional notes
   - Reject with reason for changes
4. **Publish**: Once approved, publish to create actual matches

### Handling Conflicts

1. Navigate to **Conflicts** tab
2. View all detected conflicts with severity indicators
3. For auto-resolvable conflicts, click **Auto Resolve**
4. For manual conflicts, edit the plan and reschedule matches

### Exporting Schedules

1. Go to **Import/Export** tab
2. Select a plan
3. Choose export format (CSV, Excel, JSON, PDF, iCal)
4. Click the format button to download

### Importing Schedules

1. Go to **Import/Export** tab
2. Select import format
3. Choose file
4. Select target plan (or create new)
5. Click **Import Schedule**

## API Endpoints

### Schedule Plans

- `GET /admin/schedule_management/` - List all plans
- `POST /admin/schedule_management/` - Create new plan
- `GET /admin/schedule_management/draft/<id>/matches` - Get plan matches
- `POST /admin/schedule_management/draft/<id>/reorder` - Save new order
- `POST /admin/schedule_management/draft/<id>/submit` - Submit for approval
- `POST /admin/schedule_management/draft/<id>/approve` - Approve plan
- `POST /admin/schedule_management/draft/<id>/reject` - Reject plan
- `POST /admin/schedule_management/draft/<id>/publish` - Publish to matches
- `DELETE /admin/schedule_management/draft/<id>` - Delete plan

### Blackout Dates

- `POST /admin/schedule_management/blackout` - Add blackout date
- `DELETE /admin/schedule_management/blackout/<id>` - Delete blackout date

### Import/Export

- `GET /admin/schedule_management/draft/<id>/export?format=<format>` - Export schedule
- `POST /admin/schedule_management/import` - Import schedule

## Conflict Types

### 1. Blackout Date Violation
**Severity**: Error
**Auto-resolvable**: Yes
**Description**: Match scheduled during a blackout period
**Resolution**: Automatically moves match to next available date

### 2. Double Booking
**Severity**: Error
**Auto-resolvable**: No
**Description**: Team has multiple matches on same day
**Resolution**: Manual rescheduling required

### 3. Rest Period Violation
**Severity**: Warning
**Auto-resolvable**: Yes
**Description**: Less than 2 days between matches for same team
**Resolution**: Automatically adjusts match dates to ensure minimum rest

### 4. Venue Conflict
**Severity**: Error
**Auto-resolvable**: No
**Description**: Venue booked for multiple matches within 4 hours
**Resolution**: Change venue or adjust timing manually

## Best Practices

1. **Create Multiple Plans**: Test different scheduling options
2. **Set Blackout Dates Early**: Define holidays, international breaks before generating schedules
3. **Review Conflicts**: Always check and resolve conflicts before submitting for approval
4. **Use Meaningful Names**: Name plans descriptively (e.g., "2024 Spring Season - Option A")
5. **Export Regularly**: Backup schedules by exporting to multiple formats
6. **Test Publish on Copy**: Create a copy of approved plan before publishing to production

## Workflow Example

### Typical Season Setup

1. **Planning Phase**
   - Define blackout dates (holidays, international breaks)
   - Create 2-3 plan options with different parameters

2. **Review Phase**
   - Review each plan for conflicts
   - Use drag-and-drop to optimize match order
   - Get stakeholder feedback

3. **Selection Phase**
   - Choose best plan
   - Submit for official approval

4. **Approval Phase**
   - League officials review and approve
   - Make final adjustments if needed

5. **Publication**
   - Publish approved schedule
   - Export to various formats for distribution
   - Share with teams, venues, and media

## Technical Details

### Generation Algorithm

The system uses a **round-robin algorithm** to ensure fair scheduling:

1. Each team plays every other team once (or twice for double round-robin)
2. Teams are rotated while keeping one team fixed (circle method)
3. Blackout dates are automatically skipped
4. Matches are distributed at specified intervals

### Conflict Detection

Runs automatically after:
- Plan creation
- Manual reordering
- Import operations

Checks performed:
- Database queries for overlapping schedules
- Date range validations
- Team availability checks
- Venue capacity and booking checks

### Performance Optimizations

- Indexed database tables for fast queries
- Batch operations for bulk imports
- Lazy loading for large plan lists
- Caching of conflict detection results

## Troubleshooting

### Plan Not Generating

**Problem**: "At least 2 teams required" error
**Solution**: Ensure league has at least 2 teams created

### Conflicts Not Resolving

**Problem**: Auto-resolve not working
**Solution**: Some conflicts require manual intervention (e.g., venue conflicts)

### Import Failing

**Problem**: File import errors
**Solution**: Download and use the provided templates, ensure correct format

### Published Matches Not Appearing

**Problem**: Plan published but no matches visible
**Solution**: Check that plan was in "approved" status before publishing

## Future Enhancements

- [ ] AI-powered scheduling optimization
- [ ] Weather integration for outdoor venues
- [ ] Broadcasting slot preferences
- [ ] Multi-league coordination
- [ ] Mobile app for approval workflow
- [ ] Real-time collaboration on plans
- [ ] Advanced analytics on schedule fairness

## Support

For issues or feature requests, please contact the development team or file an issue in the project repository.

