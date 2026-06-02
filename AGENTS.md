# Project Instructions

This project is TutorBuddy, a Django multi-app web application.

## Project Structure

- `apps/accounts/` handles Member and Tutor accounts.
- `apps/admin_panel/` handles system config and reports.
- `apps/bookings/` handles bookings, tutoring activity, job completion, and reviews.
- `apps/courses/` handles faculties, majors, course groups, and courses.
- `apps/credits/` handles refills and withdrawals.
- `apps/messaging/` handles inbox and messages.
- `apps/notifications/` handles notifications and signals.
- `apps/tutoring/` handles tutor courses, rates, schedules, and time slots.
- `config/` contains Django settings and root URLs.
- `templates/` contains Django templates.
- `static/` contains CSS, JavaScript, Bootstrap 5, Font Awesome 6, and images.
- `media/` contains uploaded files.

## Tech Stack

- Framework: Django
- Language: Python
- Templates: Django Templates
- CSS/JS: Bootstrap 5, Font Awesome 6, and custom static files
- Environment: Python virtual environment
- Dependencies: `requirements.txt`

## Coding Rules

- Follow the existing Django app structure.
- Keep model, view, form, URL, template, and static changes in the correct app.
- Use English for variable names, function names, class names, and Django conventions.
- Comments may be written in Thai when useful.
- Do not modify `venv/`.
- Do not modify uploaded files in `media/` unless explicitly requested.
- Do not guess model fields, function names, settings, or URLs. Check the existing code first.

## When Editing

- Keep changes small and focused.
- Before editing, identify which app and file are being changed.
- If changing `models.py`, mention that migrations are needed.
- If adding imports, packages, middleware, context processors, or settings, explain what was added and where.
- If changing UI, keep it responsive for mobile and desktop.
- Preserve the existing template and static file organization.

## Commands

Use these commands when relevant:

```bash
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

## Final Response

- Explain changes in Thai.
- Mention files changed.
- Mention any commands that should be run.
- If `models.py` changed, remind the user to run:

```bash
python manage.py makemigrations
python manage.py migrate
```
