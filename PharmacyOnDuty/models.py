from django.db import models


class Pharmacy(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    address = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=False, blank=False)
    district = models.CharField(max_length=100, null=False, blank=False)
    phone = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField()
    website = models.URLField()
