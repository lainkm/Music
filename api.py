#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Lainly'

'''
网易云音乐 Api
'''

import re
import os
import json
import time
import hashlib
import random
import base64
import binascii
import subprocess

from Crypto.Cipher import AES
from http.cookiejar import LWPCookieJar
from bs4 import BeautifulSoup
import requests

# from .config import Config
from storage import Storage
# from .utils import notify

default_timeout = 10

modulus = ('00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7'
           'b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280'
           '104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932'
           '575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b'
           '3ece0462db0a22b8e7')
nonce = '0CoJUm6Qyw8W8jud'
pubKey = '010001'


# 歌曲加密算法, 基于https://github.com/yanunon/NeteaseCloudMusic脚本实现
def encrypted_id(id):
    magic = bytearray('3go8&$8*3*3h0k(2)2', 'u8')
    song_id = bytearray(id, 'u8')
    magic_len = len(magic)
    for i, sid in enumerate(song_id):
        song_id[i] = sid ^ magic[i % magic_len]
    m = hashlib.md5(song_id)
    result = m.digest()
    result = base64.b64encode(result)
    result = result.replace(b'/', b'_')
    result = result.replace(b'+', b'-')
    return result.decode('utf-8')


# 登录加密算法, 基于https://github.com/stkevintan/nw_musicbox脚本实现
def encrypted_request(text):
    text = json.dumps(text)
    secKey = createSecretKey(16)
    encText = aesEncrypt(aesEncrypt(text, nonce), secKey)
    encSecKey = rsaEncrypt(secKey, pubKey, modulus)
    data = {'params': encText, 'encSecKey': encSecKey}
    return data


def aesEncrypt(text, secKey):
    pad = 16 - len(text) % 16
    text = text + chr(pad) * pad
    encryptor = AES.new(secKey, 2, '0102030405060708')
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.b64encode(ciphertext).decode('utf-8')
    return ciphertext


def rsaEncrypt(text, pubKey, modulus):
    text = text[::-1]
    rs = pow(int(binascii.hexlify(text), 16), int(pubKey, 16), int(modulus, 16))
    return format(rs, 'x').zfill(256)


def createSecretKey(size):
    return binascii.hexlify(os.urandom(size))[:16]


# list去重
def uniq(arr):
    arr2 = list(set(arr))
    arr2.sort(key=arr.index)
    return arr2


# 获取高音质mp3 url
def geturl(song):
    try:
        return geturl_v1(song)
    except KeyError as e:
        return geturl_v3(song)


# 老的获取歌曲url方法
def geturl_v1(song):
    quality = Config().get_item('music_quality')
    if song['hMusic'] and quality <= 0:
        music = song['hMusic']
        quality = 'HD'
    elif song['mMusic'] and quality <= 1:
        music = song['mMusic']
        quality = 'MD'
    elif song['lMusic'] and quality <= 2:
        music = song['lMusic']
        quality = 'LD'
    else:
        return song['mp3Url'], ''

    quality = quality + ' {0}k'.format(music['bitrate'] // 1000)
    song_id = str(music['dfsId'])
    enc_id = encrypted_id(song_id)
    url = 'http://m%s.music.126.net/%s/%s.mp3' % (random.randrange(1, 3),
                                                  enc_id, song_id)
    return url, quality

# 新的获取歌曲url方法
def geturl_v3(song):
    quality = Config().get_item('music_quality')
    if song['h'] and quality <= 0:
        music = song['h']
        quality = 'HD'
    elif song['m'] and quality <= 1:
        music = song['m']
        quality = 'MD'
    elif song['l'] and quality <= 2:
        music = song['l']
        quality = 'LD'
    else:
        return song.get('mp3Url', ''), ''

    quality = quality + ' {0}k'.format(music['br'] // 1000)
    song_id = str(music['fid'])
    enc_id = encrypted_id(song_id)
    url = 'http://m%s.music.126.net/%s/%s.mp3' % (random.randrange(1, 3),
                                                  enc_id, song_id)
    return url, quality    

def geturl_new_api(song):
    br_to_quality = {128000: 'MD 128k', 320000: 'HD 320k'}
    alter = NetEase().songs_detail_new_api([song['id']])[0]
    url = alter['url']
    quality = br_to_quality.get(alter['br'], '')
    return url, quality


class NetEase(object):
    def __init__(self):
        self.header = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Referer': 'http://music.163.com/search/',
            'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'  # NOQA
        }
        self.cookies = {'appver': '1.5.2'}
        self.playlist_class_dict = {}
        self.session = requests.Session()
        self.storage = Storage()
        self.session.cookies = LWPCookieJar(self.storage.cookie_path)
        self.popen_handler = None
        try:
            self.session.cookies.load()
            cookie = ''
            if os.path.isfile(self.storage.cookie_path):
                self.file = open(self.storage.cookie_path, 'r')
                cookie = self.file.read()
                self.file.close()
            expire_time = re.compile(r'\d{4}-\d{2}-\d{2}').findall(cookie)
            if expire_time:
                if expire_time[0] < time.strftime('%Y-%m-%d', time.localtime(time.time())):
                    self.storage.database['user'] = {
                        'username': '',
                        'password': '',
                        'user_id': '',
                        'nickname': '',
                    }
                    self.storage.save()
                    os.remove(self.storage.cookie_path)
        except IOError as e:
            # log.error(e)
            self.session.cookies.save()
    # def return_toplists(self):
    #     return [l[0] for l in top_list_all.values()]
    def httpRequest(self,
                    method,
                    action,
                    query=None,
                    urlencoded=None,
                    callback=None,
                    timeout=None):
        connection = json.loads(
            self.rawHttpRequest(method, action, query, urlencoded, callback, timeout)
        )
        return connection
    def rawHttpRequest(self,
                       method,
                       action,
                       query=None,
                       urlencoded=None,
                       callback=None,
                       timeout=None):
        if method == 'GET':
            url = action if query is None else action + '?' + query
            connection = self.session.get(url,
                                          headers=self.header,
                                          timeout=default_timeout)
        elif method == 'POST':
            connection = self.session.post(action,
                                           data=query,
                                           headers=self.header,
                                           timeout=default_timeout)
        elif method == 'Login_POST':
            connection = self.session.post(action,
                                           data=query,
                                           headers=self.header,
                                           timeout=default_timeout)
            self.session.cookies.save()
        connection.encoding = 'UTF-8'
        print('haha')
        return connection.text
    def songs_detail(self, ids, offset=0):
        tmpids = ids[offset:]
        tmpids = tmpids[0:100]
        tmpids = list(map(str, tmpids))
        action = 'http://music.163.com/api/song/detail?ids=[{}]'.format(  # NOQA
            ','.join(tmpids))
        try:
            data = self.httpRequest('GET', action)
            # the order of data['songs'] is no longer the same as tmpids,
            # so just make the order back
            data['songs'].sort(key=lambda song: tmpids.index(str(song['id'])))
            return data['songs']
        except requests.exceptions.RequestException as e:
            # log.error(e)
            return []


    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=100):
        action = 'http://music.163.com/api/user/playlist/?offset={}&limit={}&uid={}'.format(  # NOQA
            offset, limit, uid)
        try:
            data = self.httpRequest('GET', action)
            print('xixi')
            return data['playlist'][:2]
        except (requests.exceptions.RequestException, KeyError) as e:
            # log.error(e)
            return -1

    # 歌单详情， 使用新版本v3接口，借鉴自https://github.com/Binaryify/NeteaseCloudMusicApi/commit/a1239a838c97367e86e2ec3cdce5557f1aa47bc1
    def playlist_detail(self, playlist_id):
        action = 'http://music.163.com/weapi/v3/playlist/detail'
        self.session.cookies.load()
        csrf = ''
        for cookie in self.session.cookies:
            if cookie.name == '__csrf':
                csrf = cookie.value
        data = {'id': playlist_id, 'total': 'true', 'csrf_token': csrf, 'limit': 1000, 'n': 1000, 'offset': 0}
        connection = self.session.post(action,
                                       data=encrypted_request(data),
                                       headers=self.header, )
        result = json.loads(connection.text)
        # log.debug(result['playlist']['tracks'])
        return result['playlist']['tracks'][:1]


    def song_comments(self, music_id, offset=0, total='false', limit=100):
        action = 'http://music.163.com/api/v1/resource/comments/R_SO_4_{}/?rid=R_SO_4_{}&\
            offset={}&total={}&limit={}'.format(music_id, music_id, offset, total, limit)
        try:
            comments = self.httpRequest('GET', action)
            return comments
        except requests.exceptions.RequestException as e:
            # log.error(e)
            return []

    def songs_detail_new_api(self, music_ids, bit_rate=320000):
        action = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='  # NOQA
        self.session.cookies.load()
        csrf = ''
        for cookie in self.session.cookies:
            if cookie.name == '__csrf':
                csrf = cookie.value
        # if csrf == '':
        #     notify('You Need Login', 1)
        action += csrf
        data = {'ids': music_ids, 'br': bit_rate, 'csrf_token': csrf}
        connection = self.session.post(action,
                                       data=encrypted_request(data),
                                       headers=self.header, )
        result = json.loads(connection.text)
        return result['data']

    # lyric http://music.163.com/api/song/lyric?os=osx&id= &lv=-1&kv=-1&tv=-1
    def song_lyric(self, music_id):
        action = 'http://music.163.com/api/song/lyric?os=osx&id={}&lv=-1&kv=-1&tv=-1'.format(  # NOQA
            music_id)
        try:
            data = self.httpRequest('GET', action)
            if 'lrc' in data and data['lrc']['lyric'] is not None:
                lyric_info = data['lrc']['lyric']
            else:
                lyric_info = '未找到歌词'
            return lyric_info
        except requests.exceptions.RequestException as e:
            # log.error(e)
            return []

    def run(self, arg):
        """
    	arg是url
    	"""
        para = ['mpg123', '-R']
        mpg = {
                'value': [],
                'default': [],
                'describe': 'The additional parameters when mpg123 start.'
            }
        para[1:1] = mpg.get('value')
        print(para)
        self.popen_handler = subprocess.Popen(para,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE)
        # self.popen_handler.stdin.write(b'V ' + str(self.info['playing_volume']).encode('utf-8') + b'\n')
        
        self.popen_handler.stdin.write(b'L ' + arg.encode('utf-8') + b'\n')
        self.popen_handler.stdin.flush()
        # self.popen_handler.stdin.write(b'\nL ' + new_url.encode('utf-8') + b'\n')
        # self.popen_handler.stdin.flush()

        a = self.popen_handler.stdout.readline()

        print(a)
        a = self.popen_handler.stdout.readline()

        print(a)
        a = self.popen_handler.stdout.readline()
        print(a)
        a = self.popen_handler.stdout.readline()
        print(a)
        a = self.popen_handler.stdout.readline()
        print(a)
        a = self.popen_handler.stdout.readline()
        print(a)
if __name__ == '__main__':
    ne = NetEase()
    # x = ne.user_playlist(282048033)[0]
    # print(x)
    # print(x['id'])
    # songs_id = ne.playlist_detail(x['id'])[0]['id']
    # print()
    # print(geturl_new_api(ne.songs_detail([27902910])[0]))  # MD 128k, fallback
    # print(ne.song_lyric([27902912]))
    print(ne.songs_detail_new_api([27902910])[0]['url'])
    url = ne.songs_detail_new_api([27902910])[0]['url']
    # print(ne.songs_detail_new_api([songs_id])[0]['url'])
    # print(requests.get(ne.songs_detail([405079776])[0]['mp3Url']).status_code)  # 404
    ne.run(url)
