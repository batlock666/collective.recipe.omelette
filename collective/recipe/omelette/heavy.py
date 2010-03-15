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
This recipe creates an easily navigable directory structure copying to the
contents of all the eggs installed in the recipe.  See README.txt for details.
"""

import os
import sys
import shutil

from collective.recipe.omelette.skinny import Omelette
from collective.recipe.omelette.utils import (islink, makedirs, rmitem,
    rmtree, symlink, unlink, WIN32)

class BigOmelette(Omelette):
    """A zc.buildout recipe similar to the default FluffyOmelette recipe (or
    skinny omelette) except that it uses both the egg white and yoke. This
    recipe copies the entire package (egg) contents into a single directory
    instead of creating symbolic links for them."""

    def cook(self):
        pass
