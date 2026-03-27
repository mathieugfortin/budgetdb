# budgetdb/scheduler.py
import os
import fcntl
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

def run_extend_ledgers():
    status_msg = f"Running (Worker PID: {os.getpid()})"
    cache.set('ledger_task_status', status_msg, timeout=3600)
    try:
        call_command('extend_ledgers')
        cache.set('ledger_task_last_run', timezone.now(), timeout=None)
        cache.set('ledger_task_status', 'Idle', timeout=None)
    except Exception as e:
        cache.set('ledger_task_status', f'Error: {str(e)}', timeout=None)

def start():
    # Use a file in /tmp to coordinate between workers
    lock_file_path = '/tmp/budgetdb_scheduler.lock'

    try:
        # Open file (create if it doesn't exist)
        f = open(lock_file_path, 'wb')

        # LOCK_EX: Exclusive lock
        # LOCK_NB: Non-blocking (fail immediately if someone else has it)
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # If we get here, this worker is the "Winner"
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            lambda: call_command('extend_ledgers'), 
            'cron', 
            day=1, 
            hour=3, 
            id='extend_ledgers_job',
            replace_existing=True
        )
        scheduler.start()
        # Use logger so Gunicorn's capture_output sees it
        logger.info(f"--- Scheduler started on Worker PID {os.getpid()} ---")
        
        # Note: We do NOT close 'f' here. 
        # The lock stays active as long as this process is alive.
        
    except OSError:
        # Lock is held by the other worker
        logger.debug(f"Worker PID {os.getpid()} skipping scheduler (already active).")
        return
