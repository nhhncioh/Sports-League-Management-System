"""Registration forms for teams and players."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import BooleanField, EmailField, StringField, TextAreaField, DateField, SelectField, IntegerField, TelField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange


class TeamRegistrationForm(FlaskForm):
    """Form for team-based registration."""

    # Contact Information
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

    phone = TelField(
        "Phone Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "(123) 456-7890"}
    )

    # Team Information
    team_name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Your team name"}
    )

    team_size = IntegerField(
        "Expected Team Size",
        validators=[Optional(), NumberRange(min=1, max=100)],
        render_kw={"placeholder": "Number of players"}
    )

    team_logo = FileField(
        "Team Logo",
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')],
        render_kw={"class": "form-control"}
    )

    # Division and skill
    preferred_division = StringField(
        "Preferred Division",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Division A, Recreational, etc."}
    )

    skill_level = SelectField(
        "Team Skill Level",
        choices=[
            ('', 'Select skill level'),
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('competitive', 'Competitive')
        ],
        validators=[Optional()]
    )

    # Team Colors
    primary_color = StringField(
        "Primary Color",
        validators=[Optional(), Length(max=7)],
        render_kw={
            "type": "color",
            "class": "form-control form-control-color",
            "title": "Choose your team's primary color",
            "value": "#007bff"
        }
    )

    secondary_color = StringField(
        "Secondary Color",
        validators=[Optional(), Length(max=7)],
        render_kw={
            "type": "color",
            "class": "form-control form-control-color",
            "title": "Choose your team's secondary color",
            "value": "#6c757d"
        }
    )

    accent_color = StringField(
        "Accent Color",
        validators=[Optional(), Length(max=7)],
        render_kw={
            "type": "color",
            "class": "form-control form-control-color",
            "title": "Choose your team's accent color",
            "value": "#28a745"
        }
    )

    # Emergency Contact
    emergency_contact_name = StringField(
        "Emergency Contact Name",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Full name"}
    )

    emergency_contact_phone = TelField(
        "Emergency Contact Phone",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "(123) 456-7890"}
    )

    emergency_contact_relationship = StringField(
        "Relationship",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Parent, Spouse, Friend"}
    )

    # Additional Information
    notes = TextAreaField(
        "Additional Notes",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any additional information, special requests, or questions",
            "rows": 3
        }
    )

    special_requirements = TextAreaField(
        "Special Requirements",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any special requirements or accommodations needed",
            "rows": 2
        }
    )

    # Waiver
    waiver_agreement = BooleanField(
        "I agree to the waiver",
        validators=[DataRequired()],
        render_kw={"class": "form-check-input"}
    )


class PlayerRegistrationForm(FlaskForm):
    """Form for individual player registration."""

    # Personal Information
    name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=255)],
        render_kw={"placeholder": "Your full name"}
    )

    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "your.email@example.com"}
    )

    phone = TelField(
        "Phone Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "(123) 456-7890"}
    )

    date_of_birth = DateField(
        "Date of Birth",
        validators=[Optional()],
        format='%Y-%m-%d',
        render_kw={"type": "date"}
    )

    gender = SelectField(
        "Gender",
        choices=[
            ('', 'Prefer not to say'),
            ('male', 'Male'),
            ('female', 'Female'),
            ('non-binary', 'Non-binary'),
            ('other', 'Other')
        ],
        validators=[Optional()]
    )

    player_photo = FileField(
        "Player Photo",
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')],
        render_kw={"class": "form-control"}
    )

    # Player Details
    skill_level = SelectField(
        "Skill Level",
        choices=[
            ('', 'Select skill level'),
            ('beginner', 'Beginner - Just starting out'),
            ('intermediate', 'Intermediate - Some experience'),
            ('advanced', 'Advanced - Experienced player'),
            ('competitive', 'Competitive - High skill level')
        ],
        validators=[Optional()]
    )

    jersey_size = SelectField(
        "Jersey Size",
        choices=[
            ('', 'Select size'),
            ('XS', 'Extra Small'),
            ('S', 'Small'),
            ('M', 'Medium'),
            ('L', 'Large'),
            ('XL', 'Extra Large'),
            ('XXL', '2XL'),
            ('XXXL', '3XL')
        ],
        validators=[Optional()]
    )

    jersey_number_preference = StringField(
        "Preferred Jersey Number",
        validators=[Optional(), Length(max=10)],
        render_kw={"placeholder": "e.g. 7, 23, etc. (not guaranteed)"}
    )

    # Division Preference
    preferred_division = StringField(
        "Preferred Division",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Division A, Recreational, etc."}
    )

    # Emergency Contact
    emergency_contact_name = StringField(
        "Emergency Contact Name",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"placeholder": "Full name"}
    )

    emergency_contact_phone = TelField(
        "Emergency Contact Phone",
        validators=[DataRequired(), Length(max=20)],
        render_kw={"placeholder": "(123) 456-7890"}
    )

    emergency_contact_relationship = StringField(
        "Relationship to Emergency Contact",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Parent, Spouse, Friend"}
    )

    # Medical Information
    medical_conditions = TextAreaField(
        "Medical Conditions",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Please list any medical conditions we should be aware of",
            "rows": 2
        }
    )

    allergies = TextAreaField(
        "Allergies",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Please list any allergies",
            "rows": 2
        }
    )

    # Additional Information
    notes = TextAreaField(
        "Additional Notes",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any additional information, availability constraints, or preferences",
            "rows": 3
        }
    )

    special_requirements = TextAreaField(
        "Special Requirements",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "placeholder": "Any special requirements or accommodations needed",
            "rows": 2
        }
    )

    # Waiver
    waiver_agreement = BooleanField(
        "I agree to the waiver",
        validators=[DataRequired()],
        render_kw={"class": "form-check-input"}
    )


__all__ = ["TeamRegistrationForm", "PlayerRegistrationForm"]