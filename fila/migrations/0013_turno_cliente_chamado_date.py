# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-02-16 20:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fila', '0012_delete_telegramdispatcher'),
    ]

    operations = [
        migrations.AddField(
            model_name='turno',
            name='cliente_chamado_date',
            field=models.DateTimeField(editable=False, null=True),
        ),
    ]