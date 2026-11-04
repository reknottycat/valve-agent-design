"""Execute only reviewed upstream bytes, with a closed local import table.

Not a Python sandbox: the interpreter, stdlib, adapter and installed PyYAML are
trusted runtime dependencies. Snapshot modules and their bytecode are not.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import datetime
import fractions
import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import math
import pathlib
import re
import sys
import sysconfig
import types
import unicodedata

MODULES = (
    'kb_entries', 'flw001_contract', 'valve_completion_contract',
    'valve_variant_binding', 'source_closure_contract',
    'formula_input_contract', 'acceptance_card',
)
STDLIB = {m.__name__: m for m in (
    argparse, ast, datetime, fractions, hashlib, json, math, pathlib, re,
    unicodedata,
)}
# Upstream scripts set this flag at import. Keep that write local to this loader.
STDLIB['sys'] = types.SimpleNamespace(dont_write_bytecode=True)


class FrozenPath:
    """Only the read operations actually used by formula_input_contract.validate."""
    def __init__(self, files, relative=''):
        self._files = files
        self._relative = relative

    def __truediv__(self, part):
        part = str(part)
        pieces = pathlib.PurePosixPath(part).parts
        if not pieces or part.startswith('/') or '..' in pieces or '\\' in part:
            raise ValueError('unsafe frozen input path')
        return FrozenPath(self._files, '/'.join(filter(None, (self._relative, part))))

    def read_text(self, encoding='utf-8'):
        return self.read_bytes().decode(encoding)

    def read_bytes(self):
        try:
            return self._files[self._relative]
        except KeyError as exc:
            raise ValueError('unlocked upstream input: ' + self._relative) from exc


def _yaml_dependency():
    """Reject ordinary cwd/PYTHONPATH and sys.modules yaml impersonation.

    PyYAML is part of the trusted installed runtime, not snapshot code. It must
    resolve inside the interpreter's installation, never a snapshot/plugin path.
    Run the CLI with -I -B; arbitrary hostile mutation of Python is out of scope.
    """
    roots = {str(pathlib.Path(sysconfig.get_path(k)).resolve())
             for k in ('purelib', 'platlib')}
    spec = importlib.machinery.PathFinder.find_spec('yaml', sorted(roots))
    if not spec or not spec.origin:
        raise ValueError('installed PyYAML 6.0.3 is required')
    origin = pathlib.Path(spec.origin).resolve()
    if not any(origin.is_relative_to(pathlib.Path(p)) for p in roots):
        raise ValueError('PyYAML is outside the trusted runtime installation')
    current = sys.modules.get('yaml')
    visible = getattr(current, '__spec__', None) if current else importlib.util.find_spec('yaml')
    if not visible or not visible.origin or pathlib.Path(visible.origin).resolve() != origin:
        raise ValueError('untrusted yaml module resolution')
    for name, module in tuple(sys.modules.items()):
        if name.startswith('yaml.'):
            file = getattr(module, '__file__', None)
            if not file or not pathlib.Path(file).resolve().is_relative_to(origin.parent):
                raise ValueError('untrusted yaml dependency: ' + name)
    prior = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        yaml = importlib.import_module('yaml')
    finally:
        sys.dont_write_bytecode = prior
    if yaml.__version__ != '6.0.3':
        raise ValueError('unsupported PyYAML version; expected 6.0.3')
    return yaml


def load_modules(verified_files):
    """Caller must authenticate the entire dependency set before calling this."""
    source = {name: verified_files['tools/' + name + '.py'] for name in MODULES}
    # Resolve runtime dependency before executing any upstream module.
    yaml = _yaml_dependency()
    local = {}

    def import_verified(name, globals=None, locals=None, fromlist=(), level=0):
        if level:
            raise ImportError('relative upstream imports are not supported')
        if name in source:
            return load(name)
        if name == 'yaml':
            return yaml
        if name == '__future__':
            return __import__('__future__', globals, locals, fromlist, level)
        if name in STDLIB:
            return STDLIB[name]
        raise ImportError('dependency outside reviewed call graph: ' + name)

    def load(name):
        if name in local:
            return local[name]
        module = types.ModuleType(name)
        module.__file__ = '/__pinned_standards__/tools/' + name + '.py'
        module.__dict__['__builtins__'] = dict(vars(builtins), __import__=import_verified)
        local[name] = module
        # Never SourceFileLoader, sys.path, sys.modules or a .pyc for upstream code.
        exec(compile(source[name], module.__file__, 'exec', dont_inherit=True), module.__dict__)
        return module

    for name in MODULES:
        load(name)
    return local
