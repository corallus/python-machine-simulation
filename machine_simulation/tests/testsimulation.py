__author__ = 'Vincent van Bergen'

from machine_simulation.simulation import *


class TestBreakableComponent(BreakableComponent):
    """
    Class used to avoid random number generation in tests
    """
    def time_to_failure(self):
        """Return time until next failure"""
        return self.mean