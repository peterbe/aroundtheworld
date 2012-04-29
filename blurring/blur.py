import os, sys
sys.path.insert(0, os.path.abspath('../server/admin/handlers'))
import picture_factory

def run(original, iterations, effect):
    for i, (im, format) in enumerate(picture_factory.blurrer(original, (200, 200), int(iterations), int(effect))):
        dest = os.path.basename(original)
        dest = dest.replace('.', '.%s.' % i)
        dest = os.path.join('blurred', dest)
        im.save(dest)

if __name__=='__main__':
    run(*sys.argv[1:])
