#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Lainly'

# def Singleton(cls):

# 	_instance = {}
# 	def get_instance(*args, **kwargs):
# 		if cls not in _instance:
# 			_instance[cls] = cls(*args, **kwargs)
# 		return _instance
# 	return get_instance


class Singleton(object):

	def __init__(self, cls):
		self._cls = cls
		self._instance = None

	def __call__(self, *args, **kwargs):
		if not self._instance:
			self._instance = self._cls(*args, **kwargs)
		return self._instance

# import subprocess

# obj = subprocess.Popen(["python"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# obj.stdin.write(b'print(1) \n')
# obj.stdin.write(b'print(2)\n')
# obj.stdin.write(b'print(3)\n')
# # obj.stdin.write(b'print 4 \n')
# obj.stdin.close()

# cmd_out = obj.stdout.read()
# obj.stdout.close()
# cmd_error = obj.stderr.read()
# obj.stderr.close()

# print(cmd_out)
# print(cmd_error)
