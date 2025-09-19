"""RQ Worker for background job processing."""

import os
import sys
from datetime import datetime, timedelta

import redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

# Add the slms directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def get_redis_connection():
    """Get Redis connection from environment."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)


def setup_queues():
    """Setup RQ queues."""
    redis_conn = get_redis_connection()

    # Define queues with different priorities
    email_queue = Queue('email', connection=redis_conn)
    schedule_queue = Queue('schedule', connection=redis_conn)
    default_queue = Queue(connection=redis_conn)

    return {
        'email': email_queue,
        'schedule': schedule_queue,
        'default': default_queue
    }


if __name__ == '__main__':
    """Start the RQ worker."""
    try:
        redis_conn = get_redis_connection()
        queues = setup_queues()

        # Import job functions
        from slms.services.jobs import (
            send_email_job,
            send_registration_confirmation_job,
            send_game_reminder_job,
            send_game_recap_job,
            generate_schedule_job,
            send_daily_game_reminders_job,
            retry_failed_emails_job
        )

        # Create worker with multiple queues (email has higher priority)
        worker = Worker(
            [queues['email'], queues['schedule'], queues['default']],
            connection=redis_conn
        )

        print("Starting RQ worker...")
        print(f"Listening on queues: {list(queues.keys())}")
        print(f"Redis connection: {redis_conn}")

        worker.work()
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
        if 'worker' in locals():
            worker.stop()
    except Exception as e:
        print(f"Worker error: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise in Docker - just exit gracefully