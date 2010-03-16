# -*- coding: utf-8 -*-

class IngredientConflict(Exception):
    """Exception triggered when a package of the same name already exists."""

    def __init__(self, dist, package):
        self.dist = dist
        self.package = package

    def __str__(self):
        return ("Apparently '%s' was already added by some other "
            "distribution. This happened while attempting to add %s." %
            (self.package, str(self.dist)))

class RottenEgg(Exception):
    """Exception triggered when a binary egg is found where it is unwanted.
    """

    def __init__(self, dist):
        self.dist = dist

    def __str__(self):
        return "%s is a rotten egg (binary distribution)." % str(self.dist)
