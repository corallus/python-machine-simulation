__author__ = 'vincent'
import unittest

from machine_simulation.simulation import *
from machine_simulation.input import *

OPERATOR_SALARY = 10
MAINTENANCE_MAN_SALARY = 5


class IntegrationTest(unittest.TestCase):
    """
    Test boundary cases
    """

    def setUp(self):
        self.env = simpy.Environment()
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5),
        ]
        self.module = Module(self.env, "Module", TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB),
                             breakable_components)

    def test_zero_maintenance_men(self):
        Factory(self.env, 0, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY, PolicyA)
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

    def test_policy_o(self):
        Factory(self.env, NUMBER_MAINTENANCE_MEN, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY, PolicyO)
        time = 1000
        self.env.run(until=time)
        self.assertEqual(self.module.stock.purchase_costs, 0)
        for component in self.module.breakable_components:
            self.assertNotEqual(component.stock.purchase_costs, 0)

    def test_policy_a(self):
        Factory(self.env, NUMBER_MAINTENANCE_MEN, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY, PolicyA)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(self.module.stock.purchase_costs, 0)
        self.assertNotEqual(self.module.breakable_components[1].stock.purchase_costs, 0)
        self.assertEqual(self.module.breakable_components[0].stock.purchase_costs, 0)

    def test_policy_b(self):
        Factory(self.env, NUMBER_MAINTENANCE_MEN, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY, PolicyB)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(self.module.stock.purchase_costs, 0)
        self.assertNotEqual(self.module.breakable_components[0].stock.purchase_costs, 0)
        self.assertEqual(self.module.breakable_components[1].stock.purchase_costs, 0)

    def test_policy_c(self):
        Factory(self.env, NUMBER_MAINTENANCE_MEN, self.module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY, PolicyAB)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(self.module.stock.purchase_costs, 0)
        self.assertEqual(self.module.breakable_components[0].stock.purchase_costs, 0)
        self.assertEqual(self.module.breakable_components[1].stock.purchase_costs, 0)