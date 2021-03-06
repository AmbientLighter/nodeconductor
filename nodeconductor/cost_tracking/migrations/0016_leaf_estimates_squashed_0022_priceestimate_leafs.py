# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-02-28 13:09
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import nodeconductor.core.fields


class Migration(migrations.Migration):

    replaces = [('cost_tracking', '0016_leaf_estimates'), ('cost_tracking', '0017_nullable_object_id'), ('cost_tracking', '0018_priceestimate_threshold'), ('cost_tracking', '0019_priceestimate_limit'), ('cost_tracking', '0020_reset_price_list_item'), ('cost_tracking', '0021_delete_applicationtype'), ('cost_tracking', '0022_priceestimate_leafs')]

    dependencies = [
        ('structure', '__latest__'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('cost_tracking', '0015_defaultpricelistitem_metadata'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='priceestimate',
            name='consumed',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='priceestimate',
            name='scope_customer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='structure.Customer'),
        ),
        migrations.AlterField(
            model_name='priceestimate',
            name='content_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='priceestimate',
            name='object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='priceestimate',
            name='threshold',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='priceestimate',
            name='limit',
            field=models.FloatField(default=-1),
        ),
        migrations.AlterUniqueTogether(
            name='pricelistitem',
            unique_together=set([]),
        ),
        migrations.DeleteModel(
            name='PriceListItem',
        ),
        migrations.CreateModel(
            name='PriceListItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('value', models.DecimalField(decimal_places=5, default=0, max_digits=11, verbose_name='Hourly rate')),
                ('units', models.CharField(blank=True, max_length=255)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('default_price_list_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cost_tracking.DefaultPriceListItem')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='pricelistitem',
            unique_together=set([('content_type', 'object_id', 'default_price_list_item')]),
        ),
        migrations.DeleteModel(
            name='ApplicationType',
        ),
        migrations.AddField(
            model_name='priceestimate',
            name='leafs',
            field=models.ManyToManyField(related_name='_priceestimate_leafs_+', to=b'cost_tracking.PriceEstimate'),
        ),
    ]
