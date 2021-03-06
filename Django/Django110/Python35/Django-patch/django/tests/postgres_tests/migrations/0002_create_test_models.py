# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from ..fields import (
    ArrayField, BigIntegerRangeField, DateRangeField, DateTimeRangeField,
    FloatRangeField, HStoreField, IntegerRangeField, JSONField,
    SearchVectorField,
)
from ..models import TagField


class Migration(migrations.Migration):

    dependencies = [
        ('postgres_tests', '0001_setup_extensions'),
    ]

    operations = [
        migrations.CreateModel(
            name='CharArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.CharField(max_length=10), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DateTimeArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datetimes', ArrayField(models.DateTimeField(), size=None)),
                ('dates', ArrayField(models.DateField(), size=None)),
                ('times', ArrayField(models.TimeField(), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HStoreModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', HStoreField(blank=True, null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OtherTypesArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ips', ArrayField(models.GenericIPAddressField(), size=None)),
                ('uuids', ArrayField(models.UUIDField(), size=None)),
                ('decimals', ArrayField(models.DecimalField(max_digits=5, decimal_places=2), size=None)),
                ('tags', ArrayField(TagField(), blank=True, null=True, size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.IntegerField(), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NestedIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(ArrayField(models.IntegerField(), size=None), size=None)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NullableIntegerArrayModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', ArrayField(models.IntegerField(), size=None, null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CharFieldModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.CharField(max_length=16)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='TextFieldModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.TextField()),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='Scene',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scene', models.CharField(max_length=255)),
                ('setting', models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options=None,
            bases=None,
        ),
        migrations.CreateModel(
            name='Line',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scene', models.ForeignKey('postgres_tests.Scene', on_delete=models.SET_NULL)),
                ('character', models.ForeignKey('postgres_tests.Character', on_delete=models.SET_NULL)),
                ('dialogue', models.TextField(blank=True, null=True)),
                ('dialogue_search_vector', SearchVectorField(blank=True, null=True)),
                ('dialogue_config', models.CharField(max_length=100, blank=True, null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=None,
        ),
        migrations.CreateModel(
            name='AggregateTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('boolean_field', models.NullBooleanField()),
                ('char_field', models.CharField(max_length=30, blank=True)),
                ('integer_field', models.IntegerField(null=True)),
            ]
        ),
        migrations.CreateModel(
            name='StatTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('int1', models.IntegerField()),
                ('int2', models.IntegerField()),
                ('related_field', models.ForeignKey(
                    'postgres_tests.AggregateTestModel',
                    models.SET_NULL,
                    null=True,
                )),
            ]
        ),
        migrations.CreateModel(
            name='NowTestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('when', models.DateTimeField(null=True, default=None)),
            ]
        ),
        migrations.CreateModel(
            name='RangesModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ints', IntegerRangeField(null=True, blank=True)),
                ('bigints', BigIntegerRangeField(null=True, blank=True)),
                ('floats', FloatRangeField(null=True, blank=True)),
                ('timestamps', DateTimeRangeField(null=True, blank=True)),
                ('dates', DateRangeField(null=True, blank=True)),
            ],
            options={
                'required_db_vendor': 'postgresql'
            },
            bases=(models.Model,)
        ),
        migrations.CreateModel(
            name='RangeLookupsModel',
            fields=[
                ('parent', models.ForeignKey(
                    'postgres_tests.RangesModel',
                    models.SET_NULL,
                    blank=True, null=True,
                )),
                ('integer', models.IntegerField(blank=True, null=True)),
                ('big_integer', models.BigIntegerField(blank=True, null=True)),
                ('float', models.FloatField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
                ('date', models.DateField(blank=True, null=True)),
            ],
            options={
                'required_db_vendor': 'postgresql',
            },
            bases=(models.Model,),
        ),
    ]

    pg_94_operations = [
        migrations.CreateModel(
            name='JSONModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', JSONField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        try:
            PG_VERSION = schema_editor.connection.pg_version
        except AttributeError:
            pass  # We are probably not on PostgreSQL
        else:
            if PG_VERSION >= 90400:
                self.operations = self.operations + self.pg_94_operations
        return super(Migration, self).apply(project_state, schema_editor, collect_sql)
