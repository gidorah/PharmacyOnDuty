# Eczanerede (Pharmacy Locator)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://example.com/build)  <!-- Placeholder for build status badge -->

Eczanerede is a mobile-first web application designed to help users quickly find open and on-duty pharmacies in Turkish cities. It currently supports Eskişehir, Istanbul, and Ankara, with plans for expansion. The application provides real-time status updates, location-based search, interactive maps with turn-by-turn directions, and estimated travel distances, all within a user-friendly, responsive interface.

**Live Website:** [eczanerede.com](https://eczanerede.com)

## Table of Contents

- [Eczanerede (Pharmacy Locator)](#eczanerede-pharmacy-locator)
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
* **requests**: Python HTTP library for making requests.
* **beautifulsoup4**: Library used for web scraping.
* **python-dotenv**: Library for managing .env files.

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
│   ├── utils/              # Utility functions and web scrapers
│   │   ├── ankaraeo_scraper.py      # Scraper for Ankara Eczacılar Odası
│   │   ├── eskisehireo_scraper.py   # Scraper for Eskişehir Eczacılar Odası
│   │   ├── istanbul_saglik_scraper.py# Scraper for Istanbul İl Sağlık Müdürlüğü
│   │   ├── pharmacy_fetch.py        # Logic for fetching data from Google Places API
│   │   └── utils.py                 # General utility functions
│   ├── views.py            # API endpoints and views
│   ├── urls.py             # URL routing for the pharmacies app
│   ├── admin.py            # Django admin configuration
│   ├── apps.py             # App configuration
│   └── tests.py            # Unit tests (currently empty)
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
│   ├── settings.py         # Django settings (database, API keys, etc.)
│   ├── sitemaps.py          # Sitemap configuration
│   ├── urls.py             # Project-level URL routing
│   └── wsgi.py
├── docker-compose.yml      # Docker Compose configuration (development)
├── docker-compose.prod.yml # Docker Compose configuration (production)
├── Dockerfile              # Dockerfile for building the Django container (development)
├── dockerfile.prod         # Dockerfile for building the Django container (production)
├── Dockerfile.postgis      # Dockerfile for building the PostGIS container
├── Dockerfile.osrm         # Dockerfile for building the OSRM container (commented out)
├── manage.py               # Django management script
├── Procfile                # Procfile for Heroku deployment
├── readme.md               # This file
├── requirements.txt        # Python dependencies
└── setup-postgis.sh          # Script for setting up PostGIS extensions
```

### Key Components and Workflow

1.  **Data Collection (Scraping and APIs):**

    *   **Web Scrapers:** The `pharmacies/utils` directory contains custom web scrapers (`ankaraeo_scraper.py`, `eskisehireo_scraper.py`, `istanbul_saglik_scraper.py`) that extract pharmacy data from the respective city pharmacy chamber websites. These scrapers are designed to handle the specific HTML structure of each website. Data is scraped on-demand when the data in the database is considered "old."
    *   **Google Places API:** The `pharmacy_fetch.py` module utilizes the Google Places API's Nearby Search to find pharmacies near the user's location. This is used primarily when pharmacies are "open" (during regular business hours). Results are cached using `@lru_cache`.
    *   **Google Maps Geocoding API:** Used in `get_city_name_from_location` (within `utils.py`) to determine the user's city based on their latitude and longitude. This helps determine which city's on-duty pharmacy data to retrieve. Results are cached.
    *   **Google Maps Distance Matrix API:** Used to efficiently calculate travel distances and durations between the user's location and multiple pharmacies. This information is used to sort the pharmacy list by proximity. Results are cached.

2.  **Spatial Database (PostGIS):**

    *   **Data Models:** The `pharmacies/models.py` file defines three core models:
        *   `City`: Represents a city (e.g., "eskisehir," "istanbul," "ankara"). Stores the city name and the timestamp of the last successful data scrape. Includes methods to check pharmacy status and retrieve on-duty pharmacies.
        *   `WorkingSchedule`: Defines the regular opening and closing times for pharmacies in a specific city (weekday and Saturday hours). Has a one-to-one relationship with the `City` model. Includes methods to check if pharmacies are currently open.
        *   `Pharmacy`: Stores information about individual pharmacies, including name, location (as a PostGIS `PointField`), address, contact details, and duty start/end times (when applicable). Has a foreign key relationship with the `City` model.
    *   **Geospatial Queries:** GeoDjango and PostGIS enable efficient spatial queries, such as finding pharmacies within a certain radius of the user's location and ordering them by distance.

3.  **API Layer (Django Views):**

    *   **`get_pharmacy_points` (POST):** This is the primary API endpoint. It accepts the user's latitude and longitude as input.
        *   Determines the user's city using `get_city_name_from_location`.
        *   Checks the `City` model's `last_scraped_at` field to see if the on-duty pharmacy data needs to be refreshed (scraped again).
        *   If the data is old or the city is in "open" status, fetches updated data and updates/creates records in the database.
        *   Queries the database for the nearest on-duty pharmacies (if applicable) or uses the Google Places API to find open pharmacies.
        *   Calculates travel distances using the Google Maps Distance Matrix API.
        *   Returns a JSON response containing a list of pharmacy data, including location, name, address, status, and travel distance.
    *   **`google_maps_proxy` (GET):** A proxy endpoint for the Google Maps JavaScript API. This is used to avoid exposing the API key directly in the client-side code and to implement caching. It checks the `Referer` header to prevent unauthorized use.

4.  **Frontend Interface (HTML/CSS/JavaScript):**

    *   **Interactive Map:** The Google Maps JavaScript API is used to display an interactive map centered on the user's location. Markers are added for the user's location and the nearest pharmacies.
    *   **Pharmacy List:** The list of pharmacies is dynamically generated using JavaScript based on the API response. Each pharmacy item displays relevant information and includes a button to get directions.
    *   **Swipeable Bottom Sheet:** The pharmacy list is presented in a bottom sheet that can be expanded or collapsed by clicking or swiping (using Hammer.js).
    *   **Responsive Design:** Tailwind CSS is used to create a responsive layout that adapts to different screen sizes.

5.  **Infrastructure:**

    *   **Docker and Docker Compose:** The application is containerized using Docker, making it easy to deploy and run consistently across different environments. Docker Compose is used to define and manage the multi-container setup (Django, PostgreSQL/PostGIS, and potentially OSRM – though OSRM is currently commented out).
    *   **Heroku:** The production environment is hosted on Heroku. The `Procfile` specifies the commands to run the web server (Gunicorn) and perform database migrations.
    *   **WhiteNoise:** Static files (CSS, JavaScript, images) are served efficiently using WhiteNoise.
    *   **Sentry:** Sentry is integrated for error tracking and monitoring.

## Setup and Installation


### Prerequisites

*   **Git:** For cloning the repository.
*   **Python 3.13:** The required Python version.
*   **pip:** Python package installer.
*   **Docker (and Docker Compose):** For running the application in containers (recommended).
*   **A Google Maps API Key:** Required for using the Google Maps services.
*   **A Sentry DSN (Optional):** Required for using Sentry.

### Steps

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/pharmacyonduty.git  # Replace with your repository URL
    cd pharmacyonduty
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**

    ```bash
    python3.13 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate    # On Windows
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Environment Variables:**

   Create a `.env` file in the project root directory (or set these variables directly in your environment, for example in `docker-compose.yml` for Docker-based setups). See the [Environment Variables](#environment-variables) section for details.

5. **Database Setup:**

    *   **Without Docker:**
        *   Make sure you have PostgreSQL and PostGIS installed and running.
        *   Create a database and user with the credentials specified in your `.env` file.
        *   Enable the PostGIS extension on the database: `CREATE EXTENSION postgis;`
    *   **With Docker (Recommended):**
        *   Docker Compose will handle the database setup automatically.

6.  **Apply Database Migrations:**

    ```bash
    python manage.py migrate
    ```

7.  **Create a Superuser (Optional):**

    ```bash
    python manage.py createsuperuser
    ```

8.  **Add Cities and Working Schedules:**

    You'll need to populate the `City` and `WorkingSchedule` models with data for the supported cities. You can do this via the Django admin interface (after creating a superuser) or by using a custom management command (like the provided `create_working_schedule.py` example, which you'd need to adapt/extend for other cities). For example, to use `create_working_schedule.py`, run:

    ```bash
    python manage.py create_working_schedule
    ```

9. **Run the Development Server:**

    *   **Without Docker:**

        ```bash
        python manage.py runserver 0.0.0.0:8000
        ```

    *   **With Docker Compose (Recommended):**

        ```bash
        docker-compose up --build
        ```
      This command builds the Docker images (if necessary) and starts the containers defined in `docker-compose.yml`.

    For production, use `docker-compose.prod.yml`:

    ```bash
     docker-compose -f docker-compose.prod.yml up --build
    ```

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

## Testing

To run the tests, use the following command:

```bash
python manage.py test
```

Currently, the test suite is minimal. Contributions to expand test coverage are highly encouraged.  When adding new features or fixing bugs, please include corresponding tests.

## Contributing

Contributions are welcome! Here's how you can contribute:

1.  **Fork the repository.**
2.  **Create a new branch:** `git checkout -b feature/your-feature-name`
3.  **Make your changes and commit them:** `git commit -m "Add your commit message"`
4.  **Push to the branch:** `git push origin feature/your-feature-name`
5.  **Create a Pull Request.**

Please follow these guidelines:

*   **Code Style:** Follow PEP 8 for Python code. Use Black for automatic code formatting.
*   **Testing:** Include tests for new features or bug fixes. Run tests with `python manage.py test`.
*   **Commit Messages:** Write clear and concise commit messages. Explain the purpose of your changes.
*   **Pull Requests:** Keep your pull requests focused on a single feature or bug fix. Provide a clear description of the changes and any relevant context.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact:

Onur Akyüz
onur_akyuz@icloud.com
