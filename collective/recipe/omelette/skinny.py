# -*- coding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2008 David Glick.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""
This recipe creates an easily navigable directory structure linking to the
contents of a lists of eggs.  See README.txt for details.
"""

import os
import sys
import shutil
import logging
import zc.recipe.egg
from collective.recipe.omelette.utils import (islink, makedirs, rmitem,
    rmtree, symlink, unlink, WIN32)

def uninstall(name, options):
    location = options.get('location')
    if os.path.exists(location):
        rmtree(location)

class Omelette(object):
    """zc.buildout recipe"""

    def __init__(self, buildout, name, options):
        # Typical recipe assignements
        self.buildout, self.name, self.options = buildout, name, options
        # Setup a logger
        self.logger = logging.getLogger(self.name)
        # Create an instance of the Egg recipe for obtaining eggs and egg
        #   egg related information
        recipe = options['recipe'].split(':')[0]
        self.egg = zc.recipe.egg.Egg(buildout, recipe, options)

        # Determine the location the recipe should use for the cooked results
        if not options.has_key('location'):
            # If a location wasn't provided we will use buildout's parts
            #   directory (e.g. mybuildout/parts/omelette)
            options['location'] = os.path.join(
                buildout['buildout']['parts-directory'],
                self.name,
                )
        # For easy reference and backwards compatibility with the uninstall
        #   proceedure we location in the options dictionary.
        self.location = options['location']

        ignore_develop = options.get('ignore-develop', '').lower()
        develop_eggs = []
        if ignore_develop in ('yes', 'true', 'on', '1', 'sure'):
            develop_eggs = os.listdir(
                self.buildout['buildout']['develop-eggs-directory'])
            develop_eggs = [dev_egg[:-9] for dev_egg in develop_eggs]
        ignores = options.get('ignores', '').split()
        self.ignored_eggs = develop_eggs + ignores

        # Zope2-centric?
        products = options.get('products', '').split()
        self.packages = [(p, 'Products') for p in products]
        self.packages += [l.split()
            for l in options.get('packages', '').splitlines()
            if l.strip()]

    def cook(self):
        raise NotImplementedError()

    def install(self):
        """Crack the eggs open and mix them together"""
        # Smash the plate if there is one and create a new one
        uninstall(self.name, self.options)
        os.mkdir(self.location)

        # Cook the omelette, if it's not perfect throw it away
        try:
            self.cook()
        except:
            for item in os.listdir(self.location):
                rmitem(os.path.join(self.location, item))
            raise

        # Serve the omelette
        return self.location

    update = install


class FluffyOmelette(Omelette):
    """zc.buildout recipe for creating an egg whites only omelette. This
    recipe will create a single directory with symbolic links to all the
    packages (eggs) in the recipe."""

    def _add_bacon(self, package_dir, target_dir):
        """Link packages from package_dir into target_dir. Recurse a level if
        target_dir/(package) already exists."""
        if os.path.exists(package_dir):
            if islink(target_dir):
                self.logger.warn("Warning: (While processing package "
                    "directory %s) Link already exists at %s.  Skipping." %
                    (package_dir, target_dir))
                return
            elif not os.path.exists(target_dir):
                if not makedirs(target_dir):
                    self.logger.warn("Warning: (While processing package "
                        "directory %s) Link already exists at %s.  "
                        "Skipping." % (package_dir, target_dir))
                    return
            package_names = [p
                for p in os.listdir(package_dir)
                if not p.startswith('.')]
            for package_name in package_names:
                package_location = os.path.join(package_dir, package_name)
                if not os.path.isdir(package_location):
                    # skip ordinary files
                    continue
                link_location = os.path.join(target_dir, package_name)
                if islink(link_location):
                    self.logger.warn("Warning: (While processing package "
                        "%s) Link already exists.  Skipping." %
                        package_location)
                elif os.path.isdir(link_location):
                    self._add_bacon(package_location, link_location)
                else:
                    symlink(package_location, link_location)
        else:
            self.logger.warn("Warning: Product directory %s not found.  "
                "Skipping." % package_dir)

    def _create_namespaces(self, dist, namespaces, ns_base=()):
        for k, v in namespaces.iteritems():
            ns_parts = ns_base + (k,)
            link_dir = os.path.join(self.location, *ns_parts)
            if not os.path.exists(link_dir):
                if not makedirs(link_dir, is_namespace=True):
                    self.logger.warn("Warning: (While processing egg %s) "
                        "Could not create namespace directory (%s).  "
                        "Skipping." % (project_name, link_dir))
                    continue
            if len(v) > 0:
                self._create_namespaces(dist, v, ns_parts)
            else:
                egg_ns_dir = os.path.join(dist.location, *ns_parts)
                if not os.path.isdir(egg_ns_dir):
                    self.logger.info("(While processing egg %s) Package "
                        "'%s' is zipped.  Skipping." %
                        (project_name, os.path.sep.join(ns_parts)))
                    continue
                dirs = os.listdir(egg_ns_dir)
                for name in dirs:
                    if name.startswith('.'):
                        continue
                    name_parts = ns_parts + (name,)
                    src = os.path.join(dist.location, *name_parts)
                    dst = os.path.join(self.location, *name_parts)
                    if os.path.exists(dst):
                        continue
                    try:
                        symlink(src, dst)
                    except OSError:
                        self.logger.warn("Could not create symlink while "
                            "processing %s" % (os.path.join(*name_parts)))

    def _add_seasoning(self, dist, namespaces):
        top_level = list(dist._get_metadata('top_level.txt'))
        native_libs = list(dist._get_metadata('native_libs.txt'))
        for package_name in top_level:
            if package_name in namespaces:
                # These are processed in create_namespaces
                continue
            else:
                if not os.path.isdir(dist.location):
                    self.logger.info("(While processing egg %s) Package "
                        "'%s' is zipped.  Skipping." %
                        (project_name, package_name))
                    continue

                package_location = os.path.join(dist.location, package_name)
                link_location = os.path.join(self.location, package_name)

                # Check for single python module
                if not os.path.exists(package_location):
                    name = package_name + '.py'
                    package_location = os.path.join(dist.location, name)
                    link_location = os.path.join(self.location, name)

                # Check for native libs
                # XXX - this should use native_libs from above
                if not os.path.exists(package_location):
                    name = package_name + '.so'
                    package_location = os.path.join(dist.location, name)
                    link_location = os.path.join(self.location, name)
                if not os.path.exists(package_location):
                    name = package_name + '.dll'
                    package_location = os.path.join(dist.location, name)
                    link_location = os.path.join(self.location, name)

                if not os.path.exists(package_location):
                    self.logger.warn("Warning: (While processing egg %s) "
                        "Package '%s' not found.  Skipping." %
                        (project_name, package_name))
                    continue

            if not os.path.exists(link_location):
                if WIN32 and not os.path.isdir(package_location):
                    self.logger.warn("Warning: (While processing egg %s) "
                        "Can't link files on Windows (%s -> %s).  "
                        "Skipping." % (project_name,
                        package_location, link_location))
                    continue
                symlink(package_location, link_location)
            else:
                self.logger.info("(While processing egg %s) Link already "
                    "exists (%s -> %s).  Skipping." % (project_name,
                    package_location, link_location))
                continue

    def cook(self):
        """Cook the omelette."""
        requirements, ws = self.egg.working_set()
        for dist in ws.by_key.values():
            project_name =  dist.project_name
            if project_name not in self.ignored_eggs:
                namespaces = {}
                for line in dist._get_metadata('namespace_packages.txt'):
                    ns = namespaces
                    for part in line.split('.'):
                        ns = ns.setdefault(part, {})
                self._create_namespaces(dist, namespaces)
                self._add_seasoning(dist, namespaces)

        for package in self.packages:
            if len(package) == 1:
                link_name = 'Products/'
                package_dir = package[0]
            elif len(package) == 2:
                link_name = package[1]
                package_dir = package[0]
            else:
                self.logger.warn("Warning: Invalid package: %s" % package)
                continue

            link_dir = os.path.join(self.location, link_name)
            self._add_bacon(package_dir, link_dir)
