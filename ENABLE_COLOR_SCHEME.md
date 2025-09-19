# How to Enable Team Color Scheme Feature

The team color scheme feature has been implemented but is temporarily disabled to prevent database errors. Follow these steps to enable it:

## Step 1: Run the Database Migration

First, run the migration to add the color fields to your database:

```bash
# Option 1: Using Alembic directly (if available)
alembic upgrade head

# Option 2: Using Flask-Migrate (if configured)
flask db upgrade

# Option 3: Using Docker
docker-compose exec web alembic upgrade head
```

## Step 2: Enable the Feature

Once the migration is complete, uncomment the following code:

### 1. In `slms/models/models.py`:

**Team model** (around line 280):
```python
# Uncomment these lines:
primary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
secondary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
accent_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
```

**Registration model** (around line 512):
```python
# Uncomment these lines:
primary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
secondary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
accent_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
```

### 2. In `slms/forms/registration.py`:

**Around line 46**, uncomment the color field definitions:
```python
# Uncomment these form fields:
primary_color = StringField(...)
secondary_color = StringField(...)
accent_color = StringField(...)
```

### 3. In `slms/blueprints/public/registration_routes.py`:

**Around line 65**, uncomment the color data saving:
```python
# Uncomment these lines:
primary_color=form.primary_color.data or None,
secondary_color=form.secondary_color.data or None,
accent_color=form.accent_color.data or None,
```

### 4. In `slms/templates/public/registration/team_form.html`:

**Around line 117**, uncomment the HTML color picker section (remove the `<!--` and `-->` comments).

## Step 3: Test the Feature

1. Restart your application
2. Navigate to team registration
3. You should see color picker fields for Primary, Secondary, and Accent colors
4. Test registering a team with colors selected

## Feature Description

This feature adds:
- **Color pickers** in the team registration form
- **Database storage** for team color preferences
- **Optional fields** - teams can skip color selection if desired
- **Hex color validation** - ensures proper color format
- **Ready for display** - colors can be used in team profiles, uniforms, etc.

## Troubleshooting

If you encounter issues:

1. **Migration fails**: Check your database connection and ensure you have proper permissions
2. **App won't start**: Verify all code is uncommented correctly and syntax is valid
3. **Colors not saving**: Check browser developer tools for JavaScript errors

## Future Enhancements

Once enabled, you can extend this feature by:
- Displaying team colors in team listings
- Using colors in team profiles
- Adding color schemes to game schedules
- Creating uniform/jersey visualizations