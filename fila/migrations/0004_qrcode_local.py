# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-28 13:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fila', '0003_auto_20171228_1329'),
    ]

    operations = [
        migrations.AddField(
            model_name='qrcode',
            name='local',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='fila.Local', verbose_name='Local'),
        ),
    ]
