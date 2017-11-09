# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-09 17:39
from __future__ import unicode_literals

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('fila', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupChannels',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_name', models.CharField(max_length=100, verbose_name='Grupo')),
                ('channel_name', models.CharField(max_length=100, verbose_name='Canal')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Cliente',
            fields=[
            ],
            options={
                'indexes': [],
                'proxy': True,
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Funcionario',
            fields=[
            ],
            options={
                'indexes': [],
                'proxy': True,
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterField(
            model_name='posto',
            name='funcionario',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='fila.Funcionario', verbose_name='Funcionario'),
        ),
        migrations.AlterField(
            model_name='turno',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='turnos', to='fila.Cliente', verbose_name='Cliente'),
        ),
        migrations.AlterField(
            model_name='turno',
            name='estado',
            field=models.IntegerField(choices=[(0, 'Inicial'), (1, 'Na Fila'), (2, 'Cancelado'), (3, 'No Atendimento'), (4, 'Ausente'), (5, 'Atendido')], default=1),
        ),
        migrations.AlterUniqueTogether(
            name='groupchannels',
            unique_together=set([('group_name', 'channel_name')]),
        ),
    ]