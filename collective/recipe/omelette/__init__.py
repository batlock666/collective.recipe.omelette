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
from collective.recipe.omelette.utils import symlink, unlink, islink, rmtree

def makedirs(target):
    """ Similar to os.makedirs, but adds __init__.py files as it goes.  Returns a boolean
        indicating success.
    """
    drive, path = os.path.splitdrive(target)
    parts = path.split(os.path.sep)
    current = drive + os.path.sep    
    for part in parts:
        current = os.path.join(current, part)
        if islink(current):
            return False
        if not os.path.exists(current):
            os.mkdir(current)
            init_filename = os.path.join(current, '__init__.py')
            if not os.path.exists(init_filename):
                init_file = open(init_filename, 'w')
                init_file.write("# mushroom")
                init_file.close()
    return True
    
class Recipe(object):
    """zc.buildout recipe"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        self.logger = logging.getLogger(self.name)
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)
                
        if not options.has_key('location'):
            options['location'] = os.path.join(
                buildout['buildout']['parts-directory'],
                self.name,
                )
        
        ignore_develop = options.get('ignore-develop', '').lower()
        develop_eggs = []
        if ignore_develop in ('yes', 'true', 'on', '1', 'sure'):
            develop_eggs = os.listdir(
                               buildout['buildout']['develop-eggs-directory'])
            develop_eggs = [dev_egg[:-9] for dev_egg in develop_eggs]
        ignores = options.get('ignores', '').split()
        self.ignored_eggs = develop_eggs + ignores
        
        products = options.get('products', '').split()
        self.packages = [(p, 'Products') for p in products]
        self.packages += [l.split()
                         for l in options.get('packages', '').splitlines()
                         if l.strip()]

    def install(self):
        """Crack the eggs open and mix them together"""

        location = self.options['location']
        if os.path.exists(location):
            rmtree(location)
        os.mkdir(location)

        try:
            requirements, ws = self.egg.working_set()
            for dist in ws.by_key.values():
                project_name =  dist.project_name
                if project_name not in self.ignored_eggs:
                    namespaces = {}
                    for line in dist._get_metadata('namespace_packages.txt'):
                        ns = namespaces
                        for part in line.split('.'):
                            ns = ns.setdefault(part, {})
                    top_level = list(dist._get_metadata('top_level.txt'))
                    def create_namespaces(namespaces, ns_base=()):
                        for k, v in namespaces.iteritems():
                            ns_parts = ns_base + (k,)
                            link_dir = os.path.join(location, *ns_parts)
                            if not os.path.exists(link_dir):
                                if '/zc' in link_dir:
                                    print link_dir, package_name, namespaces
                                if not makedirs(link_dir):
                                    self.logger.warn("Warning: (While processing egg %s) Could not create namespace directory (%s).  Skipping." % (project_name, link_dir))
                                    continue
                            if len(v) > 0:
                                create_namespaces(v, ns_parts)
                            else:
                                egg_ns_dir = os.path.join(dist.location, *ns_parts)
                                dirs = [x for x in os.listdir(egg_ns_dir)
                                        if os.path.isdir(
                                            os.path.join(egg_ns_dir, x)
                                        )]
                                for name in dirs:
                                    name_parts = ns_parts + (name,)
                                    src = os.path.join(dist.location, *name_parts)
                                    dst = os.path.join(location, *name_parts)
                                    symlink(src, dst)
                    create_namespaces(namespaces)
                    for package_name in top_level:
                        if package_name in namespaces:
                            # These are processed in create_namespaces
                            continue
                        else:
                            package_location = os.path.join(dist.location, package_name)
                            link_location = os.path.join(location, package_name)
                            if not os.path.exists(package_location):
                                package_location = os.path.join(dist.location, package_name+".py")
                                link_location = os.path.join(location, package_name+".py")
                            if not os.path.exists(package_location):
                                package_location = os.path.join(dist.location, package_name+".so")
                                link_location = os.path.join(location, package_name+".so")
                            if not os.path.exists(package_location):
                                package_location = os.path.join(dist.location, package_name+".dll")
                                link_location = os.path.join(location, package_name+".dll")
                            if not os.path.exists(package_location):
                                self.logger.warn("Warning: (While processing egg %s) Package '%s' not found.  Skipping." % (project_name, package_name))
                                continue
                        if not os.path.exists(link_location):
                            symlink(package_location, link_location)
                        else:
                            self.logger.warn("Warning: (While processing egg %s) Link already exists (%s -> %s).  Skipping." % (project_name, package_location, link_location))
                            continue
                    # parts = project_name.split('.')
                    # namespaces = parts[:-1]
                    # package_name = parts[-1]
                    # egg_location = os.path.join(dist.location, *parts)
                    # 
                    # link_dir = os.path.join(location, *namespaces)
                    # if not os.path.exists(link_dir):
                    #     if not makedirs(link_dir):
                    #         self.logger.warn("Warning: (While processing egg %s) Could not create containing directory.  Skipping." % (project_name))
                    #         continue
                    # link_location = os.path.join(link_dir, package_name)
                    # if not os.path.exists(egg_location):
                    #     self.logger.warn("Warning: (While processing egg %s) Egg contents not found at %s.  Skipping." % (project_name, egg_location))
                    #     continue
                    # if not os.path.exists(link_location):
                    #     symlink(egg_location, link_location)
                    # else:
                    #     self.logger.warn("Warning: (While processing egg %s) Link already exists.  Skipping." % project_name)
                    #     continue

            for package in self.packages:
                if len(package) == 1:
                    link_name = 'Products/'
                    package_dir = package[0]
                elif len(package) == 2:
                    link_name = package[1]
                    package_dir = package[0]
                else:
                    self.logger.warn("Warning: Invalid package: %s" % (self.name, package))
                    continue
                
                link_dir = os.path.join(location, link_name)
                self._add_bacon(package_dir, link_dir)
                            
        except:
            if os.path.exists(location):
                rmtree(location)
            raise
        
        return location
        
    def _add_bacon(self, package_dir, target_dir):
        """ Link packages from package_dir into target_dir.  Recurse a level if target_dir/(package)
            already exists.
        """
        if os.path.exists(package_dir):
            if islink(target_dir):
                self.logger.warn("Warning: (While processing package directory %s) Link already exists at %s.  Skipping." % (package_dir, target_dir))
                return            
            elif not os.path.exists(target_dir):
                if not makedirs(target_dir):
                    self.logger.warn("Warning: (While processing package directory %s) Link already exists at %s.  Skipping." % (package_dir, target_dir))
                    return            
            for package_name in [p for p in os.listdir(package_dir) if not p.startswith('.')]:
                package_location = os.path.join(package_dir, package_name)
                if not os.path.isdir(package_location):
                    # skip ordinary files
                    continue
                link_location = os.path.join(target_dir, package_name)
                if islink(link_location):
                    self.logger.warn("Warning: (While processing package %s) Link already exists.  Skipping." % package_location)
                elif os.path.isdir(link_location):
                    self._add_bacon(package_location, link_location)
                else:
                    symlink(package_location, link_location)
        else:
            self.logger.warn("Warning: Product directory %s not found.  Skipping." % package_dir)
        
def uninstall(name, options):
    location = options.get('location')
    if os.path.exists(location):
        rmtree(location)
