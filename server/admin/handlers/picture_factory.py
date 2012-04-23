from cStringIO import StringIO
import PIL
from PIL import ImageFilter, Image


def blurrer(original, size, iterations, effect, sample=False):
    im = Image.open(original)
    format = im.format
    im.resize(size)
    for i in range(iterations):
        for j in range(effect):
            im = im.filter(ImageFilter.BLUR)
        yield (im, format)
