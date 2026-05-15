import os
import sys

 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onlineshop.settings')

# Create WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Vercel requires this variable name
app = application
