from django.db import connection, models

from .fields import (
    ArrayField, BigIntegerRangeField, DateRangeField, DateTimeRangeField,
    FloatRangeField, HStoreField, IntegerRangeField, JSONField,
    SearchVectorField,
)


class Tag(object):
    def __init__(self, tag_id):
        self.tag_id = tag_id

    def __eq__(self, other):
        return isinstance(other, Tag) and self.tag_id == other.tag_id


class TagField(models.SmallIntegerField):

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return Tag(int(value))

    def to_python(self, value):
        if isinstance(value, Tag):
            return value
        if value is None:
            return value
        return Tag(int(value))

    def get_prep_value(self, value):
        return value.tag_id


class PostgreSQLModel(models.Model):
    class Meta:
        abstract = True
        required_db_vendor = 'postgresql'


class IntegerArrayModel(PostgreSQLModel):
    field = ArrayField(models.IntegerField())


class NullableIntegerArrayModel(PostgreSQLModel):
    field = ArrayField(models.IntegerField(), blank=True, null=True)


class CharArrayModel(PostgreSQLModel):
    field = ArrayField(models.CharField(max_length=10))


class DateTimeArrayModel(PostgreSQLModel):
    datetimes = ArrayField(models.DateTimeField())
    dates = ArrayField(models.DateField())
    times = ArrayField(models.TimeField())


class NestedIntegerArrayModel(PostgreSQLModel):
    field = ArrayField(ArrayField(models.IntegerField()))


class OtherTypesArrayModel(PostgreSQLModel):
    ips = ArrayField(models.GenericIPAddressField())
    uuids = ArrayField(models.UUIDField())
    decimals = ArrayField(models.DecimalField(max_digits=5, decimal_places=2))
    tags = ArrayField(TagField(), blank=True, null=True)


class HStoreModel(PostgreSQLModel):
    field = HStoreField(blank=True, null=True)


class CharFieldModel(models.Model):
    field = models.CharField(max_length=16)


class TextFieldModel(models.Model):
    field = models.TextField()

    def __str__(self):
        return self.field


# Scene/Character/Line models are used to test full text search. They're
# populated with content from Monty Python and the Holy Grail.
class Scene(models.Model):
    scene = models.CharField(max_length=255)
    setting = models.CharField(max_length=255)

    def __str__(self):
        return self.scene


class Character(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Line(PostgreSQLModel):
    scene = models.ForeignKey('Scene', models.CASCADE)
    character = models.ForeignKey('Character', models.CASCADE)
    dialogue = models.TextField(blank=True, null=True)
    dialogue_search_vector = SearchVectorField(blank=True, null=True)
    dialogue_config = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.dialogue or ''


class RangesModel(PostgreSQLModel):
    ints = IntegerRangeField(blank=True, null=True)
    bigints = BigIntegerRangeField(blank=True, null=True)
    floats = FloatRangeField(blank=True, null=True)
    timestamps = DateTimeRangeField(blank=True, null=True)
    dates = DateRangeField(blank=True, null=True)


class RangeLookupsModel(PostgreSQLModel):
    parent = models.ForeignKey(RangesModel, models.SET_NULL, blank=True, null=True)
    integer = models.IntegerField(blank=True, null=True)
    big_integer = models.BigIntegerField(blank=True, null=True)
    float = models.FloatField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)


# Only create this model for postgres >= 9.4
if connection.vendor == 'postgresql' and connection.pg_version >= 90400:
    class JSONModel(models.Model):
        field = JSONField(blank=True, null=True)
else:
    # create an object with this name so we don't have failing imports
    class JSONModel(object):
        pass


class ArrayFieldSubclass(ArrayField):
    def __init__(self, *args, **kwargs):
        super(ArrayFieldSubclass, self).__init__(models.IntegerField())


class AggregateTestModel(models.Model):
    """
    To test postgres-specific general aggregation functions
    """
    char_field = models.CharField(max_length=30, blank=True)
    integer_field = models.IntegerField(null=True)
    boolean_field = models.NullBooleanField()


class StatTestModel(models.Model):
    """
    To test postgres-specific aggregation functions for statistics
    """
    int1 = models.IntegerField()
    int2 = models.IntegerField()
    related_field = models.ForeignKey(AggregateTestModel, models.SET_NULL, null=True)


class NowTestModel(models.Model):
    when = models.DateTimeField(null=True, default=None)
