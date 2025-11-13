FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY mntr_project/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY mntr_project /app/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
