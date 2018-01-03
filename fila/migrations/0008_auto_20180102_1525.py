# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-02 15:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fila', '0007_posto_local'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posto',
            name='local',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postos', to='fila.Local', verbose_name='Local'),
        ),
    ]