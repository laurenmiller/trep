#!/usr/bin/python

try:
    from setuptools import setup, Extension, convert_path
except ImportError:
    from distutils.core import setup
    from distutils.util import convert_path
    from distutils.extension import Extension
import sys
import subprocess
from sysconfig import get_config_var
import os.path
import numpy


def has_header(path):
    INCLUDE = get_config_var('INCLUDEDIR')
    return os.path.exists(os.path.join(INCLUDE, *path))


include_dirs = [numpy.get_include()]
cflags=[]
ldflags=[]
define_macros=[]
cmd_class = {}
cmd_options = {}


# Use safe indexing to force bounds and type checks in our numpy array
# acceses.
#define_macros += [("TREP_SAFE_INDEXING", None)]

# If this is a debug build and the valgrind headers are available,
# enable calls to start and stop callgrind instrumentation.
#define_macros += [("USE_CALLGRIND", None)]
        

################################################################################
# Version management
#   Tries to create src/__version__.py from git describe.

VERSION_PY = """
# This file was generated by setup.py

__version__ = '%s'
"""

def update_version_file():
    try:
        version_git = get_version_from_git()
        version_file = get_version_from_file()
        if version_git == version_file:
            return
    except (GitDescribeError, IOError):
        pass

    version = get_version()
    f = open(convert_path("src/__version__.py"), "wt")
    f.write(VERSION_PY % version)
    f.close()
    return version

class GitDescribeError(StandardError): pass


def get_version_from_git():
    try:
        p = subprocess.Popen(["git", "describe", "--dirty", "--always"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except EnvironmentError as e:
        raise GitDescribeError(e)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise GitDescribeError("git describe failed: '%s'" % stderr)
    return stdout.strip()


def get_version_from_file():
    glob = {'__builtins__' : __builtins__ }
    execfile('src/__version__.py', glob)
    return glob['__version__']


def get_version():
    try:
        return get_version_from_git()
    except GitDescribeError:
        pass
    try:
        return get_version_from_file()
    except IOError:
        pass
    return '<unknown>'

def get_approx_version():
    # Removes the extra information from the version to just get the
    # most recent tag and a '-dev' suffix if appropriate.  This is to
    # keep distutils from creating .eggs for every minor version
    # during development.
    version = get_version()
    if '-' in version:
        version = version[:version.index('-')] + '.dev'
    return version
        

update_version_file()


################################################################################
# Sphinx support

# Try to add support to build the documentation if Sphinx is
# installed.
try:
    from sphinx.setup_command import BuildDoc
    cmd_class['build_sphinx'] = BuildDoc
    cmd_options['build_sphinx'] = {
        'version' : ('setup.py', get_approx_version()),
        'release' : ('setup.py', '')
        }
    # See docstring for BuildDoc on how to set default options here.
except ImportError:
    pass

ext_modules = []

_trep = Extension('trep._trep',
                  include_dirs=include_dirs,
                  define_macros=define_macros,
                  extra_compile_args=cflags,
                  extra_link_args=ldflags,
                  sources = [
                      'src/_trep/midpointvi.c',
                      'src/_trep/system.c',
                      'src/_trep/math-code.c',
                      'src/_trep/frame.c',
                      'src/_trep/_trep.c',
                      'src/_trep/config.c',
                      'src/_trep/potential.c',
                      'src/_trep/force.c',
                      'src/_trep/input.c',
                      'src/_trep/constraint.c',
                      'src/_trep/frametransform.c',
                      'src/_trep/spline.c',
                      'src/_trep/tapemeasure.c',
                      
                      # Constraints
                      'src/_trep/constraints/distance.c',
                      'src/_trep/constraints/plane.c',
                      'src/_trep/constraints/point.c',
                      
                      # Potentials
                      'src/_trep/potentials/gravity.c',
                      'src/_trep/potentials/linearspring.c',
                      'src/_trep/potentials/configspring.c',
                      'src/_trep/potentials/nonlinear_config_spring.c',
                      
                      # Forces
                      'src/_trep/forces/damping.c',
                      'src/_trep/forces/lineardamper.c',
                      'src/_trep/forces/configforce.c',
                      'src/_trep/forces/bodywrench.c',
                      'src/_trep/forces/hybridwrench.c', 
                      'src/_trep/forces/spatialwrench.c',
                      'src/_trep/forces/pistonexample.c',
                      ],
                  depends=[
                      'src/_trep/trep.h',
                      'src/_trep/c_api.h'
                      ])

ext_modules += [_trep]


# Check for OpenGL headers.  If we can't find anything, just don't
# build _polyobject.  There is a python implementation to fallback on.
if sys.platform == 'darwin':
    _polyobject = Extension('trep.visual._polyobject',
                            include_dirs=include_dirs,
                            extra_compile_args=[],
                            extra_link_args=['/System/Library/Frameworks/OpenGL.framework/OpenGL'],
                            sources = ['src/visual/_polyobject.c'])
    ext_modules += [_polyobject]
else:
    if has_header(['GL', 'gl.h']):
        _polyobject = Extension('trep.visual._polyobject',
                                extra_compile_args=[],
                                extra_link_args=['-lGL'],
                                sources = ['src/visual/_polyobject.c'])
        ext_modules += [_polyobject]


setup (name = 'trep',
       version = get_approx_version()[1:],
       description = 'trep is used to simulate mechanical systems.',
       long_description="Trep is a Python module for modeling articulated rigid body mechanical systems in \
generalized coordinates. Trep supports basic simulation but it is primarily designed to serve as a \
calculation engine for analysis and optimal control algorithms that require 1st and 2nd derivatives \
of the system's dynamics.",
       author = 'Elliot Johnson',
       author_email = 'elliot.r.johnson@gmail.com',
       url = 'http://murpheylab.github.io/trep/',
       license='GPLv3',
       platforms='Linux, Mac, Windows',
       package_dir = {'' : 'src', 'trep': 'src'},
       packages=['trep',
                 'trep.constraints',
                 'trep.potentials',
                 'trep.forces',
                 'trep.visual',
                 'trep.puppets',
                 'trep.discopt',
                 'trep.ros'
                 ],
       package_data={
           'trep.visual' : ['icons/*.svg'], 'trep' : ['_trep/*.h']
           },
       ext_modules=ext_modules,
       cmdclass=cmd_class,
       command_options=cmd_options,
       zip_safe=False,
       install_requires=[
           'numpy',
           'scipy',
       ],
       headers=[
           'src/_trep/trep.h',
           'src/_trep/c_api.h'
           ])
