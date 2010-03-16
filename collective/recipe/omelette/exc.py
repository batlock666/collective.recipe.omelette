# -*- coding: utf-8 -*-

class RottenEgg(Exception):
    """Exception triggered when a binary egg is found where it is unwanted.
    """

    def __init__(self, dist, msg=''):
        self.dist = dist
        self.msg = msg

    def __str__(self):
        return "%s is a rotten egg." % str(self.dist)
