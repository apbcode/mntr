from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import MonitoredPage, NotificationSettings
from .tasks import check_page
from unittest.mock import patch, MagicMock
from django.urls import reverse
from .forms import MonitoredPageForm

class MonitoredPageModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.page = MonitoredPage.objects.create(
            user=self.user,
            name='Example',
            url='http://example.com',
            frequency_number=5,
            frequency_unit='min'
        )

    def test_monitored_page_creation(self):
        self.assertEqual(self.page.name, 'Example')
        self.assertEqual(self.page.url, 'http://example.com')
        self.assertEqual(self.page.frequency_number, 5)
        self.assertEqual(self.page.frequency_unit, 'min')
        self.assertEqual(self.page.user, self.user)
        self.assertFalse(self.page.has_changed)

class CheckPageTaskTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.page = MonitoredPage.objects.create(
            user=self.user,
            name='Example',
            url='http://example.com',
            frequency_number=5,
            frequency_unit='min'
        )
        # Create an initial snapshot
        self.page.snapshots.create(content='<html><body><h1>Old Content</h1></body></html>')
        NotificationSettings.objects.create(
            user=self.user,
            notification_type='email',
            email_address='test@example.com'
        )

    @patch('monitor.tasks.requests.get')
    def test_check_page_task_with_change(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>New Content</h1></body></html>'
        mock_get.return_value = mock_response

        result = check_page(self.page.id)
        self.page.refresh_from_db()

        self.assertEqual(result, 'Successfully checked "Example"')
        self.assertTrue(self.page.has_changed)
        self.assertEqual(self.page.snapshots.count(), 2)
        self.assertEqual(self.page.snapshots.latest('created_at').content, '<html><body><h1>New Content</h1></body></html>')

    @patch('monitor.tasks.requests.get')
    def test_check_page_task_no_change(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Old Content</h1></body></html>'
        mock_get.return_value = mock_response

        result = check_page(self.page.id)
        self.page.refresh_from_db()

        self.assertEqual(result, 'Successfully checked "Example"')
        self.assertFalse(self.page.has_changed)
        self.assertEqual(self.page.snapshots.count(), 1)


class MonitoredPageListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.page = MonitoredPage.objects.create(
            user=self.user,
            name='Example',
            url='http://example.com',
            frequency_number=5,
            frequency_unit='min'
        )

    def test_list_view_renders_correctly(self):
        response = self.client.get(reverse('monitoredpage_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Example')


class NewMonitoredPageDetailViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.page = MonitoredPage.objects.create(
            user=self.user,
            name='Example',
            url='http://example.com',
            frequency_number=5,
            frequency_unit='min',
            has_changed=True
        )

        # Snapshots
        self.s1 = self.page.snapshots.create(content='<html><body><h1>Old Content</h1></body></html>')
        self.s2 = self.page.snapshots.create(content='<html><body><h1>New Content</h1></body></html>')
        self.s3 = self.page.snapshots.create(content='<html><body><h1>Newest Content</h1></body></html>')

        self.page.last_seen_snapshot = self.s1
        self.page.save()

    def test_view_displays_form(self):
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], MonitoredPageForm)

    def test_view_updates_page(self):
        new_data = {
            'name': 'New Example Name',
            'url': 'http://new-example.com',
            'frequency_number': 10,
            'frequency_unit': 'hour'
        }
        response = self.client.post(reverse('monitoredpage_detail', args=[self.page.id]), new_data)
        self.assertEqual(response.status_code, 302)
        self.page.refresh_from_db()
        self.assertEqual(self.page.name, 'New Example Name')
        self.assertEqual(self.page.frequency_unit, 'hour')

    def test_view_shows_inline_diff(self):
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe srcdoc="')
        self.assertContains(response, '<ins>Newest</ins> Content</h1></body></html>')

    def test_last_seen_snapshot_is_distinguished(self):
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<li class="last-seen"><a href="?snapshot_id={self.s1.pk}">')

    def test_viewing_specific_snapshot_diff(self):
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]), {'snapshot_id': self.s2.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe srcdoc="')
        self.assertContains(response, '<html><body><h1><del>Old</del><ins>New</ins> Content</h1></body></html>')
