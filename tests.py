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

def test_TranslationUnit(index):
	filename = 'tests/enumeration.hpp'
	tu = index.from_source(filename)
	equals(tu.spelling, filename)
	equals(str(tu), filename)
	test_File(tu.file(filename), filename)
	match_location(tu.location(tu.file(filename), 3, 2), filename, 3, 2, 13)
	equals(list(tu.diagnostics), [])

libclang.load()

test_SourceLocation()
test_SourceRange()

index = libclang.Index()

test_TranslationUnit(index)
