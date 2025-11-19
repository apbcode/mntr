from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import MonitoredPage, NotificationSettings
from .forms import MonitoredPageForm, NotificationSettingsForm
from django.urls import reverse_lazy
import requests
from .tasks import check_page
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)

class MonitoredPageListView(LoginRequiredMixin, ListView):
    """
    Displays a list of all MonitoredPage objects for the currently logged-in user.
    """
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_list.html'

    def get_queryset(self):
        """
        Returns only the MonitoredPage objects belonging to the current user.
        """
        return MonitoredPage.objects.filter(user=self.request.user).order_by('pk')

class MonitoredPageCreateView(LoginRequiredMixin, CreateView):
    """
    Handles the creation of a new MonitoredPage object.
    """
    model = MonitoredPage
    form_class = MonitoredPageForm
    template_name = 'monitor/monitoredpage_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def form_valid(self, form):
        """
        Sets the user of the new MonitoredPage to the currently logged-in user.
        """
        form.instance.user = self.request.user
        return super().form_valid(form)

class MonitoredPageUpdateView(LoginRequiredMixin, UpdateView):
    """
    Handles the updating of an existing MonitoredPage object.
    """
    model = MonitoredPage
    form_class = MonitoredPageForm
    template_name = 'monitor/monitoredpage_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_queryset(self):
        """
        Ensures that users can only edit their own MonitoredPage objects.
        """
        return MonitoredPage.objects.filter(user=self.request.user)

class MonitoredPageDeleteView(LoginRequiredMixin, DeleteView):
    """
    Handles the deletion of a MonitoredPage object.
    """
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_confirm_delete.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_queryset(self):
        """
        Ensures that users can only delete their own MonitoredPage objects.
        """
        return MonitoredPage.objects.filter(user=self.request.user)

class MonitoredPageDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a MonitoredPage, including a diff of the changes.
    """
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_detail.html'

    def get_context_data(self, **kwargs):
        """
        Prepares the context data for the detail view, including the diff content.
        """
        context = super().get_context_data(**kwargs)
        page = kwargs.get('object', self.object)
        logger.info(f"Preparing context for MonitoredPageDetailView. Page: {page.name} (ID: {page.id})")

        if 'form' not in context:
            context['form'] = MonitoredPageForm(instance=page)

        # Get all snapshots for the page, ordered by creation date
        all_snapshots = page.snapshots.order_by('-created_at')
        context['all_snapshots'] = all_snapshots
        logger.info(f"Found {all_snapshots.count()} snapshots for page {page.id}")

        snapshot_id_to_show = self.request.GET.get('snapshot_id')

        diff_content = ""
        base_snapshot = page.last_seen_snapshot

        # Determine which snapshot to diff against
        snapshot_to_diff_against = None
        if snapshot_id_to_show:
            snapshot_to_diff_against = get_object_or_404(all_snapshots, pk=snapshot_id_to_show)
            logger.info(f"User requested specific snapshot ID: {snapshot_id_to_show}")
        elif page.has_changed:
            snapshot_to_diff_against = all_snapshots.first()
            logger.info(f"Page has changed. Defaulting to latest snapshot ID: {snapshot_to_diff_against.id if snapshot_to_diff_against else 'None'}")

        # Generate the diff content
        if snapshot_to_diff_against:
            if base_snapshot and base_snapshot != snapshot_to_diff_against:
                logger.info(f"Calculating diff between Base Snapshot {base_snapshot.id} and Target Snapshot {snapshot_to_diff_against.id}")
                from .templatetags.monitor_extras import htmldiff
                diff_content = htmldiff(base_snapshot.content, snapshot_to_diff_against.content)
            else:
                logger.info("No base snapshot or base snapshot is same as target. Showing target content directly.")
                diff_content = snapshot_to_diff_against.content

        context['diff_content'] = diff_content
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and marks the latest changes as seen.
        """
        self.object = self.get_object()

        object_for_template = MonitoredPage.objects.get(pk=self.object.pk)

        # If the page has changed and the user is not viewing a specific snapshot,
        # mark the latest snapshot as seen.
        if self.object.has_changed and not request.GET.get('snapshot_id'):
            latest_snapshot = self.object.snapshots.order_by('-created_at').first()
            if latest_snapshot:
                self.object.last_seen_snapshot = latest_snapshot
                self.object.has_changed = False
                self.object.save()

        context = self.get_context_data(object=object_for_template)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for updating the MonitoredPage.
        """
        self.object = self.get_object()
        form = MonitoredPageForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            return redirect('monitoredpage_detail', pk=self.object.pk)

        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)

class NotificationSettingsUpdateView(LoginRequiredMixin, UpdateView):
    """
    Handles the updating of NotificationSettings for the current user.
    """
    model = NotificationSettings
    form_class = NotificationSettingsForm
    template_name = 'monitor/notificationsettings_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_object(self):
        """
        Returns the NotificationSettings object for the current user,
        creating it if it doesn't exist.
        """
        settings, created = NotificationSettings.objects.get_or_create(user=self.request.user)
        return settings

@login_required
@require_POST
def check_now(request, pk):
    """
    Triggers an immediate check for a MonitoredPage.
    """
    page = get_object_or_404(MonitoredPage, pk=pk, user=request.user)
    check_page.delay(page.id)
    return redirect('monitoredpage_list')
