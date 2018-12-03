# -*- coding:utf-8 -*-

import time
import aiohttp
import os
import re
import asyncio
import redis
from queue import Queue
from threading import Thread
from bs4 import BeautifulSoup


def now(): return time.time()

async def aiohttp_parse_index(key_words, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            print(resp.status)
            html = await resp.text(encoding='gbk')
            soup = BeautifulSoup(html, features='html5lib')
            content_list = soup.find_all("td", {'class': 'tal'})
            for target in content_list:
                title = target.find('h3').get_text()
                if any(key in title for key in key_words):
                    url = target.find("a")
                    print(title)
                    # print(str(url['href']))
                    dict = (str(url['href']), title)
                    pages_queue.put(dict)
            await asyncio.sleep(2)


async def aiohttp_parse_pic(url, title):
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url + url) as resp:
            print(resp.status)
            html = await resp.text(encoding='gbk')
            url_list = []
            soup = BeautifulSoup(html, features='html5lib')
            content_list = soup.find_all("tr", {'class': 'tr1 do_not_catch'})
            for target in content_list:
                img_list = target.find_all('input', {'data-link': re.compile('(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'),'type': 'image'})
                # img_list = target.find_all('input', {
                #     'data-link': re.compile('(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'),
                #     'data-src': re.compile('(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'),
                #     'type': 'image',
                #     'src': re.compile('(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]')
                # })
                # print(img_list)
                for img_src in img_list:
                    url_list.append(img_src['data-src'])
            pics_queue.put((title, url_list))
            # print(url_list)
            await asyncio.sleep(2)


async def download_pic(pic_url, pic_name='', pic_path=''):
    try:
        if len(pic_name) == 0:
            pic_name = re.split('/', pic_url)[-1]
        if len(pic_path) != 0:
            if not (os.path.exists(pic_path)):
                await os.makedirs(pic_path)
            file_name = os.path.join(pic_path, pic_name)
        else:
            file_name = pic_name
        if os.path.isfile(file_name):
            print('    文件已存在，无需重复下载')
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                pic = await response.read()  # 以Bytes方式读入非文字
                with open(file_name, "wb") as code:
                    code.write(pic)
        # print('    下载成功 %s' % pic_url)
    except Exception as e:
        print(e)
        print('    下载失败 %s' % pic_url)
        pass


async def download_pics(pic_urls, pic_path):
    if pic_urls is None:
        return
    print('>>> 共 %d 张图片需要下载...' % len(pic_urls))
    num = 0
    for pic_url in pic_urls:
        num += 1
        print("第{}/{}个:".format(num, len(pic_urls)))
        await download_pic(pic_url, '', pic_path)
    await asyncio.sleep(2)


def get_redis():
    connection_pool = redis.ConnectionPool(host='127.0.0.1', db=3)
    return redis.Redis(connection_pool=connection_pool)


async def parse_index_worker():
    print('Start parse_index_worker')

    while True:
        start = now()
        # task = rcon.rpop("queue")

        if index_queue.empty():
            await asyncio.sleep(1)
            continue
        url = index_queue.get_nowait()
        print('Wait index ', url)
        await aiohttp_parse_index(key_words, url)
        print('Done index ', url, now() - start)


async def parse_pic_worker():
    print('Start parse_pic_worker')

    while True:
        start = now()
        # task = rcon.rpop("queue")

        if pages_queue.empty():
            await asyncio.sleep(1)
            continue
        url = pages_queue.get_nowait()
        print('Wait pages ', url[1])
        await aiohttp_parse_pic(url[0], url[1])
        print('Done pages ', url[1], now() - start)


async def download_pic_worker():
    print('Start download_worker')

    while True:
        start = now()
        # task = rcon.rpop("queue")
        if pics_queue.empty():
            await asyncio.sleep(1)
            continue
        url = pics_queue.get_nowait()
        print('Wait download ', url[0])
        await download_pics(url[1], os.path.join(save_path, 'pictures', re.sub('[>/:*\|?\\<]', '-', url[0])))
        print('Done download ', url[0], now() - start)


def main():
    asyncio.ensure_future(parse_index_worker())
    asyncio.ensure_future(parse_pic_worker())
    asyncio.ensure_future(download_pic_worker())

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        print(asyncio.gather(*asyncio.Task.all_tasks()).cancel())
        loop.stop()
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    pages_queue = Queue()
    pics_queue = Queue()
    index_queue = Queue()
    download_queue = Queue()

    rcon = get_redis()
    base_url = 'http://t66y.com/'
    url_list = ["http://t66y.com/thread0806.php?fid=16&page=1"]
    for url in url_list:
        index_queue.put(url)
    key_words = ['原创', '原創']
    save_path = '/root/t66y'  # 默认目录

    main()
