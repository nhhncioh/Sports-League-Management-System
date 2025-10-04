from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from slms.extensions import db, bcrypt

JSONType = JSON().with_variant(JSONB, 'postgresql')


class TimestampedBase(db.Model):
    """Abstract base providing id/created/updated columns."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    COACH = "coach"
    SCOREKEEPER = "scorekeeper"
    PLAYER = "player"
    VIEWER = "viewer"


class SportType(Enum):
    BASKETBALL = "basketball"
    SOCCER = "soccer"
    HOCKEY = "hockey"
    VOLLEYBALL = "volleyball"
    OTHER = "other"


class GameStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    OVERTIME = "overtime"
    FINAL = "final"
    FORFEIT = "forfeit"
    CANCELED = "canceled"


class PeriodType(Enum):
    REGULATION = "regulation"
    OVERTIME = "overtime"
    SHOOTOUT = "shootout"


class StatType(Enum):
    # Basketball
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    STEALS = "steals"
    BLOCKS = "blocks"
    FOULS = "fouls"
    # Soccer
    GOALS = "goals"
    ASSISTS_SOCCER = "assists_soccer"
    SHOTS = "shots"
    SAVES = "saves"
    YELLOW_CARDS = "yellow_cards"
    RED_CARDS = "red_cards"
    # Hockey
    GOALS_HOCKEY = "goals_hockey"
    ASSISTS_HOCKEY = "assists_hockey"
    PENALTY_MINUTES = "penalty_minutes"
    # Volleyball
    KILLS = "kills"
    ACES = "aces"
    DIGS = "digs"
    # Generic
    MINUTES_PLAYED = "minutes_played"


class LeagueStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class SeasonStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    OFF_SEASON = "off_season"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PaymentStatus(Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    WAIVED = "waived"


class EmailStatus(Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class EmailType(Enum):
    REGISTRATION_CONFIRMATION = "registration_confirmation"
    GAME_REMINDER = "game_reminder"
    GAME_RECAP = "game_recap"
    CUSTOM = "custom"


class RegistrationMode(Enum):
    TEAM_BASED = "team_based"
    PLAYER_BASED = "player_based"


class RegistrationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"


class BlackoutScope(Enum):
    VENUE = "venue"
    TEAM = "team"


class EmailStatus(Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class Organization(TimestampedBase):
    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Contact & Description
    description: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(512))

    # Branding
    primary_color: Mapped[str | None] = mapped_column(String(32))
    secondary_color: Mapped[str | None] = mapped_column(String(32))
    logo_url: Mapped[str | None] = mapped_column(String(512))
    favicon_url: Mapped[str | None] = mapped_column(String(512))
    banner_image_url: Mapped[str | None] = mapped_column(String(512))
    custom_css: Mapped[str | None] = mapped_column(Text)
    hero_config: Mapped[dict | None] = mapped_column(JSONType)
    modules_config: Mapped[dict | None] = mapped_column(JSONType)

    # Settings
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default='UTC')
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default='en_US')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Custom domain (future feature)
    custom_domain: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)

    # Storage quota (in bytes, None = unlimited)
    storage_quota: Mapped[int | None] = mapped_column(Integer)
    storage_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Plan/Subscription
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False, default='free')
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    leagues: Mapped[list["League"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    venues: Mapped[list["Venue"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class User(TimestampedBase):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_user_org_email"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.VIEWER,
    )
    active: Mapped[bool] = mapped_column('is_active', Boolean, nullable=False, default=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mfa_recovery_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of hashed codes
    password_reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length

    organization: Mapped[Organization] = relationship(back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except ValueError:
            return False

    def has_role(self, *roles: UserRole | str) -> bool:
        role_value = self.role.value if isinstance(self.role, UserRole) else str(self.role)
        allowed = {r.value if isinstance(r, UserRole) else str(r) for r in roles}
        return role_value in allowed

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:  # Flask-Login compatibility
        return bool(self.active)

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return self.id

    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until:
            from datetime import datetime, timezone
            if datetime.now(timezone.utc) < self.locked_until:
                return True
            # Unlock if lock period expired
            self.locked_until = None
            self.failed_login_attempts = 0
        return False

    def record_failed_login(self) -> None:
        """Record a failed login attempt and lock account if threshold exceeded."""
        from datetime import datetime, timezone, timedelta
        self.failed_login_attempts += 1
        # Lock account for 15 minutes after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def reset_failed_login_attempts(self) -> None:
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def generate_mfa_secret(self) -> str:
        """Generate a new MFA secret."""
        import pyotp
        secret = pyotp.random_base32()
        self.mfa_secret = secret
        return secret

    def get_mfa_uri(self, org_name: str | None = None) -> str:
        """Get TOTP URI for QR code generation."""
        import pyotp
        if not self.mfa_secret:
            self.generate_mfa_secret()
        name = f"{org_name or 'SLMS'}:{self.email}"
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(name=name, issuer_name=org_name or "SLMS")

    def verify_mfa_token(self, token: str) -> bool:
        """Verify a TOTP token."""
        import pyotp
        if not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)

    def generate_recovery_codes(self, count: int = 8) -> list[str]:
        """Generate recovery codes for MFA backup."""
        import secrets
        import json
        from slms.extensions import bcrypt
        codes = [f"{secrets.randbelow(10000000):08d}" for _ in range(count)]
        # Store hashed versions
        hashed_codes = [bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') for code in codes]
        self.mfa_recovery_codes = json.dumps(hashed_codes)
        return codes  # Return plain codes to show user once

    def verify_recovery_code(self, code: str) -> bool:
        """Verify and consume a recovery code."""
        import json
        from slms.extensions import bcrypt
        if not self.mfa_recovery_codes:
            return False
        try:
            hashed_codes = json.loads(self.mfa_recovery_codes)
            for i, hashed_code in enumerate(hashed_codes):
                if bcrypt.checkpw(code.encode('utf-8'), hashed_code.encode('utf-8')):
                    # Remove used code
                    hashed_codes.pop(i)
                    self.mfa_recovery_codes = json.dumps(hashed_codes) if hashed_codes else None
                    return True
            return False
        except (json.JSONDecodeError, ValueError):
            return False


class League(TimestampedBase):
    __tablename__ = "league"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[SportType] = mapped_column(
        SqlEnum(SportType, name="sport_type", native_enum=False),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LeagueStatus] = mapped_column(
        SqlEnum(LeagueStatus, name="league_status", native_enum=False),
        nullable=False,
        default=LeagueStatus.DRAFT,
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default='UTC')
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # League settings
    settings: Mapped[dict | None] = mapped_column(JSONType, default=dict)

    organization: Mapped[Organization] = relationship(back_populates="leagues")
    seasons: Mapped[list["Season"]] = relationship(
        back_populates="league",
        cascade="all, delete-orphan",
    )


class Season(TimestampedBase):
    __tablename__ = "season"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    league_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("league.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_game_length_minutes: Mapped[int | None] = mapped_column(Integer)

    # Lifecycle status
    status: Mapped[SeasonStatus] = mapped_column(
        SqlEnum(SeasonStatus, name="season_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SeasonStatus.DRAFT,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Registration fields
    registration_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registration_mode: Mapped[RegistrationMode | None] = mapped_column(
        SqlEnum(RegistrationMode, name="registration_mode", native_enum=False),
        nullable=True,
    )
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fee_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CAD")

    # Season-specific rules and settings (JSON)
    rules: Mapped[dict | None] = mapped_column(JSONType, default=dict)
    # Example rules structure:
    # {
    #   "overtime_enabled": true,
    #   "overtime_length_minutes": 5,
    #   "ties_allowed": false,
    #   "max_players_per_team": 15,
    #   "min_players_per_team": 8,
    #   "point_system": {"win": 3, "tie": 1, "loss": 0},
    #   "playoff_format": "single_elimination",
    #   "playoff_teams": 4,
    #   "custom_rules": "text description of league-specific rules"
    # }

    # Timezone override (defaults to league timezone)
    timezone: Mapped[str | None] = mapped_column(String(64))

    # Off-season configuration
    off_season_start: Mapped[date | None] = mapped_column(Date)
    off_season_end: Mapped[date | None] = mapped_column(Date)
    off_season_message: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship()
    league: Mapped[League] = relationship(back_populates="seasons")
    teams: Mapped[list["Team"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )
    games: Mapped[list["Game"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )


class Team(TimestampedBase):
    __tablename__ = "team"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    coach_name: Mapped[str | None] = mapped_column(String(255))
    coach_email: Mapped[str | None] = mapped_column(String(255))

    # Color scheme fields (temporarily commented out until migration is run)
    # primary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
    # secondary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
    # accent_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code

    season: Mapped[Season] = relationship(back_populates="teams")
    players: Mapped[list["Player"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    home_games: Mapped[list["Game"]] = relationship(
        back_populates="home_team",
        foreign_keys="Game.home_team_id",
    )
    away_games: Mapped[list["Game"]] = relationship(
        back_populates="away_team",
        foreign_keys="Game.away_team_id",
    )


class Player(TimestampedBase):
    __tablename__ = "player"
    __table_args__ = (
        Index("ix_player_org_team", "org_id", "team_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    jersey_number: Mapped[int | None] = mapped_column(Integer)
    birthdate: Mapped[date | None] = mapped_column(Date)

    team: Mapped[Team | None] = relationship(back_populates="players")


class Venue(TimestampedBase):
    __tablename__ = "venue"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str | None] = mapped_column(String(64))
    court_label: Mapped[str | None] = mapped_column(String(64))

    # Operating hours (stored as time strings, e.g. "09:00", "22:00")
    open_time: Mapped[str | None] = mapped_column(String(5))  # "HH:MM"
    close_time: Mapped[str | None] = mapped_column(String(5))  # "HH:MM"

    organization: Mapped[Organization] = relationship(back_populates="venues")
    games: Mapped[list["Game"]] = relationship(back_populates="venue")
    blackouts: Mapped[list["Blackout"]] = relationship(
        back_populates="venue",
        cascade="all, delete-orphan",
    )


class Game(TimestampedBase):
    __tablename__ = "game"
    __table_args__ = (
        Index("ix_game_org_season", "org_id", "season_id"),
        Index("ix_game_org_start_time", "org_id", "start_time"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    home_team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    away_team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    venue_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("venue.id", ondelete="SET NULL"),
        index=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[GameStatus] = mapped_column(
        SqlEnum(GameStatus, name="game_status", native_enum=False),
        nullable=False,
        default=GameStatus.SCHEDULED,
    )
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    # Overtime and period tracking
    went_to_overtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overtime_periods: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    home_score_regulation: Mapped[int | None] = mapped_column(Integer)
    away_score_regulation: Mapped[int | None] = mapped_column(Integer)

    # Period-by-period scores (JSON array)
    # Format: [{"period": 1, "home": 10, "away": 8}, {"period": 2, "home": 15, "away": 12}, ...]
    period_scores: Mapped[dict | None] = mapped_column(JSONType, default=dict)

    # Game reconciliation
    is_reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciled_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
    )

    # Live game tracking
    current_period: Mapped[int | None] = mapped_column(Integer)
    game_clock: Mapped[str | None] = mapped_column(String(10))  # e.g., "12:34"
    last_score_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    season: Mapped[Season] = relationship(back_populates="games")
    home_team: Mapped[Team | None] = relationship(
        back_populates="home_games",
        foreign_keys=[home_team_id],
    )
    away_team: Mapped[Team | None] = relationship(
        back_populates="away_games",
        foreign_keys=[away_team_id],
    )
    venue: Mapped[Venue | None] = relationship(back_populates="games")
    reconciled_by: Mapped["User | None"] = relationship(foreign_keys=[reconciled_by_user_id])

    game_events: Mapped[list["GameEvent"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )
    player_stats: Mapped[list["PlayerGameStat"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )
    penalties: Mapped[list["Penalty"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )






class Blackout(TimestampedBase):
    __tablename__ = "blackout"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[BlackoutScope] = mapped_column(
        SqlEnum(BlackoutScope, name="blackout_scope", native_enum=False),
        nullable=False,
    )
    venue_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("venue.id", ondelete="SET NULL"),
        index=True,
    )
    team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))

    venue: Mapped[Venue | None] = relationship(back_populates="blackouts")
    team: Mapped[Team | None] = relationship()


class AuditLog(TimestampedBase):
    __tablename__ = "audit_log"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    meta: Mapped[dict | None] = mapped_column(JSONType, default=dict)

    user: Mapped[User | None] = relationship(back_populates="audit_logs")


class Waiver(TimestampedBase):
    __tablename__ = "waiver"

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization: Mapped[Organization] = relationship()
    registrations: Mapped[list["Registration"]] = relationship(back_populates="waiver")


class Registration(TimestampedBase):
    __tablename__ = "registration"
    __table_args__ = (
        Index("ix_registration_status", "status"),
        Index("ix_registration_org_status", "org_id", "status"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    waiver_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("waiver.id", ondelete="SET NULL"),
        index=True,
    )
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
    )

    # Basic registration details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))

    # Team-based registration fields
    team_name: Mapped[str | None] = mapped_column(String(255))
    team_size: Mapped[int | None] = mapped_column(Integer)
    team_logo_url: Mapped[str | None] = mapped_column(String(512))

    # Player-specific fields
    player_photo_url: Mapped[str | None] = mapped_column(String(512))
    skill_level: Mapped[str | None] = mapped_column(String(50))
    jersey_size: Mapped[str | None] = mapped_column(String(10))
    jersey_number_preference: Mapped[str | None] = mapped_column(String(10))

    # Preferences and notes
    preferred_division: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    # Emergency contact
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20))
    emergency_contact_relationship: Mapped[str | None] = mapped_column(String(100))

    # Medical information
    medical_conditions: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    special_requirements: Mapped[str | None] = mapped_column(Text)

    # Team color preferences
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    accent_color: Mapped[str | None] = mapped_column(String(7))

    # Status and approval
    status: Mapped[RegistrationStatus] = mapped_column(
        SqlEnum(RegistrationStatus, name="registration_status", native_enum=False),
        nullable=False,
        default=RegistrationStatus.PENDING,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    admin_notes: Mapped[str | None] = mapped_column(Text)

    # Waiver
    waiver_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waiver_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Payment
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.UNPAID,
    )
    payment_method: Mapped[str | None] = mapped_column(String(50))
    payment_transaction_id: Mapped[str | None] = mapped_column(String(255))
    payment_notes: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped[Organization] = relationship()
    season: Mapped[Season] = relationship(back_populates="registrations")
    waiver: Mapped[Waiver | None] = relationship(back_populates="registrations")
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_user_id])

    @property
    def contact_email(self):
        """Convenience property for email access."""
        return self.email

    @property
    def age(self):
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class MediaAsset(TimestampedBase):
    __tablename__ = "media_asset"
    __table_args__ = (
        Index("ix_media_asset_org_created", "org_id", "created_at"),
        Index("ix_media_asset_org_type", "org_id", "media_type"),
        Index("ix_media_asset_org_category", "org_id", "category"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, default="image")
    category: Mapped[str | None] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(String(512))
    public_url: Mapped[str | None] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    original_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(Integer)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    uploaded_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )

    organization: Mapped[Organization] = relationship()
    uploaded_by: Mapped["User | None"] = relationship()

    @property
    def url(self) -> str | None:
        return self.public_url or self.source_url




class EmailMessage(TimestampedBase):
    __tablename__ = "email_message"
    __table_args__ = (
        Index("ix_email_org_status", "org_id", "status"),
        Index("ix_email_org_created", "org_id", "created_at"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_name: Mapped[str | None] = mapped_column(String(255))
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    email_type: Mapped[EmailType] = mapped_column(
        SqlEnum(EmailType, name="email_type", native_enum=False),
        nullable=False,
        default=EmailType.CUSTOM,
    )
    status: Mapped[EmailStatus] = mapped_column(
        SqlEnum(EmailStatus, name="email_status", native_enum=False),
        nullable=False,
        default=EmailStatus.QUEUED,
    )
    context: Mapped[dict | None] = mapped_column(JSONType, default=dict)
    html_content: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Related entities (optional)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    game_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="SET NULL"),
        index=True,
    )
    registration_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("registration.id", ondelete="SET NULL"),
        index=True,
    )

    organization: Mapped[Organization] = relationship()
    user: Mapped[User | None] = relationship()
    game: Mapped[Game | None] = relationship()
    registration: Mapped[Registration | None] = relationship()


class Coach(TimestampedBase):
    """Coach model for managing team coaches."""
    __tablename__ = "coach"
    __table_args__ = (
        Index("ix_coach_org", "org_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    bio: Mapped[str | None] = mapped_column(Text)
    certification_level: Mapped[str | None] = mapped_column(String(100))
    years_experience: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    team_assignments: Mapped[list["CoachAssignment"]] = relationship(
        back_populates="coach",
        cascade="all, delete-orphan",
    )


class CoachAssignment(TimestampedBase):
    """Link table for coach-team assignments."""
    __tablename__ = "coach_assignment"
    __table_args__ = (
        UniqueConstraint("coach_id", "team_id", "season_id", name="uq_coach_team_season"),
        Index("ix_coach_assignment_team", "team_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coach_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coach.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default='head_coach')  # head_coach, assistant, trainer
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    coach: Mapped[Coach] = relationship(back_populates="team_assignments")
    team: Mapped[Team] = relationship()
    season: Mapped[Season] = relationship()


class Referee(TimestampedBase):
    """Referee model for game officials."""
    __tablename__ = "referee"
    __table_args__ = (
        Index("ix_referee_org", "org_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    certification_level: Mapped[str | None] = mapped_column(String(100))
    license_number: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    game_assignments: Mapped[list["GameOfficials"]] = relationship(
        back_populates="referee",
        cascade="all, delete-orphan",
    )


class GameOfficials(TimestampedBase):
    """Link table for referee-game assignments."""
    __tablename__ = "game_officials"
    __table_args__ = (
        UniqueConstraint("game_id", "referee_id", name="uq_game_referee"),
        Index("ix_game_officials_game", "game_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("referee.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default='referee')  # referee, umpire, scorer, timekeeper
    payment_amount: Mapped[int | None] = mapped_column(Integer)  # in cents
    payment_status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, paid, cancelled

    referee: Mapped[Referee] = relationship(back_populates="game_assignments")
    game: Mapped[Game] = relationship()


class Sponsor(TimestampedBase):
    """Sponsor model for league/team sponsors."""
    __tablename__ = "sponsor"
    __table_args__ = (
        Index("ix_sponsor_org", "org_id"),
        Index("ix_sponsor_org_tier", "org_id", "tier"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(512))
    logo_url: Mapped[str | None] = mapped_column(String(512))

    tier: Mapped[str] = mapped_column(String(50), nullable=False, default='bronze')  # platinum, gold, silver, bronze
    contract_start: Mapped[date | None] = mapped_column(Date)
    contract_end: Mapped[date | None] = mapped_column(Date)
    sponsorship_amount: Mapped[int | None] = mapped_column(Integer)  # in cents
    benefits: Mapped[str | None] = mapped_column(Text)  # Description of sponsorship benefits
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Link to team if team-specific sponsor (null = league-wide)
    team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    team: Mapped[Team | None] = relationship()


class Transaction(TimestampedBase):
    """Financial transaction tracking."""
    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_org_date", "org_id", "transaction_date"),
        Index("ix_transaction_org_category", "org_id", "category"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # registration_fee, sponsorship, venue_rental, referee_payment, equipment, misc
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in cents, positive = income, negative = expense
    payment_method: Mapped[str | None] = mapped_column(String(50))  # cash, check, credit_card, bank_transfer, etc
    reference_number: Mapped[str | None] = mapped_column(String(100))  # Check number, transaction ID, etc
    notes: Mapped[str | None] = mapped_column(Text)

    # Link to related entities
    team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    registration_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("registration.id", ondelete="SET NULL"),
        index=True,
    )
    sponsor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sponsor.id", ondelete="SET NULL"),
        index=True,
    )

    team: Mapped[Team | None] = relationship()
    registration: Mapped[Registration | None] = relationship()
    sponsor: Mapped[Sponsor | None] = relationship()


class GameEvent(TimestampedBase):
    """Track significant game events (goals, penalties, timeouts, etc.)"""
    __tablename__ = "game_event"
    __table_args__ = (
        Index("ix_game_event_game", "game_id"),
        Index("ix_game_event_game_time", "game_id", "event_time"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Event types: goal, penalty, timeout, substitution, period_start, period_end, etc.

    team_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="SET NULL"),
        index=True,
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("player.id", ondelete="SET NULL"),
        index=True,
    )

    period: Mapped[int | None] = mapped_column(Integer)
    period_type: Mapped[PeriodType | None] = mapped_column(
        SqlEnum(PeriodType, name="period_type", native_enum=False),
        nullable=True,
    )
    game_clock: Mapped[str | None] = mapped_column(String(10))  # Time on clock when event occurred
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Event details (JSON - flexible for different event types)
    details: Mapped[dict | None] = mapped_column(JSONType, default=dict)
    # Examples:
    # Goal: {"assist_player_id": "...", "shot_type": "3-pointer"}
    # Penalty: {"penalty_type": "holding", "minutes": 2}
    # Timeout: {"timeout_type": "full", "duration": 60}

    description: Mapped[str | None] = mapped_column(Text)

    game: Mapped[Game] = relationship(back_populates="game_events")
    team: Mapped[Team | None] = relationship()
    player: Mapped[Player | None] = relationship()


class PlayerGameStat(TimestampedBase):
    """Player statistics for a specific game"""
    __tablename__ = "player_game_stat"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", "stat_type", name="uq_player_game_stat"),
        Index("ix_player_game_stat_game", "game_id"),
        Index("ix_player_game_stat_player", "player_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("player.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stat_type: Mapped[StatType] = mapped_column(
        SqlEnum(StatType, name="stat_type", native_enum=False),
        nullable=False,
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    game: Mapped[Game] = relationship(back_populates="player_stats")
    player: Mapped[Player] = relationship()
    team: Mapped[Team] = relationship()


class Penalty(TimestampedBase):
    """Track penalties/fouls during games"""
    __tablename__ = "penalty"
    __table_args__ = (
        Index("ix_penalty_game", "game_id"),
        Index("ix_penalty_player", "player_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("player.id", ondelete="SET NULL"),
        index=True,
    )

    penalty_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Examples: personal_foul, technical_foul, yellow_card, red_card, minor_penalty, major_penalty

    period: Mapped[int | None] = mapped_column(Integer)
    game_clock: Mapped[str | None] = mapped_column(String(10))

    minutes: Mapped[int | None] = mapped_column(Integer)  # Penalty duration in minutes (hockey)
    severity: Mapped[str | None] = mapped_column(String(20))  # minor, major, misconduct, etc.

    description: Mapped[str | None] = mapped_column(Text)
    resulted_in_ejection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    game: Mapped[Game] = relationship(back_populates="penalties")
    team: Mapped[Team] = relationship()
    player: Mapped[Player | None] = relationship()


class ScoreUpdate(TimestampedBase):
    """Audit trail for score changes"""
    __tablename__ = "score_update"
    __table_args__ = (
        Index("ix_score_update_game", "game_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )

    previous_home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    new_home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    new_away_score: Mapped[int] = mapped_column(Integer, nullable=False)

    update_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: manual_entry, live_update, reconciliation, correction

    notes: Mapped[str | None] = mapped_column(Text)

    game: Mapped[Game] = relationship()
    user: Mapped[User | None] = relationship()


class ArticleStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    TRASHED = "trashed"


class Article(TimestampedBase):
    """News articles and blog posts with moderation workflow."""
    __tablename__ = "article"
    __table_args__ = (
        Index("ix_article_org_status", "org_id", "status"),
        Index("ix_article_org_published", "org_id", "published_at"),
        Index("ix_article_slug", "slug"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(600), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # SEO & Meta
    meta_description: Mapped[str | None] = mapped_column(String(500))
    meta_keywords: Mapped[str | None] = mapped_column(String(500))
    featured_image_url: Mapped[str | None] = mapped_column(String(512))

    # Publishing
    status: Mapped[ArticleStatus] = mapped_column(
        SqlEnum(ArticleStatus, name="article_status", native_enum=False),
        nullable=False,
        default=ArticleStatus.DRAFT,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Author & Editor
    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_edited_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )

    # Moderation
    reviewed_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)

    # Trash/Archive
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trashed_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="SET NULL"),
    )

    # Engagement
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Categories & Tags (JSON arrays)
    categories: Mapped[list | None] = mapped_column(JSONType, default=list)
    tags: Mapped[list | None] = mapped_column(JSONType, default=list)

    # Relationships
    author: Mapped[User] = relationship(foreign_keys=[author_id])
    last_edited_by: Mapped[User | None] = relationship(foreign_keys=[last_edited_by_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    trashed_by: Mapped[User | None] = relationship(foreign_keys=[trashed_by_id])

    revisions: Mapped[list["ArticleRevision"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )


class ArticleRevision(TimestampedBase):
    """Article revision history for version control."""
    __tablename__ = "article_revision"
    __table_args__ = (
        Index("ix_article_revision_article", "article_id"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("article.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)

    # Change tracking
    edited_by_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_summary: Mapped[str | None] = mapped_column(String(500))

    # Snapshot of metadata at revision time
    metadata_snapshot: Mapped[dict | None] = mapped_column(JSONType, default=dict)

    article: Mapped[Article] = relationship(back_populates="revisions")
    edited_by: Mapped[User] = relationship()


class ContentAsset(TimestampedBase):
    """Content assets (images, videos, documents) with organization."""
    __tablename__ = "content_asset"
    __table_args__ = (
        Index("ix_content_asset_org_type", "org_id", "asset_type"),
        Index("ix_content_asset_org_folder", "org_id", "folder"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(1000))

    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, video, document, audio
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes

    # Organization
    folder: Mapped[str | None] = mapped_column(String(500))  # e.g., "news/2025/march"
    description: Mapped[str | None] = mapped_column(Text)
    alt_text: Mapped[str | None] = mapped_column(String(500))

    # Media metadata (for images/videos)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[int | None] = mapped_column(Integer)  # seconds for video/audio

    # Upload tracking
    uploaded_by_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    uploaded_by: Mapped[User] = relationship()


class EditorPermission(TimestampedBase):
    """Fine-grained permissions for editors."""
    __tablename__ = "editor_permission"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_type", name="uq_user_permission"),
    )

    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    permission_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Permissions: create_article, edit_own, edit_all, publish, approve, delete, manage_assets

    granted_by_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    granted_by: Mapped[User] = relationship(foreign_keys=[granted_by_id])


__all__ = [name for name in globals() if name[0].isupper()]






