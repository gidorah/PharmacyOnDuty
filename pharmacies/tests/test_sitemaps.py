from django.test import TestCase
from django.urls import reverse


class SitemapTests(TestCase):
    def test_sitemap_generation(self) -> None:
        """
        Test that the sitemap can be generated successfully.
        """
        response = self.client.get(reverse("django.contrib.sitemaps.views.sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<loc>")
