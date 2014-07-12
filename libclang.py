#!/usr/bin/python

# Copyright (C) 2014 Reece H. Dunn
#
# This file is part of libclangpy.
#
# libclangpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# libclangpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with libclangpy.  If not, see <http://www.gnu.org/licenses/>.

from ctypes import *
import platform

_lib_extension = { 'Darwin': 'dylib', 'Linux': 'so', 'Windows': 'dll' }
_system = platform.system()
_libclang = None

class _CXString(Structure):
	_fields_ = [
		('data', c_void_p),
		('private_flags', c_uint)
	]

def load(name=None, version=None):
	""" Load libclang from the specified name and/or version. """

	global _libclang
	if not name:
		name = 'libclang'
	if version:
		name = '{0}-{1}'.format(name, version)
	_libclang = cdll.LoadLibrary('{0}.{1}'.format(name, _lib_extension[_system]))

class MissingFunction(Exception):
	""" The requested function was not found in the loaded libclang library. """

	pass

def _bind_api(name, argtypes, restype):
	global _libclang
	try:
		api = getattr(_libclang, name)
	except AttributeError:
		raise MissingFunction('Function %s not supported in this version of libclang.' % name)

	try:
		registered = api.registered
	except AttributeError:
		registered = False

	if not registered:
		api.argtypes = argtypes
		api.restype = restype
		api.registered = True

def requires(version, name=None, argtypes=None, restype=None):
	""" Python decorator to annotate required libclang API call dependencies, or libclang version. """

	def new(f):
		def call(*args):
			if name:
				_bind_api(name, argtypes=argtypes, restype=restype)
			return f(*args)
		return call
	return new

def optional(version, name, argtypes=None, restype=None):
	""" Python decorator to annotate optional libclang API call dependencies. """

	def new(f):
		def call(*args):
			global _libclang
			try:
				_bind_api(name, argtypes=argtypes, restype=restype)
			except MissingFunction:
				setattr(_libclang, name, None)
			return f(*args)
		return call
	return new

@requires(2.7, 'clang_getCString', [_CXString], c_char_p)
@requires(2.7, 'clang_disposeString', [_CXString])
def _to_str(s):
	ret = str(_libclang.clang_getCString(s))
	_libclang.clang_disposeString(s)
	return ret