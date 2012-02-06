import logging
import datetime
import os
from time import mktime
import settings
import json
from tornado_utils.thumbnailer import get_thumbnail
import tornado.web


def _commafy(s):
    r = []
    for i, c in enumerate(reversed(str(s))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)


class Thousands(tornado.web.UIModule):

    def render(self, number):
        return _commafy(str(number))


class JSON(tornado.web.UIModule):

    def render(self, data):
        return tornado.escape.json_encode(data)


class QuestionPictureThumbnailMixin:

    def make_thumbnail(self, question_image, (max_width, max_height)):
        timestamp = int(mktime(question_image.modify_date.timetuple()))
        image = question_image.fs.get_last_version('original')
        if image.content_type == 'image/png':
            ext = '.png'
        elif image.content_type == 'image/jpeg':
            ext = '.jpg'
        elif image.content_type == 'image/gif':
            ext = '.gif'
        else:
            raise ValueError(
              "Unrecognized content_type %r" % image.content_type)
        path = (datetime.datetime.now()
                .strftime('%Y %m %d')
                .split())
        path.append('%s-%s-%s-%s%s' % (question_image._id,
                                       max_width, max_height,
                                       timestamp,
                                       ext))
        path.insert(0, settings.THUMBNAIL_DIRECTORY)
        path = os.path.join(*path)
        try:
            (width, height) = get_thumbnail(path, image.read(),
                                        (max_width, max_height))
        except IOError:
            logging.error("Unable to make thumbnail out of %r" % question_image,
                          exc_info=True)
            if max_width > 100 or max_height > 100:
                path = '/static/images/file_broken_large.png'
                width, height = (128, 128)
            else:
                path = '/static/images/file_broken_small.png'
                width, height = (20, 20)

        return path.replace(settings.ROOT, ''), (width, height)


class ShowQuestionPictureThumbnail(tornado.web.UIModule,
                                 QuestionPictureThumbnailMixin):
    def render(self, question_image, (max_width, max_height), alt="",
               return_json=False, return_args=False,
               **kwargs):
        uri, (width, height) = self.make_thumbnail(question_image,
                                                   (max_width, max_height))
        url = self.handler.static_url(uri.replace('/static/', ''))
        args = {'src': url, 'width': width, 'height': height, 'alt': alt}
        if (not question_image.render_attributes
          or kwargs.get('save_render_attributes', False)):
            question_image.render_attributes = args
            question_image.save()
        if return_args:
            return args
        args.update(kwargs)
        if return_json:
            return json.dumps(args)
        tag = ['<img']
        for key, value in args.items():
            tag.append('%s="%s"' % (key, value))
        tag.append('>')
        return ' '.join(tag)


class GetQuestionPictureThumbnailSrc(ShowQuestionPictureThumbnail):
    def render(self, *args, **kwargs):
        attrs = (super(GetQuestionPictureThumbnailSrc, self)
                       .render(*args, return_args=True, **kwargs))
        return attrs['src']
