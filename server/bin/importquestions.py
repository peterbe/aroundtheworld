#!/usr/bin/env python

import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

from pprint import pprint
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

def unicode_csv_reader(unicode_csv_data,
                       encoding='utf-8',
                       **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data, encoding),
                             **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, encoding) for cell in row]

def utf_8_encoder(unicode_csv_data, encoding):
    for line in unicode_csv_data:
        yield line.encode(encoding)

def parse_questions(file_name, encoding='utf8'):
    csv_file = codecs.open(file_name, 'r', encoding)
    #reader = csv.reader(csv_file)
    reader = unicode_csv_reader(csv_file, encoding, delimiter='\t')

    for row in reader:
        if row[0] == 'CODE':
            continue
        yield row

    csv_file.close()

if __name__ == '__main__':
    from models import *
    from pymongo.objectid import InvalidId, ObjectId

    import settings
    db = connection[settings.DATABASE_NAME]
    import sys, os
    args = sys.argv[1:]
    if '--verbose' in args:
        args.remove('--verbose')
        verbose = True
    elif '-v' in args:
        args.remove('-v')
        verbose = True
    else:
        verbose = False

    filename = os.path.abspath(args[0])

    for row in parse_questions(filename):
        (code, __, text, correct,
         alt1, alt2, alt3, alt4, alt_ordered,
         points_value, _id) = row
        if _id:
            question = db.Question.find_one({'_id': ObjectId(_id)})
        else:
            question = db.Question()
        location = db.Location.find_one({'code': code.upper()})
        if question['location'] != location['_id']:
            question['location'] = location['_id']
        question['text'] = text.strip()
        if correct.lower() in ('true', 'false'):
            correct = correct.capitalize()
        question['correct'] = correct
        if alt1.lower() in ('true', 'false'):
            alt1 = alt1.capitalize()
        if alt2.lower() in ('true', 'false'):
            alt2 = alt2.capitalize()
        alternatives = [x.strip() for x in (alt1, alt2, alt3, alt4)
                        if x.strip()]
        question['alternatives'] = alternatives
        if correct not in alternatives:
            print "ERROR",
            print repr(correct), "not in alternatives", repr(alternatives)
        #print alternatives
        points_value = int(points_value)
        if verbose:
            d = dict(question)
            del d['add_date']
            del d['modify_date']
            pprint(d)
            if raw_input('Save? [Y/n] ').strip().lower() == 'n':
                print "SKIP"
                continue
        question.save()
