from dateutil.parser import parse as parse_date
from segment_source import get_source
from dateutil.tz import tzlocal
from pydash import omit
import datetime

source = get_source()

def serialize_datetime(timestamp):
    if isinstance(timestamp, datetime.date):
        date = timestamp
    else:
        date = parse_date(timestamp)

    with_timezone = date.replace(tzinfo=date.tzinfo or tzlocal())
    timestring = with_timezone.isoformat()

    return timestring

class Resource:
    _parser_map = {
        'string': str,
        'float': float,
        'integer': int,
        'datetime': serialize_datetime
    }

    def __init__(self, collection, fetch, schema, parent=None, transform=None):
        # Validations ->
        # Prefer custom validation exceptions to assertions? These are mainly
        # to prevent developer errors so I thought they'd be a god .
        assert callable(fetch)
        # assert validate_schema(schema) ->
        # - Instance method (e.g. `self.validate_schema`)?
        # -- If so, call after assignment?
        assert callable(transform) or transform is None
        assert isinstance(parent, str) or parent is None

        self.collection = collection
        self.parent = parent

        self._fetch = fetch
        self._schema = schema
        self._transform = transform

    def fetch(self, seed):
        return self._fetch(seed)

    def transform(self, obj, seed=None):
        ret = {}

        if self._transform:
            obj = self._transform(obj, seed)

        for column, definition in self._schema.items():
            source_name = definition.get('api_name', column)
            source_value = obj.get(source_name)
            if source_value is None: continue

            if callable(definition['type']):
                parser_func = definition['type']
            elif definition['type'] in self._parser_map:
                parser_func = self._parser_map[definition['type']]
            else:
                raise ValueError("Invalid schema definition: {}".format(definition['type']))

            ret[column] = parser_func(source_value)

        return ret

    def set(self, obj):
        source.set(self.collection, obj['id'], omit(obj, 'id'))
