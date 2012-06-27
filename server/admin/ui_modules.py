import textwrap
import tornado.web
import tornado.escape
from tornado_utils.timesince import smartertimesince
from admin.utils import truncate_text


class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()


class ShowComment(tornado.web.UIModule):

    def render(self, comment):
        return tornado.escape.linkify(comment).replace('\n', '<br>\n')


class Truncate(tornado.web.UIModule):

    def render(self, text, characters):
        return tornado.escape.xhtml_escape(truncate_text(text, characters))


class SortArrow(tornado.web.UIModule):

    def render(self, key, sort_key, sort_order):
        return self.render_string("admin/_sort_arrow.html",
                                  key=key,
                                  sort_key=sort_key,
                                  sort_order=sort_order)

class TextWrap(tornado.web.UIModule):

    def render(self, text, indent=''):
        wrapped = textwrap.wrap(text,
                             initial_indent=indent,
                             subsequent_indent=indent)
        return '\n'.join(wrapped)


class TimeSince(tornado.web.UIModule):
    def render(self, date, date2=None):
        assert date
        return smartertimesince(date, date2)
