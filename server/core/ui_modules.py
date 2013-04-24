import cgi
import logging
import datetime
import os
import time
import settings
import json
from tornado_utils.thumbnailer import get_thumbnail
from tornado_utils.timesince import smartertimesince
import tornado.web


ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7

def commafy(s):
    r = []
    for i, c in enumerate(reversed(str(s))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)


class Thousands(tornado.web.UIModule):

    def render(self, number):
        return commafy(str(number))


class ShowMiles(Thousands):

    def render(self, number):
        number = super(ShowMiles, self).render(int(number))
        return "%s miles" % number


class ShowCoins(Thousands):

    def render(self, number):
        number = super(ShowCoins, self).render(int(number))
        if number == 1:
            return "1 coin"
        return "%s coins" % number


class ShowBriefMessageSafely(tornado.web.UIModule):

    def render(self, message, max_length):
        if len(message) > max_length:
            message = message[:max_length] + '...'
        return cgi.escape(message, True)


class JSON(tornado.web.UIModule):

    def render(self, data):
        return tornado.escape.json_encode(data)


class PictureThumbnailMixin:

    def make_thumbnail(self, question_image, (max_width, max_height), **kwargs):
        timestamp = int(time.mktime(question_image['modify_date'].timetuple()))
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
        if kwargs.get('crop'):
            filename = (
              '%s-%s-%s-cropped%s%s'
               % (question_image._id,
                  max_width, max_height,
                  timestamp,
                  ext)
            )
        else:
            filename = (
                '%s-%s-%s-%s%s'
                % (question_image._id,
                   max_width, max_height,
                   timestamp,
                   ext)
            )
        path.append(filename)
        path.insert(0, settings.THUMBNAIL_DIRECTORY)
        path = os.path.join(*path)
        try:
            (width, height) = get_thumbnail(
                path, image.read(),
                (max_width, max_height),
                **kwargs
            )
            assert os.path.isfile(path), path
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

    def get_thumbnail(self, question_image, (max_width, max_height), **kwargs):
        """wrapper on PictureThumbnailMixin.make_thumbnail() that uses
        a global object cache."""

        # with this trick, this mixin can be used for UIModules as well as
        # RequestHandlers
        redis_ = getattr(self, 'redis', None) or self.handler.redis
        cache_key = '%s%s%s' % (question_image['_id'], max_width, max_height)
        cache_key += str(kwargs)
        result = redis_.get(cache_key)
        # remember if redis returned anything, it'll be a JSON encoded list
        if result and 'file_broken' in result:
            result = None
        if result is None:
            logging.info('Thumbnail Cache miss')
            result = self.make_thumbnail(question_image, (max_width, max_height), **kwargs)

            if 'file_broken' in result[0]:
                _expires = 60  # to avoid repeating the same mistake over and over
            else:
                _expires = ONE_WEEK
            redis_.setex(cache_key, tornado.escape.json_encode(result), _expires)
        else:
            result = tornado.escape.json_decode(result)
        return result


class ShowPictureThumbnail(tornado.web.UIModule,
                           PictureThumbnailMixin):

    def render(self, question_image, (max_width, max_height), alt="",
               return_json=False, return_args=False,
               **kwargs):
        uri, (width, height) = self.get_thumbnail(
            question_image,
            (max_width, max_height),
            **kwargs
        )
        if kwargs.get('crop'):
            if width != max_width or height != max_height:
                logging.warn("Cropped failed (%s, %s)" % (width, height))

        url = self.handler.static_url(uri.replace('/static/', ''))
        args = {'src': url, 'width': width, 'height': height, 'alt': alt}
        if (not question_image['render_attributes']
          or kwargs.get('save_render_attributes', False)):
            question_image['render_attributes'] = args
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


class GetPictureThumbnailSrc(ShowPictureThumbnail):
    def render(self, *args, **kwargs):
        attrs = (super(GetPictureThumbnailSrc, self)
                       .render(*args, return_args=True, **kwargs))
        return attrs['src']


class ScriptTags(tornado.web.UIModule):

    def render(self, *uris, **attrs):
        if self.handler.application.settings['optimize_static_content']:
            module = self.handler.application.ui_modules['Static'](self.handler)
            return module.render(*uris, **attrs)

        html = []
        for each in uris:
            tag = '<script '
            if attrs.get('async'):
                tag += 'async '
            tag += 'src="%s"></script>' % self.handler.static_url(each)
            html.append(tag)
        return '\n'.join(html)


class LinkTags(tornado.web.UIModule):

    def render(self, *uris):
        if self.handler.application.settings['optimize_static_content']:
            module = self.handler.application.ui_modules['Static'](self.handler)
            return module.render(*uris)

        html = []
        for each in uris:
            html.append('<link href="%s" rel="stylesheet" type="text/css">' %
                         self.handler.static_url(each))
        return '\n'.join(html)


class TimeSince(tornado.web.UIModule):
    def render(self, date, date2=None):
        assert date
        return smartertimesince(date, date2)


class InlineCSS(tornado.web.UIModule):

    def render(self, *uris):
        module = self.handler.application.ui_modules['StaticInline'](self.handler)
        return module.render(*uris)
