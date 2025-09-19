"""Background job functions for RQ worker."""

import os
from datetime import datetime, timedelta


def send_email_job(to_email, subject, template_key, context=None, **kwargs):
    """Background job to send emails."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.services.emailer import send_email
            return send_email(
                to_email=to_email,
                subject=subject,
                template_key=template_key,
                context=context or {},
                **kwargs
            )
        except Exception as e:
            print(f"Email job failed: {str(e)}")
            raise


def send_registration_confirmation_job(registration_id, to_email, to_name=None):
    """Background job to send registration confirmation."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.services.emailer import send_registration_confirmation
            return send_registration_confirmation(
                registration_id=registration_id,
                to_email=to_email,
                to_name=to_name
            )
        except Exception as e:
            print(f"Registration confirmation job failed: {str(e)}")
            raise


def send_game_reminder_job(game_id, to_email, to_name=None):
    """Background job to send game reminders."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.services.emailer import send_game_reminder
            return send_game_reminder(
                game_id=game_id,
                to_email=to_email,
                to_name=to_name
            )
        except Exception as e:
            print(f"Game reminder job failed: {str(e)}")
            raise


def send_game_recap_job(game_id, to_email, to_name=None):
    """Background job to send game recaps."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.services.emailer import send_game_recap
            return send_game_recap(
                game_id=game_id,
                to_email=to_email,
                to_name=to_name
            )
        except Exception as e:
            print(f"Game recap job failed: {str(e)}")
            raise


def generate_schedule_job(season_id, start_date, end_date, preferred_weekdays,
                         preferred_start_times, selected_venue_ids, rounds=1):
    """Background job to generate schedules."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.services.scheduler import generate_season_schedule
            return generate_season_schedule(
                season_id=season_id,
                start_date=start_date,
                end_date=end_date,
                preferred_weekdays=preferred_weekdays,
                preferred_start_times=preferred_start_times,
                selected_venue_ids=selected_venue_ids,
                rounds=rounds,
                persist=True
            )
        except Exception as e:
            print(f"Schedule generation job failed: {str(e)}")
            raise


def send_daily_game_reminders_job():
    """Background job to send daily game reminders (24h before games)."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.extensions import db
            from slms.models import Game, GameStatus, User, UserRole

            tomorrow = datetime.utcnow() + timedelta(days=1)
            start_of_day = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Find games scheduled for tomorrow
            from slms.blueprints.common.tenant import org_query
            upcoming_games = (
                org_query(Game)
                .filter(
                    Game.start_time >= start_of_day,
                    Game.start_time <= end_of_day,
                    Game.status == GameStatus.SCHEDULED
                )
                .all()
            )

            from slms.services.queue import queue_service
            sent_count = 0

            for game in upcoming_games:
                # Send reminders to coaches
                teams = [game.home_team, game.away_team]

                for team in teams:
                    if team:
                        # Find team coaches
                        coaches = (
                            db.session.query(User)
                            .filter(
                                User.org_id == game.org_id,
                                User.role.in_([UserRole.COACH, UserRole.ADMIN, UserRole.OWNER])
                            )
                            .all()
                        )

                        for coach in coaches:
                            if coach.email:
                                queue_service.enqueue_email(
                                    'send_game_reminder_job',
                                    game_id=game.id,
                                    to_email=coach.email,
                                    to_name=coach.email  # Using email as name fallback
                                )
                                sent_count += 1

            print(f"Queued {sent_count} game reminder emails for tomorrow's games")
            return sent_count

        except Exception as e:
            print(f"Daily game reminders job failed: {str(e)}")
            raise


def retry_failed_emails_job():
    """Background job to retry failed emails."""
    from slms import create_app

    app = create_app()

    with app.app_context():
        try:
            from slms.extensions import db
            from slms.models import EmailMessage, EmailStatus

            # Find failed emails that haven't exceeded max retries
            failed_emails = (
                db.session.query(EmailMessage)
                .filter(
                    EmailMessage.status == EmailStatus.FAILED,
                    EmailMessage.retry_count < EmailMessage.max_retries
                )
                .limit(50)  # Process max 50 at a time
                .all()
            )

            from slms.services.queue import queue_service
            retry_count = 0

            for email_msg in failed_emails:
                queue_service.enqueue_email(
                    'send_email_job',
                    to_email=email_msg.to_email,
                    subject=email_msg.subject,
                    template_key=email_msg.template_key,
                    context=email_msg.context,
                    to_name=email_msg.to_name
                )
                retry_count += 1

            print(f"Queued {retry_count} failed emails for retry")
            return retry_count

        except Exception as e:
            print(f"Retry failed emails job failed: {str(e)}")
            raise