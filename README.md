# libclangpy 2.8

The libclangpy project is a Python binding to the libclang 2.8 API. It differs
from the cindex bindings from LLVM/clang in that it:

1.  a more complete libclang binding (see Implementation Status below);

2.  annotates which libclang version is needed by each API;

3.  provides a cleaner, more pythonic API;

4.  provides backward compatibility for several APIs;

5.  supports Python 2 and Python 3.

## Implementation Status

The support status for libclang 2.8 is as follows:

| API                     | libclang | libclangpy |
|-------------------------|----------|------------|
| `CXCodeCompleteResults` | 2.8      | No         |
| `CXCompletionChunkKind` | 2.7      | No         |
| `CXCompletionResult`    | 2.8      | No         |
| `CXCompletionString`    | 2.8      | No         |
| `CXCursor`              | 2.8      | Yes        |
| `CXCursorKind`          | 2.9      | Yes        |
| `CXDiagnostic`          | 2.9      | Yes        |
| `CXFile`                | 2.7      | Yes        |
| `CXIndex`               | 2.8      | Yes        |
| `CXSourceLocation`      | 2.9      | Yes        |
| `CXSourceRange`         | 2.7      | Yes        |
| `CXString`              | 2.7      | Yes        |
| `CXToken`               | 2.7      | Yes        |
| `CXTokenKind`           | 2.7      | Yes        |
| `CXTranslationUnit`     | 2.8      | Yes        |
| `CXType`                | 2.9      | Yes        |
| `CXTypeKind`            | 2.8      | Yes        |
| `clang_constructUSR_*`  | 2.8      | No         |
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

## License

The libclangpy API is licensed under the GNU Public License (GPL) version 3 or
later.

Copyright (C) 2014 Reece H. Dunn
