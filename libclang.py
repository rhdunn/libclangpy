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

time_t = c_uint

class _CXString(Structure):
	_fields_ = [
		('data', c_void_p),
		('private_flags', c_uint)
	]

class _CXSourceLocation(Structure):
	_fields_ = [
		('ptr_data', c_void_p * 2),
		('int_data', c_uint)
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

class File:
	@requires(2.7)
	def __init__(self, f):
		self._f = f

	@requires(2.7)
	def __str__(self):
		return self.name

	@requires(2.7)
	def __eq__(self, other):
		return self.name == other.name

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@property
	@requires(2.7, 'clang_getFileName', [c_void_p], _CXString)
	def name(self):
		ret = _libclang.clang_getFileName(self._f)
		return _to_str(ret)

	@property
	@requires(2.7, 'clang_getFileTime', [c_void_p], time_t)
	def time(self):
		return _libclang.clang_getFileTime(self._f)

class SourceLocationData:
	def __init__(self, f, l, c, o):
		self.file = File(f) if f else None
		self.line = int(l.value)
		self.column = int(c.value)
		self.offset = int(o.value)

class SourceLocation:
	@requires(2.7)
	def __init__(self, sl):
		self._sl = sl
		self._instantiation = None

	@requires(2.7, 'clang_equalLocations', [_CXSourceLocation, _CXSourceLocation], c_uint)
	def __eq__(self, other):
		return bool(_libclang.clang_equalLocations(self._sl, other._sl))

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@property
	@requires(2.7, 'clang_getInstantiationLocation', [_CXSourceLocation, POINTER(c_void_p), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def instantiation_location(self):
		if self._instantiation is None:
			f, l, c, o = c_void_p(), c_uint(), c_uint(), c_uint()
			_libclang.clang_getInstantiationLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
			self._instantiation = SourceLocationData(f, l, c, o)
		return self._instantiation

	@staticmethod
	@requires(2.7, 'clang_getNullLocation', [], _CXSourceLocation)
	def null():
		sl = _libclang.clang_getNullLocation()
		return SourceLocation(sl)

	@property
	@requires(2.7)
	def file(self):
		return self.instantiation_location.file

	@property
	@requires(2.7)
	def line(self):
		return self.instantiation_location.line

	@property
	@requires(2.7)
	def column(self):
		return self.instantiation_location.column

	@property
	@requires(2.7)
	def offset(self):
		return self.instantiation_location.offset

class TranslationUnit:
	@requires(2.7)
	def __init__(self, tu):
		self._tu = tu

	@requires(2.7, 'clang_getFile', [c_void_p, c_char_p], c_void_p)
	def file(self, filename):
		ret = _libclang.clang_getFile(self._tu, filename)
		if not ret:
			raise Exception('File "%s" not in the translation unit.' % filename)
		return File(ret)

	@requires(2.7, 'clang_getLocation', [c_void_p, c_void_p, c_uint, c_uint], _CXSourceLocation)
	def location(self, cxfile, line, column):
		ret = _libclang.clang_getLocation(self._tu, cxfile._f, line, column)
		return SourceLocation(ret)
