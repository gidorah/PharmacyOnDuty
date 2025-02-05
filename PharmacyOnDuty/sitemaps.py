from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    def items(self):
        # List the names of the URL patterns you want to include
        return ["home", "terms_of_service", "privacy_policy", "cookie_policy"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == "home":
            return 0.8
        return 0.3

    def changefreq(self, item):
        if item == "home":
            return "daily"
        return "monthly"
