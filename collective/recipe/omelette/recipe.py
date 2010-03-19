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
from ConfigParser import ConfigParser

import zc.recipe.egg
from collective.recipe.omelette.exc import IngredientConflict, RottenEgg
from collective.recipe.omelette.utils import (islink, makedirs, rmitem,
    rmtree, symlink, unlink, WIN32)
from collective.recipe.omelette.utils import get_namespaces

try:
    from shutil import ignore_patterns
except ImportError:
    from collective.recipe.omelette.utils import ignore_patterns

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
        #   proceedure, we keep location in the options dictionary up-to-date.
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

        # Metadata config file
        self._init_metadata()

    def _init_metadata(self):
        """Initialize the metadata configuration file."""
        filename = self.options.get('metadata', None)
        if filename is None:
            self.metadata = self.metadata_file = None
        else:
            self.metadata_file = os.path.join(
                self.buildout['buildout']['directory'], filename)
            self.metadata = ConfigParser()
            self.metadata.read(self.metadata_file)

    def _build_namespace_tree(self, dist, excluder=None):
        """Creates the namespace directory tree struction."""
        namespaces = get_namespaces(dist)
        def create_namespace(pkg_location, namespaces, ns_base=()):
            for k, v in namespaces.iteritems():
                ns_parts = ns_base + (k,)
                target_dir = os.path.join(self.location, *ns_parts)
                # 1. Target namespace level has been already been created?
                if not os.path.exists(target_dir):
                    # Has not been previously created?
                    if not makedirs(target_dir, is_namespace=True):
                        continue
                # 2. Is namespace of more than one level?
                if len(v) > 0:
                    create_namespace(pkg_location, v, ns_parts)
                # 3. end of the line, packages from here on out
                else:
                    egg_ns_dir = os.path.join(pkg_location, *ns_parts)
                    # Check if it's a binary (rotten) egg and pitch it
                    if not os.path.isdir(egg_ns_dir):
                        raise Exception()
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
                            self.utensil(src, dst, excluder=excluder)
                        except OSError:
                            pass
        create_namespace(dist.location, namespaces)

    def utensil(self, src, dst, excluder=None):
        """The action used to process the distribute. For example, it could
        be a cut and paste process."""
        raise NotImplementedError()

    def cook(self):
        """Process all the distributions specified in this recipe."""
        raise NotImplementedError()

    def install(self):
        """Crack the eggs (distributions) open and mix them together."""
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

        # Write out the metadata file before completing the install
        if self.metadata:
            file = open(self.metadata_file, 'w')
            self.metadata.write(file)

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

    def _crack_shell(self, dist, namespaces, ns_base=()):
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
                self._crack_shell(dist, v, ns_parts)
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
                namespaces = get_namespaces(dist)
                self._crack_shell(dist, namespaces)
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


class FatOmelette(Omelette):
    """A zc.buildout recipe similar to the default FluffyOmelette recipe (or
    skinny omelette) except that it uses both the egg white and yoke. This
    recipe copies the entire package (egg) contents into a single directory
    instead of creating symbolic links for them."""

    def __init__(self, buildout, name, options):
        options['metadata'] = 'setup.cfg'
        super(FatOmelette, self).__init__(buildout, name, options)

    def _add_ingredient(self, dist):
        # Check to see if it is a binary distribution.
        # Note: Binary distributiones (.egg) are being depricated in favor of
        #   only source distributions.
        if not os.path.isdir(dist.location):
            raise RottenEgg(dist)

        skillet = self.options['location']
        name_filter = ignore_patterns('*.pyc', '.svn', '.hg*', '.git*')
        top_level = list(dist._get_metadata('top_level.txt'))
        # native_libs = list(dist._get_metadata('native_libs.txt'))
        project_name = dist.project_name

        # Create the namespaces and copy the contents
        self._build_namespace_tree(dist, name_filter)
        # Process any top_level items that aren't namespaces
        namespaces = get_namespaces(dist)
        for pkg_name in top_level:
            if pkg_name in namespaces:
                # These have been processed previously by
                #   _build_namespace_tree
                continue

            pkg_location = os.path.join(dist.location, pkg_name)
            target_location = os.path.join(self.location, pkg_name)

            # Check for single python module
            if not os.path.exists(pkg_location):
                name = '.'.join([pkg_name, 'py'])
                pkg_location = os.path.join(dist.location, name)
                target_location = os.path.join(self.location, name)
            # Check for native libs
            # XXX - this should use native_libs from above
            if not os.path.exists(pkg_location):
                name = '.'.join([pkg_name, 'so'])
                pkg_location = os.path.join(dist.location, name)
                target_location = os.path.join(self.location, name)
            if not os.path.exists(pkg_location):
                name = '.'.join([pkg_name, 'dll'])
                pkg_location = os.path.join(dist.location, name)
                target_location = os.path.join(self.location, name)
            if not os.path.exists(pkg_location):
                self.logger.warn("Warning: (While processing egg %s) Package "
                    "'%s' not found.  Skipping." %
                    (project_name, pkg_name))
                continue

            if os.path.exists(target_location):
                raise IngredientConflict(dist, pkg_name)
            else:
                self.utensil(pkg_location, target_location)
        return True

    def _add_bacon(self, package_dir, target_dir):
        """Copy packages from package_dir into target_dir. Recurse a level if
        target_dir/(package) already exists."""
        if not os.path.exists(package_dir):
            raise RuntimeError("Package directory '%s' not found." %
                package_dir)

        self.logger.warn("Packages at '%s' will not be included." % package_dir)

    def utensil(self, src, dst, excluder=None):
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=excluder)
            else:
                shutil.copy2(src, dst)
        except OSError:
            pass # XXX
        return True

    def cook(self):
        requirements, ws = self.egg.working_set()
        # Initialize the metadata variables with initial whitespace for
        #   indention style formating.
        provides = ['']
        requires = ['']
        namespaces = ['']

        for dist in ws.by_key.values():
            project_name =  dist.project_name
            if project_name not in self.ignored_eggs:
                try:
                    # Attempt to add a distribution
                    self._add_ingredient(dist)
                except RottenEgg as err_ob:
                    # While attempting to add the distribution, we found a
                    #   problem where we can't add the distribution to this
                    #   package, therefore we need to require it
                    requires.append("%s (==%s)" % (
                        err_ob.dist.project_name, err_ob.dist.version))
                else:
                    # The distribution was successfully added and now
                    #   this package provides it
                    provides.append("%s (==%s)" % (
                        dist.project_name, dist.version))
                # XXX Grabbing at the namespaces dictionary far to often.
                for ns in dist._get_metadata('namespace_packages.txt'):
                    namespaces.append(ns)

        # Assign the requires and provides metadata
        section = 'metadata'
        if not self.metadata.has_section(section):
            self.metadata.add_section(section)
        requires.sort()
        provides.sort()
        self.metadata.set(section, 'requires', '\n'.join(requires))
        self.metadata.set(section, 'provides', '\n'.join(provides))
        # Assign the namespaces metadata
        section = 'namespaces' # XXX this isn't a valid PEP 390 section
        if not self.metadata.has_section(section):
            self.metadata.add_section(section)
        namespaces = list(set(namespaces)) # duplicate entry removal
        namespaces.sort()
        self.metadata.set(section, 'namespaces', '\n'.join(namespaces))

        if self.packages:
            self.logger.warn("Warning: Packages and Products are not used "
                "by this recipe.")
        # for package in self.packages:
        #     if len(package) == 1:
        #         # If it only one element it's a Product?
        #         target_name = 'Products'
        #         package_dir = package[0]
        #     elif len(package) == 2:
        #         # If it's more than one element, then it's a package; which
        #         #   means that it should have a valid package structure.
        #         target_name = package[1]
        #         package_dir = package[0]
        #     else:
        #         raise RuntimeError("Warning: Invalid packaging syntax for: "
        #             "%s" % package)
        # 
        #     target_dir = os.path.join(self.location, target_name)
        #     self._add_bacon(package_dir, target_dir)
