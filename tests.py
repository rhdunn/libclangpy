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

import sys
import traceback

import libclang

class UnsupportedException(Exception):
	pass

class ParseError(UnsupportedException):
	pass

if sys.version_info.major >= 3:
	long = int

def equals(a, b):
	ta, tb = type(a), type(b)
	if ta.__name__ != tb.__name__:
		raise AssertionError('Type mismatch: `{0}` != `{1}`'.format(ta.__name__, tb.__name__))
	if a != b:
		raise AssertionError('Value mismatch: `{0}` != `{1}`'.format(str(a), str(b)))

def oneof(a, items):
	for item in items:
		if a != item:
			continue
		ta, tb = type(a), type(item)
		if ta.__name__ != tb.__name__:
			raise AssertionError('Type mismatch: `{0}` != `{1}`'.format(ta.__name__, tb.__name__))
		return
	itemstr = ', '.join(['`{0}`'.format(str(item)) for item in items])
	raise AssertionError('Value mismatch: `{0}` not in [{1}]'.format(str(a), itemstr))

_passed  = 0
_skipped = 0
_failed  = 0

def run(version, test):
	global _passed
	global _skipped
	global _failed
	sys.stdout.write('Running {0} ... '.format(test.__name__))
	try:
		test()
		print('passed')
		_passed = _passed + 1
	except libclang.MissingFunction:
		if libclang.version < version:
			print('skipping ... missing APIs')
			_skipped = _skipped + 1
		else:
			print('failed ... incorrect API binding')
			_failed = _failed + 1
	except UnsupportedException as e:
		if libclang.version < version:
			print('skipping ... {0}'.format(e))
			_skipped = _skipped + 1
		else:
			print('failed ... {0}'.format(e))
			_failed = _failed + 1
	except Exception as e:
		print('failed')
		print(traceback.format_exc())
		_failed = _failed + 1

def summary():
	print('-'*60)
	print('   {0} passed, {1} skipped, {2} failed'.format(_passed, _skipped, _failed))
	print('')

def parse_str(contents, filename='parse_str.cpp', args=None, ignore_errors=False):
	index = libclang.Index()
	tu = index.from_source(filename, unsaved_files=[(filename, contents)], args=args)
	if not ignore_errors:
		diagnostics = list(tu.diagnostics)
		if len(diagnostics) > 0:
			raise ParseError(diagnostics[0].spelling)
	return [child for child in tu.cursor().children if child.location.file]

def match_location(loc, filename, line, column, offset):
	if isinstance(loc.file, libclang.File):
		equals(loc.file.name, filename)
	else:
		equals(loc.file, filename)
	equals(loc.line, line)
	equals(loc.column, column)
	equals(loc.offset, offset)

def match_tokens(a, b):
	tokens = [str(t) for t in a]
	equals(tokens, b)

def match_type(a, b):
	equals(isinstance(a, libclang.Type), True)
	if a.kind == libclang.TypeKind.UNEXPOSED:
		raise UnsupportedException('type is not supported')
	equals(a.kind, b)

def match_cursor(a, b):
	equals(isinstance(a, libclang.Cursor), True)
	if a.kind in [libclang.CursorKind.UNEXPOSED_DECL,
	              libclang.CursorKind.UNEXPOSED_EXPR,
	              libclang.CursorKind.UNEXPOSED_STMT,
	              libclang.CursorKind.UNEXPOSED_ATTR]:
		raise UnsupportedException('cursor is not supported')
	equals(a.kind, b)

def test_version():
	oneof(libclang.version, [2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5])

def test_File(f, filename):
	equals(f.name, filename)
	equals(f.time > 0, True)
	equals(str(f), filename)
	equals(f == f, True)
	equals(f != f, False)
	equals(f == filename, True)
	equals(f != filename, False)

def test_SourceLocation():
	loc = libclang.SourceLocation.null()
	match_location(loc, None, 0, 0, 0)
	match_location(loc.instantiation_location, None, 0, 0, 0)
	equals(loc == libclang.SourceLocation.null(), True)
	equals(loc != libclang.SourceLocation.null(), False)
	equals(loc.is_null, True)

def test_SourceLocation29():
	loc = libclang.SourceLocation.null()
	match_location(loc.spelling_location, None, 0, 0, 0)

def test_SourceLocation30():
	loc = libclang.SourceLocation.null()
	match_location(loc.presumed_location, '', 0, 0, 0)

def test_SourceLocation31():
	loc = libclang.SourceLocation.null()
	match_location(loc.expansion_location, None, 0, 0, 0)

def test_SourceLocation33():
	loc = libclang.SourceLocation.null()
	equals(loc.is_in_system_header, False)
	match_location(loc.file_location, None, 0, 0, 0)

def test_SourceLocation34():
	loc = libclang.SourceLocation.null()
	equals(loc.is_from_main_file, False)

def test_SourceRange():
	rng1 = libclang.SourceRange.null()
	equals(rng1.start, libclang.SourceLocation.null())
	equals(rng1.end,   libclang.SourceLocation.null())
	rng2 = libclang.SourceRange(libclang.SourceLocation.null(),
	                            libclang.SourceLocation.null())
	equals(rng2.start, libclang.SourceLocation.null())
	equals(rng2.end,   libclang.SourceLocation.null())
	equals(rng1 == rng2, True)
	equals(rng1 != rng2, False)
	equals(rng1.is_null, True)

def test_DiagnosticDisplayOptions():
	a = libclang.DiagnosticDisplayOptions.COLUMN
	b = libclang.DiagnosticDisplayOptions.SOURCE_RANGES
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 6)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'DiagnosticDisplayOptions(2)')

def test_DiagnosticSeverity():
	a = libclang.DiagnosticSeverity.NOTE
	b = libclang.DiagnosticSeverity.ERROR
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'DiagnosticSeverity(1)')

def test_DiagnosticCategory29():
	a = libclang.DiagnosticCategory(1)
	b = libclang.DiagnosticCategory(2)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	oneof(a.name, [
		'Parse Issue', # 2.9 or earlier
		'Lexical or Preprocessor Issue']) # 3.0 or later
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'DiagnosticCategory(1)')

def test_Linkage():
	a = libclang.Linkage.NO_LINKAGE
	b = libclang.Linkage.INTERNAL
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'Linkage(1)')

def test_TokenKind():
	a = libclang.TokenKind.KEYWORD
	b = libclang.TokenKind.LITERAL
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'TokenKind(1)')

def test_CursorKind():
	equals(libclang.CursorKind.CLASS_DECL == libclang.CursorKind.CLASS_DECL, True)
	equals(libclang.CursorKind.CLASS_DECL == libclang.CursorKind.UNION_DECL, False)
	equals(libclang.CursorKind.CLASS_DECL != libclang.CursorKind.CLASS_DECL, False)
	equals(libclang.CursorKind.CLASS_DECL != libclang.CursorKind.UNION_DECL, True)
	kind = libclang.CursorKind.STRUCT_DECL
	equals(kind.spelling, 'StructDecl')
	equals(str(kind), 'StructDecl')
	equals(kind.is_declaration, True)
	equals(kind.is_reference, False)
	equals(kind.is_expression, False)
	equals(kind.is_statement, False)
	equals(kind.is_invalid, False)
	equals(kind.is_translation_unit, False)
	a = libclang.CursorKind.VAR_DECL
	b = libclang.CursorKind.FIELD_DECL
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'CursorKind(9|VarDecl)')

def test_CursorKind28():
	kind = libclang.CursorKind.STRUCT_DECL
	equals(kind.is_preprocessing, False)
	equals(kind.is_unexposed, False)

def test_CursorKind30():
	kind = libclang.CursorKind.STRUCT_DECL
	equals(kind.is_attribute, False)

def test_TypeKind28():
	equals(libclang.TypeKind.VOID == libclang.TypeKind.VOID, True)
	equals(libclang.TypeKind.VOID == libclang.TypeKind.UINT, False)
	equals(libclang.TypeKind.VOID != libclang.TypeKind.VOID, False)
	equals(libclang.TypeKind.VOID != libclang.TypeKind.UINT, True)
	kind = libclang.TypeKind.FLOAT
	equals(kind.spelling, 'Float')
	equals(str(kind), 'Float')
	a = libclang.TypeKind.LONG
	b = libclang.TypeKind.SHORT
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'TypeKind(18|Long)')

def test_AvailabilityKind28():
	a = libclang.AvailabilityKind.DEPRECATED
	b = libclang.AvailabilityKind.NOT_AVAILABLE
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'AvailabilityKind(1)')

def test_LanguageKind28():
	a = libclang.LanguageKind.C
	b = libclang.LanguageKind.OBJC
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'LanguageKind(1)')

def test_AccessSpecifier28():
	a = libclang.AccessSpecifier.PUBLIC
	b = libclang.AccessSpecifier.PRIVATE
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'AccessSpecifier(1)')

def test_NameRefFlags30():
	a = libclang.NameRefFlags.WANT_QUALIFIER
	b = libclang.NameRefFlags.WANT_TEMPLATE_ARGS
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals((a | b).value, 3)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'NameRefFlags(1)')

def test_TranslationUnitFlags28():
	a = libclang.TranslationUnitFlags.INCOMPLETE
	b = libclang.TranslationUnitFlags.CACHE_COMPLETION_RESULTS
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'TranslationUnitFlags(2)')

def test_SaveTranslationUnitFlags28():
	a = libclang.SaveTranslationUnitFlags(2)
	b = libclang.SaveTranslationUnitFlags(8)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'SaveTranslationUnitFlags(2)')

def test_ReparseTranslationUnitFlags28():
	a = libclang.ReparseTranslationUnitFlags(2)
	b = libclang.ReparseTranslationUnitFlags(8)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'ReparseTranslationUnitFlags(2)')

def test_GlobalOptionFlags31():
	a = libclang.GlobalOptionFlags(2)
	b = libclang.GlobalOptionFlags(8)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'GlobalOptionFlags(2)')

def test_CallingConvention31():
	a = libclang.CallingConvention.X86_STDCALL
	b = libclang.CallingConvention.C
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'CallingConvention(2)')

def test_ObjCPropertyAttributes33():
	a = libclang.ObjCPropertyAttributes(2)
	b = libclang.ObjCPropertyAttributes(8)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'ObjCPropertyAttributes(2)')

def test_ObjCDeclQualifierKind33():
	a = libclang.ObjCDeclQualifierKind(2)
	b = libclang.ObjCDeclQualifierKind(8)
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 2)
	equals((a | b).value, 10)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'ObjCDeclQualifierKind(2)')

def test_RefQualifierKind34():
	a = libclang.RefQualifierKind.LVALUE
	b = libclang.RefQualifierKind.RVALUE
	equals(a == a, True)
	equals(a == b, False)
	equals(a != a, False)
	equals(a != b, True)
	equals(a.value, 1)
	equals(hash(a) == hash(a), True)
	equals(hash(a) == hash(b), False)
	equals(repr(a), 'RefQualifierKind(1)')

def test_Index():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	# no args
	tu = index.from_source(filename)
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# no args -- as keyword argument
	tu = index.from_source(filename=filename)
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# file as arg
	tu = index.from_source(args=[filename])
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# args
	tu = index.from_source(filename, args=['-std=c++98'])
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# unsaved files
	tu = index.from_source('unsaved.hpp', unsaved_files=[('unsaved.hpp', 'struct test {};')])
	equals(tu.spelling, 'unsaved.hpp')
	equals(len(list(tu.diagnostics)), 0)
	# unsaved files
	tu = index.from_source('unsaved.cpp', unsaved_files=[('unsaved.cpp', 'struct test {};')])
	equals(tu.spelling, 'unsaved.cpp')
	equals(len(list(tu.diagnostics)), 0)

def test_Index28():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	# no args
	tu = index.parse(filename)
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# no args -- as keyword argument
	tu = index.parse(filename=filename)
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# file as arg
	tu = index.parse(args=[filename])
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# args
	tu = index.parse(filename, args=['-std=c++98'])
	equals(tu.spelling, filename)
	equals(len(list(tu.diagnostics)), 0)
	# unsaved files
	tu = index.parse('unsaved.hpp', unsaved_files=[('unsaved.hpp', 'struct test {};')])
	equals(tu.spelling, 'unsaved.hpp')
	equals(len(list(tu.diagnostics)), 0)
	# unsaved files
	tu = index.parse('unsaved.cpp', unsaved_files=[('unsaved.cpp', 'struct test {};')])
	equals(tu.spelling, 'unsaved.cpp')
	equals(len(list(tu.diagnostics)), 0)

def test_Index31():
	index = libclang.Index()
	equals(index.global_options, libclang.GlobalOptionFlags.NONE)
	index.global_options = libclang.GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_INDEXING
	equals(index.global_options, libclang.GlobalOptionFlags.THREAD_BACKGROUND_PRIORITY_FOR_INDEXING)

def test_TranslationUnit():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	equals(tu.spelling, filename)
	equals(str(tu), filename)
	test_File(tu.file(filename), filename)
	match_location(tu.location(tu.file(filename), 3, 2), filename, 3, 2, 13)
	match_location(tu.location(tu.file(filename), line=3, column=2), filename, 3, 2, 13)
	match_location(tu.location(filename, 3, 2), filename, 3, 2, 13)
	match_location(tu.location(filename, line=3, column=2), filename, 3, 2, 13)
	match_location(tu.location(tu.spelling, 3, 2), filename, 3, 2, 13)
	match_location(tu.location(tu.spelling, line=3, column=2), filename, 3, 2, 13)
	equals(list(tu.diagnostics), [])

def test_TranslationUnit29():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	match_location(tu.location(tu.file(filename), offset=13), filename, 3, 2, 13)

def test_TranslationUnit30():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	equals(tu.is_multiple_include_guarded(tu.file(filename)), False)

def test_Diagnostic():
	index = libclang.Index()
	tu = index.from_source('tests/error.hpp')
	diagnostics = list(tu.diagnostics)
	equals(len(diagnostics), 1)
	d = diagnostics[0]
	equals(d.spelling, 'expected \';\' after struct')
	equals(str(d), 'expected \';\' after struct')
	equals(d.format(),
	       'tests/error.hpp:3:2: error: expected \';\' after struct')
	equals(d.format(libclang.DiagnosticDisplayOptions.SOURCE_LOCATION),
	       'tests/error.hpp:3: error: expected \';\' after struct')
	equals(d.severity, libclang.DiagnosticSeverity.ERROR)
	match_location(d.location, 'tests/error.hpp', 3, 2, 16)
	# ranges
	r = list(d.ranges)
	equals(len(r), 0)
	# fixits
	f = list(d.fixits)
	equals(len(f), 1)
	match_location(f[0].extent.start, 'tests/error.hpp', 3, 2, 16)
	match_location(f[0].extent.end, 'tests/error.hpp', 3, 2, 16)
	equals(f[0].spelling, ';')

def test_Diagnostic29():
	index = libclang.Index()
	tu = index.from_source('tests/error.hpp')
	diagnostics = list(tu.diagnostics)
	equals(len(diagnostics), 1)
	d = diagnostics[0]
	equals(d.option, '')
	equals(d.disable_option, '')
	equals(d.category.name, 'Parse Issue')
	equals(d.category_text, 'Parse Issue')

def test_Cursor():
	c = parse_str('enum test { a, b };', filename='tests/enumeration.hpp')[0]
	equals(c == c, True)
	equals(c == libclang.Cursor.null(), False)
	equals(c != c, False)
	equals(c != libclang.Cursor.null(), True)
	equals(c.is_null, False)
	equals(hash(c), hash(c))
	equals(c.spelling, 'test')
	equals(str(c), 'test')
	equals(c.kind, libclang.CursorKind.ENUM_DECL)
	equals(c.parent.kind, libclang.CursorKind.TRANSLATION_UNIT)
	equals(c.linkage, libclang.Linkage.EXTERNAL)
	match_location(c.location, 'tests/enumeration.hpp', 1, 6, 5)
	match_location(c.extent.start, 'tests/enumeration.hpp', 1, 1, 0)
	match_location(c.extent.end, 'tests/enumeration.hpp', 1, 1, 0)
	equals(c.usr, 'c:@E@test')
	equals(c.referenced, c)
	equals(c.definition, c)
	equals(c.is_definition, True)
	equals(c.translation_unit.spelling, 'tests/enumeration.hpp')
	# children
	children = [child for child in c.children if child.location.file]
	equals(len(children), 2)
	equals(children[0].kind, libclang.CursorKind.ENUM_CONSTANT_DECL)
	equals(children[0].parent, c)
	# tokens
	c = parse_str('enum test { x, y = 3, z };')[0]
	x, y, z = c.children
	match_tokens(c.tokens, ['enum', 'test', '{', 'x', ',', 'y', '=', '3', ',', 'z', '}', ';'])
	match_tokens(x.tokens, ['x', ','])
	match_tokens(y.tokens, ['y', '=', '3', ','])
	match_tokens(z.tokens, ['z', '}'])
	match_tokens(c.tokens_left_of_children, ['enum', 'test', '{', 'x'])
	match_tokens(x.tokens_left_of_children, ['x', ','])
	match_tokens(y.tokens_left_of_children, ['y', '=', '3'])
	match_tokens(z.tokens_left_of_children, ['z', '}'])
	# tokens
	c = parse_str('extern "C" void f(int x, int y);')[0]
	f = c.children[0]
	x, y = f.children
	if libclang.version <= 2.8:
		match_tokens(c.tokens, ['"C"', 'void'])
		match_tokens(f.tokens, ['f', '(', 'int', 'x', ',', 'int', 'y', ')', ';'])
		match_tokens(c.tokens_left_of_children, ['"C"', 'void', 'f'])
		match_tokens(f.tokens_left_of_children, ['f', '(', 'int'])
	elif libclang.version == 2.9:
		match_tokens(c.tokens, ['"C"', 'void', 'f', '(', 'int', 'x', ',', 'int', 'y', ')', ';'])
		match_tokens(f.tokens, ['f', '(', 'int', 'x', ',', 'int', 'y', ')', ';'])
		match_tokens(c.tokens_left_of_children, ['"C"', 'void', 'f'])
		match_tokens(f.tokens_left_of_children, ['f', '(', 'int'])
	else:
		match_tokens(c.tokens, ['extern', '"C"', 'void', 'f', '(', 'int', 'x', ',', 'int', 'y', ')', ';'])
		match_tokens(f.tokens, ['void', 'f', '(', 'int', 'x', ',', 'int', 'y', ')', ';'])
		match_tokens(c.tokens_left_of_children, ['extern', '"C"', 'void'])
		match_tokens(f.tokens_left_of_children, ['void', 'f', '(', 'int'])
	match_tokens(x.tokens, ['int', 'x', ','])
	match_tokens(y.tokens, ['int', 'y', ')'])
	match_tokens(x.tokens_left_of_children, ['int', 'x', ','])
	match_tokens(y.tokens_left_of_children, ['int', 'y', ')'])

def test_Cursor28():
	c = parse_str('enum test {};')[0]
	equals(c.type.kind, libclang.TypeKind.ENUM)
	equals(c.result_type.kind, libclang.TypeKind.INVALID)
	equals(c.ib_outlet_collection_type.kind, libclang.TypeKind.INVALID)
	equals(c.availability, libclang.AvailabilityKind.AVAILABLE)
	equals(c.language, libclang.LanguageKind.C)
	equals(c.access_specifier, libclang.AccessSpecifier.INVALID)
	equals(c.template_kind, libclang.CursorKind.NO_DECL_FOUND)
	equals(c.specialized_template.kind, libclang.CursorKind.INVALID_FILE)
	equals(c.is_virtual_base, False)
	equals(c.is_static_method, False)

def test_Cursor29():
	c = parse_str('enum test { a };')[0]
	a = c.children[0]
	equals(a.semantic_parent, c)
	equals(a.lexical_parent, c)
	equals(c.included_file.name, None)
	equals(c.objc_type_encoding, '?')
	equals(len(list(c.overloads)), 0)
	equals(c.display_name, 'test')
	equals(c.canonical, c)
	equals(len(c.overridden), 0)

def test_Cursor30():
	c = parse_str('enum test {};', filename='cursor30.hpp')[0]
	equals(c.is_virtual, False)
	rng = c.reference_name_range(libclang.NameRefFlags.WANT_TEMPLATE_ARGS, 0)
	match_location(rng.start, 'cursor30.hpp', 1, 1, 0)
	match_location(rng.end, 'cursor30.hpp', 1, 1, 0)

def test_Cursor31():
	c = parse_str('enum test { a = 7 };', filename='cursor31.hpp')[0]
	equals(len(list(c.arguments)), 0)
	equals(c.objc_selector_index, -1)
	rng = c.spelling_name_range(libclang.NameRefFlags.WANT_TEMPLATE_ARGS, 0)
	match_location(rng.start, 'cursor31.hpp', 1, 6, 5)
	match_location(rng.end, 'cursor31.hpp', 1, 6, 5)

def test_Cursor32():
	c = parse_str('enum test {};', filename='cursor32.hpp')[0]
	equals(c.is_dynamic_call, False)
	equals(c.receiver_type.kind, libclang.TypeKind.INVALID)
	match_location(c.comment_range.start, None, 0, 0, 0)
	match_location(c.comment_range.end, None, 0, 0, 0)
	equals(c.raw_comment, None)
	equals(c.brief_comment, None)

def test_Cursor33():
	c = parse_str('enum test {};', filename='cursor33.hpp')[0]
	equals(c.is_bit_field, False)
	equals(c.bit_field_width, -1)
	equals(c.is_variadic, False)
	equals(c.objc_property_attributes, libclang.ObjCPropertyAttributes.NO_ATTR)
	equals(c.objc_decl_qualifiers, libclang.ObjCDeclQualifierKind.NONE)

def test_Cursor34():
	c = parse_str('enum test {};', filename='cursor34.hpp')[0]
	equals(c.is_objc_optional, False)
	equals(c.is_pure_virtual, False)

def test_StructDecl27():
	x = parse_str('struct x { int a; };')[0]
	# x
	match_cursor(x, libclang.CursorKind.STRUCT_DECL)
	equals(isinstance(x, libclang.RecordDecl), True)
	equals(isinstance(x, libclang.StructDecl), True)

def test_UnionDecl27():
	x = parse_str('union x { int a; };')[0]
	# x
	match_cursor(x, libclang.CursorKind.UNION_DECL)
	equals(isinstance(x, libclang.RecordDecl), True)
	equals(isinstance(x, libclang.UnionDecl), True)

def test_ClassDecl27():
	x = parse_str('class x { int a; };')[0]
	# x
	match_cursor(x, libclang.CursorKind.CLASS_DECL)
	equals(isinstance(x, libclang.RecordDecl), True)
	equals(isinstance(x, libclang.ClassDecl), True)

def test_EnumDecl27():
	x = parse_str('enum x { a = 7 };')[0]
	# x
	match_cursor(x, libclang.CursorKind.ENUM_DECL)
	equals(isinstance(x, libclang.RecordDecl), False) # Does not support fields, methods, etc.
	equals(isinstance(x, libclang.EnumDecl), True)
	equals(x.is_enum_class, False)

def test_EnumDecl29():
	x, y = parse_str("""
		enum class x { b };
		enum class y : unsigned char { c };""", args=['-std=c++11'])
	# x
	match_cursor(x, libclang.CursorKind.ENUM_DECL)
	equals(isinstance(x, libclang.EnumDecl), True)
	equals(x.is_enum_class, True)
	# y
	match_cursor(y, libclang.CursorKind.ENUM_DECL)
	equals(isinstance(y, libclang.EnumDecl), True)
	equals(y.is_enum_class, True)

def test_EnumDecl31():
	x, y, z = parse_str("""
		enum x { a = 7 };
		enum class y { b };
		enum class z : unsigned char { c };""", args=['-std=c++11'])
	equals(x.enum_type.kind, libclang.TypeKind.UINT)
	equals(y.enum_type.kind, libclang.TypeKind.INT)
	equals(z.enum_type.kind, libclang.TypeKind.UCHAR)

def test_FieldDecl27():
	x = parse_str('struct x { int a; };')[0]
	a = x.children[0]
	# a
	match_cursor(a, libclang.CursorKind.FIELD_DECL)
	equals(isinstance(a, libclang.VarDecl), True)
	equals(isinstance(a, libclang.FieldDecl), True)

def test_EnumConstantDecl27():
	x = parse_str('enum x { a = 7 };')[0]
	a = x.children[0]
	# a
	match_cursor(a, libclang.CursorKind.ENUM_CONSTANT_DECL)
	equals(isinstance(a, libclang.EnumConstantDecl), True)
	equals(a.type.kind, libclang.TypeKind.ENUM)

def test_EnumConstantDecl29():
	x, y = parse_str("""
		enum class x : short { b = 2 };
		enum class y : unsigned char { c = 158 };""", args=['-std=c++11'])
	a = x.children[0]
	b = y.children[0]
	# a
	match_cursor(a, libclang.CursorKind.ENUM_CONSTANT_DECL)
	equals(isinstance(a, libclang.EnumConstantDecl), True)
	equals(a.type.kind, libclang.TypeKind.ENUM)
	# b
	match_cursor(b, libclang.CursorKind.ENUM_CONSTANT_DECL)
	equals(isinstance(b, libclang.EnumConstantDecl), True)
	equals(b.type.kind, libclang.TypeKind.ENUM)

def test_EnumConstantDecl31():
	x, y, z = parse_str("""
		enum x { a = 7 };
		enum class y : short { b = 2 };
		enum class z : unsigned char { c = 158 };""", args=['-std=c++11'])
	equals(x.children[0].enum_value, long(7))
	equals(y.children[0].enum_value, 2)
	equals(z.children[0].enum_value, long(158))

def test_FunctionDecl27():
	f = parse_str('void f(int x);')[0]
	# f
	match_cursor(f, libclang.CursorKind.FUNCTION_DECL)
	equals(isinstance(f, libclang.FunctionDecl), True)

def test_VarDecl27():
	x = parse_str('int x;')[0]
	# x
	match_cursor(x, libclang.CursorKind.VAR_DECL)
	equals(isinstance(x, libclang.VarDecl), True)

def test_ParmDecl27():
	f = parse_str('void f(int x);')[0]
	x = f.children[0]
	# x
	match_cursor(x, libclang.CursorKind.PARM_DECL)
	equals(isinstance(x, libclang.VarDecl), True)
	equals(isinstance(x, libclang.ParmDecl), True)

def test_ObjCInterfaceDecl27():
	x = parse_str('@interface x @end', args=['-ObjC'])[0]
	# x
	match_cursor(x, libclang.CursorKind.OBJC_INTERFACE_DECL)
	equals(isinstance(x, libclang.ObjCInterfaceDecl), True)

def test_ObjCCategoryDecl27():
	x, c = parse_str("""
		@interface x @end
		@interface x (c) @end""", args=['-ObjC'])
	# c
	match_cursor(c, libclang.CursorKind.OBJC_CATEGORY_DECL)
	equals(isinstance(c, libclang.ObjCCategoryDecl), True)

def test_ObjCProtocolDecl27():
	x = parse_str('@protocol x @end', args=['-ObjC'])[0]
	# x
	match_cursor(x, libclang.CursorKind.OBJC_PROTOCOL_DECL)
	equals(isinstance(x, libclang.ObjCProtocolDecl), True)

def test_ObjCPropertyDecl27():
	x = parse_str('@interface x @property int a; @end', args=['-ObjC'])[0]
	a = x.children[0]
	# x
	match_cursor(a, libclang.CursorKind.OBJC_PROPERTY_DECL)
	equals(isinstance(a, libclang.ObjCPropertyDecl), True)

def test_ObjCIvarDecl27():
	x = parse_str('@interface x { int a; } @end', args=['-ObjC'])[0]
	a = x.children[0]
	# x
	match_cursor(a, libclang.CursorKind.OBJC_IVAR_DECL)
	equals(isinstance(a, libclang.VarDecl), True)
	equals(isinstance(a, libclang.FieldDecl), True)
	equals(isinstance(a, libclang.ObjCIvarDecl), True)

def test_ObjCInstanceMethodDecl27():
	x = parse_str('@interface x -(int)a; @end', args=['-ObjC'])[0]
	a = x.children[0]
	# x
	match_cursor(a, libclang.CursorKind.OBJC_INSTANCE_METHOD_DECL)
	equals(isinstance(a, libclang.FunctionDecl), True)
	equals(isinstance(a, libclang.ObjCInstanceMethodDecl), True)

def test_ObjCClassMethodDecl27():
	x = parse_str('@interface x +(int)a; @end', args=['-ObjC'])[0]
	a = x.children[0]
	# x
	match_cursor(a, libclang.CursorKind.OBJC_CLASS_METHOD_DECL)
	equals(isinstance(a, libclang.FunctionDecl), True)
	equals(isinstance(a, libclang.ObjCClassMethodDecl), True)

def test_ObjCImplementationDecl27():
	i, x = parse_str("""
		@interface x @end
		@implementation x @end""", args=['-ObjC', '-Wno-objc-root-class'])
	# x
	match_cursor(x, libclang.CursorKind.OBJC_IMPLEMENTATION_DECL)
	equals(isinstance(x, libclang.ObjCImplementationDecl), True)

def test_ObjCCategoryImplDecl27():
	i, x = parse_str("""
		@interface x @end
		@implementation x (c) @end""", args=['-ObjC', '-Wno-objc-root-class'])
	# x
	match_cursor(x, libclang.CursorKind.OBJC_CATEGORY_IMPL_DECL)
	equals(isinstance(x, libclang.ObjCCategoryImplDecl), True)

def test_TypedefDecl27():
	x = parse_str('typedef float x;')[0]
	match_cursor(x, libclang.CursorKind.TYPEDEF_DECL)
	equals(isinstance(x, libclang.TypedefDecl), True)

def test_TypedefDecl31():
	x = parse_str('typedef float x;')[0]
	equals(x.underlying_type.kind, libclang.TypeKind.FLOAT)

def test_MethodDecl28():
	x = parse_str('struct x { void f(int x); };')[0]
	f = x.children[0]
	# f
	match_cursor(f, libclang.CursorKind.CXX_METHOD_DECL)
	equals(isinstance(f, libclang.FunctionDecl), True)
	equals(isinstance(f, libclang.MethodDecl), True)

def test_Namespace28():
	x = parse_str('namespace x {}')[0]
	# x
	match_cursor(x, libclang.CursorKind.NAMESPACE)
	equals(isinstance(x, libclang.Namespace), True)

def test_LinkageSpec28():
	s = parse_str('extern "C" void f(int x);')[0]
	# s
	equals(s.kind, libclang.CursorKind.UNEXPOSED_DECL)
	equals(isinstance(s, libclang.Cursor), True)

def test_Token():
	index = libclang.Index()
	tu = index.from_source('tests/enumeration.hpp')
	f = tu.file('tests/enumeration.hpp')
	rng = libclang.SourceRange(tu.location(f, 1, 1), tu.location(f, 2, 1))
	children = [child for child in tu.cursor().children if child.location.file]
	# tokenize
	tokens = tu.tokenize(libclang.SourceRange.null())
	equals(len(tokens), 0)
	tokens = tu.tokenize(rng)
	equals(len(tokens), 3)
	equals(tokens[0].spelling, 'enum')
	equals(tokens[0].kind, libclang.TokenKind.KEYWORD)
	equals(tokens[1].spelling, 'test')
	equals(tokens[1].kind, libclang.TokenKind.IDENTIFIER)
	equals(tokens[2].spelling, '{')
	equals(tokens[2].kind, libclang.TokenKind.PUNCTUATION)
	# token
	token = tokens[0]
	equals(str(token), 'enum')
	equals(token.location, tu.location(f, 1, 1))
	match_location(token.location, 'tests/enumeration.hpp', 1, 1, 0)
	match_location(token.extent.start, 'tests/enumeration.hpp', 1, 1, 0)
	match_location(token.extent.end, 'tests/enumeration.hpp', 1, 1, 0)
	equals(token.cursor, children[0])

def test_Type28():
	c = parse_str('int a;')[0]
	t = c.type
	equals(t == t, True)
	equals(t == t.pointee_type, False)
	equals(t != t, False)
	equals(t != t.pointee_type, True)
	# type
	equals(t.kind, libclang.TypeKind.INT)
	equals(t.canonical_type, t)
	equals(t.pointee_type.kind, libclang.TypeKind.INVALID)
	equals(t.result_type.kind, libclang.TypeKind.INVALID)
	equals(t.declaration.kind, libclang.CursorKind.NO_DECL_FOUND)
	equals(t.is_pod, True)

def test_Type29():
	c = parse_str('int a;')[0]
	t = c.type
	equals(t.is_const_qualified, False)
	equals(t.is_volatile_qualified, False)
	equals(t.is_restrict_qualified, False)

def test_Type30():
	c = parse_str('long a[4];')[0]
	t = c.type
	equals(t.array_element_type.kind, libclang.TypeKind.LONG)
	equals(t.array_size, 4)

def test_Type31():
	c = parse_str('long a[4];')[0]
	t = c.type
	equals(len(list(t.argument_types)), 0)
	equals(t.element_type.kind, libclang.TypeKind.LONG)
	equals(t.element_count, 4)
	equals(t.is_variadic, False)
	equals(t.calling_convention, libclang.CallingConvention.INVALID)

def test_Type33():
	c = parse_str('short a[4];')[0]
	t = c.type
	equals(t.spelling, 'short [4]')
	equals(str(t), 'short [4]')
	equals(t.alignment, 2)
	equals(t.size, 8)
	equals(t.offset('a'), -1)

def test_builtin_type(program, kind, args=None, ignore_errors=False, signed=False, unsigned=False, floating_point=False):
	c = parse_str(program, args=args, ignore_errors=ignore_errors)[0]
	t = c.type
	match_type(t, kind)
	equals(isinstance(t, libclang.BuiltinType), True)
	equals(t.is_signed_integer, signed)
	equals(t.is_unsigned_integer, unsigned)
	equals(t.is_floating_point, floating_point)

def test_BuiltinType28():
	Kind = libclang.TypeKind
	test_builtin_type('void a;', Kind.VOID, ignore_errors=True,
	                  signed=False, unsigned=False, floating_point=False)
	test_builtin_type('bool a;', Kind.BOOL,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('char a;', Kind.CHAR_U, args=['-funsigned-char'],
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('unsigned char a;', Kind.UCHAR,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('wchar_t a;', Kind.WCHAR, args=['-funsigned-char'],
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('char16_t a;', Kind.CHAR16, args=['-std=c++11'],
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('char32_t a;', Kind.CHAR32, args=['-std=c++11'],
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('unsigned short a;', Kind.USHORT,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('unsigned int a;', Kind.UINT,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('unsigned long a;', Kind.ULONG,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('unsigned long long a;', Kind.ULONGLONG,
	                  signed=False, unsigned=True,  floating_point=False)
	test_builtin_type('char a;', Kind.CHAR_S,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('signed char a;', Kind.SCHAR,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('wchar_t a;', Kind.WCHAR,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('short a;', Kind.SHORT,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('int a;', Kind.INT,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('long a;', Kind.LONG,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('long long a;', Kind.LONGLONG,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('float a;', Kind.FLOAT,
	                  signed=False, unsigned=False, floating_point=True)
	test_builtin_type('double a;', Kind.DOUBLE,
	                  signed=False, unsigned=False, floating_point=True)
	test_builtin_type('long double a;', Kind.LONG_DOUBLE,
	                  signed=False, unsigned=False, floating_point=True)

def test_BuiltinType31():
	Kind = libclang.TypeKind
	test_builtin_type('__int128 a;', Kind.INT128,
	                  signed=True,  unsigned=False, floating_point=False)
	test_builtin_type('unsigned __int128 a;', Kind.UINT128,
	                  signed=False, unsigned=True,  floating_point=False)

def test_FunctionProtoType34():
	s = parse_str("""
		struct test {
			int f(float x);
			int g(float x) const &;
			int h(float x) const &&;
		};""", args=['-std=c++11'])[0]
	f, g, h = s.children
	# f -- no ref-qualifier
	equals(f.spelling, 'f')
	ft = f.type
	match_type(ft, libclang.TypeKind.FUNCTION_PROTO)
	equals(isinstance(ft, libclang.FunctionProtoType), True)
	equals(ft.cxx_ref_qualifier, libclang.RefQualifierKind.NONE)
	# g -- const lvalue
	equals(g.spelling, 'g')
	gt = g.type
	match_type(gt, libclang.TypeKind.FUNCTION_PROTO)
	equals(isinstance(gt, libclang.FunctionProtoType), True)
	equals(gt.cxx_ref_qualifier, libclang.RefQualifierKind.LVALUE)
	# g -- const rvalue
	equals(h.spelling, 'h')
	ht = h.type
	match_type(ht, libclang.TypeKind.FUNCTION_PROTO)
	equals(isinstance(ht, libclang.FunctionProtoType), True)
	equals(ht.cxx_ref_qualifier, libclang.RefQualifierKind.RVALUE)

def test_MemberPointerType34():
	s, mp = parse_str('struct A{}; int *A::* b;')
	t = mp.type
	match_type(t, libclang.TypeKind.MEMBER_POINTER)
	equals(isinstance(t, libclang.MemberPointerType), True)
	equals(t.class_type.kind, libclang.TypeKind.RECORD)

if len(sys.argv) > 1:
	libclang.load(name=sys.argv[1])
else:
	libclang.load()

run(2.7, test_version)
run(2.7, test_SourceLocation)
run(2.9, test_SourceLocation29)
run(3.0, test_SourceLocation30)
run(3.1, test_SourceLocation31)
run(3.3, test_SourceLocation33)
run(3.4, test_SourceLocation34)
run(2.7, test_SourceRange)
run(2.7, test_DiagnosticDisplayOptions)
run(2.7, test_DiagnosticSeverity)
run(2.9, test_DiagnosticCategory29)
run(2.7, test_Linkage)
run(2.7, test_TokenKind)
run(2.7, test_CursorKind)
run(2.8, test_CursorKind28)
run(3.0, test_CursorKind30)
run(2.8, test_TypeKind28)
run(2.8, test_AvailabilityKind28)
run(2.8, test_LanguageKind28)
run(2.8, test_AccessSpecifier28)
run(3.0, test_NameRefFlags30)
run(2.8, test_TranslationUnitFlags28)
run(2.8, test_SaveTranslationUnitFlags28)
run(2.8, test_ReparseTranslationUnitFlags28)
run(3.1, test_GlobalOptionFlags31)
run(3.1, test_CallingConvention31)
run(3.3, test_ObjCPropertyAttributes33)
run(3.3, test_ObjCDeclQualifierKind33)
run(3.4, test_RefQualifierKind34)
run(2.7, test_Index)
run(2.8, test_Index28)
run(3.1, test_Index31)
run(2.7, test_TranslationUnit)
run(2.9, test_TranslationUnit29)
run(3.0, test_TranslationUnit30)
run(2.7, test_Diagnostic)
run(2.9, test_Diagnostic29)
run(2.7, test_Cursor)
run(2.8, test_Cursor28)
run(2.9, test_Cursor29)
run(3.0, test_Cursor30)
run(3.1, test_Cursor31)
run(3.2, test_Cursor32)
run(3.3, test_Cursor33)
run(3.4, test_Cursor34)
run(2.7, test_StructDecl27)
run(2.7, test_UnionDecl27)
run(2.7, test_ClassDecl27)
run(2.7, test_EnumDecl27)
run(2.9, test_EnumDecl29) # C++11 enum class
run(3.1, test_EnumDecl31)
run(2.7, test_FieldDecl27)
run(2.7, test_EnumConstantDecl27)
run(2.9, test_EnumConstantDecl29) # C++11 enum class
run(3.1, test_EnumConstantDecl31)
run(2.7, test_FunctionDecl27)
run(2.7, test_VarDecl27)
run(2.7, test_ParmDecl27)
run(2.7, test_ObjCInterfaceDecl27)
run(2.7, test_ObjCCategoryDecl27)
run(2.7, test_ObjCProtocolDecl27)
run(2.7, test_ObjCIvarDecl27)
run(2.7, test_ObjCInstanceMethodDecl27)
run(2.7, test_ObjCClassMethodDecl27)
run(2.7, test_ObjCImplementationDecl27)
run(2.7, test_ObjCCategoryImplDecl27)
run(2.7, test_TypedefDecl27)
run(3.1, test_TypedefDecl31)
run(2.8, test_MethodDecl28)
run(2.8, test_Namespace28)
run(2.8, test_LinkageSpec28)
run(2.7, test_Token)
run(2.8, test_Type28)
run(2.9, test_Type29)
run(3.0, test_Type30)
run(3.1, test_Type31)
run(3.3, test_Type33)
run(2.8, test_BuiltinType28)
run(3.1, test_BuiltinType31)
run(3.4, test_FunctionProtoType34)
run(3.4, test_MemberPointerType34)

summary()
