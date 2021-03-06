from coroweb import get, post
from models import Blog, User, Comment, next_id
import time
from apis import APIValueError, APIError
import re
import hashlib
from aiohttp import web
import json
from config import configs
import logging

COOKIE_NAME = 'cooksession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(
    r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@get('/')
async def index(request):
    blogs = await Blog.findAll()
    return {'__template__': 'index.html', 'blogs': blogs}


@get('/blog/{id}')
async def getBlog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll("blog_id=?", [id])
    return {'__template__': 'blog.html', 'blog': blog, "comments": comments}


@get('/register')
async def register():
    return {'__template__': 'register.html'}


@get('/login')
async def login():
    return {'__template__': 'login.html'}


@get('/logout')
async def logout(request):
    # referer表示从那个链接发过来，登出后回到之前那个页面
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    return r


@get('/create/blog')
async def create_blog():
    return {'__template__': 'create_blog.html'}


@get('/manage/blogs/edit')
async def editBlog(*, blogId):
    return {'__template__': 'create_blog.html', 'blogId': blogId}


# 管理博客
@get('/manage/blogs')
async def manage_blogs(*, page="1"):
    return {'__template__': 'manage_blogs.html', 'page_index': page}


@get('/user')
async def getUser(request):
    users = await User.findAll()
    return dict(users=users)


@get('/api/blogs')
async def api_blogs(*, page="1"):
    index = int(page)
    num = await Blog.findNumber('count(id)')
    from apis import Page
    p = Page(num, index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc',
                               limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)


@get('/api/blog')
async def api_get_blog(*, blogId):
    blog = await Blog.find(blogId)
    return blog


@post('/api/blog')
async def api_create_blogs(request, *, title, summary, content, blogId):
    if blogId:
        blog = await Blog.find(blogId)
        blog.name = title
        blog.summary = summary
        blog.content = content
        await blog.update()
    else:
        blog = Blog(user_id=request.__user__.id,
                    user_name=request.__user__.name,
                    user_image=request.__user__.image,
                    name=title.strip(),
                    summary=summary.strip(),
                    content=content.strip(),
                    created_at=time.time())
        await blog.save()
    return blog


@post('/api/delete/blog')
async def api_delete_blog(*, blogId):
    blog = await Blog.find(blogId)
    await blog.remove()
    return dict(blogId=blogId)


@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', {email})
    if len(users):
        raise APIError('register failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid,
                name=name.strip(),
                email=email,
                passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' %
                hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME,
                 user2cookie(user, 86400),
                 max_age=86400,
                 httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/api/create/comment')
async def createComment(request, *, content, blogId):
    user = request.__user__
    comment = Comment(blog_id=blogId,
                      content=content,
                      user_id=user.id,
                      user_name=user.name,
                      user_image=user.image)
    await comment.save()
    return comment


@post("/api/delete/comment")
async def deleteComment(request, *, commentId):
    comment = await Comment.find(commentId)
    await comment.remove()
    return dict(id=commentId)


@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME,
                 user2cookie(user, 86400),
                 max_age=86400,
                 httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.warning(e)
        return None


def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    res = '-'.join(
        [user.id, expires,
         hashlib.sha1(s.encode('utf-8')).hexdigest()])
    return res
