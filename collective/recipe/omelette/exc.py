# -*- coding: utf-8 -*-

class RottenEgg(object):
    """Exception triggered when a binary egg is found where it is unwanted.
    """

    def __init__(self, dist, msg=''):
        self.dist = dist
        self.msg = msg
