#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IceCream - Never use print() to debug again

Enjoy IceCream!

License: MIT
Version: See icecream/__init__.py
GitHub: https://github.com/gruns/icecream
Original Author: Ansgar Grunseid
Maintainer: Jakeroid (Ivan Karabadzhak)
"""

import sys
import ast
import textwrap
import tokenize
import inspect
import pprint
import functools
from contextlib import contextmanager
from datetime import datetime
from os.path import basename, realpath

try:
    import colorama
except ImportError:
    colorama = None

try:
    import pygments
    from pygments.lexers import PythonLexer
    from pygments.formatters import Terminal256Formatter
except ImportError:
    pygments = None

from executing import Source


DEFAULT_PREFIX = 'ic| '
DEFAULT_LINE_WRAP_WIDTH = 70  # Characters.
DEFAULT_CONTEXT_DELIMITER = '- '
DEFAULT_OUTPUT_FUNCTION = None
DEFAULT_ARG_TO_STRING_FUNCTION = None
DEFAULT_INCLUDE_CONTEXT = False
DEFAULT_CONTEXT_ABS_PATH = False


class ListMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_data'] = []
        return super().__new__(mcs, name, bases, attrs)


class IceCreamDebugger:
    _enabled = True
    _outputFunction = None

    colorize = True
    lineWrapWidth = DEFAULT_LINE_WRAP_WIDTH
    contextDelimiter = DEFAULT_CONTEXT_DELIMITER

    def __init__(self, prefix=DEFAULT_PREFIX,
                 outputFunction=DEFAULT_OUTPUT_FUNCTION,
                 argToStringFunction=DEFAULT_ARG_TO_STRING_FUNCTION,
                 includeContext=DEFAULT_INCLUDE_CONTEXT,
                 contextAbsPath=DEFAULT_CONTEXT_ABS_PATH):
        self.enabled = True
        self.prefix = prefix
        self.includeContext = includeContext
        self.contextAbsPath = contextAbsPath
        self.outputFunction = outputFunction or self._defaultOutputFunction
        self.argToStringFunction = argToStringFunction or pprint.pformat

    @staticmethod
    def _defaultOutputFunction(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    def __call__(self, *args):
        if self.enabled:
            callOrValue = self._callOrValue(*args)
            self.outputFunction(callOrValue)

        if not args:
            passthrough = None
        elif len(args) == 1:
            passthrough = args[0]
        else:
            passthrough = args

        return passthrough

    def format(self, *args):
        callOrValue = self._callOrValue(*args)
        return callOrValue

    def _callOrValue(self, *args):
        # Identify the call node in the source so we can extract argument
        # source text.
        frame = inspect.currentframe().f_back.f_back
        callNode = None
        try:
            callNode = Source.executing(frame).node
        except Exception:
            pass

        prefix = self.prefix() if callable(self.prefix) else self.prefix

        if callNode is not None:
            context = self._formatContext(frame, callNode)
            if not args:
                out = prefix + context
            else:
                if self.includeContext:
                    prefix += context + self.contextDelimiter
                out = prefix + self._formatArgs(args, callNode)
        else:
            prefix = self.prefix() if callable(self.prefix) else self.prefix
            context = self._formatContextFromFrame(frame)
            if not args:
                out = prefix + context
            else:
                if self.includeContext:
                    prefix += context + self.contextDelimiter
                out = prefix + ', '.join(self.argToStringFunction(arg) for arg in args)

        return out

    def _formatContext(self, frame, callNode):
        filename = self._getFilename(frame)
        lineNumber = callNode.lineno
        parentFunction = self._getParentFunction(frame)
        if parentFunction:
            return '%s:%s in %s()' % (filename, lineNumber, parentFunction)
        return '%s:%s' % (filename, lineNumber)

    def _formatContextFromFrame(self, frame):
        filename = self._getFilename(frame)
        lineNumber = frame.f_lineno
        parentFunction = self._getParentFunction(frame)
        if parentFunction:
            return '%s:%s in %s()' % (filename, lineNumber, parentFunction)
        return '%s:%s' % (filename, lineNumber)

    def _getFilename(self, frame):
        filename = frame.f_code.co_filename
        if self.contextAbsPath:
            return realpath(filename)
        return basename(filename)

    @staticmethod
    def _getParentFunction(frame):
        parentFrame = frame.f_back
        if parentFrame:
            return parentFrame.f_code.co_name
        return None

    def _formatArgs(self, args, callNode):
        source = Source.for_frame(inspect.currentframe().f_back.f_back.f_back)
        sanitized_args = []
        try:
            for argNode, arg in zip(callNode.args, args):
                argSrc = source.asttokens().get_text(argNode)
                sanitized_args.append('%s: %s' % (argSrc, self.argToStringFunction(arg)))
        except Exception:
            sanitized_args = [self.argToStringFunction(arg) for arg in args]
        return ', '.join(sanitized_args)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    @contextmanager
    def disabled(self):
        """Context manager that temporarily disables IceCream output.

        Suppresses ic() output inside the block and restores the previous
        enabled state on exit, even if an exception is raised. Nesting is
        safe: an inner disabled() block will not re-enable ic when the
        outer block had already disabled it.

        Example::

            ic(1)  # prints
            with ic.disabled():
                ic(2)  # suppressed
            ic(3)  # prints again
        """
        saved = self.enabled
        self.enabled = False
        try:
            yield
        finally:
            self.enabled = saved

    def configureOutput(self, prefix=None, outputFunction=None,
                        argToStringFunction=None, includeContext=None,
                        contextAbsPath=None):
        if prefix is not None:
            self.prefix = prefix
        if outputFunction is not None:
            self.outputFunction = outputFunction
        if argToStringFunction is not None:
            self.argToStringFunction = argToStringFunction
        if includeContext is not None:
            self.includeContext = includeContext
        if contextAbsPath is not None:
            self.contextAbsPath = contextAbsPath


@functools.singledispatch
def argumentToString(obj):
    return pprint.pformat(obj)


argumentToString.register = functools.singledispatch(argumentToString).register  # noqa


ic = IceCreamDebugger(argToStringFunction=argumentToString)


def install(ic_=None):
    import builtins
    setattr(builtins, 'ic', ic_ or ic)


def uninstall():
    import builtins
    if hasattr(builtins, 'ic'):
        delattr(builtins, 'ic')
