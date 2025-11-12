# mntr - A Page Monitoring App

mntr is a Django application that monitors web pages for changes and notifies you when they are updated.

## Features

*   **Automatic Page Monitoring:** Add URLs to monitor, and mntr will check them for changes at a frequency you define.
*   **User-Defined Frequency:** Set the check frequency for each page (e.g., every 5 minutes, 2 hours, 1 day, 3 weeks, etc.).
*   **Multi-Channel Notifications:** Receive notifications via email, Slack, or Telegram when a page has changed.
*   **Change Visualization:** Notifications include a "diff" of the changes, showing you exactly what was added or removed.
*   **Manual Checks:** A "Check Now" button allows you to trigger an immediate check for any page, regardless of its schedule.
*   **Web Interface:** A clean user interface to view your monitored pages, see their status, and view the detected changes.

## Setup and Running with Docker

To get the mntr application running locally, you will need to have Docker and Docker Compose installed.

### 1. Clone the Repository

```bash
git clone <repository_url>
cd <repository_directory>
```

### 2. Configure Environment Variables

The application uses environment variables for configuration. A `.env.example` file is provided in the `mntr_project` directory. Copy it to `.env` and update the values:

```bash
cp mntr_project/.env.example mntr_project/.env
```

You will need to set the following variables in the `.env` file:

*   `DJANGO_SECRET_KEY`: A long, random string used for cryptographic signing.
*   `DJANGO_DEBUG`: Set to `True` for development, `False` for production.
*   `TELEGRAM_BOT_TOKEN`: Your Telegram bot token, if you want to use Telegram notifications.

### 3. Build and Run the Application

With Docker and Docker Compose installed, you can build and run the application with a single command:

```bash
docker compose up --build
```

This will build the Docker image for the application and start the `web`, `redis`, `worker`, and `beat` services.

### 4. Set Up the Database

The first time you run the application, you will need to run the database migrations. You can do this by opening a new terminal and running the following command:

```bash
docker compose exec web python manage.py migrate
```

You can now access the application at `http://127.0.0.1:8000/`.
