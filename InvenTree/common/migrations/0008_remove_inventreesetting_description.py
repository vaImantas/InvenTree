# Generated by Django 3.0.7 on 2020-10-19 13:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0007_colortheme'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventreesetting',
            name='description',
        ),
    ]