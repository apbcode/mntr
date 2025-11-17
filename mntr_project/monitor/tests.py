from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import MonitoredPage, NotificationSettings
from .tasks import check_page
from unittest.mock import patch, MagicMock
from django.urls import reverse

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

class MonitoredPageDetailViewTest(TestCase):
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
        self.page.snapshots.create(content='<html><body><h1>Old Content</h1></body></html>')
        self.page.snapshots.create(content='<html><body><h1>New Content</h1></body></html>')


    def test_detail_view_does_not_mark_as_seen(self):
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.page.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.page.has_changed)

    def test_detail_view_no_change(self):
        self.page.has_changed = False
        self.page.save()

        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<h2>Changes:</h2>')

    @patch('monitor.views.requests.get')
    def test_iframe_content_view_marks_as_seen(self, mock_get):
        response = self.client.get(reverse('iframe_content', args=[self.page.id]))
        self.page.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.page.has_changed)
        self.assertContains(response, '<ins>')
        self.assertContains(response, '<del>')
