from celery import shared_task
from .models import MonitoredPage
import requests
from django.utils import timezone
import difflib
from .notifications import send_notification
from datetime import timedelta

@shared_task
def check_page(page_id):
    try:
        page = MonitoredPage.objects.get(id=page_id)
        response = requests.get(page.url)
        response.raise_for_status()
        current_content = response.text
        if page.last_content:
            if current_content != page.last_content:
                page.has_changed = True
                diff = "".join(difflib.unified_diff(
                    page.last_content.splitlines(keepends=True),
                    current_content.splitlines(keepends=True),
                    fromfile='old',
                    tofile='new',
                ))
                send_notification(page, diff)
        page.last_content = current_content
        page.last_checked = timezone.now()
        page.save()
        return f'Successfully checked "{page.name}"'
    except MonitoredPage.DoesNotExist:
        return f'MonitoredPage with id {page_id} does not exist.'
    except requests.exceptions.RequestException as e:
        return f'Error checking "{page.name}": {e}'

@shared_task
def check_all_pages():
    for page in MonitoredPage.objects.all():
        if page.last_checked:
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

            if timezone.now() > page.last_checked + delta:
                check_page.delay(page.id)
        else:
            # If the page has never been checked, check it now.
            check_page.delay(page.id)
