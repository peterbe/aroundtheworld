from cStringIO import StringIO
import PIL
from PIL import ImageFilter, Image


def blurrer(original, size, iterations, effect, sample=False):
    im = Image.open(original)
    format = im.format

    x, y = [float(v) for v in im.size]
    xr, yr = [float(v) for v in size]
    r = max(xr / x, yr / y)

    for i in range(iterations):
        for j in range(effect):
            im = im.filter(ImageFilter.BLUR)
        result = im.resize((int(round(x * r)), int(round(y * r))),
                   resample=Image.ANTIALIAS)
        yield result, format


def tileshift(original, size, iterations):
    im = Image.open(original)
    format = im.format

    x, y = [float(v) for v in im.size]
    xr, yr = [float(v) for v in size]
    r = max(xr / x, yr / y)
#    im = im.resize((int(round(x * r)), int(round(y * r))),
#                   resample=Image.ANTIALIAS)
    format = im.format

    for i in range(iterations):
#        print "I", i
        result = _chop(im, i)
        result = result.resize((int(round(x * r)), int(round(y * r))),
                   resample=Image.ANTIALIAS)
        yield result, format

## (LEFT, UPPER, RIGHT, LOWER)

def _chop(im, i):
    w, h = im.size

    if i % 2:
        op = left_to_right
        d = w
    else:
        op = top_to_bottom
        d = h
    im = op(im, d / (i / 2 + 2))
    return im

def left_to_right(im, width):
    regions = []
    w, h = im.size
    slices = w / width
    c = 0
    boxes = []
    for i in range(slices):
        box = (width * i, 0, width * (i + 1), h)
        region = im.crop(box)
        boxes.append(box)
        region.load()
        regions.append(region)
        c += width
    boxes.reverse()
    for box, region in zip(boxes, regions):
        im.paste(region, (box[0], box[1]))
    return im

def top_to_bottom(im, height):
    regions = []
    w, h = im.size
    slices = h / height
    c = 0
    boxes = []
    for i in range(slices):
        box = (0, height * i, w, height * (i + 1))
        region = im.crop(box)
        boxes.append(box)
        region.load()
        regions.append(region)
        c += height
    boxes.reverse()
    for box, region in zip(boxes, regions):
        im.paste(region, (box[0], box[1]))
    return im
