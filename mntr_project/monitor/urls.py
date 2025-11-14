from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.MonitoredPageListView.as_view(), name='monitoredpage_list'),
    path('page/add/', views.MonitoredPageCreateView.as_view(), name='monitoredpage_create'),
    path('page/<int:pk>/', views.MonitoredPageDetailView.as_view(), name='monitoredpage_detail'),
    path('page/<int:pk>/edit/', views.MonitoredPageUpdateView.as_view(), name='monitoredpage_update'),
    path('page/<int:pk>/delete/', views.MonitoredPageDeleteView.as_view(), name='monitoredpage_delete'),
    path('page/<int:pk>/check/', views.check_now, name='check_now'),
    path('settings/', views.NotificationSettingsUpdateView.as_view(), name='notificationsettings_update'),
    path('login/', auth_views.LoginView.as_view(template_name='monitor/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='monitor/logout.html'), name='logout'),
]
