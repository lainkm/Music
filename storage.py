#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Lainly'
'''
Class to stores everything into a json file.
'''

import json
from singleton import Singleton
from const import Constant

@Singleton
class Storage(object):

    def __init__(self):

        if hasattr(self, '_init'):
            return
        self._init = True
        self.database = {
            'version': 4,
            'user': {
                'username': '',
                'password': '',
                'user_id': '',
                'nickname': '',
            },
            'collections': [[]],
            'songs': {},
            'player_info': {
                'player_list': [],
                'player_list_type': '',
                'player_list_title': '',
                'playing_list': [],
                'playing_mode': 0,
                'idx': 0,
                'ridx': 0,
                'playing_volume': 60,
            }
        }
        self.storage_path = Constant.storage_path
        self.cookie_path = Constant.cookie_path
        self.file = None

    def load(self):
        try:
            self.file = open(self.storage_path, 'r')
            self.database = json.loads(self.file.read())
            self.file.close()
        except (ValueError, OSError, IOError):
            self.__init__()
        if not self.check_version():
            self.save()

    def save(self):
        self.file = open(self.storage_path, 'w')
        db_str = json.dumps(self.database)
        utf8_data_to_file(self.file, db_str)
        self.file.close()

s = Storage()
print(s.cookie_path)
