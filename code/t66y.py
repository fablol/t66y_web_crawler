# -*- coding:utf-8 -*-

import urllib, http.cookiejar, requests
import threading
import os,re
from bs4 import BeautifulSoup

proxies = {
    'https': 'https://192.168.23.150:1080',
    'http': 'http://192.168.23.150:1080'
}

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

def get_page(url,timeout=20):
    # 仅返回网页，不做任何操作
    try:
        response = requests.get(url, proxies=proxies)
        response.encoding = 'gbk'
        page = response.text
        return page
    except:
        print('>>> 页面下载失败...%s' % url)

def get_item(url):
    # 通过分析网页返回该页所有的帖子信息：[地址, 标题]
    # 部分帖子(尤其是达盖尔)存在颜色标记, 需要额外去除
    try:
        page = get_page(url)
        page = re.sub('[\n|\r|\t]|<font color=.+?>|</font>','',page)
        item_pattern = re.compile('(?<=<h3><a href="htm_data).+?(?=</a></h3>)')
        items = re.findall(item_pattern, page)
        res = [re.split('" target="_blank" id="">',item) for item in items]
        return res
    except:
        print('>>> 获取帖子信息失败...')

def get_range(url, page_start, page_end):
    # 批量下载多页帖子信息，未实现多线程，需要优化
    # 返回结果同 get_item
    items = []
    for page_num in range(page_start, page_end+1):
        try:
            print('>>> 开始下载第 %d 页...' % page_num)
            items = items + get_item(url + '&page=%d' % page_num)
            print('    第 %d 页下载成功' % page_num)
        except:
            print('    第 %d 页下载失败' % page_num)
        finally:
            print('>>> -------------------------------')
    return items

def search_item(key_word_list, items):
    print('>>> 目标包含 %d 条目, 按照关键词: %s 展开搜索...' % (len(items),' | '.join(key_word_list)))
    search_result = []
    if len(key_word_list) == 0 : return items
    for item in items:
        for key_word in key_word_list:
            if key_word in item[1]:
                search_result.append(item)
                break
    print('>>> 共搜索到 %d 个主题' % len(search_result))
    return search_result

def get_torrent_hash(page):
    try:
        hash_pattern = re.compile('(?<=hash=).+?(?=&z">)') 
        torrent_hash = re.findall(hash_pattern, page)[0]
        return torrent_hash
    except Exception as e:
        print(' get_torrent_hash 错误为:{}'.format(e))
        pass
    finally:
        print('>>> -------------------------------')


def get_pic_urls(page):
    try:
        pic_pattern1 = re.compile('(?<=<input src=\').+?(?=\'\s)')
        pic_pattern2 = re.compile('(?<=img src=\').+?(?=\'\s)')
        pic_urls = re.findall(pic_pattern1, page) + re.findall(pic_pattern2, page)
        return pic_urls
    except Exception as e:
        print('get_pic_urls 错误为:{}'.format(e))
        pass
    finally:
        print('>>> -------------------------------')

def queryurl(URL):
    content = requests.get(URL,proxies=proxies).content
    return content

def download_torrent(torrent_hash, torrent_name='', torrent_path=''):
    # 此处 url 对应为帖子地址
    try:
        print('>>> 开始下载种子...')
        get_ref_url = 'http://www.rmdown.com/link.php?hash={}'.format(torrent_hash)
        reff_content = queryurl(get_ref_url)
        soup = BeautifulSoup(reff_content, 'lxml')
        reff = soup.find(attrs={"name": "reff"})['value']
        torrent_url = 'http://www.rmdown.com/download.php?reff={}&ref={}'.format(reff,torrent_hash)
        torrent_content=queryurl(torrent_url)

        if len(torrent_name) == 0:
            torrent_name = torrent_hash
        else:
            torrent_name = re.sub('[>/:*\|?\\<]',' - ',torrent_name)
        if len(torrent_path) != 0:
            if not(os.path.exists(torrent_path)):
                os.makedirs(torrent_path)
            file_name = os.path.join(torrent_path, torrent_name + '.torrent')
        else:
            file_name = torrent_name + '.torrent'
        with open(file_name, "wb") as code:
            code.write(torrent_content)
    except Exception as e:
        print('{} 错误为:{}'.format(get_ref_url, e))
        pass
        
    finally:
        print('>>> -------------------------------')

def download_pic(pic_url,pic_name='',pic_path=''):
    try:
        if len(pic_name) == 0: pic_name = re.split('/',pic_url)[-1]
        if len(pic_path) != 0:
            if not(os.path.exists(pic_path)):
                os.makedirs(pic_path)
            file_name = os.path.join(pic_path, pic_name)
        else:
            file_name = pic_name
        if os.path.isfile(file_name):
            print('    文件已存在，无需重复下载')
            return
        r = requests.get(pic_url, proxies=proxies,timeout = 20)
        # r = requests.get(pic_url,timeout = 20)
        with open(file_name, "wb") as code:
            code.write(r.content)
        print('    下载成功 %s' % pic_url)
    except Exception as e:
        print(e)
        print('    下载失败 %s' % pic_url)
        pass

def download_pics(pic_urls, pic_path):
    print('>>> 共 %d 张图片需要下载...' % len(pic_urls))
    task_threads = []
    num = 0
    for pic_url in pic_urls:
        print("第{}/{}个:".format(++num,len(pic_urls)))
        download_pic(pic_url,'',pic_path)

def download_pics_from_range(url, page_start, page_end, key_word_list, save_path):
    items = get_range(url, page_start, page_end)
    matched_items = search_item(key_word_list, items)
    for i in matched_items:
        i[1]=i[1].replace('&nbsp; ','')
        print('>>> 下载主题 %s' % i[1])
        page = get_page(cl_url+'htm_data'+i[0])
        if page is None:
            continue
        pic_urls = get_pic_urls(page)
        print(save_path+'\\'+re.sub('[>/:*\|?\\<]','-',i[1]))
        download_pics(pic_urls,save_path+'\\'+'pictures'+'\\'+re.sub('[>/:*\|?\\<]','-',i[1]))

def download_all_from_range(url, page_start, page_end, key_word_list, save_path):
    items = get_range(url, page_start, page_end)
    matched_items = search_item(key_word_list, items)
    for i in matched_items:
        print('>>> 下载主题 %s' % i[1])
        page = get_page(cl_url+'htm_data'+i[0])
        pic_urls = get_pic_urls(page)
        torrent_hash = get_torrent_hash(page)
        download_pics(pic_urls,save_path+'\\'+'pictures'+'\\'+re.sub('[>/:*\|?\\<]','-',i[1]))
        download_torrent(torrent_hash, i[1], save_path+'\\'+'torrents'+'\\'+re.sub('[>/:*\|?\\<]','-',i[1]))

if __name__ == '__main__':

    cl_url = 'http://t66y.com/' # 定期更换
    Asia_non_mosaic    = cl_url + 'thread0806.php?fid=2'   # 亚洲无码
    Asia_mosaic        = cl_url + 'thread0806.php?fid=15'  # 亚洲有码
    Original_Western   = cl_url + 'thread0806.php?fid=4'   # 欧美原创
    Original_Animation = cl_url + 'thread0806.php?fid=5'   # 动漫原创
    Flag_of_Daguerre   = cl_url + 'thread0806.php?fid=16'  # 达盖尔的旗帜
    New_Era_for_All    = cl_url + 'thread0806.php?fid=8'   # 新时代的我们
    Tech_Talk          = cl_url + 'thread0806.php?fid=7'   # 技术讨论区
    Homemade_original  = cl_url + 'thread0806.php?fid=25'   # 国产原创区
    address_dic = {1: Asia_non_mosaic,
                   2: Asia_mosaic,
                   3: Original_Western,
                   4: Original_Animation,
                   5: Flag_of_Daguerre,
                   6: New_Era_for_All,
                   7: Tech_Talk,
                   8: Homemade_original
                #    9: 
                   }
    
    welcome_info = '''>>> 你，国之栋梁，请注意节制

    1. 亚洲无码     Asia_non_mosaic
    2. 亚洲有码     Asia_mosaic
    3. 欧美原创     Original_Western
    4. 动漫原创     Original_Animation
    5. 达盖尔的旗帜 Flag_of_Daguerre
    6. 新时代的我们 New_Era_for_All 
    7. 技术讨论区   Tech_Talk
    8. 国产原创区   Homemade_original
    '''
    print(welcome_info)
    save_path = 'your path'
    # key_words = ['原创','原創']
    key_words = []

    download_all_from_range(Homemade_original, 1, 20, key_words, save_path)
    # download_all_from_range(Tech_Talk, 1, 20, key_words, save_path)
    # m = search_item(key_words, get_range(Tech_Talk,1,1))
    # for s in m:
    #     print(s)
    print(key_words)
    print("-========= end ===========-")
