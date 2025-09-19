"""Registration forms for teams and players."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class TeamRegistrationForm(FlaskForm):
    """Form for team-based registration."""

    name = StringField(
        "Contact Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Your full name"}
    )

    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "your.email@example.com"}
    )

    team_name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Your team name"}
    )

    preferred_division = StringField(
        "Preferred Division",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Division A, Recreational, etc."}
    )

    notes = TextAreaField(
        "Additional Notes",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any additional information, special requests, or questions",
            "rows": 4
        }
    )

    # Team color scheme fields (temporarily commented out until migration is run)
    # primary_color = StringField(
    #     "Primary Color",
    #     validators=[Optional(), Length(max=7)],
    #     render_kw={
    #         "type": "color",
    #         "class": "form-control form-control-color",
    #         "title": "Choose your team's primary color"
    #     }
    # )

    # secondary_color = StringField(
    #     "Secondary Color",
    #     validators=[Optional(), Length(max=7)],
    #     render_kw={
    #         "type": "color",
    #         "class": "form-control form-control-color",
    #         "title": "Choose your team's secondary color"
    #     }
    # )

    # accent_color = StringField(
    #     "Accent Color",
    #     validators=[Optional(), Length(max=7)],
    #     render_kw={
    #         "type": "color",
    #         "class": "form-control form-control-color",
    #         "title": "Choose your team's accent color"
    #     }
    # )

    waiver_agreement = BooleanField(
        "I agree to the waiver",
        validators=[DataRequired()],
        render_kw={"class": "form-check-input"}
    )


class PlayerRegistrationForm(FlaskForm):
    """Form for individual player registration."""

    name = StringField(
        "Player Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Your full name"}
    )

    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "your.email@example.com"}
    )

    preferred_division = StringField(
        "Preferred Division",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Division A, Recreational, etc."}
    )

    notes = TextAreaField(
        "Additional Notes",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any additional information, skill level, or preferences",
            "rows": 4
        }
    )

    waiver_agreement = BooleanField(
        "I agree to the waiver",
        validators=[DataRequired()],
        render_kw={"class": "form-check-input"}
    )


__all__ = ["TeamRegistrationForm", "PlayerRegistrationForm"]