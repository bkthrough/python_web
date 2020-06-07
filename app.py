from config import configs
from jinja2 import Environment, FileSystemLoader
from coroweb import add_routes, add_static
import asyncio
from aiohttp import web
import logging
import os
import time
import datetime
logging.basicConfig(level=logging.INFO)


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(autoescape=kw.get('autoescape', True),
                   block_start_string=kw.get('block_start_string', '{%'),
                   block_end_string=kw.get('block_end_string', '%}'),
                   variable_start_string=kw.get('variable_start_string', '%%'),
                   variable_end_string=kw.get('variable_end_string', '%%'),
                   auto_reload=kw.get('auto_reload', True))
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def init(loop):
    from middleware import auth_factory, response_factory
    app = web.Application(loop=loop,
                          middlewares=[response_factory, auth_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), configs.server.host,
                                   configs.server.port)
    logging.info('server started at http://127.0.0.1:8888...')
    import orm
    await orm.create_pool(loop, **configs.db)
    return srv


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
