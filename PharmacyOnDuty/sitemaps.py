"""
Sitemap configuration for SEO.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):  # type: ignore[type-arg]
    """
    Sitemap for static pages (Home, Privacy Policy, Terms, etc.).
    """

    priority = 0.5
    changefreq = "daily"

    def items(self) -> list[str]:
        """Return list of static route names."""
        return [
            "home",
            "privacy_policy",
            "terms_of_service",
            "cookie_policy",
        ]

    def location(self, item: str) -> str:
        """Return the URL for the given route name."""
        return reverse(item)


# class CitySitemap(Sitemap):
#     changefreq = "daily"
#     priority = 0.8
#
#     def items(self) -> QuerySet[City]:
#         return City.objects.all()
#
#     def location(self, obj: City) -> str:
#         return reverse("city_pharmacies", args=[obj.slug])
