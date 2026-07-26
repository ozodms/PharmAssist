# PharmAssist

Django project (5.2.7).

## Quick start
1) Create venv and activate:
   python -m venv .venv
   source .venv/bin/activate

2) Install deps:
   python -m pip install -r requirements.txt

3) Set up environment variables:
   cp .env.example .env
   # then edit .env and set your own SECRET_KEY

4) Run migrations and server:
   python manage.py migrate
   python manage.py runserver
