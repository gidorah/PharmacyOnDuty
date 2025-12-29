from django.test import TestCase
from django.urls import reverse


class SitemapTests(TestCase):
    def test_sitemap_generation(self) -> None:
        """
        Test that the sitemap can be generated successfully.
        This test is expected to fail initially due to NoReverseMatch.
        """
        try:
            response = self.client.get(reverse("django.contrib.sitemaps.views.sitemap"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "<loc>")
        except Exception as e:
            # We want to explicitly catch the NoReverseMatch if it bubbles up,
            # but usually client.get catches it and returns 500 or raises it depending on test client setup.
            # However, for the purpose of the 'Red' phase, simply running this and seeing it fail is enough.
            raise e
