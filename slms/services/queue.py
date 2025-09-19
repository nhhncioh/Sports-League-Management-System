"""Queue service for background jobs using RQ."""

import os
from datetime import datetime, timedelta

import redis
from rq import Queue
from rq.job import Job

from slms.services.jobs import (
    send_email_job,
    send_registration_confirmation_job,
    send_game_reminder_job,
    send_game_recap_job,
    generate_schedule_job,
    send_daily_game_reminders_job,
    retry_failed_emails_job
)


class QueueService:
    """Service for managing background job queues."""

    def __init__(self):
        self.redis_conn = self._get_redis_connection()
        self.email_queue = Queue('email', connection=self.redis_conn)
        self.schedule_queue = Queue('schedule', connection=self.redis_conn)
        self.default_queue = Queue(connection=self.redis_conn)

    def _get_redis_connection(self):
        """Get Redis connection from environment."""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)

    def enqueue_email(self, to_email, subject, template_key, context=None, **kwargs):
        """Queue an email to be sent."""
        job = self.email_queue.enqueue(
            send_email_job,
            to_email=to_email,
            subject=subject,
            template_key=template_key,
            context=context or {},
            **kwargs
        )
        return job

    def enqueue_registration_confirmation(self, registration_id, to_email, to_name=None):
        """Queue a registration confirmation email."""
        job = self.email_queue.enqueue(
            send_registration_confirmation_job,
            registration_id=registration_id,
            to_email=to_email,
            to_name=to_name
        )
        return job

    def enqueue_game_reminder(self, game_id, to_email, to_name=None, delay_seconds=None):
        """Queue a game reminder email."""
        if delay_seconds:
            # Schedule for later
            job = self.email_queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                send_game_reminder_job,
                game_id=game_id,
                to_email=to_email,
                to_name=to_name
            )
        else:
            job = self.email_queue.enqueue(
                send_game_reminder_job,
                game_id=game_id,
                to_email=to_email,
                to_name=to_name
            )
        return job

    def enqueue_game_recap(self, game_id, to_email, to_name=None):
        """Queue a game recap email."""
        job = self.email_queue.enqueue(
            send_game_recap_job,
            game_id=game_id,
            to_email=to_email,
            to_name=to_name
        )
        return job

    def enqueue_schedule_generation(self, season_id, start_date, end_date,
                                   preferred_weekdays, preferred_start_times,
                                   selected_venue_ids, rounds=1):
        """Queue schedule generation."""
        job = self.schedule_queue.enqueue(
            generate_schedule_job,
            season_id=season_id,
            start_date=start_date,
            end_date=end_date,
            preferred_weekdays=preferred_weekdays,
            preferred_start_times=preferred_start_times,
            selected_venue_ids=selected_venue_ids,
            rounds=rounds,
            timeout=600  # 10 minutes timeout for schedule generation
        )
        return job

    def schedule_daily_reminders(self):
        """Schedule daily game reminders job."""
        # Run every day at 9 AM
        job = self.default_queue.enqueue_at(
            datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1),
            send_daily_game_reminders_job
        )
        return job

    def schedule_retry_failed_emails(self):
        """Schedule retry of failed emails."""
        # Run every hour
        job = self.default_queue.enqueue_in(
            timedelta(hours=1),
            retry_failed_emails_job
        )
        return job

    def get_job_status(self, job_id):
        """Get the status of a job by ID."""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                'id': job.id,
                'status': job.get_status(),
                'result': job.result,
                'exc_info': job.exc_info,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at,
                'meta': job.meta
            }
        except Exception:
            return None

    def get_queue_stats(self):
        """Get queue statistics."""
        return {
            'email_queue': {
                'name': 'email',
                'length': len(self.email_queue),
                'failed_count': self.email_queue.failed_job_registry.count,
                'scheduled_count': self.email_queue.scheduled_job_registry.count
            },
            'schedule_queue': {
                'name': 'schedule',
                'length': len(self.schedule_queue),
                'failed_count': self.schedule_queue.failed_job_registry.count,
                'scheduled_count': self.schedule_queue.scheduled_job_registry.count
            },
            'default_queue': {
                'name': 'default',
                'length': len(self.default_queue),
                'failed_count': self.default_queue.failed_job_registry.count,
                'scheduled_count': self.default_queue.scheduled_job_registry.count
            }
        }

    def get_recent_jobs(self, queue_name='email', limit=50):
        """Get recent jobs from a queue."""
        queue_map = {
            'email': self.email_queue,
            'schedule': self.schedule_queue,
            'default': self.default_queue
        }

        queue = queue_map.get(queue_name, self.email_queue)

        # Get finished jobs
        finished_jobs = queue.finished_job_registry.get_job_ids(0, limit)
        failed_jobs = queue.failed_job_registry.get_job_ids(0, limit)

        jobs = []

        # Process finished jobs
        for job_id in finished_jobs[:limit//2]:
            try:
                job = Job.fetch(job_id, connection=self.redis_conn)
                jobs.append({
                    'id': job.id,
                    'status': 'finished',
                    'created_at': job.created_at,
                    'ended_at': job.ended_at,
                    'func_name': job.func_name,
                    'args': job.args[:2] if job.args else []  # Limit for privacy
                })
            except Exception:
                continue

        # Process failed jobs
        for job_id in failed_jobs[:limit//2]:
            try:
                job = Job.fetch(job_id, connection=self.redis_conn)
                jobs.append({
                    'id': job.id,
                    'status': 'failed',
                    'created_at': job.created_at,
                    'ended_at': job.ended_at,
                    'func_name': job.func_name,
                    'args': job.args[:2] if job.args else [],
                    'exc_info': job.exc_info
                })
            except Exception:
                continue

        # Sort by created_at desc
        jobs.sort(key=lambda x: x['created_at'], reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id):
        """Cancel a job by ID."""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            return True
        except Exception:
            return False

    def retry_job(self, job_id):
        """Retry a failed job."""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.retry()
            return True
        except Exception:
            return False


# Global queue service instance
queue_service = QueueService()


__all__ = ['QueueService', 'queue_service']