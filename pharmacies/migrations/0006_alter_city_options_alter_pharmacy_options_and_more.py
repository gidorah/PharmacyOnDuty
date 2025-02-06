# Generated by Django 5.1.4 on 2025-02-06 08:06

import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0005_city_last_scraped_at'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='city',
            options={'verbose_name': 'City', 'verbose_name_plural': 'Cities'},
        ),
        migrations.AlterModelOptions(
            name='pharmacy',
            options={'verbose_name': 'Pharmacy', 'verbose_name_plural': 'Pharmacies'},
        ),
        migrations.AlterModelOptions(
            name='workingschedule',
            options={'verbose_name': 'Working Schedule', 'verbose_name_plural': 'Working Schedules'},
        ),
        migrations.AddIndex(
            model_name='pharmacy',
            index=django.contrib.postgres.indexes.GistIndex(fields=['location'], name='pharmacies__locatio_376bde_gist'),
        ),
        migrations.AddIndex(
            model_name='pharmacy',
            index=models.Index(fields=['duty_start'], name='pharmacies__duty_st_c731ef_idx'),
        ),
        migrations.AddIndex(
            model_name='pharmacy',
            index=models.Index(fields=['duty_end'], name='pharmacies__duty_en_d68779_idx'),
        ),
    ]
