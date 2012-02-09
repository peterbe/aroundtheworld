#!/usr/bin/env python
import os
import re
import here
import logging
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import redis.client
from tornado.options import define, options
from tornado_utils.routes import route
import core.handlers
import admin.handlers
import settings



define("debug", default=False, help="run in debug mode", type=bool)
define("database_name", default=settings.DATABASE_NAME, help="db name")
define("port", default=8000, help="run on the given port", type=int)
define("dont_optimize_static_content", default=False,
       help="Don't combine static resources", type=bool)
define("dont_embed_static_url", default=False,
       help="Don't put embed the static URL in static_url()", type=bool)


class Application(tornado.web.Application):
    def __init__(self, database_name=None):
        ui_modules_map = {}
        for each in ('core.ui_modules', 'admin.ui_modules'):
            _ui_modules = __import__(each, globals(), locals(),
                                     ['ui_modules'], -1)
            for name in [x for x in dir(_ui_modules)
                         if re.findall('[A-Z]\w+', x)]:
                thing = getattr(_ui_modules, name)
                try:
                    if issubclass(thing, tornado.web.UIModule):
                        ui_modules_map[name] = thing
                except TypeError:  # pragma: no cover
                    # most likely a builtin class or something
                    pass

        try:
            cdn_prefix = [x.strip() for x in open('cdn_prefix.conf')
                          if x.strip() and not x.strip().startswith('#')][0]
            logging.info("Using %r as static URL prefix" % cdn_prefix)
        except (IOError, IndexError):
            cdn_prefix = None

        from tornado_utils import tornado_static
        ui_modules_map['Static'] = tornado_static.Static
        ui_modules_map['StaticURL'] = tornado_static.StaticURL
        ui_modules_map['Static64'] = tornado_static.Static64
        routed_handlers = route.get_routes()
        app_settings = dict(
            title=settings.PROJECT_TITLE,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret=settings.COOKIE_SECRET,
            debug=options.debug,
            email_backend=options.debug and \
                 'tornado_utils.send_mail.backends.console.EmailBackend' \
              or 'tornado_utils.send_mail.backends.pickle.EmailBackend',
            admin_emails=settings.ADMIN_EMAILS,
            ui_modules=ui_modules_map,
            embed_static_url_timestamp=not options.dont_embed_static_url,
            optimize_static_content=not options.dont_optimize_static_content,
            cdn_prefix=cdn_prefix,
            CLOSURE_LOCATION=os.path.join(os.path.dirname(__file__),
                                          "static", "compiler.jar"),

        )
        if 1:#0 or not options.debug:
            routed_handlers.append(
              tornado.web.url('/admin/.*?',
                              core.handlers.PageNotFoundHandler,
                              name='page_not_found')
            )
        super(Application, self).__init__(routed_handlers, **app_settings)

        self.redis = redis.client.Redis(settings.REDIS_HOST,
                                        settings.REDIS_PORT)

        from core.models import connection
        import admin.models  # so it gets registered
        self.db = connection[database_name or settings.DATABASE_NAME]


def main():  # pragma: no cover
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    print "Starting tornado on port", options.port
    http_server.listen(options.port)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
