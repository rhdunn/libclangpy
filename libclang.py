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

class _CXCursor(Structure):
	_fields_ = [
		('kind', c_uint),
		('data', c_void_p * 3)
	]

cb_cursor_visitor = CFUNCTYPE(c_int, _CXCursor, _CXCursor, py_object)

def _marshall_args(args):
	if not args or len(args) == 0:
		return 0, None
	return len(args), (c_utf8_p * len(args))(*args)

def _marshall_unsaved_files(unsaved_files):
	if not unsaved_files or len(unsaved_files) == 0:
		return 0, None
	ret = (_CXUnsavedFile * len(unsaved_files))()
	for i, (name, contents) in enumerate(unsaved_files):
		if hasattr(contents, 'read'):
			contents = contents.read()
		ret[i].name = name
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

CursorKind.OBJC_SUPER_CLASS_REF = CursorKind(40) # 2.7
CursorKind.OBJC_PROTOCOL_REF = CursorKind(41) # 2.7
CursorKind.OBJC_CLASS_REF = CursorKind(42) # 2.7
CursorKind.TYPE_REF = CursorKind(43) # 2.7

CursorKind.INVALID_FILE = CursorKind(70) # 2.7
CursorKind.NO_DECL_FOUND = CursorKind(71) # 2.7
CursorKind.NOT_IMPLEMENTED = CursorKind(72) # 2.7

CursorKind.UNEXPOSED_EXPR = CursorKind(100) # 2.7
CursorKind.DECL_REF_EXPR = CursorKind(101) # 2.7
CursorKind.MEMBER_REF_EXPR = CursorKind(102) # 2.7
CursorKind.CALL_EXPR = CursorKind(103) # 2.7
CursorKind.OBJC_MESSAGE_EXPR = CursorKind(104) # 2.7

CursorKind.UNEXPOSED_STMT = CursorKind(200) # 2.7

CursorKind.TRANSLATION_UNIT = CursorKind(300) # 2.7

CursorKind.UNEXPOSED_ATTR = CursorKind(400) # 2.7
CursorKind.IB_ACTION_ATTR = CursorKind(401) # 2.7
CursorKind.IB_OUTLET_ATTR = CursorKind(402) # 2.7

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
