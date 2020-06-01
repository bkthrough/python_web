from handlers import COOKIE_NAME, cookie2user


async def auth_factory(app, handler):
    async def auth(request):
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                request.__user__ = user
        return await handler(request)

    return auth
