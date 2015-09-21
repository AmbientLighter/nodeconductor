# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('iaas', '0047_refactor_application_type_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='last_usage_update_time',
            field=models.DateTimeField(default=datetime.datetime(2015, 9, 21, 7, 48, 17, 947642, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
