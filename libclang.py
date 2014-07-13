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

class _CXCursor(Structure):
	_fields_ = [
		('kind', c_uint),
		('data', c_void_p * 3)
	]

class _CXType(Structure):
	_fields_ = [
		('kind', c_uint),
		('data', c_void_p * 2)
	]

cb_cursor_visitor = CFUNCTYPE(c_int, _CXCursor, _CXCursor, py_object)

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

class SourceRange:
	@requires(2.7)
	def __init__(self, sr):
		self._sr = sr

	@requires(2.7)
	def __eq__(self, other):
		return self.start == other.start and self.end == other.end

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@staticmethod
	@requires(2.7, 'clang_getNullRange', [], _CXSourceRange)
	def null():
		sr = _libclang.clang_getNullRange()
		return SourceRange(sr)

	@staticmethod
	@requires(2.7, 'clang_getRange', [_CXSourceLocation, _CXSourceLocation], _CXSourceRange)
	def create(start, end):
		sr = _libclang.clang_getRange(start._sl, end._sl)
		return SourceRange(sr)

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

	@staticmethod
	@requires(2.7, 'clang_defaultDiagnosticDisplayOptions', [], c_uint)
	def DEFAULT():
		value = _libclang.clang_defaultDiagnosticDisplayOptions()
		return DiagnosticDisplayOptions(value)

DiagnosticDisplayOptions.SOURCE_LOCATION = DiagnosticDisplayOptions(1) # 2.7
DiagnosticDisplayOptions.COLUMN = DiagnosticDisplayOptions(2) # 2.7
DiagnosticDisplayOptions.SOURCE_RANGES = DiagnosticDisplayOptions(4) # 2.7

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

DiagnosticSeverity.IGNORED = DiagnosticSeverity(0) # 2.7
DiagnosticSeverity.NOTE = DiagnosticSeverity(1) # 2.7
DiagnosticSeverity.WARNING = DiagnosticSeverity(2) # 2.7
DiagnosticSeverity.ERROR = DiagnosticSeverity(3) # 2.7
DiagnosticSeverity.FATAL = DiagnosticSeverity(4) # 2.7

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
			yield SourceRange(sr)

	@property
	@requires(2.7, 'clang_getDiagnosticNumFixIts', [c_void_p], c_uint)
	@requires(2.7, 'clang_getDiagnosticFixIt', [c_void_p, c_uint, POINTER(_CXSourceRange)], _CXString)
	def fixits(self):
		for i in range(0, _libclang.clang_getDiagnosticNumFixIts(self._d)):
			sr = _CXSourceRange()
			s  = _libclang.clang_getDiagnosticFixIt(self._d, i, byref(sr))
			yield (SourceRange(sr), _to_str(s))

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

TokenKind.PUNCTUATION = TokenKind(0) # 2.7
TokenKind.KEYWORD = TokenKind(1) # 2.7
TokenKind.IDENTIFIER = TokenKind(2) # 2.7
TokenKind.LITERAL = TokenKind(3) # 2.7
TokenKind.COMMENT = TokenKind(4) # 2.7

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
		return SourceRange(sr)

	@property
	@requires(2.7, 'clang_getCursor', [c_void_p, _CXSourceLocation], _CXCursor)
	def cursor(self):
		# NOTE: This is doing what clang_annotateTokens does, but on one token only.
		c = _libclang.clang_getCursor(self._tu._tu, self.location._sl)
		return Cursor(c, None, self._tu)

class TokenList:
	@requires(2.7)
	def __init__(self, tu, tokens, length):
		self._tu = tu
		self._data = tokens
		self._tokens = cast(tokens, POINTER(_CXToken * length)).contents
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

CursorKind.OBJC_SUPER_CLASS_REF = CursorKind(40) # 2.7
CursorKind.OBJC_PROTOCOL_REF = CursorKind(41) # 2.7
CursorKind.OBJC_CLASS_REF = CursorKind(42) # 2.7
CursorKind.TYPE_REF = CursorKind(43) # 2.7
CursorKind.CXX_BASE_SPECIFIER = CursorKind(44) # 2.8
CursorKind.TEMPLATE_REF = CursorKind(45) # 2.8
CursorKind.NAMESPACE_REF = CursorKind(46) # 2.8

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

CursorKind.UNEXPOSED_STMT = CursorKind(200) # 2.7

CursorKind.TRANSLATION_UNIT = CursorKind(300) # 2.7

CursorKind.UNEXPOSED_ATTR = CursorKind(400) # 2.7
CursorKind.IB_ACTION_ATTR = CursorKind(401) # 2.7
CursorKind.IB_OUTLET_ATTR = CursorKind(402) # 2.7
CursorKind.IB_OUTLET_COLLECTION_ATTR = CursorKind(403) # 2.8

CursorKind.PREPROCESSING_DIRECTIVE = CursorKind(500) # 2.8
CursorKind.MACRO_DEFINITION = CursorKind(501) # 2.8
CursorKind.MACRO_INSTANTIATION = CursorKind(502) # 2.8

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
	@requires(2.8, 'clang_getTypeDeclaration', [_CXType], _CXCursor)
	def declaration(self):
		c = _libclang.clang_getTypeDeclaration(self._t)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.8, 'clang_isPODType', [_CXType], c_uint)
	def is_pod(self):
		return bool(_libclang.clang_isPODType(self._t))

class Cursor:
	@requires(2.7)
	def __init__(self, c, parent, tu):
		self._c = c
		self.parent = parent
		self._tu = tu

	@requires(2.7, 'clang_equalCursors', [_CXCursor, _CXCursor], c_uint)
	def __eq__(self, other):
		return bool(_libclang.clang_equalCursors(self._c, other._c))

	@requires(2.7)
	def __ne__(self, other):
		return not self == other

	@requires(2.7)
	def __str__(self):
		return self.spelling

	@staticmethod
	@requires(2.7, 'clang_getNullCursor', [], _CXCursor)
	def null():
		c = _libclang.clang_getNullCursor()
		return Cursor(c, None, None)

	@property
	@requires(2.7, 'clang_getCursorKind', [_CXCursor], c_uint)
	def kind(self):
		kind = _libclang.clang_getCursorKind(self._c)
		return CursorKind(kind)

	@property
	@requires(2.7, 'clang_getCursorLinkage', [_CXCursor], c_uint)
	def linkage(self):
		return Linkage(_libclang.clang_getCursorLinkage(self._c))

	@property
	@requires(2.7, 'clang_getCursorLocation', [_CXCursor], _CXSourceLocation)
	def location(self):
		sl = _libclang.clang_getCursorLocation(self._c)
		return SourceLocation(sl)

	@property
	@requires(2.7, 'clang_getCursorExtent', [_CXCursor], _CXSourceRange)
	def extent(self):
		sr = _libclang.clang_getCursorExtent(self._c)
		return SourceRange(sr)

	@property
	@requires(2.7, 'clang_visitChildren', [_CXCursor, cb_cursor_visitor, py_object], c_uint)
	def children(self):
		def visitor(child, parent_cursor, args):
			(children, parent) = args
			c = Cursor(child, parent, self._tu)
			if c != Cursor.null():
				children.append(c)
			return 1 # continue
		ret = []
		_libclang.clang_visitChildren(self._c, cb_cursor_visitor(visitor), (ret, self))
		return ret

	@property
	@requires(2.7, 'clang_getCursorUSR', [_CXCursor], _CXString)
	def usr(self):
		s = _libclang.clang_getCursorUSR(self._c)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getCursorSpelling', [_CXCursor], _CXString)
	def spelling(self):
		s = _libclang.clang_getCursorSpelling(self._c)
		return _to_str(s)

	@property
	@requires(2.7, 'clang_getCursorReferenced', [_CXCursor], _CXCursor)
	def referenced(self):
		c = _libclang.clang_getCursorReferenced(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.7, 'clang_getCursorDefinition', [_CXCursor], _CXCursor)
	def definition(self):
		c = _libclang.clang_getCursorDefinition(self._c)
		return Cursor(c, None, self._tu)

	@property
	@requires(2.7, 'clang_isCursorDefinition', [_CXCursor], c_uint)
	def is_definition(self):
		return bool(_libclang.clang_isCursorDefinition(self._c))

	@property
	@requires(2.7)
	def tokens(self):
		return self._tu.tokenize(self.extent)

	@property
	@requires(2.8, 'clang_getCursorType', [_CXCursor], _CXType)
	def type(self):
		t = _libclang.clang_getCursorType(self._c)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getCursorResultType', [_CXCursor], _CXType)
	def result_type(self):
		t = _libclang.clang_getCursorResultType(self._c)
		return Type(t, self._tu)

	@property
	@requires(2.8, 'clang_getIBOutletCollectionType', [_CXCursor], _CXType)
	def ib_outlet_collection_type(self):
		t = _libclang.clang_getIBOutletCollectionType(self._c)
		return Type(t, self._tu)

class TranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.8)
	def __or__(self, other):
		return TranslationUnitFlags(self.value | other.value)

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

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

class SaveTranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

SaveTranslationUnitFlags.NONE = SaveTranslationUnitFlags(0) # 2.8

class ReparseTranslationUnitFlags:
	@requires(2.8)
	def __init__(self, value):
		self.value = value

	@requires(2.7)
	def __eq__(self, other):
		return self.value == other.value

	@requires(2.7)
	def __ne__(self, other):
		return self.value != other.value

ReparseTranslationUnitFlags.NONE = ReparseTranslationUnitFlags(0) # 2.8

class TranslationUnit:
	@requires(2.7)
	def __init__(self, tu):
		self._tu = tu

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
	def location(self, cxfile, line, column):
		ret = _libclang.clang_getLocation(self._tu, cxfile._f, line, column)
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

	@requires(2.7, 'clang_getTranslationUnitCursor', [c_void_p], _CXCursor)
	@requires(2.7, 'clang_getCursor', [c_void_p, _CXSourceLocation], _CXCursor)
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
		if length < 1:
			return None
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

class Index:
	@requires(2.7, 'clang_createIndex', [c_int, c_int], c_void_p)
	def __init__(self, exclude_from_pch=True, display_diagnostics=False):
		self._index = _libclang.clang_createIndex(exclude_from_pch, display_diagnostics)

	@requires(2.7, 'clang_disposeIndex', [c_void_p])
	def __del__(self):
		_libclang.clang_disposeIndex(self._index)

	@requires(2.7, 'clang_setUseExternalASTGeneration', [c_void_p, c_int])
	def use_external_ast_generation(self, use_external_ast):
		_libclang.clang_setUseExternalASTGeneration(self._index, use_external_ast)

	@requires(2.7, 'clang_createTranslationUnit', [c_void_p, c_utf8_p], c_void_p)
	def from_ast(self, filename):
		tu = _libclang.clang_createTranslationUnit(self._index, filename)
		return TranslationUnit(tu)

	@requires(2.7, 'clang_createTranslationUnitFromSourceFile', [c_void_p, c_utf8_p, c_int, POINTER(c_utf8_p), c_uint, POINTER(_CXUnsavedFile)], c_void_p)
	def from_source(self, filename=None, args=None, unsaved_files=None):
		argc, argv = _marshall_args(args)
		unsavedc, unsavedv = _marshall_unsaved_files(unsaved_files)
		tu = _libclang.clang_createTranslationUnitFromSourceFile(self._index, filename, argc, argv, unsavedc, unsavedv)
		return TranslationUnit(tu)

	@requires(2.8, 'clang_parseTranslationUnit', [c_void_p, c_utf8_p, POINTER(c_utf8_p), c_uint, POINTER(_CXUnsavedFile), c_uint, c_uint], c_void_p)
	def parse(self, filename=None, args=None, unsaved_files=None, options=TranslationUnitFlags.NONE):
		argc, argv = _marshall_args(args)
		unsavedc, unsavedv = _marshall_unsaved_files(unsaved_files)
		tu = _libclang.clang_parseTranslationUnit(self._index, filename, argv, argc, unsavedv, unsavedc, options.value)
		return TranslationUnit(tu)
