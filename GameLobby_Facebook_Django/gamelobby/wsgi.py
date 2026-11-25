"""Copy this file into PythonAnywhere's linked WSGI configuration."""

import getpass
import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

project_dir = Path(__file__).resolve().parent.parent
if not (project_dir / "manage.py").is_file():
    project_dir = Path.home() / "Combined_Django"
project_dir = Path(os.environ.get("DJANGO_PROJECT_DIR", str(project_dir)))
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

account = getpass.getuser().lower()
domains = (f"{account}.pythonanywhere.com", f"{account}.eu.pythonanywhere.com")
os.environ.setdefault("DJANGO_DEBUG", "0")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", ",".join(domains))
os.environ.setdefault(
    "DJANGO_CSRF_TRUSTED_ORIGINS", ",".join(f"https://{domain}" for domain in domains)
)
os.environ.setdefault("DJANGO_TRUST_PROXY_SSL", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gamelobby.settings")

application = get_wsgi_application()
