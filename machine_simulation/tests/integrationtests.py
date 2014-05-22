__author__ = 'vincent'
import unittest

from machine_simulation.simulation import *
from machine_simulation.input import *


class IntegrationTest(unittest.TestCase):
    """
    Test boundary cases
    """

    def setUp(self):
        """
        Sets up machine with module consisting of 2 parts with non-zero inventory holding costs and non-zero purchase
        costs
        """
        self.env = simpy.Environment()
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, False),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, True),
        ]
        self.module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB),
                             breakable_components)

    def test_zero_maintenance_men(self):
        """
        Tests whether operators take care of replacement when number of maintenance men set to 0
        """
        factory = Factory(self.env, 0, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertEqual(factory.maintenance_men_salary, 0)


class TestRandomSeed(unittest.TestCase):
    def test_random_seed(self):
        """
        Tests whether simulation results are the same for 2 simulations if a random seed is set
        """
        env = simpy.Environment()
        breakable_components = [
            BreakableComponent(env, "Part A", TRA, ComponentStock(env, CA, LA, CHA, SA), 5, False),
            BreakableComponent(env, "Part B", TRB, ComponentStock(env, CB, LB, CHB, SB), 5, False),
        ]
        self.module = Module(env, TRAB, ComponentStock(env, CAB, LAB, CHAB, SAB),
                             breakable_components)
        factory1 = Factory(env, 4, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        env.run(until=time)
        env = simpy.Environment()
        breakable_components = [
            BreakableComponent(env, "Part A", TRA, ComponentStock(env, CA, LA, CHA, SA), 5, False),
            BreakableComponent(env, "Part B", TRB, ComponentStock(env, CB, LB, CHB, SB), 5, False),
        ]
        self.module = Module(env, TRAB, ComponentStock(env, CAB, LAB, CHAB, SAB),
                             breakable_components)
        factory2 = Factory(env, 4, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        env.run(until=time)

        self.assertEqual(factory1.module.stock.purchase_costs, factory2.module.stock.purchase_costs)

        index = 0
        for component1 in factory1.module.breakable_components:
            self.assertEqual(component1.stock.purchase_costs,
                             factory2.module.breakable_components[index].stock.purchase_costs,
                             "%s %s" % (component1.name, factory2.module.breakable_components[index].name))
            index += 1