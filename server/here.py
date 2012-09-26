import sys, site, os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)
prev_sys_path = list(sys.path)
site.addsitedir(path('vendor'))
site.addsitedir(path('vendor/lib/python'))

# Move the new items to the front of sys.path. (via virtualenv)
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
    sys.path[:0] = new_sys_path
