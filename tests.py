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

import libclang

def equals(a, b):
	ta, tb = type(a), type(b)
	if ta.__name__ != tb.__name__:
		raise AssertionError('Type mismatch: `{0}` != `{1}`'.format(ta.__name__, tb.__name__))
	if a != b:
		raise AssertionError('Value mismatch: `{0}` != `{1}`'.format(str(a), str(b)))

def match_location(loc, filename, line, column, offset):
	if filename:
		equals(loc.file.name, filename)
	else:
		equals(loc.file, None)
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

def test_Index(index):
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

def test_TranslationUnit(index):
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	equals(tu.spelling, filename)
	equals(str(tu), filename)
	test_File(tu.file(filename), filename)
	match_location(tu.location(tu.file(filename), 3, 2), filename, 3, 2, 13)
	equals(list(tu.diagnostics), [])

def test_Diagnostic(index):
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

def test_Cursor(index):
	tu = index.from_source('tests/enumeration.hpp')
	c = tu.cursor()
	equals(c == c, True)
	equals(c == libclang.Cursor.null(), False)
	equals(c != c, False)
	equals(c != libclang.Cursor.null(), True)
	equals(c.spelling, 'tests/enumeration.hpp')
	equals(str(c), 'tests/enumeration.hpp')
	equals(c.kind, libclang.CursorKind.TRANSLATION_UNIT)
	equals(c.linkage, libclang.Linkage.INVALID)
	equals(c.location, libclang.SourceLocation.null())
	match_location(c.extent.start, 'tests/enumeration.hpp', 1, 1, 0)
	match_location(c.extent.end, 'tests/enumeration.hpp', 1, 1, 0)
	equals(c.usr, '')
	equals(c.referenced, libclang.Cursor.null())
	equals(c.definition, libclang.Cursor.null())
	equals(c.is_definition, False)
	# children
	children = [child for child in c.children if child.location.file]
	equals(len(children), 1)
	equals(children[0].kind, libclang.CursorKind.ENUM_DECL)
	# tokens
	tokens = list(c.tokens)
	equals(len(tokens), 11)
	equals(tokens[0].kind, libclang.TokenKind.KEYWORD)

def test_Token(index):
	tu = index.from_source('tests/enumeration.hpp')
	f = tu.file('tests/enumeration.hpp')
	rng = libclang.SourceRange.create(tu.location(f, 1, 1), tu.location(f, 2, 1))
	children = [child for child in tu.cursor().children if child.location.file]
	# tokenize
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

libclang.load()

test_SourceLocation()
test_SourceRange()
test_CursorKind()

index = libclang.Index()

test_Index(index)
test_TranslationUnit(index)
test_Diagnostic(index)
test_Cursor(index)
test_Token(index)

print('success')
