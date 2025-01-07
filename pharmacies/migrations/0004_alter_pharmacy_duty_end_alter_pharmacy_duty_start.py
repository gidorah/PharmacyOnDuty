from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacies", "0003_alter_pharmacy_address"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE pharmacies_pharmacy
                ALTER COLUMN duty_start TYPE timestamp with time zone
                USING (TIMESTAMP '1970-01-01' + duty_start::time),
                ALTER COLUMN duty_end TYPE timestamp with time zone
                USING (TIMESTAMP '1970-01-01' + duty_end::time);
            """,
            reverse_sql="""
                ALTER TABLE pharmacies_pharmacy
                ALTER COLUMN duty_start TYPE time without time zone
                USING (duty_start::time),
                ALTER COLUMN duty_end TYPE time without time zone
                USING (duty_end::time);
            """,
        ),
        migrations.AlterField(
            model_name="pharmacy",
            name="duty_start",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="pharmacy",
            name="duty_end",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
