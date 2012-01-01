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
    reader = unicode_csv_reader(csv_file, encoding, delimiter=',')

    for row in reader:
        if row[0] == 'CODE':
            continue
        yield row

    csv_file.close()

def is_different(dict1, dict2):
    if not dict2:
        return True

    keys = ('text', 'alternatives', 'author', 'alternatives_sorted',
            'category', 'correct', 'location', 'points_value')
    for key in keys:
        v1 = dict1[key]
        v2 = dict2[key]
        if v1 != v2:
            return True

    return False

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

    default_category = db.Category.find_one({'name': 'Tour guide'})
    assert default_category
    _cats = dict((x['name'].lower().strip(), x['_id'])
                 for x in db.Category.find())

    for row in parse_questions(filename):
        category=None
        _id = None
        try:
            (code, __, text, correct,
             alt1, alt2, alt3, alt4, alt_ordered,
             points_value, category) = row[:11]
        except ValueError:
            print
            print row
            print len(row)
            print
            raise
        if len(row) == 12:
            _id = row[11]

        if category:
            category = _cats[category.lower().strip()]
        else:
            category = default_category['_id']

        text = text.strip()
        if not text.endswith('?'):
            text += '?'
            print "ADDING ? TO:", repr(text)

        if _id:
            question = db.Question.find_one({'_id': ObjectId(_id)})
        else:
            question = db.Question.find_one({'text': text})
            if not question:
                question = db.Question()

        if hasattr(question, '_id'):
            orig_question = dict(question)
        else:
            orig_question = None

        location = db.Location.find_one({'code': code.upper()})
        if not location:
            print "CODE", repr(code)
            raise ValueError("Unrecognized code %r" % code)
        if question['location'] != location['_id']:
            question['location'] = location['_id']
        question['text'] = text
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
        question['category'] = category
        if correct not in alternatives:
            print "ERROR",
            print repr(correct), "not in alternatives", repr(alternatives)
        #print alternatives
        points_value = int(points_value)
        question['points_value'] = points_value

        if not is_different(dict(question), orig_question):
            continue

        if verbose:
            d = dict(question)
            del d['add_date']
            del d['modify_date']
            print question['text']
            print "\tCorrect:", repr(question['correct'])
            print "\tAlternatives:", repr(question['alternatives'])
            print "\tLocation:", unicode(db.Location.find_one({'_id': question['location']}))
            print "\tCategory:", unicode(db.Category.find_one({'_id': question['category']}))
            print "\tPoints value:", question['points_value']

            i = raw_input('Save? [Y/a/n] ').strip().lower()
            if i == 'a':
                verbose = False
            elif i == 'n':
                print "SKIP"
                continue
        question.save()

    if verbose:
        print
        print "There are now", db.Question.find().count(), "questions!"
