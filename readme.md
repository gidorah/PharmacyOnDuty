# Eczanerede (Pharmacy Locator)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Eczanerede is a mobile-first web application designed to help users quickly find open and on-duty pharmacies in Turkish cities. It currently supports Eskişehir, Istanbul, and Ankara, with plans for expansion. The application provides real-time status updates, location-based search, interactive maps with turn-by-turn directions, and estimated travel distances, all within a user-friendly, responsive interface.

**Live Website:** [eczanerede.com](https://eczanerede.com)

## Screenshots

<img src="screenshots/Screenshot%20Map.png" width="300"> <img src="screenshots/Screenshot%20List.png" width="300">

## Table of Contents

- [Eczanerede (Pharmacy Locator)](#eczanerede-pharmacy-locator)
  - [Screenshots](#screenshots)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Tech Stack](#tech-stack)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Database](#database)
    - [DevOps and Infrastructure](#devops-and-infrastructure)
    - [Development Tools](#development-tools)
  - [Architecture](#architecture)
    - [Project Structure](#project-structure)
    - [Key Components and Workflow](#key-components-and-workflow)
  - [Setup and Installation](#setup-and-installation)
    - [Prerequisites](#prerequisites)
    - [Steps](#steps)
    - [Remote Development Setup (docker-compose.remotedev.yml)](#remote-development-setup-docker-composeremotedevyml)
  - [Production Deployment (HTTPS with Docker, Nginx, and Let’s Encrypt)](#production-deployment-https-with-docker-nginx-and-lets-encrypt)
  - [Environment Variables](#environment-variables)
  - [Testing](#testing)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)

## Features

*   **Real-time Pharmacy Status:**  Displays whether pharmacies are currently "open" (during regular business hours) or "on-duty" (available outside of regular hours).
*   **Location-Based Search:**  Automatically detects the user's location (with permission) and finds the nearest pharmacies.
*   **Interactive Map:** Integrates with Google Maps to display pharmacy locations and provide directions.
*   **Turn-by-Turn Directions:**  Offers detailed driving directions to the selected pharmacy via the Google Maps API.
*   **Travel Distance Estimates:**  Calculates and displays the approximate distance and travel time to each pharmacy.
*   **Mobile-Responsive Design:**  Built with a mobile-first approach using Tailwind CSS, ensuring optimal viewing and usability on various devices.
*   **Swipeable Pharmacy List:**  Uses Hammer.js to provide a modern, intuitive user experience, allowing users to easily swipe through the list of pharmacies.
*   **Cached API Responses:**  Implements caching for API responses to improve performance and reduce unnecessary API calls.
*   **SEO Optimized:** Includes `sitemap.xml`, `robots.txt`, and relevant meta tags to improve search engine visibility.
*   **Error Tracking:** Integrated with Sentry for real-time error monitoring and debugging.
*   **Startup Reliability:** Implements a robust "wait-for-services" mechanism to ensure the application only starts when database and message broker services are fully ready.
*   **Static File Optimization:** Uses WhiteNoise for efficient serving of static assets (CSS, JavaScript, images).
*   **Remote Debugging:** Supports remote debugging using `debugpy` for easier development and troubleshooting, particularly within Docker containers.
*   **Database Indexes:** Includes indexes on `location`, `duty_start`, and `duty_end` for efficient querying.

## Tech Stack

### Backend

*   **Python 3.13:**  The primary programming language.
*   **Django 5.1:**  A high-level Python web framework for rapid development and clean design.
*   **PostGIS:**  A spatial database extender for PostgreSQL, enabling efficient storage and querying of geographic data.
*   **GeoDjango:**  Django's built-in framework for handling geographic data and integrating with PostGIS.
*   **Gunicorn:**  A production-ready WSGI HTTP server for serving the Django application.
*   **requests**: Python HTTP library for making requests.
*   **beautifulsoup4**: Library used for web scraping.
*   **python-dotenv**: Library for managing .env files.
*   **Celery:** A distributed task queue for asynchronous and periodic tasks.
*   **Redis:** An in-memory data structure store, used as a message broker for Celery.
*   **django-celery-beat:** A Celery Beat scheduler that stores the periodic task schedule in the Django database.

### Frontend

*   **HTML5/CSS3:**  Standard web technologies for structure and styling.
*   **JavaScript (ES6+):**  Used for client-side interactivity and dynamic updates.
*   **Tailwind CSS:**  A utility-first CSS framework for rapidly building custom user interfaces.
*   **jQuery:**  A fast, small, and feature-rich JavaScript library used for DOM manipulation and AJAX requests.
*   **Hammer.js:**  A JavaScript library for handling multi-touch gestures, enabling the swipeable list functionality.
*   **Google Maps JavaScript API:**  Provides the interactive map, geocoding, directions, and distance matrix services.

### Database

*   **PostgreSQL 15 (with PostGIS extension):**  A robust, open-source relational database system with powerful spatial capabilities.

### DevOps and Infrastructure

*   **Docker:** Containerization technology for consistent and reproducible deployments.
*   **Docker Compose:** A tool for defining and managing multi-container Docker applications.
*   **Heroku:** Cloud platform used for hosting the production environment.
*   **Sentry:** Error tracking and performance monitoring platform for identifying and resolving issues in real-time.
*   **WhiteNoise:** A library for serving static files efficiently in a Django application, especially useful in production.

### Development Tools

*   **pre-commit:**  A framework for managing and maintaining pre-commit hooks (e.g., code formatting, linting).
*   **mypy:**  An optional static type checker for Python, helping to catch type errors early in development.
*   **ruff**  An uncompromising Python code formatter, ensuring consistent code style.
*   **debugpy:**  A debugger for Python, supporting remote debugging in development environments.
*   **django-browser-reload:** Automatically reloads the browser when templates are changed.

## Architecture

### Project Structure

```
PharmacyOnDuty/
├── pharmacies/             # Main Django application
│   ├── management/
│   │   └── commands/     # Custom Django management commands (e.g., create_working_schedule)
│   ├── migrations/         # Database migrations
│   ├── models.py           # Database models (City, Pharmacy, WorkingSchedule)
│   ├── tasks.py            # Celery tasks (e.g., run_scraper)
│   ├── utils/              # Utility functions and web scrapers (run asynchronously with Celery)
│   │   ├── ankaraeo_scraper.py      # Scraper for Ankara Eczacılar Odası
│   │   ├── eskisehireo_scraper.py   # Scraper for Eskişehir Eczacılar Odası
│   │   ├── istanbul_saglik_scraper.py# Scraper for Istanbul İl Sağlık Müdürlüğü
│   │   ├── pharmacy_fetch.py        # Logic for fetching data from Google Places API
│   │   └── utils.py                 # General utility functions
│   ├── views.py            # API endpoints and views
│   ├── urls.py             # URL routing for the pharmacies app
│   ├───admin.py            # Django admin configuration
│   ├───apps.py             # App configuration
│   └── tests/              # Unit tests and regression tests
├── scripts/                # Utility and entrypoint scripts
│   ├── entrypoint.sh       # Container entrypoint with service wait logic
│   └── wait_for_services.py# Script to verify DB/Redis availability
├── theme/                  # Tailwind CSS configuration and static assets
│   ├── static/
│   │   └── css/
│   │       └── dist/       # Compiled CSS (generated by Tailwind)
│   │           └── styles.css
│   ├── static_src/         # Source files for Tailwind
│   │   ├── src/
│   │   │   └── styles.css  # Input CSS file for Tailwind
│   │   ├── package.json    # npm package configuration
│   │   └── package-lock.json
│   └── templates/          # HTML templates
│       ├── cookie_policy.html
│       ├── pharmacies.html # Main application template
│       ├── privacy_policy.html
│       └── terms_of_service.html
├── templates/              # Project-level templates
│   └── robots.txt
├── PharmacyOnDuty/         # Project-level settings and configuration
│   ├── asgi.py
│   ├── celery.py           # Celery configuration
│   ├── settings.py         # Django settings (database, API keys, etc.)
│   ├── sitemaps.py          # Sitemap configuration
│   ├── urls.py             # Project-level URL routing
│   └── wsgi.py
├── docker-compose.yml      # Docker Compose configuration (development)
├── docker-compose.prod.yml # Docker Compose configuration (production)
├── Dockerfile              # Dockerfile for building the Django container (development)
├── dockerfile.prod         # Dockerfile for building the Django container (production)
├── dockerfile.scraper      # Dockerfile for building the scraper (worker) container (production)
├── Dockerfile.postgis      # Dockerfile for building the PostGIS container
├── Dockerfile.osrm         # Dockerfile for building the OSRM container (commented out)
├── manage.py               # Django management script
├── nginx.conf              # Nginx configuration for production
├── Procfile                # Procfile for Heroku deployment
├── pyproject.toml          # Python dependencies and project metadata (uv)
├── uv.lock                 # Locked dependency versions (uv)
├── readme.md               # This file
├── remotedev_nginx.conf.template # Nginx configuration for remote development
└── setup-postgis.sh          # Script for setting up PostGIS extensions
```

### Key Components and Workflow

1.  **Data Collection (Scraping and APIs):**

    *   **Web Scrapers:** The `pharmacies/utils` directory contains custom web scrapers (`ankaraeo_scraper.py`, `eskisehireo_scraper.py`, `istanbul_saglik_scraper.py`) that extract pharmacy data from the respective city pharmacy chamber websites. These scrapers are designed to handle the specific HTML structure of each website. Data is scraped on-demand when the data in the database is considered "old." The scrapers are run asynchronously using Celery to improve performance and overcome potential geoblocking issues.
    *   **Google Places API:** The `pharmacy_fetch.py` module utilizes the Google Places API's Nearby Search to find pharmacies near the user's location. This is used primarily when pharmacies are "open" (during regular business hours). Results are cached using `@lru_cache`.
    *   **Google Maps Geocoding API:** Used in `get_city_name_from_location` (within `utils.py`) to determine the user's city based on their latitude and longitude. This helps determine which city's on-duty pharmacy data to retrieve. Results are cached.
    *   **Google Maps Distance Matrix API:** Used to efficiently calculate travel distances and durations between the user's location and multiple pharmacies. This information is used to sort the pharmacy list by proximity. Results are cached.

2.  **Asynchronous Task Processing (Celery):**

    * Celery is used to run the web scrapers asynchronously. This improves the responsiveness of the web application and allows for offloading long-running scraping tasks to a separate worker process.
    * Redis is used as the message broker for Celery, facilitating communication between the Django application and the Celery workers.
    * The `pharmacies/tasks.py` file defines the Celery tasks, including the `run_scraper` task, which takes a city name as input and executes the corresponding scraper.
    *    Celery Beat is used for scheduling periodic tasks. The schedule is stored in the database using `django-celery-beat`.

3.  **Spatial Database (PostGIS):**

    *   **Data Models:** The `pharmacies/models.py` file defines three core models:
        *   `City`: Represents a city (e.g., "eskisehir," "istanbul," "ankara"). Stores the city name and the timestamp of the last successful data scrape. Includes methods to check pharmacy status and retrieve on-duty pharmacies.
        *   `WorkingSchedule`: Defines the regular opening and closing times for pharmacies in a specific city (weekday and Saturday hours). Has a one-to-one relationship with the `City` model. Includes methods to check if pharmacies are currently open.
        *   `Pharmacy`: Stores information about individual pharmacies, including name, location (as a PostGIS `PointField`), address, contact details, and duty start/end times (when applicable). Has a foreign key relationship with the `City` model.
    *   **Geospatial Queries:** GeoDjango and PostGIS enable efficient spatial queries, such as finding pharmacies within a certain radius of the user's location and ordering them by distance.

4.  **API Layer (Django Views):**

    *   **`get_pharmacy_points` (POST):** This is the primary API endpoint. It accepts the user's latitude and longitude as input.
        *   Determines the user's city using `get_city_name_from_location`.
        *   Checks the `City` model's `last_scraped_at` field to see if the on-duty pharmacy data needs to be refreshed (scraped again).
        *   If the data is old or the city is in "open" status, fetches updated data and updates/creates records in the database.
        *   Queries the database for the nearest on-duty pharmacies (if applicable) or uses the Google Places API to find open pharmacies.
        *   Calculates travel distances using the Google Maps Distance Matrix API.
        *   Returns a JSON response containing a list of pharmacy data, including location, name, address, status, and travel distance.
    *   **`google_maps_proxy` (GET):** A proxy endpoint for the Google Maps JavaScript API. This is used to avoid exposing the API key directly in the client-side code and to implement caching. It checks the `Referer` header to prevent unauthorized use.

5.  **Frontend Interface (HTML/CSS/JavaScript):**

    *   **Interactive Map:** The Google Maps JavaScript API is used to display an interactive map centered on the user's location. Markers are added for the user's location and the nearest pharmacies.
    *   **Pharmacy List:** The list of pharmacies is dynamically generated using JavaScript based on the API response. Each pharmacy item displays relevant information and includes a button to get directions.
    *   **Swipeable Bottom Sheet:** The pharmacy list is presented in a bottom sheet that can be expanded or collapsed by clicking or swiping (using Hammer.js).
    *   **Responsive Design:** Tailwind CSS is used to create a responsive layout that adapts to different screen sizes.

6.  **Infrastructure:**

    *   **Docker and Docker Compose:** The application is containerized using Docker, making it easy to deploy and run consistently across different environments. Docker Compose is used to define and manage the multi-container setup (Django, PostgreSQL/PostGIS, and potentially OSRM – though OSRM is currently commented out).
    *   **Heroku:** The production environment is hosted on Heroku. The `Procfile` specifies the commands to run the web server (Gunicorn) and perform database migrations.
    *   **WhiteNoise:** Static files (CSS, JavaScript, images) are served efficiently using WhiteNoise.
    *   **Sentry:** Sentry is integrated for error tracking and monitoring.

7.  **Service Readiness and Startup Synchronization:**

    To prevent "Temporary failure in name resolution" errors during container orchestration, a custom `wait_for_services.py` script runs before migrations or application startup. This script verifies that both PostgreSQL and Redis are accepting connections, providing a robust startup sequence in both development and production environments.

## Setup and Installation


### Prerequisites

*   **Git:** For cloning the repository.
*   **Python 3.13:** The required Python version.
*   **uv:** Modern Python package installer and environment manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/)).
*   **Docker (and Docker Compose):** For running the application in containers (recommended).
*   **A Google Maps API Key:** Required for using the Google Maps services.
*   **A Sentry DSN (Optional):** Required for using Sentry.

### Steps

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/pharmacyonduty.git  # Replace with your repository URL
    cd pharmacyonduty
    ```

2.  **Install uv (if not already installed):**

    ```bash
    # On macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # On Windows
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

3.  **Install Dependencies:**

    ```bash
    uv sync
    ```

    This will create a virtual environment in `.venv` and install all dependencies from `pyproject.toml`.

4.  **Set Environment Variables:**

   Create a `.env` file in the project root directory (or set these variables directly in your environment, for example in `docker-compose.yml` for Docker-based setups). See the [Environment Variables](#environment-variables) section for details.  Make sure to set `REDIS_PASSWORD` to a secure password.

5. **Database Setup:**

    *   **Without Docker:**
        *   Make sure you have PostgreSQL and PostGIS installed and running.
        *   Create a database and user with the credentials specified in your `.env` file.
        *   Enable the PostGIS extension on the database: `CREATE EXTENSION postgis;`
    *   **With Docker (Recommended):**
        *   Docker Compose will handle the database setup automatically.

6.  **Apply Database Migrations:**

    ```bash
    uv run python manage.py migrate
    ```

7.  **Create a Superuser (Optional):**

    ```bash
    uv run python manage.py createsuperuser
    ```

8.  **Add Cities and Working Schedules:**

    You'll need to populate the `City` and `WorkingSchedule` models with data for the supported cities. You can do this via the Django admin interface (after creating a superuser) or by using a custom management command (like the provided `create_working_schedule.py` example, which you'd need to adapt/extend for other cities). For example, to use `create_working_schedule.py`, run:

    ```bash
    uv run python manage.py create_working_schedule
    ```

9. **Run the Development Server:**

    *   **Without Docker:**

        ```bash
        uv run python manage.py runserver 0.0.0.0:8000
        ```

    *   **With Docker Compose (Recommended):**

        ```bash
        docker-compose up --build
        ```
      This command builds the Docker images (if necessary) and starts the containers defined in `docker-compose.yml`.

    For production, use `docker-compose.prod.yml`:

    ```bash
    # On the main server (runs all services except the Celery worker)
     docker-compose -f docker-compose.prod.yml up --build -d --no-deps django db nginx redis certbot beat

    # On the worker server (runs only the Celery worker)
     docker-compose -f docker-compose.prod.yml up --build -d --no-deps worker
    ```
> Note: Before running these commands, ensure that the necessary environment variables are set, especially `DJANGO_SETTINGS_MODULE` for the worker, and that the dockerfiles (`dockerfile.prod` and `Dockerfile.scraper`) are correctly configured.

    In both cases, the application will be accessible at `http://localhost:8000`. With Docker, the database will be accessible at `http://localhost:5432`, and debugpy will be accessible at `http://localhost:5678`.

### Remote Development Setup (docker-compose.remotedev.yml)

For remote development and debugging within Docker containers, use the `docker-compose.remotedev.yml` file. This configuration includes settings for remote debugging with `debugpy`.

1.  **Generate SSL Certificates:**

    Run this command on your host machine (not inside a container) to generate self-signed SSL certificates for local HTTPS development. This is necessary because the application uses HTTPS, and the browser will not allow insecure connections to localhost. Your own server IP address should be specified in command!

    ```bash
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout private/nginx-selfsigned.key \
      -out certs/nginx-selfsigned.crt \
      -subj "/CN=XXX.XXX.XXX.XXX"
    ```

2.  **Create `remotedev_nginx.conf`:**

    Create a file named `remotedev_nginx.conf` in the project root directory using the `remotedev_nginx.conf.template` as a template:

    ```
    cp remotedev_nginx.conf.template remotedev_nginx.conf
    ```

    Open `remotedev_nginx.conf` and replace `XXX.XXX.XXX.XXX` with your server's public IP address in both `server_name` directives.

3.  **Run with Remote Development Compose File:**

    ```bash
    docker-compose -f docker-compose.remotedev.yml up --build
    ```

This will start the application with the remote debugging configuration. You can then attach a debugger (like VS Code's debugger) to the running container on port 5678.

## Production Deployment (HTTPS with Docker, Nginx, and Let’s Encrypt)

This section explains how to run the application in a production setting using docker-compose.prod.yml. It also covers configuring Nginx as a reverse proxy and obtaining an SSL certificate with Certbot for eczanerede.com.

1.  **Prerequisites**

    -   **Domain Name:** You must own a domain (e.g., eczanerede.com) pointing to the IP of your server.
    -   **DNS Config:** An A-record or CNAME pointing eczanerede.com and (optionally) www.eczanerede.com to your server’s public IP.
    -   **Ports:** Make sure ports 80 (HTTP) and 443 (HTTPS) are open on your server/firewall.
    -   **Docker + Docker Compose:** installed on your server.

2.  **Ensure Your docker-compose.prod.yml Is Set for Production**

    A sample docker-compose.prod.yml might contain services for:

    -   django (running Gunicorn on port 8000 internally),
    -   db (PostgreSQL with PostGIS),
    -   nginx (serving on ports 80 and 443),
    -   certbot (for Let’s Encrypt).

    Example snippet (abridged):

    ```yaml
    version: '3.8'

    services:
      django:
        build:
          context: .
          dockerfile: dockerfile.prod
        depends_on:
          - db
        environment:
          - DB_HOST=db
          - DJANGO_DEBUG=False
        command: >
          sh -c "uv run python manage.py collectstatic --noinput &&
                 uv run gunicorn PharmacyOnDuty.wsgi:application --bind 0.0.0.0:8000"

      db:
        build:
          context: .
          dockerfile: Dockerfile.postgis
        environment:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
          POSTGRES_DB: gis

      nginx:
        image: nginx:alpine
        depends_on:
          - django
        # Expose both HTTP and HTTPS
        ports:
          - "80:80"
          - "443:443"
        # Mount config and cert volumes
        volumes:
          - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
          - ./certbot_webroot:/var/www/certbot
          - ./certbot_letsencrypt:/etc/letsencrypt:ro

      certbot:
        image: certbot/certbot
        volumes:
          - ./certbot_webroot:/var/www/certbot
          - ./certbot_letsencrypt:/etc/letsencrypt
        # No entrypoint here until we do the initial issuance
        # entrypoint: ...
    ```

3.  **Create & Mount the Folders for Certbot**

    On your server (in the project directory):

    ```bash
    mkdir -p certbot_webroot certbot_letsencrypt
    ```

    -   `certbot_webroot` is where Let’s Encrypt’s HTTP-01 challenge files go.
    -   `certbot_letsencrypt` is where your certificates (fullchain + privkey) will be stored.

4.  **Minimal nginx.conf for Production**

    Below is a sample nginx.conf you could commit to version control. It serves two server blocks: one for HTTP (port 80) to allow ACME challenges and redirect to HTTPS, and one for HTTPS on port 443.

    ```nginx
    server {
        listen 80;
        server_name eczanerede.com www.eczanerede.com;

        # Serve Let’s Encrypt ACME challenges from /var/www/certbot
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # (Optional) Redirect everything else on port 80 to HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name eczanerede.com www.eczanerede.com;

        # These will be populated by Certbot
        ssl_certificate /etc/letsencrypt/live/eczanerede.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/eczanerede.com/privkey.pem;

        # Basic security headers (optional)
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header X-XSS-Protection "1; mode=block";

        # Proxy requests to Django
        location / {
            proxy_pass http://django:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Serve ACME challenges on port 443 as well (not strictly required)
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
    }
    ```

5.  **Build and Start Containers (HTTP-Only First)**

    Before obtaining a certificate, comment out the HTTPS parts or keep them but point to a dummy certificate. For instance, just remove `listen 443 ssl;` lines until you fetch real certs:

    1.  ```bash
        docker-compose -f docker-compose.prod.yml up -d --build
        ```
    2.  Check logs:

        ```bash
        docker-compose logs -f
        ```

        Make sure django, db, and nginx all start without errors.

    At this point, you should be able to reach `http://eczanerede.com` (port 80). If that works, proceed.

6.  **Obtain the Let’s Encrypt Certificate**

    1.  Stop any looping certbot container if it’s in your file:

        ```bash
        docker-compose -f docker-compose.prod.yml stop certbot
        ```

    2.  Run a one-time issuance:

        ```bash
        docker-compose -f docker-compose.prod.yml run --rm certbot \
          certonly \
          --webroot \
          --webroot-path /var/www/certbot \
          -d eczanerede.com -d www.eczanerede.com \
          --email <YOUR_EMAIL> \
          --agree-tos \
          --no-eff-email \
          -v
        ```

        If it succeeds, you’ll see “Successfully received certificate” and the cert files appear in `./certbot_letsencrypt/live/eczanerede.com/`.

7.  **Re-Enable HTTPS in Nginx**

    Now that you have real certificate files, uncomment or update your `nginx.conf` lines for SSL:

    ```
    server {
        listen 443 ssl;
        server_name eczanerede.com www.eczanerede.com;

        ssl_certificate /etc/letsencrypt/live/eczanerede.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/eczanerede.com/privkey.pem;

        ...
    }
    ```

    Expose port 443 in `docker-compose.prod.yml`:

    ```
    nginx:
      ports:
        - "80:80"
        - "443:443"
    ```

    Then redeploy:

    ```bash
    docker-compose -f docker-compose.prod.yml up -d --build
    ```

    Visit `https://eczanerede.com`—you should now have a valid SSL certificate.

8.  **(Optional) Automatic Certificate Renewal**

    To keep your certificate from expiring, add back a looping entrypoint for Certbot:

    ```yaml
    certbot:
      image: certbot/certbot
      volumes:
        - ./certbot_webroot:/var/www/certbot
        - ./certbot_letsencrypt:/etc/letsencrypt
      entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    ```

    Then run:

    ```bash
    docker-compose -f docker-compose.prod.yml up -d certbot
    ```

    This container will periodically run `certbot renew`, and as long as port 80 is still accessible and Nginx is configured to serve `/.well-known/acme-challenge/`, renewals will happen automatically.

    That’s it! Your application is now served securely via HTTPS at eczanerede.com.

## Environment Variables

The following environment variables are used to configure the application:

| Variable Name             | Description                                                                                                                                                                                                                            | Default Value | Required |
| :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------ | :------- |
| `DJANGO_SECRET_KEY`       | A secret key used by Django for cryptographic signing. **This should be a long, random, and unpredictable value.**                                                                                                                   |               | Yes      |
| `DJANGO_DEBUG`            | A boolean value indicating whether Django is in debug mode. Set to `True` for development and `False` for production.                                                                                                                | `True`        | Yes      |
| `GOOGLE_MAPS_API_KEY`     | Your Google Maps API key.                                                                                                                                                                                                             |               | Yes      |
| `DB_NAME`                 | The name of the PostgreSQL database.                                                                                                                                                                                                  | `postgres`    | Yes      |
| `DB_USER`                 | The username for the PostgreSQL database.                                                                                                                                                                                               | `postgres`    | Yes      |
| `DB_PASSWORD`             | The password for the PostgreSQL database.                                                                                                                                                                                               | `password`    | Yes      |
| `DB_HOST`                 | The hostname or IP address of the PostgreSQL database server. Use `localhost` if running without Docker, `db` for Docker Compose.                                                                                                      | `db`          | Yes      |
| `DB_PORT`                 | The port number of the PostgreSQL database server.                                                                                                                                                                                      | `5432`        | Yes      |
| `SENTRY_DSN`              | Your Sentry DSN (Data Source Name) for error tracking.                                                                                                                                                                                 |               | No       |
| `DJANGO_ALLOWED_HOSTS`   | A list of allowed hostnames for the Django application. Add your domain in production.                                                                                                                                                 | `localhost`   | Yes      |
| `ALLOWED_REFERERS`        | A list of allowed referrers for the Google Maps proxy. Add your domain in production.                                                                                                                                                  |               | Yes      |
| `REMOTE_DEBUGGING_PORT` | The port number for remote debugging with `debugpy`.                                                                                                                                                                                    | `5678`        | No       |
| `REDIS_PASSWORD`          | The password for Redis. Required for both the Redis server and Celery to connect.                                                                                                                                                  |               | Yes      |

## Testing

To run the tests, use the following command:

```bash
uv run python manage.py test
```

The project maintains a comprehensive test suite with high code coverage (>90%). It uses `pytest` and `coverage` to ensure reliability. Contributions should include tests to maintain this standard.

## Contributing

Contributions are welcome! Here's how you can contribute:

1.  **Fork the repository.**
2.  **Create a new branch:** `git checkout -b feature/your-feature-name`
3.  **Make your changes and commit them:** `git commit -m "Add your commit message"`
4.  **Push to the branch:** `git push origin feature/your-feature-name`
5.  **Create a Pull Request.**

Please follow these guidelines:

*   **Code Style:** Follow PEP 8 for Python code. Use Black for automatic code formatting.
*   **Testing:** Include tests for new features or bug fixes. Run tests with `uv run python manage.py test`.
*   **Commit Messages:** Write clear and concise commit messages. Explain the purpose of your changes.
*   **Pull Requests:** Keep your pull requests focused on a single feature or bug fix. Provide a clear description of the changes and any relevant context.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact:

Onur Akyüz
onur_akyuz@icloud.com
