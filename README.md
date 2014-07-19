# libclangpy 3.3

The libclangpy project is a Python binding to the libclang 3.3 API. It differs
from the cindex bindings from LLVM/clang in that it:

1.  is a more complete libclang binding (see Implementation Status below);

2.  annotates which libclang version is needed by each API;

3.  provides a cleaner, more pythonic API;

4.  provides backward compatibility for several APIs;

5.  supports Python 2 and Python 3.

## Using In Your Own Projects

To use libclangpy in your own git projects, add libclangpy as a submodule:

	git submodule add git://github.com/rhdunn/libclangpy.git

then, in your python file, add:

	from libclangpy import libclang

you can now start using it, e.g.:

	libclang.load()
	index = libclang.Index()
	tu = index.parse('test.hpp')

## Implementation Status

The support status for libclang 3.3 is as follows:

| API                     | libclang | libclangpy |
|-------------------------|----------|------------|
| `CXCodeCompleteResults` | 2.8      | No         |
| `CXComment`             | 3.2      | No         |
| `CXCompletionChunkKind` | 2.7      | No         |
| `CXCompletionContext`   | 3.0      | No         |
| `CXCompletionResults`   | 3.0      | No         |
| `CXCompletionString`    | 3.1      | No         |
| `CXCursor`              | 3.3      | Yes        |
| `CXCursorAndRangeVisitor`| 3.0     | No         |
| `CXCursorKind`          | 3.4      | Yes        |
| `CXCursorSet`           | 2.9      | No         |
| `CXDiagnostic`          | 3.1      | Yes        |
| `CXFile`                | 3.3      | 2.7        |
| `CXIdx*`                | 3.3      | Yes        |
| `CXIndex`               | 3.1      | Yes        |
| `CXIndexAction`         | 3.1      | No         |
| `CXModule`              | 3.3      | No         |
| `CXPlatformAvailability`| 3.2      | No         |
| `CXRemapping`           | 3.1      | No         |
| `CXSourceLocation`      | 3.4      | Yes        |
| `CXSourceRange`         | 3.0      | Yes        |
| `CXString`              | 2.7      | Yes        |
| `CXToken`               | 2.7      | Yes        |
| `CXTokenKind`           | 2.7      | Yes        |
| `CXTranslationUnit`     | 3.0      | Yes        |
| `CXTUResourceUsage`     | 3.0      | No         |
| `CXTUResourceUsageEntry`| 3.0      | No         |
| `CXTUResourceUsageKind` | 3.0      | No         |
| `CXType`                | 3.3      | Yes        |
| `CXTypeKind`            | 3.4      | Yes        |
| `clang_constructUSR_*`  | 2.8      | No         |
| `clang_executeOnThread` | 2.9      | No         |
| `clang_toggleCrashRecovery` | 3.0  | No         |
| `clang_getClangVersion` | 2.7      | No         |
| `clang_getInclusions`   | 2.7      | No         |

Where:
*  `API` is the name of the API type in libclang,
*  `libclang` is the version of libclang the API was updated in,
*  `libclangpy` is the support status of the API in libclangpy -- `No` means
   the API is not supported, `Yes` means the API is fully supported for this
   version of libclang, a version number specifies the version of libclang
   this API is fully supported by libclangpy in (e.g. `2.7` indicates that
   libclangpy supports the libclang 2.7 version of this API).

__NOTE__: The `clang_setUseExternalASTGeneration` API was removed in libclang
2.9, so is not supported in libclangpy.

## License

The libclangpy API is licensed under the GNU Public License (GPL) version 3 or
later.

Copyright (C) 2014 Reece H. Dunn
