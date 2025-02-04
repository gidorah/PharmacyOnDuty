from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # List the names of the URL patterns you want to include
        return [
            "home",
        ]

    def location(self, item):
        return reverse(item)
