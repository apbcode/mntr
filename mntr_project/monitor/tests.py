from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import MonitoredPage, NotificationSettings, PageSnapshot
from .tasks import check_page
from unittest.mock import patch, MagicMock
from django.urls import reverse
from .forms import MonitoredPageForm
import difflib

class MonitoredPageModelTest(TestCase):
    """
    Tests for the MonitoredPage model.
    """
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
        """
        Tests that a MonitoredPage object is created with the correct attributes.
        """
        self.assertEqual(self.page.name, 'Example')
        self.assertEqual(self.page.url, 'http://example.com')
        self.assertEqual(self.page.frequency_number, 5)
        self.assertEqual(self.page.frequency_unit, 'min')
        self.assertEqual(self.page.user, self.user)
        self.assertFalse(self.page.has_changed)

class CheckPageTaskTest(TestCase):
    """
    Tests for the check_page Celery task.
    """
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
        """
        Tests that a new snapshot is created and has_changed is set to True when the page content changes.
        """
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
        """
        Tests that no new snapshot is created and has_changed remains False when the page content is unchanged.
        """
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
    """
    Tests for the MonitoredPageListView.
    """
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
        """
        Tests that the list view renders correctly and displays the monitored page.
        """
        response = self.client.get(reverse('monitoredpage_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Example')


class NewMonitoredPageDetailViewTest(TestCase):
    """
    Tests for the MonitoredPageDetailView.
    """
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
        """
        Tests that the detail view displays the MonitoredPageForm.
        """
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], MonitoredPageForm)

    def test_view_updates_page(self):
        """
        Tests that the detail view can update a MonitoredPage object.
        """
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
        """
        Tests that the detail view shows an inline diff of the latest changes.
        """
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe srcdoc="')
        self.assertContains(response, '<ins>Newest</ins> Content</h1></body></html>')

    def test_last_seen_snapshot_is_distinguished(self):
        """
        Tests that the last seen snapshot is visually distinguished in the snapshot list.
        """
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<li class="last-seen"><a href="?snapshot_id={self.s1.pk}">')

    def test_viewing_specific_snapshot_diff(self):
        """
        Tests that the detail view can display a diff between two specific snapshots.
        """
        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]), {'snapshot_id': self.s2.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe srcdoc="')
        self.assertContains(response, '<html><body><h1><del>Old</del><ins>New</ins> Content</h1></body></html>')

    def test_diff_in_view(self):
        """
        Tests that the diff is correctly generated and displayed in the view.
        """
        s1 = self.page.snapshots.create(content='<html><body><h1>Old Content</h1></body></html>')
        s2 = self.page.snapshots.create(content='<html><body><h1>New Content</h1></body></html>')
        self.page.last_seen_snapshot = s1
        self.page.save()

        response = self.client.get(reverse('monitoredpage_detail', args=[self.page.id]), {'snapshot_id': s2.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<del>Old</del>')
        self.assertContains(response, '<ins>New</ins>')


class CoreFunctionalityTest(TestCase):
    """
    Tests for the core snapshotting and diffing functionality.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            "testuser", "test@example.com", "password"
        )
        self.page = MonitoredPage.objects.create(
            user=self.user,
            name="Example",
            url="http://example.com",
            frequency_number=5,
            frequency_unit="minute",
        )

    @patch("monitor.tasks.requests.get")
    def test_initial_snapshot_creation(self, mock_get):
        """
        Tests that the first check of a page creates an initial snapshot.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Initial Content</h1></body></html>"
        mock_get.return_value = mock_response

        check_page(self.page.id)

        self.page.refresh_from_db()
        self.assertEqual(self.page.snapshots.count(), 1)

        latest_snapshot = self.page.snapshots.first()
        self.assertEqual(latest_snapshot.content, mock_response.text)
        self.assertIsNotNone(self.page.last_checked)
        self.assertEqual(self.page.last_seen_snapshot, latest_snapshot)

    @patch("monitor.tasks.requests.get")
    def test_snapshot_on_change(self, mock_get):
        """
        Tests that a new snapshot is created when the page content changes.
        """
        initial_content = "<html><body><h1>Initial Content</h1></body></html>"
        self.page.snapshots.create(content=initial_content)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Updated Content</h1></body></html>"
        mock_get.return_value = mock_response

        check_page(self.page.id)

        self.page.refresh_from_db()
        self.assertEqual(self.page.snapshots.count(), 2)
        self.assertTrue(self.page.has_changed)

    @patch("monitor.tasks.requests.get")
    def test_no_snapshot_when_unchanged(self, mock_get):
        """
        Tests that no new snapshot is created when the page content is unchanged.
        """
        initial_content = "<html><body><h1>Initial Content</h1></body></html>"
        self.page.snapshots.create(content=initial_content)
        self.page.has_changed = False
        self.page.save()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = initial_content
        mock_get.return_value = mock_response

        check_page(self.page.id)

        self.page.refresh_from_db()
        self.assertEqual(self.page.snapshots.count(), 1)
        self.assertFalse(self.page.has_changed)
