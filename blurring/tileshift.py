import os, sys
sys.path.insert(0, os.path.abspath('../server/admin/handlers'))
import picture_factory

def run(original, iterations):
    for i, (im, format) in enumerate(picture_factory.tileshift(original, (330, 330), int(iterations))):
        dest = os.path.basename(original)
        dest = dest.replace('.', '.%s.' % (i+1))
        dest = os.path.join('tileshifted', dest)
        im.save(dest)

if __name__=='__main__':
    run(*sys.argv[1:])
