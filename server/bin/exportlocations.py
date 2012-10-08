#!/usr/bin/env python

import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

import csv
import codecs
from cStringIO import StringIO

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)


if __name__ == '__main__':
    from models import *
    from bson.objectid import ObjectId, InvalidId

    import settings
    db = connection[settings.DATABASE_NAME]
    import sys
    writer = UnicodeWriter(sys.stdout)

    categories = dict((x['_id'], x['name'])
                      for x in db.Category.find())

    def format(v):
        if ',' in v and v.replace(',', '').isdigit():
            # e.g. "2,000" becomes "'2,000"
            v = "'%s" % v
        return v

    def writerow(location):
        row = [
          location['city'],
          location['country'],
          str(location['lat']),
          str(location['lng']),
        ]

        row.append(location['locality'] if location['locality'] else '')
        row.append(location['code'] if location['code'] else '')
        row.append(location['airport_name'] if location['airport_name'] else '')
        row.append(str(location['_id']))
        writer.writerow(row)

    writer.writerow([
      'CITY',
      'COUNTRY',
      'LATITUDE',
      'LONGITUDE',
      'LOCALITY (optional)',
      'AIRPORT CODE (optional)',
      'AIRPORT NAME (optional)',
      'ID (optional)',
    ])

    #def write_row(location, question):
    for location in db.Location.find().sort([['country',1], ['city',1]]):
        writerow(location)
