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
        return MonitoredPage.objects.filter(user=self.request.user)

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
        # The diff generation and "seen" logic is now handled by the iframe_content_view.
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

    try:
        response = requests.get(page.url)
        response.raise_for_status()
        current_content = response.text

        # Generate the diff using the custom template tag logic
        from .templatetags.monitor_extras import htmldiff
        diff_content = htmldiff(page.last_content, current_content)

        # Mark as seen
        page.last_content = current_content
        page.has_changed = False
        page.save()

    except requests.exceptions.RequestException as e:
        diff_content = f"Error fetching content: {e}"

    return render(request, 'monitor/iframe_content.html', {'diff_content': diff_content})
