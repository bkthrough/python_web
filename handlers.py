from coroweb import get
from models import Blog, User
import time


@get('/')
async def index(request):
    summary = "asdddddda asdasdsad sad asdowef npwn ef oweif owef lkds fkjf dkvjhdfkjhk gjhs "
    blogs = [
        Blog(id='1',
             name='first blog',
             summary=summary,
             created_at=time.time() - 1000),
        Blog(id='2',
             name='second blog',
             summary=summary,
             created_at=time.time() - 2000),
        Blog(id='3',
             name='third blog',
             summary=summary,
             created_at=time.time())
    ]
    return {'__template__': 'blogs.html', 'blogs': blogs}


@get('/user')
async def getUser(request):
    users = await User.findAll()
    return dict(users=users)
