import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mntr_project.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='testuser').exists():
    User.objects.create_user('testuser', 'test@example.com', 'password')
