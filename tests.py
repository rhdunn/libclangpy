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

def equals(a, b):
	ta, tb = type(a), type(b)
	if ta.__name__ != tb.__name__:
		raise AssertionError('Type mismatch: `{0}` != `{1}`'.format(ta.__name__, tb.__name__))
	if a != b:
		raise AssertionError('Value mismatch: `{0}` != `{1}`'.format(str(a), str(b)))

def run(version, test):
	sys.stdout.write('Running {0} ... '.format(test.__name__))
	try:
		test()
		print('passed')
	except libclang.MissingFunction:
		print('skipping ... missing APIs')
	except Exception as e:
		print('failed')
		print(traceback.format_exc())

def parse_str(index, contents, filename='parse_str.cpp'):
	tu = index.from_source(filename, unsaved_files=[(filename, contents)])
	return [child for child in tu.cursor().children if child.location.file]

def match_location(loc, filename, line, column, offset):
	if isinstance(loc.file, libclang.File):
		equals(loc.file.name, filename)
	else:
		equals(loc.file, filename)
	equals(loc.line, line)
	equals(loc.column, column)
	equals(loc.offset, offset)

def test_File(f, filename):
	equals(f.name, filename)
	equals(str(f), filename)
	equals(f == f, True)
	equals(f != f, False)

def test_SourceLocation():
	loc = libclang.SourceLocation.null()
	match_location(loc, None, 0, 0, 0)
	match_location(loc.instantiation_location, None, 0, 0, 0)
	equals(loc == libclang.SourceLocation.null(), True)
	equals(loc != libclang.SourceLocation.null(), False)

def test_SourceLocation29():
	loc = libclang.SourceLocation.null()
	match_location(loc.spelling_location, None, 0, 0, 0)

def test_SourceLocation30():
	loc = libclang.SourceLocation.null()
	match_location(loc.expansion_location, None, 0, 0, 0)
	match_location(loc.presumed_location, '', 0, 0, 0)

def test_SourceRange():
	rng1 = libclang.SourceRange.null()
	equals(rng1.start, libclang.SourceLocation.null())
	equals(rng1.end,   libclang.SourceLocation.null())
	rng2 = libclang.SourceRange.create(libclang.SourceLocation.null(),
	                                   libclang.SourceLocation.null())
	equals(rng2.start, libclang.SourceLocation.null())
	equals(rng2.end,   libclang.SourceLocation.null())
	equals(rng1 == rng2, True)
	equals(rng1 != rng2, False)
	equals(rng1.is_null, True)

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
	tu = index.from_source('unsaved.hxx', unsaved_files=[('unsaved.hxx', 'struct test {};')])
	equals(tu.spelling, '')
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
	tu = index.parse('unsaved.hxx', unsaved_files=[('unsaved.hxx', 'struct test {};')])
	equals(tu.spelling, '')
	equals(len(list(tu.diagnostics)), 0)

def test_TranslationUnit():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	equals(tu.spelling, filename)
	equals(str(tu), filename)
	test_File(tu.file(filename), filename)
	match_location(tu.location(tu.file(filename), 3, 2), filename, 3, 2, 13)
	match_location(tu.location(tu.file(filename), line=3, column=2), filename, 3, 2, 13)
	equals(list(tu.diagnostics), [])

def test_TranslationUnit29():
	index = libclang.Index()
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	match_location(tu.location(tu.file(filename), offset=13), filename, 3, 2, 13)

def test_Diagnostic():
	index = libclang.Index()
	tu = index.from_source('tests/error.hpp')
	diagnostics = list(tu.diagnostics)
	equals(len(diagnostics), 1)
	d = diagnostics[0]
	equals(d.spelling, 'expected \';\' after enum')
	equals(str(d), 'expected \';\' after enum')
	equals(d.format(),
	       'tests/error.hpp:6:2: error: expected \';\' after enum')
	equals(d.format(libclang.DiagnosticDisplayOptions.SOURCE_LOCATION),
	       'tests/error.hpp:6: error: expected \';\' after enum')
	equals(d.severity, libclang.DiagnosticSeverity.ERROR)
	match_location(d.location, 'tests/error.hpp', 6, 2, 25)
	# ranges
	r = list(d.ranges)
	equals(len(r), 0)
	# fixits
	f = list(d.fixits)
	equals(len(f), 1)
	r, msg = f[0]
	match_location(r.start, 'tests/error.hpp', 6, 2, 25)
	match_location(r.end, 'tests/error.hpp', 6, 2, 25)
	equals(msg, ';')

def test_Diagnostic29():
	index = libclang.Index()
	tu = index.from_source('tests/error.hpp')
	diagnostics = list(tu.diagnostics)
	equals(len(diagnostics), 1)
	d = diagnostics[0]
	opt, disable = d.option
	equals(opt, '')
	equals(disable, '')
	equals(d.category.name, 'Parse Issue')

def test_Cursor():
	index = libclang.Index()
	tu = index.from_source('tests/enumeration.hpp')
	c = tu.cursor()
	equals(c == c, True)
	equals(c == libclang.Cursor.null(), False)
	equals(c != c, False)
	equals(c != libclang.Cursor.null(), True)
	equals(c.is_null, False)
	equals(c.spelling, 'tests/enumeration.hpp')
	equals(str(c), 'tests/enumeration.hpp')
	equals(c.kind, libclang.CursorKind.TRANSLATION_UNIT)
	equals(c.parent, None)
	equals(c.linkage, libclang.Linkage.INVALID)
	equals(c.location, libclang.SourceLocation.null())
	match_location(c.extent.start, 'tests/enumeration.hpp', 1, 1, 0)
	match_location(c.extent.end, 'tests/enumeration.hpp', 1, 1, 0)
	equals(c.usr, '')
	equals(c.referenced, libclang.Cursor.null())
	equals(c.definition, libclang.Cursor.null())
	equals(c.is_definition, False)
	equals(c.translation_unit.spelling, tu.spelling)
	# children
	children = [child for child in c.children if child.location.file]
	equals(len(children), 1)
	equals(children[0].kind, libclang.CursorKind.ENUM_DECL)
	equals(children[0].parent, c)
	# tokens
	tokens = list(c.tokens)
	equals(len(tokens), 11)
	equals(tokens[0].kind, libclang.TokenKind.KEYWORD)

def test_Cursor28():
	index = libclang.Index()
	c = parse_str(index, 'enum test {};')[0]
	equals(c.type.kind, libclang.TypeKind.ENUM)
	equals(c.result_type.kind, libclang.TypeKind.INVALID)
	equals(c.ib_outlet_collection_type.kind, libclang.TypeKind.INVALID)
	equals(c.availability, libclang.AvailabilityKind.AVAILABLE)
	equals(c.language, libclang.LanguageKind.C)
	equals(c.access_specifier, libclang.AccessSpecifier.INVALID)
	equals(c.template_kind, libclang.CursorKind.NO_DECL_FOUND)
	equals(c.specialized_template.kind, libclang.CursorKind.INVALID_FILE)
	equals(c.is_virtual_base, False)
	equals(c.is_static, False)

def test_Cursor29():
	index = libclang.Index()
	c = parse_str(index, 'enum test {};')[0]
	equals(hash(c), hash(c))
	equals(c.semantic_parent, c.parent)
	equals(c.lexical_parent, c.parent)
	equals(c.included_file.name, None)
	equals(c.objc_decltype_encoding, '?')
	equals(len(list(c.overloads)), 0)
	equals(c.display_name, 'test')
	equals(c.canonical, c)
	equals(len(c.overridden), 0)

def test_Cursor30():
	index = libclang.Index()
	c = parse_str(index, 'enum test {};', filename='cursor30.hpp')[0]
	equals(c.is_virtual, False)
	rng = c.reference_name_range(libclang.NameRefFlags.WANT_TEMPLATE_ARGS, 0)
	match_location(rng.start, 'cursor30.hpp', 1, 1, 0)
	match_location(rng.end, 'cursor30.hpp', 1, 1, 0)

def test_Token():
	index = libclang.Index()
	tu = index.from_source('tests/enumeration.hpp')
	f = tu.file('tests/enumeration.hpp')
	rng = libclang.SourceRange.create(tu.location(f, 1, 1), tu.location(f, 2, 1))
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
	index = libclang.Index()
	c = parse_str(index, 'int a;')[0]
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
	index = libclang.Index()
	c = parse_str(index, 'int a;')[0]
	t = c.type
	equals(t.is_const_qualified, False)
	equals(t.is_volatile_qualified, False)
	equals(t.is_restrict_qualified, False)

libclang.load()

run(2.7, test_SourceLocation)
run(2.9, test_SourceLocation29)
run(3.0, test_SourceLocation30)
run(2.7, test_SourceRange)
run(2.7, test_CursorKind)
run(2.8, test_CursorKind28)
run(3.0, test_CursorKind30)
run(2.8, test_TypeKind28)
run(2.7, test_Index)
run(2.8, test_Index28)
run(2.7, test_TranslationUnit)
run(2.9, test_TranslationUnit29)
run(2.7, test_Diagnostic)
run(2.9, test_Diagnostic29)
run(2.7, test_Cursor)
run(2.8, test_Cursor28)
run(2.9, test_Cursor29)
run(3.0, test_Cursor30)
run(2.7, test_Token)
run(2.8, test_Type28)
run(2.9, test_Type29)
