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
    FINAL = "final"
    FORFEIT = "forfeit"
    CANCELED = "canceled"


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
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    primary_color: Mapped[str | None] = mapped_column(String(32))
    logo_url: Mapped[str | None] = mapped_column(String(512))

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

    # Registration fields
    registration_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registration_mode: Mapped[RegistrationMode | None] = mapped_column(
        SqlEnum(RegistrationMode, name="registration_mode", native_enum=False),
        nullable=True,
    )
    fee_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CAD")

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

    # Registration details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    team_name: Mapped[str | None] = mapped_column(String(255))  # For team-based registration
    preferred_division: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    # Team color preferences (temporarily commented out until migration is run)
    # primary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
    # secondary_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code
    # accent_color: Mapped[str | None] = mapped_column(String(7))  # Hex color code

    # Waiver and payment
    waiver_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waiver_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.UNPAID,
    )
    payment_notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship()
    season: Mapped[Season] = relationship(back_populates="registrations")
    waiver: Mapped[Waiver | None] = relationship(back_populates="registrations")


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


__all__ = [name for name in globals() if name[0].isupper()]






