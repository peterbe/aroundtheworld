#!/usr/bin/env python

import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here


if __name__ == '__main__':
    from core.models import *
    from admin.models import *
    from pymongo.objectid import InvalidId, ObjectId

    import settings
    db = connection[settings.DATABASE_NAME]
    print "AVAILABLE:"
    print '\n'.join(['\t%s'%x for x in sorted(locals().keys(),
                       lambda x, y: cmp(x.lower(), y.lower()))
                     if re.findall('[A-Z]\w+|db|con', x)])
    print "Database available as 'db'"
    code.interact(local=locals())
