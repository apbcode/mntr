from celery import shared_task
from .models import MonitoredPage, PageSnapshot
import requests
from django.utils import timezone
import difflib
from .notifications import send_notification
from datetime import timedelta

@shared_task
def check_page(page_id):
    """
    Checks a monitored page for changes.

    Args:
        page_id: The ID of the MonitoredPage to check.
    """
    try:
        page = MonitoredPage.objects.get(id=page_id)

        # Fetch the current content of the page
        response = requests.get(page.url)
        response.raise_for_status()
        current_content = response.text

        # Get the latest snapshot of the page
        latest_snapshot = page.snapshots.order_by('-created_at').first()

        if latest_snapshot:
            # If the content has changed, create a new snapshot and send a notification
            if current_content != latest_snapshot.content:
                page.has_changed = True
                PageSnapshot.objects.create(monitored_page=page, content=current_content)

                # Generate a diff to show the changes
                diff = "".join(difflib.unified_diff(
                    latest_snapshot.content.splitlines(keepends=True),
                    current_content.splitlines(keepends=True),
                    fromfile='old',
                    tofile='new',
                ))
                send_notification(page, diff)
        else:
            # If this is the first check, create the first snapshot
            first_snapshot = PageSnapshot.objects.create(monitored_page=page, content=current_content)
            page.last_seen_snapshot = first_snapshot

        # Update the last checked timestamp
        page.last_checked = timezone.now()
        page.save()
        return f'Successfully checked "{page.name}"'
    except MonitoredPage.DoesNotExist:
        return f'MonitoredPage with id {page_id} does not exist.'
    except requests.exceptions.RequestException as e:
        return f'Error checking "{page.name}": {e}'

@shared_task
def check_all_pages():
    """
    Checks all monitored pages to see if they are due for a check.
    """
    for page in MonitoredPage.objects.all():
        if page.last_checked:
            # Calculate the time delta based on the frequency settings
            delta = timedelta()
            if page.frequency_unit == 'minute':
                delta = timedelta(minutes=page.frequency_number)
            elif page.frequency_unit == 'hour':
                delta = timedelta(hours=page.frequency_number)
            elif page.frequency_unit == 'day':
                delta = timedelta(days=page.frequency_number)
            elif page.frequency_unit == 'week':
                delta = timedelta(weeks=page.frequency_number)
            elif page.frequency_unit == 'month':
                # This is a simplification, assuming 30 days per month
                delta = timedelta(days=page.frequency_number * 30)
            elif page.frequency_unit == 'year':
                # This is a simplification, assuming 365 days per year
                delta = timedelta(days=page.frequency_number * 365)

            # If the page is due for a check, queue the check_page task
            if timezone.now() > page.last_checked + delta:
                check_page.delay(page.id)
        else:
            # If the page has never been checked, check it now
            check_page.delay(page.id)
