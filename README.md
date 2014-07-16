# libclangpy

The libclangpy project is a Python binding to the libclang API. It differs from
the cindex bindings from LLVM/clang in that it:

1.  a more complete libclang binding (see Implementation Status below);

2.  annotates which libclang version is needed by each API;

3.  provides a cleaner, more pythonic API;

4.  provides backward compatibility for several APIs;

5.  supports Python 2 and Python 3.

## Implementation Status

| API                     | Version | Supported |
|-------------------------|---------|-----------|
| `CXDiagnostic`          | 2.7     | Yes       |
| `CXCodeCompleteResults` | 2.7     | No        |
| `CXCompletionChunkKind` | 2.7     | No        |
| `CXCompletionResult`    | 2.7     | No        |
| `CXCursor`              | 2.7     | Yes       |
| `CXCursorKind`          | 2.7     | Yes       |
| `CXFile`                | 2.7     | Yes       |
| `CXIndex`               | 2.7     | Yes       |
| `CXSourceLocation`      | 2.7     | Yes       |
| `CXSourceRange`         | 2.7     | Yes       |
| `CXString`              | 2.7     | Yes       |
| `CXToken`               | 2.7     | Yes       |
| `CXTokenKind`           | 2.7     | Yes       |
| `CXTranslationUnit`     | 2.7     | Yes       |
| `clang_getClangVersion` | 2.7     | No        |
| `clang_getInclusions`   | 2.7     | No        |

Here, `API` is the name of the API type in libclang, `Version` is the version
of libclang supported for that API, and `Supported` indicates whether the API
is supported by libclangpy.

## License

The libclangpy API is licensed under the GNU Public License (GPL) version 3 or
later.

Copyright (C) 2014 Reece H. Dunn
