#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import models
import orm

async def test_orm(loop):
	await orm.create_pool(loop, user = 'xinzhi', password = 'xinzhi123', db = 'awesome')

	user = models.User(name = 'test', email = 'test@example.com', password = '123456', admin = True, image = 'about:blank')
	await user.save()

loop =asyncio.get_event_loop()
loop.run_until_complete(test_orm(loop))
loop.close()