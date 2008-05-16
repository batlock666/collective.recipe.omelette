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

WIN32 = False
if sys.platform[:3].lower() == "win":
    WIN32 = True

if WIN32:
    
    # We assume this is in the system PATH. The commands will fail if it's not.
    JUNCTION = "junction.exe" 
    
    def symlink(src, dest):
        cmd = "%s %s %s" % (JUNCTION, os.path.abspath(dest), os.path.abspath(src),)
        os.system(cmd)

    def unlink(dest):
        cmd = "%s -d %s" % (JUNCTION, os.path.abspath(dest),)
        os.system(cmd)

    def islink(dest):
        cmd = "%s %s" % (JUNCTION, os.path.abspath(dest),)
        stdout = os.popen(cmd)
        output = stdout.read()
        stdout.close()
        return "Substitute Name:" in output
        
        
    def rmtree(location, nonlinks=True):
        # Explicitly unlink all junction'd links
        for root, dirs, files in os.walk(location, topdown=False):
            for dir in dirs:
                path = os.path.join(root, dir)
                if islink(path):
                    unlink(path)
        # Then get rid of everything else
        if nonlinks:
            shutil.rmtree(location)
        
else:
    symlink = os.symlink
    islink = os.path.islink
    rmtree = shutil.rmtree

def makedirs(target):
    drive, path = os.path.splitdrive(target)
    parts = path.split(os.path.sep)
    current = drive + os.path.sep    
    for part in parts:
        current = os.path.join(current, part)
        if not os.path.exists(current):
            os.mkdir(current)
            init_filename = os.path.join(current, '__init__.py')
            if not os.path.exists(init_filename):
                init_file = open(init_filename, 'w')
                init_file.write("# mushroom")
                init_file.close()

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
        
        try:
            requirements, ws = self.egg.working_set()
            for dist in ws.by_key.values():
                project_name =  dist.project_name
                if  project_name not in self.ignored_eggs:
                    parts = project_name.split('.')
                    namespaces = parts[:-1]
                    package_name = parts[-1]
                    egg_location = os.path.join(dist.location, *parts)
                    
                    link_dir = os.path.join(location, *namespaces)
                    if not os.path.exists(link_dir):
                        makedirs(link_dir)
                    link_location = os.path.join(link_dir, package_name)
                    if not os.path.exists(egg_location):
                        self.logger.warn("Warning: (While processing egg %s) Egg contents not found at %s.  Skipping." % (project_name, egg_location))
                        continue
                    if not os.path.exists(link_location):
                        symlink(egg_location, link_location)
                    else:
                        self.logger.warn("Warning: (While processing egg %s) Link already exists.  Skipping." % project_name)
                        continue
                    
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
            if not os.path.exists(target_dir):
                makedirs(target_dir)
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
            print "Warning: Product directory %s not found." % package_dir
        
def uninstall(name, options):
    location = options.get('location')
    if os.path.exists(location):
        rmtree(location)
