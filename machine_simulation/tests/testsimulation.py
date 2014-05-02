__author__ = 'Vincent van Bergen'

from machine_simulation.simulation import *


class TestComponentType(ComponentType):
    def time_to_failure(self):
        """Return time until next failure"""
        return self.mean