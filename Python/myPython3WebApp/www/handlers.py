#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Lights Jiao'

' url handlers '
import time, re, hashlib, json, logging, asyncio
from aiohttp import web

from coroweb import get, post
from models  import User, Blog, Comment, next_id
from apis    import APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from config  import configs

#################### 一些算法，比如cookie加密 ####################
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1  = re.compile(r'^[0-9a-f]{40}$') #what is this?

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

#计算加密cookie
def user2cookie(user, max_age):
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid
    '''
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
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None




#################### web页面的映射  ####################
#测试页面，展示用户
@get('/test')
async def test(request):
    users = await User.findAll()
    return {
        '__template__':'test.html',
        'users':users
    }


#示例页面，展示最简单的博客页面
@get('/')
async def index(request):
    summary = '这是一个摘要'
    blogs = [
        Blog(id='1', name='Test Blog',     summary=summary, created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blog(id='3', name='Learn Swift',   summary=summary, created_at=time.time() - 7200)
    ]
    return {
        '__template__':'blogs.html',
        'blogs':blogs
    }


#注册页面
@get('/register')
def register():
    return {
        '__template__':'register.html'
    }


#登录页面
@get('/signin')
def signin():
    return {
        '__template__':'signin.html'
    }




####################### 页面的API #######################
#一个简单的API，获取用户名
@get('/api/test')
async def API_GetUser():
    users = await User.findAll(orderby='created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users = users)


#注册的API
#写一个修饰器 修饰函数调用时候 打印函数名和入参
@post('/api/userRegister')
async def API_UserRegister(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')

    users = await User.findAll('email = ?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()

    sha1_passwd = '%s:%s' % (uid, passwd)

    user = User(
        id      = uid,
        name    = name.strip(),
        email   = email,
        passwd  = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image   = ''#''http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest(), #???
    )
    await user.save()

    #make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


#登录的API
@post('/api/userSignin')
async def API_UserSignin(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd.')

    users = await User.findAll('email=?' , [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]

    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))

    logging.info('API_UserSignin checkParam: email:%s, passwd:%s, sha1:%s' % (user.email, user.passwd, sha1.hexdigest()))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password')

    #set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r













