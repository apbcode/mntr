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

class MonitoredPageListView(LoginRequiredMixin, ListView):
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_list.html'

    def get_queryset(self):
        return MonitoredPage.objects.filter(user=self.request.user).order_by('pk')

class MonitoredPageCreateView(LoginRequiredMixin, CreateView):
    model = MonitoredPage
    form_class = MonitoredPageForm
    template_name = 'monitor/monitoredpage_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class MonitoredPageUpdateView(LoginRequiredMixin, UpdateView):
    model = MonitoredPage
    form_class = MonitoredPageForm
    template_name = 'monitor/monitoredpage_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_queryset(self):
        return MonitoredPage.objects.filter(user=self.request.user)

class MonitoredPageDeleteView(LoginRequiredMixin, DeleteView):
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_confirm_delete.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_queryset(self):
        return MonitoredPage.objects.filter(user=self.request.user)

class MonitoredPageDetailView(LoginRequiredMixin, DetailView):
    model = MonitoredPage
    template_name = 'monitor/monitoredpage_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.object

        all_snapshots = page.snapshots.order_by('-created_at')
        latest_snapshot = all_snapshots.first()

        base_snapshot = page.last_seen_snapshot

        intermediary_snapshots = []
        if base_snapshot and latest_snapshot and base_snapshot != latest_snapshot:
            intermediary_snapshots = all_snapshots.filter(
                created_at__gt=base_snapshot.created_at,
                created_at__lt=latest_snapshot.created_at
            )

        context['latest_snapshot'] = latest_snapshot
        context['base_snapshot'] = base_snapshot
        context['intermediary_snapshots'] = intermediary_snapshots
        return context

class NotificationSettingsUpdateView(LoginRequiredMixin, UpdateView):
    model = NotificationSettings
    form_class = NotificationSettingsForm
    template_name = 'monitor/notificationsettings_form.html'
    success_url = reverse_lazy('monitoredpage_list')

    def get_object(self):
        # Create the settings object if it doesn't exist
        settings, created = NotificationSettings.objects.get_or_create(user=self.request.user)
        return settings

@login_required
@require_POST
def check_now(request, pk):
    page = get_object_or_404(MonitoredPage, pk=pk, user=request.user)
    check_page.delay(page.id)
    return redirect('monitoredpage_list')


@login_required
def iframe_content_view(request, pk):
    page = get_object_or_404(MonitoredPage, pk=pk, user=request.user)

    latest_snapshot = page.snapshots.order_by('-created_at').first()
    base_snapshot = page.last_seen_snapshot

    diff_content = ""
    if base_snapshot and latest_snapshot:
        from .templatetags.monitor_extras import htmldiff
        diff_content = htmldiff(base_snapshot.content, latest_snapshot.content)
    elif latest_snapshot:
        diff_content = latest_snapshot.content

    # Mark the latest snapshot as seen.
    if latest_snapshot:
        page.last_seen_snapshot = latest_snapshot
    page.has_changed = False
    page.save()

    return render(request, 'monitor/iframe_content.html', {'diff_content': diff_content})


@login_required
def intermediary_snapshot_diff(request, page_pk, snapshot_pk):
    page = get_object_or_404(MonitoredPage, pk=page_pk, user=request.user)

    intermediary_snapshot = get_object_or_404(page.snapshots, pk=snapshot_pk)
    base_snapshot = page.last_seen_snapshot

    diff_content = ""
    if base_snapshot and intermediary_snapshot:
        from .templatetags.monitor_extras import htmldiff
        diff_content = htmldiff(base_snapshot.content, intermediary_snapshot.content)
    elif intermediary_snapshot:
        diff_content = intermediary_snapshot.content

    return render(request, 'monitor/iframe_content.html', {'diff_content': diff_content})
