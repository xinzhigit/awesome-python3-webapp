#!/usr/bin/env python3
# -*- coding: utf-8 -*-

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
    #users = await User.findAll()
    #return {
    #    '__template__' : 'test.html',
    #    'users' : users
    #}
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id = '1', name='Teset Blog', summary=summary, created_at=time.time()-120),
        Blog(id = '2', name='Something New', summary=summary, created_at=time.time()-120),
        Blog(id = '3', name='Learn Swift', summary=summary, created_at=time.time()-120),
    ]
    return {
        '__template__' : 'blogs.html',
        'blogs' : blogs
    }