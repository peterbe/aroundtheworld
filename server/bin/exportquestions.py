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
    from pymongo.objectid import InvalidId, ObjectId

    import settings
    db = connection[settings.DATABASE_NAME]
    import sys
    writer = UnicodeWriter(sys.stdout)

    def writerow(location, question):
        if location:
            row = [
              location['code'],
              unicode(location),
            ]
        else:
            row = [
              '', ''
            ]
        row.append(question['text'])
        row.append(question['correct'])
        row.extend(question['alternatives'])
        for i in range(4 - len(question['alternatives'])):
            row.append('')
        row.append(question['alternatives_sorted'] and 'true' or 'false')
        row.append(str(question['points_value']))
        row.append(str(question['_id']))
        writer.writerow(row)

    writer.writerow([
      'CODE',
      'CITY NAME (optional)',
      'QUESTION',
      'CORRECT',
      'ALTERNATIVE 1',
      'ALTERNATIVE 2',
      'ALTERNATIVE 3',
      'ALTERNATIVE 4',
      'ALTS. ORDERED',
      'POINTS VALUE',
      'ID (optional)'
    ])

    #def write_row(location, question):
    for location in db.Location.find().sort('code', 1):
        for question in (db.Question
                         .find({'location': location['_id']})
                         .sort('add_date', 1)):
            writerow(location, question)
