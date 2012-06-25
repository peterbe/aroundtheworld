#!/usr/bin/env python
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here


def main(*apps):

    if '--help' in apps:
        print ("python %s [app [, app2]] [--background] [--clear-all-first]"
               % __file__)
        return 0

    background = False
    if '--background' in apps:
        background = True
        apps = list(apps)
        apps.remove('--background')

    clear_all_first = False
    if '--clear-all-first' in apps:
        clear_all_first = True
        apps = list(apps)
        apps.remove('--clear-all-first')

    if not apps:
        apps = ['core']

    for app in apps:
        _indexes = __import__(app, globals(), locals(), ['indexes'], -1)
        runner = _indexes.indexes.run
        print '\n'.join(runner(clear_all_first=clear_all_first,
                               background=background))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
