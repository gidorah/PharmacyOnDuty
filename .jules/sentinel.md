
## $(date +%Y-%m-%d) - Fix Missing CSRF Protection on API Endpoint
**Vulnerability:** The API endpoint `get_pharmacy_points` was marked as `@csrf_exempt`, allowing Cross-Site Request Forgery (CSRF) attacks which could be exploited by external sites to abuse backend resources and Google Maps API quota.
**Learning:** Endpoints returning sensitive or resource-intensive data without user-specific state must still enforce CSRF to prevent abuse from third-party sites, especially when integrating with paid external services.
**Prevention:** Avoid using `@csrf_exempt` on POST endpoints. For AJAX-heavy frontends, inject the `{% csrf_token %}` tag into the base template to set the `csrftoken` cookie and ensure JavaScript global configuration (like `$.ajaxSetup`) correctly attaches the `X-CSRFToken` header to all requests.
