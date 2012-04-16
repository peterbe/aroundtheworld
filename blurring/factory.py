from string import zfill
import os
import PIL
from PIL import ImageFilter, Image


if __name__ == '__main__':
    import sys
    filepath = sys.argv[1]
    iterations = int(sys.argv[2])
    times = int(sys.argv[3])
    path = os.path.dirname(filepath)
    a, b = os.path.splitext(os.path.basename(filepath))
    a += '_blurred'
    new_filepath = os.path.join(path, a + b)
    im = Image.open(filepath)
    for i in range(1, iterations + 1):
        #print i, times
        for j in range(times):
            im = im.filter(ImageFilter.BLUR)

        new_filepath = os.path.join(
          path,
          a + '_%sx%s' % (times, zfill(i, 2)) + b)
        print "\t", new_filepath
        im.save(new_filepath)
