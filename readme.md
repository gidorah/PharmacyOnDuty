# Eczanerede (Pharmacy Locator)

A mobile-first web application that helps users find open and on-duty pharmacies in Turkish cities (currently supporting Eskişehir, Istanbul, and Ankara). The application provides real-time directions and distance information to the nearest pharmacies.

Visit [eczanerede](https://eczanerede.com) for live website.

## Features

- Real-time pharmacy status tracking (open/on-duty)
- Location-based pharmacy search
- Interactive map with directions
- Travel distance estimates
- Mobile-responsive design
- Swipeable pharmacy list interface
- Cached API responses for better performance
- SEO optimized with sitemap.xml and meta tags

## Tech Stack

### Backend
- **Python 3.13**
- **Django 5.1.4** - Web framework
- **PostGIS** - Spatial database extension for PostgreSQL
- **GeoDjango** - Django's geographic framework
- **Gunicorn** - WSGI HTTP Server

### Frontend
- **HTML5/CSS3**
- **JavaScript**
- **Tailwind CSS** - Utility-first CSS framework
- **jQuery** - JavaScript library
- **Hammer.js** - Touch gestures library
- **Google Maps JavaScript API** - Maps and directions

### Database
- **PostgreSQL 15** with PostGIS extension

### DevOps & Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Heroku** - Cloud hosting platform
- **Sentry** - Error tracking
- **WhiteNoise** - Static file serving

### Development Tools
- **pre-commit** - Git hooks management
- **mypy** - Static type checking
- **black** - Code formatting
- **debugpy** - Remote debugging

## Architecture

### Project Structure
        PharmacyOnDuty/ 
        ├── pharmacies/ # Main application 
        │ └── views/ # API endpoints
        ├── models/ # Database models 
        ├── utils/ # Scrapers and utility functions 
        ├── theme/ # Tailwind CSS configuration 
        | └── static/ # CSS and JS files
        ├── templates/ # HTML templates 
        ├── static/ # Static files 
        └── PharmacyOnDuty/ # Project settings

### Key Components

1. **Data Collection Layer**
   - Scrapers for different city pharmacy websites
   - Google Places API integration
   - Geocoding services

2. **Spatial Database**
   - PostGIS for geographical queries
   - Pharmacy and City models
   - Working schedule management

3. **API Layer**
   - Pharmacy points endpoint
   - Google Maps proxy
   - Cached responses

4. **Frontend Interface**
   - Interactive map
   - Swipeable bottom sheet
   - Responsive design

5. **Infrastructure**
   - Docker containerization
   - PostgreSQL with PostGIS
   - Static file serving with WhiteNoise

## Setup and Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/pharmacyonduty.git
    cd pharmacyonduty
    ```

2. Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
    
3. Install dependencies:
    ```bash
    pip install -r requirements.txt

4. Set up environment variables:
   
   Use an .env file or add them to docker-compose.yml

    Environment Variables:
    - DJANGO_SECRET_KEY: Django secret key
    - DJANGO_DEBUG: Debug mode (True/False)
    - GOOGLE_MAPS_API_KEY: Google Maps API key
    - DB_NAME: Database name
    - DB_USER: Database user
    - DB_PASSWORD: Database password
    - DB_HOST: Database host
    - SENTRY_DSN: Sentry DSN (optional)
    - DJANGO_ALLOWED_HOSTS= www.example.com www.another.com
    - ALLOWED_REFERERS= http://localhost:8008/ htto://www.example.com #hosts that are allowed to access the API

5. Run with Docker Compose:
    ```bash
    docker-compose up --build
    ```  
## Contributing
- Fork the repository
- Create your feature branch (git checkout -b feature/AmazingFeature)
- Commit your changes (git commit -m 'Add some AmazingFeature')
- Push to the branch (git push origin feature/AmazingFeature)
- Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact
For any queries, please reach out to onur_akyuz@icloud.com