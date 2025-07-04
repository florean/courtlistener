# Generated by Django 5.1.8 on 2025-07-01 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('favorites', '0011_alter_prayeravailability_options_noop'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenericCount',
            fields=[
                ('label', models.CharField(help_text="A namespaced identifier for the object and action being tracked. Use a consistent format like 'd.1234:view' for views on docket with ID 1234, or 'o.456:view' for views on opinion with ID 456.", max_length=255, primary_key=True, serialize=False, unique=True)),
                ('value', models.BigIntegerField(default=0, help_text='The number of times the action (e.g., view) has occurred for the object identified by the key.')),
            ],
            options={
                'verbose_name': 'Generic Counter',
                'verbose_name_plural': 'Generic Counters',
            },
        ),
    ]
