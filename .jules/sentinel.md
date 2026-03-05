## 2025-12-30 - Missing GDAL prevents local GIS testing
**Vulnerability:** N/A (Environment issue)
**Learning:** Standard Django tests fail with `ImproperlyConfigured: Could not find the GDAL library` because the environment lacks PostGIS/GDAL binaries.
**Prevention:** Use mocking (`sys.modules`) to bypass GIS imports when testing non-GIS logic (like view decorators). Verify logic statically where possible.
