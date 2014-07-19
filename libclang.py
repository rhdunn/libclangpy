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
import sys

_lib_extension = { 'Darwin': 'dylib', 'Linux': 'so', 'Windows': 'dll' }
_system = platform.system()
_libclang = None
_dynamic_types = {}

version = None

time_t = c_uint

if sys.version_info.major >= 3:
	class c_utf8_p(c_char_p):
		@staticmethod
		def _check_retval_(retval):
			if not retval:
				return None
			return retval.value.decode('utf-8')

		@classmethod
		def from_param(self, value):
			if not value:
				return None
			if isinstance(value, str):
				return value.encode('utf-8')
			raise ValueError('string expected, got {0}'.format(value))
else:
	c_utf8_p = c_char_p

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

class _CXSourceRange(Structure):
	_fields_ = [
		('ptr_data', c_void_p * 2),
		('begin_int_data', c_uint),
		('end_int_data', c_uint)
	]

class _CXUnsavedFile(Structure):
	_fields_ = [
		('filename', c_utf8_p),
		('contents', c_utf8_p),
		('length', c_uint)
	]

class _CXToken(Structure):
	_fields_ = [
		('int_data', c_uint * 4),
		('ptr_data', c_void_p)
	]

class _CXCursor27(Structure):
	_fields_ = [
		('kind', c_uint),
		('data', c_void_p * 3)
	]

class _CXCursor30(Structure):
	_fields_ = [
		('kind', c_uint),
		('xdata', c_int),
		('data', c_void_p * 3)
	]

class _CXType(Structure):
	_fields_ = [
		('kind', c_uint),
		('data', c_void_p * 2)
	]

def _marshall_args(args):
	if not args or len(args) == 0:
		return 0, None
	ret = (c_utf8_p * len(args))()
	for i, arg in enumerate(args):
		ret[i] = arg.encode('utf-8')
	return len(args), ret

def _marshall_unsaved_files(unsaved_files):
	if not unsaved_files or len(unsaved_files) == 0:
		return 0, None
	ret = (_CXUnsavedFile * len(unsaved_files))()
	for i, (name, contents) in enumerate(unsaved_files):
		if hasattr(contents, 'read'):
			contents = contents.read().encode('utf-8')
		else:
			contents = contents.encode('utf-8')
		ret[i].filename = name.encode('utf-8')
		ret[i].contents = contents
		ret[i].length = len(contents)
	return len(unsaved_files), ret

def _detect_version(name):
	# The libclang documentation says that clang_getClangVersion is not
	# intended to be (a) machine parsable, or (b) stable. Therefore,
	# this uses the presence of different APIs to infer the version.
	#
	# This will only detect libclang versions upto and including the
	# version supported by libclangpy using this method.
	global version
	_version_checks = [
		(3.4, 'clang_Type_getClassType'),
		(3.3, 'clang_getTypeSpelling'),
		(3.2, 'clang_Cursor_getReceiverType'),
		(3.1, 'clang_Cursor_getArgument'),
		(3.0, 'clang_Range_isNull'),
		(2.9, 'clang_getDiagnosticOption'),
		(2.8, 'clang_isUnexposed'),
		(2.7, 'clang_isInvalid')
	]
	for v, api in _version_checks:
		if hasattr(_libclang, api):
			version = v
			return version
	raise Exception('Library {0} is not a libclang library.'.format(name))

def load(name=None, version=None):
	""" Load libclang from the specified name and/or version. """

	global _libclang
	if not name:
		name = 'libclang'
	if version:
		name = '{0}-{1}'.format(name, version)
	_libclang = cdll.LoadLibrary('{0}.{1}'.format(name, _lib_extension[_system]))
	lib_version = _detect_version(name)
	if lib_version >= 3.0:
		_dynamic_types['_CXCursor'] = _CXCursor30
		_dynamic_types['_CXCursor*'] = POINTER(_CXCursor30)
		_dynamic_types['_CXCursor**'] = POINTER(POINTER(_CXCursor30))
		_dynamic_types['cb_cursor_visitor'] = CFUNCTYPE(c_int, _CXCursor30, _CXCursor30, py_object)
	else:
		_dynamic_types['_CXCursor'] = _CXCursor27
		_dynamic_types['_CXCursor*'] = POINTER(_CXCursor27)
		_dynamic_types['_CXCursor**'] = POINTER(POINTER(_CXCursor27))
		_dynamic_types['cb_cursor_visitor'] = CFUNCTYPE(c_int, _CXCursor27, _CXCursor27, py_object)

class MissingFunction(Exception):
	""" The requested function was not found in the loaded libclang library. """

	pass

def _map_type(t):
	if isinstance(t, str):
		return _dynamic_types[t]
	return t

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
		api.argtypes = [_map_type(x) for x in argtypes]
		api.restype = _map_type(restype)
		api.registered = True

def requires(version, name=None, argtypes=None, restype=None):
	""" Python decorator to annotate required libclang API call dependencies, or libclang version. """

	def new(f):
		def call(*args, **kwargs):
			if name:
				_bind_api(name, argtypes=argtypes, restype=restype)
			return f(*args, **kwargs)
		return call
	return new

def optional(version, name, argtypes=None, restype=None):
	""" Python decorator to annotate optional libclang API call dependencies. """

	def new(f):
		def call(*args, **kwargs):
			global _libclang
			try:
				_bind_api(name, argtypes=argtypes, restype=restype)
			except MissingFunction:
				setattr(_libclang, name, None)
			return f(*args, **kwargs)
		return call
	return new

def deprecated(version, message):
	""" Python decorator to annotate libclang APIs that have been deprecated. """

	def new(f):
		def call(*args, **kwargs):
			return f(*args, **kwargs)
		return call
	return new

class cached_property(object):
	def __init__(self, wrapped):
		self.wrapped = wrapped
		self.__doc__ = wrapped.__doc__

	def __get__(self, instance, instance_type):
		if instance is None:
			return self
		value = self.wrapped(instance)
		setattr(instance, self.wrapped.__name__, value)
		return value

@requires(2.7, 'clang_getCString', [_CXString], c_utf8_p)
@requires(2.7, 'clang_disposeString', [_CXString])
def _to_str(s):
	ret = _libclang.clang_getCString(s)
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
		if isinstance(other, str):
			return self.name == other
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
	def __init__(self, l, c, o, cxfile=None, filename=None):
		if filename:
			self.file = _to_str(filename)
		elif cxfile:
			self.file = File(cxfile)
		else:
			self.file = None
		self.line = int(l.value)
		self.column = int(c.value)
		self.offset = int(o.value)

class SourceLocation:
	@requires(2.7)
	def __init__(self, sl):
		self._sl = sl

	@requires(2.7, 'clang_equalLocations', [_CXSourceLocation, _CXSourceLocation], c_uint)
	def __eq__(self, other):
		return bool(_libclang.clang_equalLocations(self._sl, other._sl))

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@cached_property
	@requires(2.7, 'clang_getInstantiationLocation', [_CXSourceLocation, POINTER(c_void_p), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def instantiation_location(self):
		f, l, c, o = c_void_p(), c_uint(), c_uint(), c_uint()
		_libclang.clang_getInstantiationLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
		return SourceLocationData(l, c, o, cxfile=f)

	@cached_property
	@requires(2.9, 'clang_getSpellingLocation', [_CXSourceLocation, POINTER(c_void_p), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def spelling_location(self):
		f, l, c, o = c_void_p(), c_uint(), c_uint(), c_uint()
		_libclang.clang_getSpellingLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
		return SourceLocationData(l, c, o, cxfile=f)

	@cached_property
	@requires(3.0, 'clang_getExpansionLocation', [_CXSourceLocation, POINTER(c_void_p), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def expansion_location(self):
		f, l, c, o = c_void_p(), c_uint(), c_uint(), c_uint()
		_libclang.clang_getExpansionLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
		return SourceLocationData(l, c, o, cxfile=f)

	@cached_property
	@requires(3.0, 'clang_getPresumedLocation', [_CXSourceLocation, POINTER(_CXString), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def presumed_location(self):
		f, l, c, o = _CXString(), c_uint(), c_uint(), c_uint()
		_libclang.clang_getPresumedLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
		return SourceLocationData(l, c, o, filename=f)

	@cached_property
	@requires(3.3, 'clang_getFileLocation', [_CXSourceLocation, POINTER(c_void_p), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)])
	def file_location(self):
		f, l, c, o = c_void_p(), c_uint(), c_uint(), c_uint()
		_libclang.clang_getFileLocation(self._sl, byref(f), byref(l), byref(c), byref(o))
		return SourceLocationData(l, c, o, cxfile=f)

	@staticmethod
	@requires(2.7, 'clang_getNullLocation', [], _CXSourceLocation)
	def null():
		sl = _libclang.clang_getNullLocation()
		return SourceLocation(sl)

	@property
	@requires(2.7)
	def is_null(self):
		return self == SourceLocation.null()

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

	@property
	@requires(3.3, 'clang_Location_isInSystemHeader', [_CXSourceLocation], c_int)
	def is_in_system_header(self):
		return bool(_libclang.clang_Location_isInSystemHeader(self._sl))

class SourceRange:
	@requires(2.7)
	@requires(2.7, 'clang_getRange', [_CXSourceLocation, _CXSourceLocation], _CXSourceRange)
	def __init__(self, start, end):
		if isinstance(start, _CXSourceRange):
			self._sr = start
		else:
			self._sr = _libclang.clang_getRange(start._sl, end._sl)

	@requires(2.7)
	@optional(3.0, 'clang_equalRanges', [_CXSourceRange, _CXSourceRange], c_uint)
	def __eq__(self, other):
		if _libclang.clang_equalRanges:
			return bool(_libclang.clang_equalRanges(self._sr, other._sr))
		return self.start == other.start and self.end == other.end

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@staticmethod
	@requires(2.7, 'clang_getNullRange', [], _CXSourceRange)
	def null():
		sr = _libclang.clang_getNullRange()
		return SourceRange(sr, None)

	@property
	@requires(2.7)
	@optional(3.0, 'clang_Range_isNull', [_CXSourceRange], c_int)
	def is_null(self):
		if _libclang.clang_Range_isNull:
			return bool(_libclang.clang_Range_isNull(self._sr))
		return self == SourceRange.null()

	@property
	@requires(2.7, 'clang_getRangeStart', [_CXSourceRange], _CXSourceLocation)
	def start(self):
		sl = _libclang.clang_getRangeStart(self._sr)
		return SourceLocation(sl)

	@property
	@requires(2.7, 'clang_getRangeEnd', [_CXSourceRange], _CXSourceLocation)
	def end(self):
		sl = _libclang.clang_getRangeStart(self._sr)
		return SourceLocation(sl)

class DiagnosticDisplayOptions:
	@requires(2.7)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __or__(self, other):
		return DiagnosticDisplayOptions(self.value | other.value)

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.7)
	def __hash__(self):
		return hash(self.value)

	@staticmethod
	@requires(2.7, 'clang_defaultDiagnosticDisplayOptions', [], c_uint)
	def DEFAULT():
		value = _libclang.clang_defaultDiagnosticDisplayOptions()
		return DiagnosticDisplayOptions(value)

DiagnosticDisplayOptions.SOURCE_LOCATION = DiagnosticDisplayOptions(1) # 2.7
DiagnosticDisplayOptions.COLUMN = DiagnosticDisplayOptions(2) # 2.7
DiagnosticDisplayOptions.SOURCE_RANGES = DiagnosticDisplayOptions(4) # 2.7
DiagnosticDisplayOptions.OPTION = DiagnosticDisplayOptions(8) # 2.9
DiagnosticDisplayOptions.CATEGORY_ID = DiagnosticDisplayOptions(16) # 2.9
DiagnosticDisplayOptions.CATEGORY_NAME = DiagnosticDisplayOptions(32) # 2.9

class DiagnosticSeverity:
	@requires(2.7)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.7)
	def __hash__(self):
		return hash(self.value)

DiagnosticSeverity.IGNORED = DiagnosticSeverity(0) # 2.7
DiagnosticSeverity.NOTE = DiagnosticSeverity(1) # 2.7
DiagnosticSeverity.WARNING = DiagnosticSeverity(2) # 2.7
DiagnosticSeverity.ERROR = DiagnosticSeverity(3) # 2.7
DiagnosticSeverity.FATAL = DiagnosticSeverity(4) # 2.7

class DiagnosticCategory:
	@requires(2.9)
	def __init__(self, value):
		self.value = value

	@requires(2.9)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.9)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.9)
	def __str__(self):
		return self.name

	@requires(2.9)
	def __hash__(self):
		return hash(self.value)

	@property
	@requires(2.9, 'clang_getDiagnosticCategoryName', [c_uint], _CXString)
	@deprecated(3.1, 'Use Diagnostic.category_text instead.')
	def name(self):
		s = _libclang.clang_getDiagnosticCategoryName(self.value)
		return _to_str(s)

class FixIt:
	def __init__(self, extent, spelling):
		self.extent = extent
		self.spelling = spelling

class Diagnostic:
	@requires(2.7)
	def __init__(self, d):
		self._d = d

	@requires(2.7, 'clang_disposeDiagnostic', [c_void_p])
	def __del__(self):
		_libclang.clang_disposeDiagnostic(self._d)

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@requires(2.7, 'clang_formatDiagnostic', [c_void_p, c_uint], _CXString)
	def format(self, options=DiagnosticDisplayOptions.SOURCE_LOCATION | DiagnosticDisplayOptions.COLUMN):
		s = _libclang.clang_formatDiagnostic(self._d, options.value)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getDiagnosticSeverity', [c_void_p], c_uint)
	def severity(self):
		return DiagnosticSeverity(_libclang.clang_getDiagnosticSeverity(self._d))

	@property
	@requires(2.7, 'clang_getDiagnosticLocation', [c_void_p], _CXSourceLocation)
	def location(self):
		sl = _libclang.clang_getDiagnosticLocation(self._d)
		return SourceLocation(sl)

	@property
	@requires(2.7, 'clang_getDiagnosticSpelling', [c_void_p], _CXString)
	def spelling(self):
		s = _libclang.clang_getDiagnosticSpelling(self._d)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getDiagnosticNumRanges', [c_void_p], c_uint)
	@requires(2.7, 'clang_getDiagnosticRange', [c_void_p, c_uint], _CXSourceRange)
	def ranges(self):
		for i in range(0, _libclang.clang_getDiagnosticNumRanges(self._d)):
			sr = _libclang.clang_getDiagnosticRange(self._d, i)
			yield SourceRange(sr, None)

	@property
	@requires(2.7, 'clang_getDiagnosticNumFixIts', [c_void_p], c_uint)
	@requires(2.7, 'clang_getDiagnosticFixIt', [c_void_p, c_uint, POINTER(_CXSourceRange)], _CXString)
	def fixits(self):
		for i in range(0, _libclang.clang_getDiagnosticNumFixIts(self._d)):
			sr = _CXSourceRange()
			s  = _libclang.clang_getDiagnosticFixIt(self._d, i, byref(sr))
			yield FixIt(SourceRange(sr, None), _to_str(s))

	@cached_property
	@requires(2.9, 'clang_getDiagnosticOption', [c_void_p, POINTER(_CXString)], _CXString)
	def _option(self):
		disable = _CXString()
		o = _libclang.clang_getDiagnosticOption(self._d, byref(disable))
		return (_to_str(o), _to_str(disable))

	@property
	@requires(2.9)
	def option(self):
		o, d = self._option
		return o

	@property
	@requires(2.9)
	def disable_option(self):
		o, d = self._option
		return d

	@property
	@requires(2.9, 'clang_getDiagnosticCategory', [c_void_p], c_uint)
	def category(self):
		return DiagnosticCategory(_libclang.clang_getDiagnosticCategory(self._d))

	@property
	@requires(2.9)
	@optional(3.1, 'clang_getDiagnosticCategoryText', [c_void_p], _CXString)
	def category_text(self):
		if _libclang.clang_getDiagnosticCategoryText:
			s = _libclang.clang_getDiagnosticCategoryText(self._d)
			return _to_str(s)
		return self.category.name

class Linkage:
	@requires(2.7)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.7)
	def __hash__(self):
		return hash(self.value)

Linkage.INVALID = Linkage(0) # 2.7
Linkage.NO_LINKAGE = Linkage(1) # 2.7
Linkage.INTERNAL = Linkage(2) # 2.7
Linkage.UNIQUE_EXTERNAL = Linkage(3) # 2.7
Linkage.EXTERNAL = Linkage(4) # 2.7

class TokenKind:
	@requires(2.7)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.7)
	def __hash__(self):
		return hash(self.value)

TokenKind.PUNCTUATION = TokenKind(0) # 2.7
TokenKind.KEYWORD = TokenKind(1) # 2.7
TokenKind.IDENTIFIER = TokenKind(2) # 2.7
TokenKind.LITERAL = TokenKind(3) # 2.7
TokenKind.COMMENT = TokenKind(4) # 2.7

TokenKind.PUNCTUATION = TokenKind(0) # 2.7
TokenKind.KEYWORD = TokenKind(1) # 2.7
TokenKind.IDENTIFIER = TokenKind(2) # 2.7
TokenKind.LITERAL = TokenKind(3) # 2.7
TokenKind.COMMENT = TokenKind(4) # 2.7

class CallingConvention:
	@requires(3.1)
	def __init__(self, value):
		self.value = value

	@requires(3.1)
	def __eq__(self, other):
		return self.value == other.value

	@requires(3.1)
	def __ne__(self, other):
		return self.value != other.value

	@requires(3.1)
	def __hash__(self):
		return hash(self.value)

CallingConvention.DEFAULT = CallingConvention(0) # 3.1
CallingConvention.C = CallingConvention(1) # 3.1
CallingConvention.X86_STDCALL = CallingConvention(2) # 3.1
CallingConvention.X86_FASTCALL = CallingConvention(3) # 3.1
CallingConvention.X86_THISCALL = CallingConvention(4) # 3.1
CallingConvention.X86_PASCAL = CallingConvention(5) # 3.1
CallingConvention.AAPCS = CallingConvention(6) # 3.1
CallingConvention.AAPCS_VFP = CallingConvention(7) # 3.1
CallingConvention.PNACL_CALL = CallingConvention(8) # 3.2
CallingConvention.INTEL_OCL_BICC = CallingConvention(9) # 3.3
CallingConvention.INVALID = CallingConvention(100) # 3.1
CallingConvention.UNEXPOSED = CallingConvention(200) # 3.1

class ObjCPropertyAttributes:
	@requires(3.3)
	def __init__(self, value):
		self.value = value

	@requires(3.3)
	def __or__(self, other):
		return ObjCPropertyAttributes(self.value | other.value)

	@requires(3.3)
	def __eq__(self, other):
		return self.value == other.value

	@requires(3.3)
	def __ne__(self, other):
		return self.value != other.value

	@requires(3.3)
	def __hash__(self):
		return hash(self.value)

ObjCPropertyAttributes.NO_ATTR = ObjCPropertyAttributes(0) # 3.3
ObjCPropertyAttributes.READONLY = ObjCPropertyAttributes(1) # 3.3
ObjCPropertyAttributes.GETTER = ObjCPropertyAttributes(2) # 3.3
ObjCPropertyAttributes.ASSIGN = ObjCPropertyAttributes(4) # 3.3
ObjCPropertyAttributes.READ_WRITE = ObjCPropertyAttributes(8) # 3.3
ObjCPropertyAttributes.RETAIN = ObjCPropertyAttributes(16) # 3.3
ObjCPropertyAttributes.COPY = ObjCPropertyAttributes(32) # 3.3
ObjCPropertyAttributes.NON_ATOMIC = ObjCPropertyAttributes(64) # 3.3
ObjCPropertyAttributes.SETTER = ObjCPropertyAttributes(128) # 3.3
ObjCPropertyAttributes.ATOMIC = ObjCPropertyAttributes(256) # 3.3
ObjCPropertyAttributes.WEAK = ObjCPropertyAttributes(512) # 3.3
ObjCPropertyAttributes.STRONG = ObjCPropertyAttributes(1024) # 3.3
ObjCPropertyAttributes.UNSAFE_UNRETAINED = ObjCPropertyAttributes(2048) # 3.3

class ObjCDeclQualifierKind:
	@requires(3.3)
	def __init__(self, value):
		self.value = value

	@requires(3.3)
	def __or__(self, other):
		return ObjCDeclQualifierKind(self.value | other.value)

	@requires(3.3)
	def __eq__(self, other):
		return self.value == other.value

	@requires(3.3)
	def __ne__(self, other):
		return self.value != other.value

	@requires(3.3)
	def __hash__(self):
		return hash(self.value)

ObjCDeclQualifierKind.NONE = ObjCDeclQualifierKind(0) # 3.3
ObjCDeclQualifierKind.IN = ObjCDeclQualifierKind(1) # 3.3
ObjCDeclQualifierKind.INOUT = ObjCDeclQualifierKind(2) # 3.3
ObjCDeclQualifierKind.OUT = ObjCDeclQualifierKind(4) # 3.3
ObjCDeclQualifierKind.BYCOPY = ObjCDeclQualifierKind(8) # 3.3
ObjCDeclQualifierKind.BYREF = ObjCDeclQualifierKind(16) # 3.3
ObjCDeclQualifierKind.ONEWAY = ObjCDeclQualifierKind(32) # 3.3

class Token:
	@requires(2.7)
	def __init__(self, t, tokens, tu):
		self._t = t
		self._tokens = tokens
		self._tu = tu

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@property
	@requires(2.7, 'clang_getTokenKind', [_CXToken], c_uint)
	def kind(self):
		kind = _libclang.clang_getTokenKind(self._t)
		return TokenKind(kind)

	@property
	@requires(2.7, 'clang_getTokenSpelling', [c_void_p, _CXToken], _CXString)
	def spelling(self):
		s = _libclang.clang_getTokenSpelling(self._tu._tu, self._t)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getTokenLocation', [c_void_p, _CXToken], _CXSourceLocation)
	def location(self):
		sl = _libclang.clang_getTokenLocation(self._tu._tu, self._t)
		return SourceLocation(sl)

	@property
	@requires(2.7, 'clang_getTokenExtent', [c_void_p, _CXToken], _CXSourceRange)
	def extent(self):
		sr = _libclang.clang_getTokenExtent(self._tu._tu, self._t)
		return SourceRange(sr, None)

	@property
	@requires(2.7, 'clang_getCursor', [c_void_p, _CXSourceLocation], '_CXCursor')
	def cursor(self):
		# NOTE: This is doing what clang_annotateTokens does, but on one token only.
		c = _libclang.clang_getCursor(self._tu._tu, self.location._sl)
		return Cursor(c, None, self._tu)

class TokenList:
	@requires(2.7)
	def __init__(self, tu, tokens, length):
		self._tu = tu
		self._data = tokens
		if tokens:
			self._tokens = cast(tokens, POINTER(_CXToken * length)).contents
		else:
			self._tokens = []
		self._length = length

	@requires(2.7, 'clang_disposeTokens', [c_void_p, POINTER(_CXToken), c_uint])
	def __del__(self):
		_libclang.clang_disposeTokens(self._tu._tu, self._data, self._length)

	@requires(2.7)
	def __len__(self):
		return self._length

	@requires(2.7)
	def __getitem__(self, key):
		return Token(self._tokens[key], self, self._tu)

	@requires(2.7)
	def __iter__(self):
		for i in range(0, len(self)):
			yield self[i]

class CursorKind:
	@requires(2.7)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.7)
	def __hash__(self):
		return hash(self.value)

	@property
	@requires(2.7, 'clang_getCursorKindSpelling', [c_uint], _CXString)
	def spelling(self):
		s = _libclang.clang_getCursorKindSpelling(self.value)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_isDeclaration', [c_uint], c_uint)
	def is_declaration(self):
		return bool(_libclang.clang_isDeclaration(self.value))

	@property
	@requires(2.7, 'clang_isReference', [c_uint], c_uint)
	def is_reference(self):
		return bool(_libclang.clang_isReference(self.value))

	@property
	@requires(2.7, 'clang_isExpression', [c_uint], c_uint)
	def is_expression(self):
		return bool(_libclang.clang_isExpression(self.value))

	@property
	@requires(2.7, 'clang_isStatement', [c_uint], c_uint)
	def is_statement(self):
		return bool(_libclang.clang_isStatement(self.value))

	@property
	@requires(2.7, 'clang_isInvalid', [c_uint], c_uint)
	def is_invalid(self):
		return bool(_libclang.clang_isInvalid(self.value))

	@property
	@requires(2.7, 'clang_isTranslationUnit', [c_uint], c_uint)
	def is_translation_unit(self):
		return bool(_libclang.clang_isTranslationUnit(self.value))

	@property
	@requires(2.8, 'clang_isPreprocessing', [c_uint], c_uint)
	def is_preprocessing(self):
		return bool(_libclang.clang_isPreprocessing(self.value))

	@property
	@requires(2.8, 'clang_isUnexposed', [c_uint], c_uint)
	def is_unexposed(self):
		return bool(_libclang.clang_isUnexposed(self.value))

	@property
	@requires(3.0, 'clang_isAttribute', [c_uint], c_uint)
	def is_attribute(self):
		return bool(_libclang.clang_isAttribute(self.value))

CursorKind.UNEXPOSED_DECL = CursorKind(1) # 2.7
CursorKind.STRUCT_DECL = CursorKind(2) # 2.7
CursorKind.UNION_DECL = CursorKind(3) # 2.7
CursorKind.CLASS_DECL = CursorKind(4) # 2.7
CursorKind.ENUM_DECL = CursorKind(5) # 2.7
CursorKind.FIELD_DECL = CursorKind(6) # 2.7
CursorKind.ENUM_CONSTANT_DECL = CursorKind(7) # 2.7
CursorKind.FUNCTION_DECL = CursorKind(8) # 2.7
CursorKind.VAR_DECL = CursorKind(9) # 2.7
CursorKind.PARM_DECL = CursorKind(10) # 2.7
CursorKind.OBJC_INTERFACE_DECL = CursorKind(11) # 2.7
CursorKind.OBJC_CATEGORY_DECL = CursorKind(12) # 2.7
CursorKind.OBJC_PROTOCOL_DECL = CursorKind(13) # 2.7
CursorKind.OBJC_PROPERTY_DECL = CursorKind(14) # 2.7
CursorKind.OBJC_IVAR_DECL = CursorKind(15) # 2.7
CursorKind.OBJC_INSTANCE_METHOD_DECL = CursorKind(16) # 2.7
CursorKind.OBJC_CLASS_METHOD_DECL = CursorKind(17) # 2.7
CursorKind.OBJC_IMPLEMENTATION_DECL = CursorKind(18) # 2.7
CursorKind.OBJC_CATEGORY_IMPL_DECL = CursorKind(19) # 2.7
CursorKind.TYPEDEF_DECL = CursorKind(20) # 2.7
CursorKind.CXX_METHOD_DECL = CursorKind(21) # 2.8
CursorKind.NAMESPACE = CursorKind(22) # 2.8
CursorKind.LINKAGE_SPEC = CursorKind(23) # 2.8
CursorKind.CONSTRUCTOR = CursorKind(24) # 2.8
CursorKind.DESTRUCTOR = CursorKind(25) # 2.8
CursorKind.CONVERSION_FUNCTION = CursorKind(26) # 2.8
CursorKind.TEMPLATE_TYPE_PARAMETER = CursorKind(27) # 2.8
CursorKind.NON_TYPE_TEMPLATE_PARAMETER = CursorKind(28) # 2.8
CursorKind.TEMPLATE_TEMPLATE_PARAMETER = CursorKind(29) # 2.8
CursorKind.FUNCTION_TEMPLATE = CursorKind(30) # 2.8
CursorKind.CLASS_TEMPLATE = CursorKind(31) # 2.8
CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION = CursorKind(32) # 2.8
CursorKind.NAMESPACE_ALIAS = CursorKind(33) # 2.8
CursorKind.USING_DIRECTIVE = CursorKind(34) # 2.8
CursorKind.USING_DECLARATION = CursorKind(35) # 2.8
CursorKind.TYPE_ALIAS_DECL = CursorKind(36) # 3.0
CursorKind.OBJC_SYNTHESIZE_DECL = CursorKind(37) # 3.0
CursorKind.OBJC_DYNAMIC_DECL = CursorKind(38) # 3.0
CursorKind.CXX_ACCESS_SPECIFIER = CursorKind(39) # 3.0

CursorKind.OBJC_SUPER_CLASS_REF = CursorKind(40) # 2.7
CursorKind.OBJC_PROTOCOL_REF = CursorKind(41) # 2.7
CursorKind.OBJC_CLASS_REF = CursorKind(42) # 2.7
CursorKind.TYPE_REF = CursorKind(43) # 2.7
CursorKind.CXX_BASE_SPECIFIER = CursorKind(44) # 2.8
CursorKind.TEMPLATE_REF = CursorKind(45) # 2.8
CursorKind.NAMESPACE_REF = CursorKind(46) # 2.8
CursorKind.MEMBER_REF = CursorKind(47) # 2.9
CursorKind.LABEL_REF = CursorKind(48) # 2.9
CursorKind.OVERLOADED_DECL_REF = CursorKind(49) # 2.9
CursorKind.VARIABLE_REF = CursorKind(50) # 3.1

CursorKind.INVALID_FILE = CursorKind(70) # 2.7
CursorKind.NO_DECL_FOUND = CursorKind(71) # 2.7
CursorKind.NOT_IMPLEMENTED = CursorKind(72) # 2.7
CursorKind.INVALID_CODE = CursorKind(73) # 2.8

CursorKind.UNEXPOSED_EXPR = CursorKind(100) # 2.7
CursorKind.DECL_REF_EXPR = CursorKind(101) # 2.7
CursorKind.MEMBER_REF_EXPR = CursorKind(102) # 2.7
CursorKind.CALL_EXPR = CursorKind(103) # 2.7
CursorKind.OBJC_MESSAGE_EXPR = CursorKind(104) # 2.7
CursorKind.BLOCK_EXPR = CursorKind(105) # 2.8
CursorKind.INTEGER_LITERAL = CursorKind(106) # 3.0
CursorKind.FLOATING_LITERAL = CursorKind(107) # 3.0
CursorKind.IMAGINARY_LITERAL = CursorKind(108) # 3.0
CursorKind.STRING_LITERAL = CursorKind(109) # 3.0
CursorKind.CHARACTER_LITERAL = CursorKind(110) # 3.0
CursorKind.PAREN_EXPR = CursorKind(111) # 3.0
CursorKind.UNARY_OPERATOR = CursorKind(112) # 3.0
CursorKind.ARRAY_SUBSCRIPT_EXPR = CursorKind(113) # 3.0
CursorKind.BINARY_OPERATOR = CursorKind(114) # 3.0
CursorKind.COMPOUND_ASSIGN_OPERATOR = CursorKind(115) # 3.0
CursorKind.CONDITIONAL_OPERATOR = CursorKind(116) # 3.0
CursorKind.C_STYLE_CAST_EXPR = CursorKind(117) # 3.0
CursorKind.COMPOUND_LITERAL_EXPR = CursorKind(118) # 3.0
CursorKind.INIT_LIST_EXPR = CursorKind(119) # 3.0
CursorKind.ADDR_LABEL_EXPR = CursorKind(120) # 3.0
CursorKind.STMT_EXPR = CursorKind(121) # 3.0
CursorKind.GENERIC_SELECTION_EXPR = CursorKind(122) # 3.0
CursorKind.GNU_NULL_EXPR = CursorKind(123) # 3.0
CursorKind.CXX_STATIC_CAST_EXPR = CursorKind(124) # 3.0
CursorKind.CXX_DYNAMIC_CAST_EXPR = CursorKind(125) # 3.0
CursorKind.CXX_REINTERPRET_CAST_EXPR = CursorKind(126) # 3.0
CursorKind.CXX_CONST_CAST_EXPR = CursorKind(127) # 3.0
CursorKind.CXX_FUNCTIONAL_CAST_EXPR = CursorKind(128) # 3.0
CursorKind.CXX_TYPEID_EXPR = CursorKind(129) # 3.0
CursorKind.CXX_BOOL_LITERAL_EXPR = CursorKind(130) # 3.0
CursorKind.CXX_NULLPTR_LITERAL_EXPR = CursorKind(131) # 3.0
CursorKind.CXX_THIS_EXPR = CursorKind(132) # 3.0
CursorKind.CXX_THROW_EXPR = CursorKind(133) # 3.0
CursorKind.CXX_NEW_EXPR = CursorKind(134) # 3.0
CursorKind.CXX_DELETE_EXPR = CursorKind(135) # 3.0
CursorKind.UNARY_EXPR = CursorKind(136) # 3.0
CursorKind.OBJC_STRING_LITERAL = CursorKind(137) # 3.0
CursorKind.OBJC_ENCODE_EXPR = CursorKind(138) # 3.0
CursorKind.OBJC_SELECTOR_EXPR = CursorKind(139) # 3.0
CursorKind.OBJC_PROTOCOL_EXPR = CursorKind(140) # 3.0
CursorKind.OBJC_BRIDGED_CAST_EXPR = CursorKind(141) # 3.0
CursorKind.PACK_EXPANSION_EXPR = CursorKind(142) # 3.0
CursorKind.SIZEOF_PACK_EXPR = CursorKind(143) # 3.0
CursorKind.LAMBDA_EXPR = CursorKind(144) # 3.1
CursorKind.OBJC_BOOL_LITERAL_EXPR = CursorKind(145) # 3.1
CursorKind.OBJC_SELF_EXPR = CursorKind(146) # 3.3

CursorKind.UNEXPOSED_STMT = CursorKind(200) # 2.7
CursorKind.LABEL_STMT = CursorKind(201) # 2.9
CursorKind.COMPOUND_STMT = CursorKind(202) # 3.0
CursorKind.CASE_STMT = CursorKind(203) # 3.0
CursorKind.DEFAULT_STMT = CursorKind(204) # 3.0
CursorKind.IF_STMT = CursorKind(205) # 3.0
CursorKind.SWITCH_STMT = CursorKind(206) # 3.0
CursorKind.WHILE_STMT = CursorKind(207) # 3.0
CursorKind.DO_STMT = CursorKind(208) # 3.0
CursorKind.FOR_STMT = CursorKind(209) # 3.0
CursorKind.GOTO_STMT = CursorKind(210) # 3.0
CursorKind.INDIRECT_GOTO_STMT = CursorKind(211) # 3.0
CursorKind.CONTINUE_STMT = CursorKind(212) # 3.0
CursorKind.BREAK_STMT = CursorKind(213) # 3.0
CursorKind.RETURN_STMT = CursorKind(214) # 3.0
CursorKind.GCC_ASM_STMT = CursorKind(215) # 3.0
CursorKind.ASM_STMT = CursorKind(215) # 3.0
CursorKind.OBJC_AT_TRY_STMT = CursorKind(216) # 3.0
CursorKind.OBJC_AT_CATCH_STMT = CursorKind(217) # 3.0
CursorKind.OBJC_AT_FINALLY_STMT = CursorKind(218) # 3.0
CursorKind.OBJC_AT_THROW_STMT = CursorKind(219) # 3.0
CursorKind.OBJC_AT_SYNCHRONIZED_STMT = CursorKind(220) # 3.0
CursorKind.OBJC_AUTORELEASE_POOL_STMT = CursorKind(221) # 3.0
CursorKind.OBJC_FOR_COLLECTION_STMT = CursorKind(222) # 3.0
CursorKind.CXX_CATCH_STMT = CursorKind(223) # 3.0
CursorKind.CXX_TRY_STMT = CursorKind(224) # 3.0
CursorKind.CXX_FOR_RANGE_STMT = CursorKind(225) # 3.0
CursorKind.SEH_TRY_STMT = CursorKind(226) # 3.0
CursorKind.SEH_EXCEPT_STMT = CursorKind(227) # 3.0
CursorKind.SEH_FINALLY_STMT = CursorKind(228) # 3.0
CursorKind.MS_ASM_STMT = CursorKind(229) # 3.2
CursorKind.NULL_STMT = CursorKind(230) # 3.0
CursorKind.DECL_STMT = CursorKind(231) # 3.0

CursorKind.TRANSLATION_UNIT = CursorKind(300) # 2.7

CursorKind.UNEXPOSED_ATTR = CursorKind(400) # 2.7
CursorKind.IB_ACTION_ATTR = CursorKind(401) # 2.7
CursorKind.IB_OUTLET_ATTR = CursorKind(402) # 2.7
CursorKind.IB_OUTLET_COLLECTION_ATTR = CursorKind(403) # 2.8
CursorKind.CXX_FINALLY_ATTR = CursorKind(404) # 3.0
CursorKind.CXX_OVERRIDE_ATTR = CursorKind(405) # 3.0
CursorKind.ANNOTATE_ATTR = CursorKind(406) # 3.0
CursorKind.ASM_LABEL_ATTR = CursorKind(407) # 3.1

CursorKind.PREPROCESSING_DIRECTIVE = CursorKind(500) # 2.8
CursorKind.MACRO_DEFINITION = CursorKind(501) # 2.8
CursorKind.MACRO_EXPANSION = CursorKind(502) # 3.0
CursorKind.MACRO_INSTANTIATION = CursorKind.MACRO_EXPANSION # 2.8
CursorKind.INCLUSION_DIRECTIVE = CursorKind(503) # 2.9

CursorKind.MODULE_IMPORT_DECL = CursorKind(600) # 3.2

class TypeKind:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __str__(self):
		return self.spelling

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

	@property
	@requires(2.8, 'clang_getTypeKindSpelling', [c_uint], _CXString)
	def spelling(self):
		s = _libclang.clang_getTypeKindSpelling(self.value)
		return _to_str(s)

TypeKind.INVALID = TypeKind(0) # 2.8
TypeKind.UNEXPOSED = TypeKind(1) # 2.8
TypeKind.VOID = TypeKind(2) # 2.8
TypeKind.BOOL = TypeKind(3) # 2.8
TypeKind.CHAR_U = TypeKind(4) # 2.8
TypeKind.UCHAR = TypeKind(5) # 2.8
TypeKind.CHAR16 = TypeKind(6) # 2.8
TypeKind.CHAR32 = TypeKind(7) # 2.8
TypeKind.USHORT = TypeKind(8) # 2.8
TypeKind.UINT = TypeKind(9) # 2.8
TypeKind.ULONG = TypeKind(10) # 2.8
TypeKind.ULONGLONG = TypeKind(11) # 2.8
TypeKind.UINT128 = TypeKind(12) # 2.8
TypeKind.CHAR_S = TypeKind(13) # 2.8
TypeKind.SCHAR = TypeKind(14) # 2.8
TypeKind.WCHAR = TypeKind(15) # 2.8
TypeKind.SHORT = TypeKind(16) # 2.8
TypeKind.INT = TypeKind(17) # 2.8
TypeKind.LONG = TypeKind(18) # 2.8
TypeKind.LONGLONG = TypeKind(19) # 2.8
TypeKind.INT128 = TypeKind(20) # 2.8
TypeKind.FLOAT = TypeKind(21) # 2.8
TypeKind.DOUBLE = TypeKind(22) # 2.8
TypeKind.LONG_DOUBLE = TypeKind(23) # 2.8
TypeKind.NULLPTR = TypeKind(24) # 2.8
TypeKind.OVERLOAD = TypeKind(25) # 2.8
TypeKind.DEPENDENT = TypeKind(26) # 2.8
TypeKind.OBJC_ID = TypeKind(27) # 2.8
TypeKind.OBJC_CLASS = TypeKind(28) # 2.8
TypeKind.OBJC_SEL = TypeKind(29) # 2.8

TypeKind.COMPLEX = TypeKind(100) # 2.8
TypeKind.POINTER = TypeKind(101) # 2.8
TypeKind.BLOCK_POINTER = TypeKind(102) # 2.8
TypeKind.LVALUE_REFERENCE = TypeKind(103) # 2.8
TypeKind.RVALUE_REFERENCE = TypeKind(104) # 2.8
TypeKind.RECORD = TypeKind(105) # 2.8
TypeKind.ENUM = TypeKind(106) # 2.8
TypeKind.TYPEDEF = TypeKind(107) # 2.8
TypeKind.OBJC_INTERFACE = TypeKind(108) # 2.8
TypeKind.OBJC_OBJECT_POINTER = TypeKind(109) # 2.8
TypeKind.FUNCTION_NO_PROTO = TypeKind(110) # 2.8
TypeKind.FUNCTION_PROTO = TypeKind(111) # 2.8

class Type:
	@requires(2.8)
	def __init__(self, t, tu):
		self._t = t
		self.kind = TypeKind(t.kind)
		self._tu = tu

	@requires(2.8, 'clang_equalTypes', [_CXType, _CXType], c_uint)
	def __eq__(self, other):
		return bool(_libclang.clang_equalTypes(self._t, other._t))

	@requires(2.8)
	def __ne__(self, other):
		return not self.__eq__(other)

	@requires(3.3)
	def __str__(self):
		return self.spelling

	@property
	@requires(2.8, 'clang_getCanonicalType', [_CXType], _CXType)
	def canonical_type(self):
		t = _libclang.clang_getCanonicalType(self._t)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getPointeeType', [_CXType], _CXType)
	def pointee_type(self):
		t = _libclang.clang_getPointeeType(self._t)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getResultType', [_CXType], _CXType)
	def result_type(self):
		t = _libclang.clang_getResultType(self._t)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getTypeDeclaration', [_CXType], '_CXCursor')
	def declaration(self):
		c = _libclang.clang_getTypeDeclaration(self._t)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.8, 'clang_isPODType', [_CXType], c_uint)
	def is_pod(self):
		return bool(_libclang.clang_isPODType(self._t))

	@property
	@requires(2.9, 'clang_isConstQualifiedType', [_CXType], c_uint)
	def is_const_qualified(self):
		return bool(_libclang.clang_isConstQualifiedType(self._t))

	@property
	@requires(2.9, 'clang_isVolatileQualifiedType', [_CXType], c_uint)
	def is_volatile_qualified(self):
		return bool(_libclang.clang_isVolatileQualifiedType(self._t))

	@property
	@requires(2.9, 'clang_isRestrictQualifiedType', [_CXType], c_uint)
	def is_restrict_qualified(self):
		return bool(_libclang.clang_isRestrictQualifiedType(self._t))

	@property
	@requires(3.0, 'clang_getArrayElementType', [_CXType], _CXType)
	def array_element_type(self):
		t = _libclang.clang_getArrayElementType(self._t)
		return Type(t, self._tu)

	@property
	@requires(3.0, 'clang_getArraySize', [_CXType], c_longlong)
	def array_size(self):
		return _libclang.clang_getArraySize(self._t)

	@property
	@requires(3.1, 'clang_getNumArgTypes', [_CXType], c_int)
	@requires(3.1, 'clang_getArgType', [_CXType, c_uint], _CXType)
	def argument_types(self):
		for i in range(0, _libclang.clang_getNumArgTypes(self._t)):
			t = _libclang.clang_getArgTypel(self._t, i)
			yield Type(t, self._tu)

	@property
	@requires(3.1, 'clang_getElementType', [_CXType], _CXType)
	def element_type(self):
		t = _libclang.clang_getElementType(self._t)
		return Type(t, self._tu)

	@property
	@requires(3.1, 'clang_getNumElements', [_CXType], c_longlong)
	def element_count(self):
		return _libclang.clang_getNumElements(self._t)

	@property
	@requires(3.1, 'clang_isFunctionTypeVariadic', [_CXType], c_uint)
	def is_variadic(self):
		return bool(_libclang.clang_isFunctionTypeVariadic(self._t))

	@property
	@requires(3.1, 'clang_getFunctionTypeCallingConv', [_CXType], c_uint)
	def calling_convention(self):
		cc = _libclang.clang_getFunctionTypeCallingConv(self._t)
		return CallingConvention(cc)

	@property
	@requires(3.3, 'clang_getTypeSpelling', [_CXType], _CXString)
	def spelling(self):
		s = _libclang.clang_getTypeSpelling(self._t)
		return _to_str(s)

	@property
	@requires(3.3, 'clang_Type_getAlignOf', [_CXType], c_longlong)
	def alignment(self):
		return _libclang.clang_Type_getAlignOf(self._t)

	@property
	@requires(3.3, 'clang_Type_getSizeOf', [_CXType], c_longlong)
	def size(self):
		return _libclang.clang_Type_getSizeOf(self._t)

	@requires(3.3, 'clang_Type_getOffsetOf', [_CXType, c_utf8_p], c_longlong)
	def offset(self, field):
		return _libclang.clang_Type_getOffsetOf(self._t, field)

class AvailabilityKind:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

AvailabilityKind.AVAILABLE = AvailabilityKind(0) # 2.8
AvailabilityKind.DEPRECATED = AvailabilityKind(1) # 2.8
AvailabilityKind.NOT_AVAILABLE = AvailabilityKind(2) # 2.8
AvailabilityKind.NOT_ACCESSIBLE = AvailabilityKind(3) # 3.0

class LanguageKind:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

LanguageKind.INVALID = LanguageKind(0) # 2.8
LanguageKind.C = LanguageKind(1) # 2.8
LanguageKind.OBJC = LanguageKind(2) # 2.8
LanguageKind.C_PLUS_PLUS = LanguageKind(3) # 2.8

class AccessSpecifier:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

AccessSpecifier.INVALID = AccessSpecifier(0) # 2.8
AccessSpecifier.PUBLIC = AccessSpecifier(1) # 2.8
AccessSpecifier.PROTECTED = AccessSpecifier(2) # 2.8
AccessSpecifier.PRIVATE = AccessSpecifier(3) # 2.8

class OverriddenCursors:
	@requires(2.9)
	def __init__(self, tu, cursors, length):
		self._tu = tu
		self._data = cursors
		if cursors:
			self._cursors = cast(cursors, POINTER(_map_type('_CXCursor') * length)).contents
		else:
			self._cursors = []
		self._length = length

	@requires(2.9, 'clang_disposeOverriddenCursors', ['_CXCursor*'])
	def __del__(self):
		_libclang.clang_disposeOverriddenCursors(self._data)

	@requires(2.9)
	def __len__(self):
		return self._length

	@requires(2.9)
	def __getitem__(self, key):
		return Cursor(self._cursors[key], None, self._tu)

	@requires(2.9)
	def __iter__(self):
		for i in range(0, len(self)):
			yield self[i]

class NameRefFlags:
	@requires(3.0)
	def __init__(self, value):
		self.value = value

	@requires(3.0)
	def __or__(self, other):
		return NameRefFlags(self.value | other.value)

	@requires(3.0)
	def __eq__(self, other):
		return self.value == other.value

	@requires(3.0)
	def __ne__(self, other):
		return self.value != other.value

	@requires(3.0)
	def __hash__(self):
		return hash(self.value)

NameRefFlags.WANT_QUALIFIER = NameRefFlags(1) # 3.0
NameRefFlags.WANT_TEMPLATE_ARGS = NameRefFlags(2) # 3.0
NameRefFlags.WANT_SINGLE_PIECE = NameRefFlags(4) # 3.0

class Cursor:
	@requires(2.7)
	def __init__(self, c, parent, tu):
		self._c = c
		self.parent = parent
		self._tu = tu

	@requires(2.7, 'clang_equalCursors', ['_CXCursor', '_CXCursor'], c_uint)
	def __eq__(self, other):
		return bool(_libclang.clang_equalCursors(self._c, other._c))

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@requires(2.7)
	@optional(2.9, 'clang_hashCursor', ['_CXCursor'], c_uint)
	def __hash__(self):
		if _libclang.clang_hashCursor:
			return _libclang.clang_hashCursor(self._c)
		return hash((self._c.kind, self._c.data[0], self._c.data[1], self._c.data[2]))

	@staticmethod
	@requires(2.7, 'clang_getNullCursor', [], '_CXCursor')
	def null():
		c = _libclang.clang_getNullCursor()
		return Cursor(c, None, None)

	@property
	@requires(2.7)
	@optional(3.0, 'clang_Cursor_isNull', ['_CXCursor'], c_int)
	def is_null(self):
		if _libclang.clang_Cursor_isNull:
			return bool(_libclang.clang_Cursor_isNull(self._c))
		return self == Cursor.null()

	@property
	@requires(2.7)
	def translation_unit(self):
		# libclang 3.0 provides a clang_Cursor_getTranslationUnit API,
		# but this already tracked in the libclangpy binding so it does
		# not need to be called.
		return self._tu

	@property
	@requires(2.7, 'clang_getCursorKind', ['_CXCursor'], c_uint)
	def kind(self):
		kind = _libclang.clang_getCursorKind(self._c)
		return CursorKind(kind)

	@property
	@requires(2.7, 'clang_getCursorLinkage', ['_CXCursor'], c_uint)
	def linkage(self):
		return Linkage(_libclang.clang_getCursorLinkage(self._c))

	@property
	@requires(2.7, 'clang_getCursorLocation', ['_CXCursor'], _CXSourceLocation)
	def location(self):
		sl = _libclang.clang_getCursorLocation(self._c)
		return SourceLocation(sl)

	@property
	@requires(2.7, 'clang_getCursorExtent', ['_CXCursor'], _CXSourceRange)
	def extent(self):
		sr = _libclang.clang_getCursorExtent(self._c)
		return SourceRange(sr, None)

	@property
	@requires(2.7, 'clang_visitChildren', ['_CXCursor', 'cb_cursor_visitor', py_object], c_uint)
	def children(self):
		def visitor(child, parent_cursor, args):
			(children, parent) = args
			c = Cursor(child, parent, self._tu)
			if c != Cursor.null():
				children.append(c)
			return 1 # continue
		ret = []
		_libclang.clang_visitChildren(self._c, _map_type('cb_cursor_visitor')(visitor), (ret, self))
		return ret

	@property
	@requires(2.7, 'clang_getCursorUSR', ['_CXCursor'], _CXString)
	def usr(self):
		s = _libclang.clang_getCursorUSR(self._c)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getCursorSpelling', ['_CXCursor'], _CXString)
	def spelling(self):
		s = _libclang.clang_getCursorSpelling(self._c)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getCursorReferenced', ['_CXCursor'], '_CXCursor')
	def referenced(self):
		c = _libclang.clang_getCursorReferenced(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.7, 'clang_getCursorDefinition', ['_CXCursor'], '_CXCursor')
	def definition(self):
		c = _libclang.clang_getCursorDefinition(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.7, 'clang_isCursorDefinition', ['_CXCursor'], c_uint)
	def is_definition(self):
		return bool(_libclang.clang_isCursorDefinition(self._c))

	@property
	@requires(2.7)
	def tokens(self):
		return self._tu.tokenize(self.extent)

	@property
	@requires(2.8, 'clang_getCursorType', ['_CXCursor'], _CXType)
	def type(self):
		t = _libclang.clang_getCursorType(self._c)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getCursorResultType', ['_CXCursor'], _CXType)
	def result_type(self):
		t = _libclang.clang_getCursorResultType(self._c)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getIBOutletCollectionType', ['_CXCursor'], _CXType)
	def ib_outlet_collection_type(self):
		t = _libclang.clang_getIBOutletCollectionType(self._c)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getCursorAvailability', ['_CXCursor'], c_uint)
	def availability(self):
		kind = _libclang.clang_getCursorAvailability(self._c)
		return AvailabilityKind(kind)

	@property
	@requires(2.8, 'clang_getCursorLanguage', ['_CXCursor'], c_uint)
	def language(self):
		kind = _libclang.clang_getCursorLanguage(self._c)
		return LanguageKind(kind)

	@property
	@requires(2.8, 'clang_getCXXAccessSpecifier', ['_CXCursor'], c_uint)
	def access_specifier(self):
		access = _libclang.clang_getCXXAccessSpecifier(self._c)
		return AccessSpecifier(access)

	@property
	@requires(2.8, 'clang_getTemplateCursorKind', ['_CXCursor'], c_uint)
	def template_kind(self):
		kind = _libclang.clang_getTemplateCursorKind(self._c)
		return CursorKind(kind)

	@property
	@requires(2.8, 'clang_getSpecializedCursorTemplate', ['_CXCursor'], '_CXCursor')
	def specialized_template(self):
		c = _libclang.clang_getSpecializedCursorTemplate(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.8, 'clang_isVirtualBase', ['_CXCursor'], c_uint)
	def is_virtual_base(self):
		return bool(_libclang.clang_isVirtualBase(self._c))

	@property
	@requires(2.8, 'clang_CXXMethod_isStatic', ['_CXCursor'], c_uint)
	def is_static_method(self):
		return bool(_libclang.clang_CXXMethod_isStatic(self._c))

	@property
	@requires(2.9, 'clang_getCursorSemanticParent', ['_CXCursor'], '_CXCursor')
	def semantic_parent(self):
		c = _libclang.clang_getCursorSemanticParent(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.9, 'clang_getCursorLexicalParent', ['_CXCursor'], '_CXCursor')
	def lexical_parent(self):
		c = _libclang.clang_getCursorLexicalParent(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.9, 'clang_getIncludedFile', ['_CXCursor'], c_void_p)
	def included_file(self):
		f = _libclang.clang_getIncludedFile(self._c)
		return File(f)

	@property
	@requires(2.9, 'clang_getDeclObjCTypeEncoding', ['_CXCursor'], _CXString)
	def objc_type_encoding(self):
		s = _libclang.clang_getDeclObjCTypeEncoding(self._c)
		return _to_str(s)

	@property
	@requires(2.9, 'clang_getNumOverloadedDecls', ['_CXCursor'], c_uint)
	@requires(2.9, 'clang_getOverloadedDecl', ['_CXCursor', c_uint], '_CXCursor')
	def overloads(self):
		for i in range(0, _libclang.clang_getNumOverloadedDecls(self._c)):
			c  = _libclang.clang_getOverloadedDecl(self._c, i)
			yield Cursor(c, None, self._tu)

	@property
	@requires(2.9, 'clang_getCursorDisplayName', ['_CXCursor'], _CXString)
	def display_name(self):
		s = _libclang.clang_getCursorDisplayName(self._c)
		return _to_str(s)

	@property
	@requires(2.9, 'clang_getCanonicalCursor', ['_CXCursor'], '_CXCursor')
	def canonical(self):
		c = _libclang.clang_getCanonicalCursor(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.9, 'clang_getOverriddenCursors', ['_CXCursor', '_CXCursor**', POINTER(c_uint)])
	def overridden(self):
		cursors = _map_type('_CXCursor*')()
		length = c_uint()
		_libclang.clang_getOverriddenCursors(self._c, byref(cursors), byref(length))
		length = int(length.value)
		return OverriddenCursors(self, cursors, length)

	@requires(3.0, 'clang_getCursorReferenceNameRange', ['_CXCursor', c_uint, c_uint], _CXSourceRange)
	def reference_name_range(self, flags, index):
		sr = _libclang.clang_getCursorReferenceNameRange(self._c, flags.value, index)
		return SourceRange(sr, None)

	@property
	@requires(3.0, 'clang_CXXMethod_isVirtual', ['_CXCursor'], c_uint)
	def is_virtual(self):
		return bool(_libclang.clang_CXXMethod_isVirtual(self._c))

	@property
	@requires(3.1, 'clang_getTypedefDeclUnderlyingType', ['_CXCursor'], _CXType)
	def underlying_typedef_type(self):
		t = _libclang.clang_getTypedefDeclUnderlyingType(self._c)
		return Type(t, self._tu)

	@property
	@requires(3.1, 'clang_getEnumDeclIntegerType', ['_CXCursor'], _CXType)
	def enum_type(self):
		t = _libclang.clang_getEnumDeclIntegerType(self._c)
		return Type(t, self._tu)

	@property
	@requires(3.1, 'clang_getEnumConstantDeclValue', ['_CXCursor'], c_longlong)
	@requires(3.1, 'clang_getEnumConstantDeclUnsignedValue', ['_CXCursor'], c_ulonglong)
	def enum_value(self):
		underlying_type = self.type
		if underlying_type.kind == TypeKind.ENUM:
			underlying_type = underlying_type.declaration.enum_type
		if underlying_type.kind in [TypeKind.CHAR_U, TypeKind.UCHAR, TypeKind.CHAR16,
		                            TypeKind.CHAR32, TypeKind.USHORT, TypeKind.UINT,
		                            TypeKind.ULONG, TypeKind.ULONGLONG, TypeKind.UINT128]:
			return _libclang.clang_getEnumConstantDeclUnsignedValue(self._c)
		return _libclang.clang_getEnumConstantDeclValue(self._c)

	@property
	@requires(3.1, 'clang_Cursor_getNumArguments', ['_CXCursor'], c_int)
	@requires(3.1, 'clang_Cursor_getArgument', ['_CXCursor', c_uint], '_CXCursor')
	def arguments(self):
		for i in range(0, _libclang.clang_Cursor_getNumArguments(self._c)):
			c  = _libclang.clang_Cursor_getArgument(self._c, i)
			yield Cursor(c, None, self._tu)

	@requires(3.1, 'clang_Cursor_getSpellingNameRange', ['_CXCursor', c_uint, c_uint], _CXSourceRange)
	def spelling_name_range(self, flags, index):
		sr = _libclang.clang_Cursor_getSpellingNameRange(self._c, index, flags.value)
		return SourceRange(sr, None)

	@property
	@requires(3.1, 'clang_Cursor_getObjCSelectorIndex', ['_CXCursor'], c_int)
	def objc_selector_index(self):
		return _libclang.clang_Cursor_getObjCSelectorIndex(self._c)

	@property
	@requires(3.2, 'clang_Cursor_isDynamicCall', ['_CXCursor'], c_int)
	def is_dynamic_call(self):
		return bool(_libclang.clang_Cursor_isDynamicCall(self._c))

	@property
	@requires(3.2, 'clang_Cursor_getReceiverType', ['_CXCursor'], _CXType)
	def receiver_type(self):
		t = _libclang.clang_Cursor_getReceiverType(self._c)
		return Type(t, self._tu)

	@property
	@requires(3.2, 'clang_Cursor_getCommentRange', ['_CXCursor'], _CXSourceRange)
	def comment_range(self):
		sr = _libclang.clang_Cursor_getCommentRange(self._c)
		return SourceRange(sr, None)

	@property
	@requires(3.2, 'clang_Cursor_getRawCommentText', ['_CXCursor'], _CXString)
	def raw_comment(self):
		s = _libclang.clang_Cursor_getRawCommentText(self._c)
		return _to_str(s)

	@property
	@requires(3.2, 'clang_Cursor_getBriefCommentText', ['_CXCursor'], _CXString)
	def brief_comment(self):
		s = _libclang.clang_Cursor_getBriefCommentText(self._c)
		return _to_str(s)

	@property
	@requires(3.3, 'clang_Cursor_isBitField', ['_CXCursor'], c_uint)
	def is_bit_field(self):
		return bool(_libclang.clang_Cursor_isBitField(self._c))

	@property
	@requires(3.3, 'clang_Cursor_isVariadic', ['_CXCursor'], c_uint)
	def is_variadic(self):
		return bool(_libclang.clang_Cursor_isVariadic(self._c))

	@property
	@requires(3.3, 'clang_Cursor_getObjCPropertyAttributes', ['_CXCursor', c_uint], c_uint)
	def objc_property_attributes(self):
		a = _libclang.clang_Cursor_getObjCPropertyAttributes(self._c, 0)
		return ObjCPropertyAttributes(a)

	@property
	@requires(3.3, 'clang_Cursor_getObjCDeclQualifiers', ['_CXCursor'], c_uint)
	def objc_decl_qualifiers(self):
		a = _libclang.clang_Cursor_getObjCDeclQualifiers(self._c)
		return ObjCDeclQualifierKind(a)

class TranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __or__(self, other):
		return TranslationUnitFlags(self.value | other.value)

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

	@staticmethod
	@requires(2.8, 'clang_defaultEditingTranslationUnitOptions', [], c_uint)
	def DEFAULT_EDITING():
		value = _libclang.clang_defaultEditingTranslationUnitOptions()
		return TranslationUnitFlags(value)

TranslationUnitFlags.NONE = TranslationUnitFlags(0) # 2.8
TranslationUnitFlags.DETAILED_PREPROCESSING_RECORD = TranslationUnitFlags(1) # 2.8
TranslationUnitFlags.INCOMPLETE = TranslationUnitFlags(2) # 2.8
TranslationUnitFlags.PRECOMPILED_PREAMBLE = TranslationUnitFlags(4) # 2.8
TranslationUnitFlags.CACHE_COMPLETION_RESULTS = TranslationUnitFlags(8) # 2.8
TranslationUnitFlags.PRECOMPILED_PREAMBLE = TranslationUnitFlags(16) # 2.9 to 3.1
TranslationUnitFlags.FOR_SERIALIZATION = TranslationUnitFlags(16) # 3.2
TranslationUnitFlags.CHAINED_PCH = TranslationUnitFlags(32) # 2.9
TranslationUnitFlags.NESTED_MACRO_EXPANSIONS = TranslationUnitFlags(64) # 3.0 only
TranslationUnitFlags.NESTED_MACRO_INSTANTIATIONS = TranslationUnitFlags.NESTED_MACRO_EXPANSIONS # 3.0 only
TranslationUnitFlags.SKIP_FUNCTION_BODIES = TranslationUnitFlags(64) # 3.1
TranslationUnitFlags.INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION = TranslationUnitFlags(128) # 3.2

class SaveTranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __or__(self, other):
		return SaveTranslationUnitFlags(self.value | other.value)

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

SaveTranslationUnitFlags.NONE = SaveTranslationUnitFlags(0) # 2.8

class ReparseTranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __or__(self, other):
		return ReparseTranslationUnitFlags(self.value | other.value)

	@requires(2.8)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.8)
	def __ne__(self, other):
		return self.value != other.value

	@requires(2.8)
	def __hash__(self):
		return hash(self.value)

ReparseTranslationUnitFlags.NONE = ReparseTranslationUnitFlags(0) # 2.8

class TranslationUnit:
	@requires(2.7)
	def __init__(self, tu, index):
		self._tu = tu
		self._index = index

	@requires(2.7, 'clang_disposeTranslationUnit', [c_void_p])
	def __del__(self):
		_libclang.clang_disposeTranslationUnit(self._tu)

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@requires(2.7, 'clang_getFile', [c_void_p, c_utf8_p], c_void_p)
	def file(self, filename):
		ret = _libclang.clang_getFile(self._tu, filename)
		if not ret:
			raise Exception('File "%s" not in the translation unit.' % filename)
		return File(ret)

	@requires(2.7, 'clang_getLocation', [c_void_p, c_void_p, c_uint, c_uint], _CXSourceLocation)
	@optional(2.9, 'clang_getLocationForOffset', [c_void_p, c_void_p, c_uint], _CXSourceLocation)
	def location(self, cxfile, line=-1, column=0, offset=-1):
		ret = None
		if isinstance(cxfile, str):
			cxfile = self.file(cxfile)
		if line != -1:
			ret = _libclang.clang_getLocation(self._tu, cxfile._f, line, column)
		elif offset != -1 and _libclang.clang_getLocationForOffset:
			ret = _libclang.clang_getLocationForOffset(self._tu, cxfile._f, offset)
		if not ret:
			raise Exception('Unable to determine the file location in this translation unit.')
		return SourceLocation(ret)

	@property
	@requires(2.7, 'clang_getNumDiagnostics', [c_void_p], c_uint)
	@requires(2.7, 'clang_getDiagnostic', [c_void_p, c_uint], c_void_p)
	def diagnostics(self):
		for i in range(0, _libclang.clang_getNumDiagnostics(self._tu)):
			d = _libclang.clang_getDiagnostic(self._tu, i)
			yield Diagnostic(d)

	@property
	@requires(2.7, 'clang_getTranslationUnitSpelling', [c_void_p], _CXString)
	def spelling(self):
		s = _libclang.clang_getTranslationUnitSpelling(self._tu)
		return _to_str(s)

	@requires(2.7, 'clang_getTranslationUnitCursor', [c_void_p], '_CXCursor')
	@requires(2.7, 'clang_getCursor', [c_void_p, _CXSourceLocation], '_CXCursor')
	def cursor(self, source_location=None):
		if not source_location:
			c = _libclang.clang_getTranslationUnitCursor(self._tu)
		else:
			c = _libclang.clang_getCursor(self._tu, source_location._sl)
		return Cursor(c, None, self)

	@requires(2.7, 'clang_tokenize', [c_void_p, _CXSourceRange, POINTER(POINTER(_CXToken)), POINTER(c_uint)])
	def tokenize(self, srcrange):
		tokens = POINTER(_CXToken)()
		length = c_uint()
		_libclang.clang_tokenize(self._tu, srcrange._sr, byref(tokens), byref(length))
		length = int(length.value)
		return TokenList(self, tokens, length)

	@staticmethod
	@requires(2.8, 'clang_defaultSaveOptions', [c_void_p], c_uint)
	def DEFAULT_SAVE_OPTIONS():
		value = _libclang.clang_defaultSaveOptions(self._tu)
		return SaveTranslationUnitFlags(value)

	@requires(2.8, 'clang_saveTranslationUnit', [c_void_p, c_utf8_p, c_uint], c_int)
	def save(self, filename, options=SaveTranslationUnitFlags.NONE):
		return bool(_libclang.clang_saveTranslationUnit(self._tu, filename, options.value))

	@staticmethod
	@requires(2.8, 'clang_defaultReparseOptions', [c_void_p], c_uint)
	def DEFAULT_REPARSE_OPTIONS():
		value = _libclang.clang_defaultReparseOptions(self._tu)
		return ReparseTranslationUnitFlags(value)

	@requires(2.8, 'clang_reparseTranslationUnit', [c_void_p, c_uint, POINTER(_CXUnsavedFile), c_uint], c_int)
	def reparse(self, unsaved_files, options=ReparseTranslationUnitFlags.NONE):
		unsavedc, unsavedv = _marshall_unsaved_files(unsaved_files)
		return bool(_libclang.clang_saveTranslationUnit(self._tu, unsavedc, unsavedv, options.value))

	@requires(3.0, 'clang_isFileMultipleIncludeGuarded', [c_void_p, c_void_p], c_uint)
	def is_multiple_include_guarded(self, srcfile):
		return bool(_libclang.clang_isFileMultipleIncludeGuarded(self._tu, srcfile._f))

class GlobalOptionFlags:
	@requires(3.1)
	def __init__(self, value):
		self.value = value

	@requires(3.1)
	def __or__(self, other):
		return GlobalOptionFlags(self.value | other.value)

	@requires(3.1)
	def __eq__(self, other):
		return self.value == other.value

	@requires(3.1)
	def __ne__(self, other):
		return self.value != other.value

	@requires(3.1)
	def __hash__(self):
		return hash(self.value)

GlobalOptionFlags.NONE = GlobalOptionFlags(0) # 3.1
GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_INDEXING = GlobalOptionFlags(1) # 3.1
GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_EDITING = GlobalOptionFlags(2) # 3.1
GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_ALL = GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_INDEXING | GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_EDITING # 3.1

class Index:
	@requires(2.7, 'clang_createIndex', [c_int, c_int], c_void_p)
	def __init__(self, exclude_from_pch=True, display_diagnostics=False):
		self._index = _libclang.clang_createIndex(exclude_from_pch, display_diagnostics)

	@requires(2.7, 'clang_disposeIndex', [c_void_p])
	def __del__(self):
		_libclang.clang_disposeIndex(self._index)

	@requires(2.7, 'clang_createTranslationUnit', [c_void_p, c_utf8_p], c_void_p)
	def from_ast(self, filename):
		tu = _libclang.clang_createTranslationUnit(self._index, filename)
		return TranslationUnit(tu, self)

	@requires(2.7, 'clang_createTranslationUnitFromSourceFile', [c_void_p, c_utf8_p, c_int, POINTER(c_utf8_p), c_uint, POINTER(_CXUnsavedFile)], c_void_p)
	def from_source(self, filename=None, args=None, unsaved_files=None):
		argc, argv = _marshall_args(args)
		unsavedc, unsavedv = _marshall_unsaved_files(unsaved_files)
		tu = _libclang.clang_createTranslationUnitFromSourceFile(self._index, filename, argc, argv, unsavedc, unsavedv)
		return TranslationUnit(tu, self)

	@requires(2.8, 'clang_parseTranslationUnit', [c_void_p, c_utf8_p, POINTER(c_utf8_p), c_uint, POINTER(_CXUnsavedFile), c_uint, c_uint], c_void_p)
	def parse(self, filename=None, args=None, unsaved_files=None, options=TranslationUnitFlags.NONE):
		argc, argv = _marshall_args(args)
		unsavedc, unsavedv = _marshall_unsaved_files(unsaved_files)
		tu = _libclang.clang_parseTranslationUnit(self._index, filename, argv, argc, unsavedv, unsavedc, options.value)
		return TranslationUnit(tu, self)

	@property
	@requires(3.1, 'clang_CXIndex_getGlobalOptions', [c_void_p], c_uint)
	def global_options(self):
		value = _libclang.clang_CXIndex_getGlobalOptions(self._index)
		return GlobalOptionFlags(value)

	@global_options.setter
	@requires(3.1, 'clang_CXIndex_setGlobalOptions', [c_void_p, c_uint])
	def global_options(self, options):
		_libclang.clang_CXIndex_setGlobalOptions(self._index, options.value)
