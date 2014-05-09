__author__ = 'vincent'
import unittest

from machine_simulation.simulation import *
from machine_simulation.input import *


class IntegrationTest(unittest.TestCase):
    """
    Test boundary cases
    """

    def setUp(self):
        self.env = simpy.Environment()
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, True),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, True),
        ]
        self.module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB),
                             breakable_components)

    def test_zero_maintenance_men(self):
        Factory(self.env, 0, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertEqual(self.module.stock.purchase_costs, 0)
        for component in self.module.breakable_components:
            self.assertEqual(component.stock.purchase_costs, 0)

        self.assertEqual(self.module.stock.inventory_holding_costs,
                         self.module.stock.capacity * self.module.stock.unit_holding_costs * time)
        for component in self.module.breakable_components:
            self.assertEqual(component.stock.inventory_holding_costs,
                             component.stock.capacity * component.stock.unit_holding_costs * time)


class TestRandomSeed(unittest.TestCase):

    def test_random_seed(self):
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
                             factory2.module.breakable_components[index].stock.purchase_costs, "%s %s" % (component1.name, factory2.module.breakable_components[index].name))
            index += 1