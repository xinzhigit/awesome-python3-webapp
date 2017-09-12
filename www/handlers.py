#!/usr/bin/env python3
# -*- coding: utf-8 -*-

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio
import markdown2

from aiohttp import web

from coroweb import get, post
from apis import APIError, APIValueError, APIPermissionError

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'
COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.password, expires, COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s : '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines);

async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
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
        s = '%s-%s-%s-%s' % (user.id, user.password, expires, COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('Invalid sha1')
            return None
        user.password = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
async def index(request):
    #summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    #content = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    #blogs = [
    #    Blog(id = '1', user_id='0', user_name='test', user_image='111', name='Teset Blog', content=content, summary=summary, created_at=time.time()-120),
    #    Blog(id = '2', user_id='0', user_name='test', user_image='111', name='Something New', content=content, summary=summary, created_at=time.time()-120),
    #    Blog(id = '3', user_id='0', user_name='test', user_image='111', name='Learn Swift', content=content, summary=summary, created_at=time.time()-120),
    #]
    #for blog in blogs:
    #    await blog.save()
    blogs = await Blog.findAll(orderBy='created_at desc')

    return {
        '__template__' : 'blogs.html',
        'blogs' : blogs,
        '__user__' : request.__user__
    }

@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy = 'created_at desc');
    for u in users:
        u.password = '******'
    return dict(users=users)

@get('/register')
def register():
    return {
        '__template__' : 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__' : 'signin.html'
    }

@post('/api/authenticate')
async def authenticate(*, email, password):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not password:
        raise APIValueError('password', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exsit.')
    user = users[0]
    # check password
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(password.encode('utf-8'))
    if user.password != sha1.hexdigest():
        raise APIValueError('password', 'Check password failed.')
    # authenticate ok, set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii = False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age = 0, httponly = True)
    logging.info('user signout.')
    return r

RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/register')
async def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('Name format error')
    if not email or not RE_EMAIL.match(email):
        raise APIValueError('Email format error.')
    if not password or not RE_SHA1.match(password):
        raise APIValueError('Password format error.')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIValueError('Register failed', 'Email is already exsit.')
    uid = next_id()
    sha1_password = '%s:%s' % (uid, password)
    user = User(id = uid, name = name.strip(), email = email, password = hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(), image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii = False).encode('utf-8')
    return r

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/manage/blogs')
def manage_blogs(*, page = '1'):
    return {
        '__template__' : manage_blogs.html,
        'page_index' : get_page_index(page)
    }

@get('/api/blogs')
async def api_blogs(*, page = '1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = page(num, page_index)
    if num == 0:
        return dict(page=p, blogs={})
    blogs = await Blog.findAll(orderBy = 'created_at desc', limit = (p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name, name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')

    user = request.__user__
    blog = Blog(user_id = user.id, user_name = user.name, user_image = user.image, name = name.strip(), summary = summary.strip(), content = content.strip())
    await blog.save()
    return blog
