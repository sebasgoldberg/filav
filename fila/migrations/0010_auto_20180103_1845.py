# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-03 18:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fila', '0009_auto_20180103_1844'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='posto',
            options={'permissions': (('atender_clientes', 'Pode ocupar um posto e atender os clientes.'),), 'verbose_name': 'Posto', 'verbose_name_plural': 'Postos'},
        ),
    ]