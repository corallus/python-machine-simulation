__author__ = 'Vincent van Bergen'

import unittest

from machine_simulation.simulation import *
from testsimulation import TestBreakableComponent
from machine_simulation.input import *


class TestComponentStock(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()

    def test_single_get(self):
        """
        Tests whether ComponentStock behaves like (S-1,S) inventory system and tests the inventory holding costs
        """
        stock = ComponentStock(self.env, 10, 10, 10, 100)
        stock.get(1)
        self.env.run(until=1)
        self.assertEqual(stock.level, 100-1)
        self.env.run(until=1+stock.delivery_time)
        self.assertEqual(stock.level, 100)
        self.assertEqual(stock.purchase_costs, stock.unit_purchase_costs)

    def test_multiple_get(self):
        """
        Tests whether stock is refilled after multiple orders
        """
        stock = ComponentStock(self.env, 10, 10, 10, 100)
        stock.get(1)
        stock.get(1)
        stock.get(1)
        self.assertEqual(stock.level, max(0, stock.capacity - 3))
        self.env.run(until=stock.delivery_time + 1)
        self.assertEqual(stock.level, stock.capacity)

    def test_empty_stock(self):
        stock = ComponentStock(self.env, 10, 10, 10, 1)
        stock.get(1)
        stock.get(1)
        self.assertEqual(stock.level, 0)
        self.env.run(until=1)
        self.assertEqual(stock.in_order, 2)
        self.env.run(until=stock.delivery_time+1)
        self.assertEqual(stock.level, 1)
        self.assertEqual(stock.in_order, 0)

    def test_inventory(self):
        stock = ComponentStock(self.env, 10, 10, 10, 1)
        self.env.run(until=100)
        self.assertEqual(stock.inventory_holding_costs, stock.unit_holding_costs*100)
        self.assertEqual(stock.purchase_costs, 0)


class TestModule(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()

    def test_break_module(self):
        breakable_components = [
            TestBreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 4, False),
            TestBreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, False),
        ]

        module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB), breakable_components)

        factory = Factory(self.env, NUMBER_MAINTENANCE_MEN, module, CD, 1, 10, 6)

        broken_component, time = min([(component, component.time_to_failure())
                                      for component in module.breakable_components], key=lambda result: result[1])

        self.assertEqual(broken_component, breakable_components[0])
        self.assertEqual(time, 4)


class TestMachine(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()

    def test_policy_o(self):
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, False),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, False),
        ]
        module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB), breakable_components)
        Factory(self.env, NUMBER_MAINTENANCE_MEN, module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertEqual(module.stock.purchase_costs, 0)
        for component in module.breakable_components:
            self.assertNotEqual(component.stock.purchase_costs, 0)

    def test_policy_a(self):
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, True),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, False),
        ]
        module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB), breakable_components)
        Factory(self.env, NUMBER_MAINTENANCE_MEN, module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(module.stock.purchase_costs, 0)
        self.assertNotEqual(module.breakable_components[1].stock.purchase_costs, 0)
        self.assertEqual(module.breakable_components[0].stock.purchase_costs, 0)

    def test_policy_b(self):
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, False),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, True),
        ]
        module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB), breakable_components)
        Factory(self.env, NUMBER_MAINTENANCE_MEN, module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(module.stock.purchase_costs, 0)
        self.assertNotEqual(module.breakable_components[0].stock.purchase_costs, 0)
        self.assertEqual(module.breakable_components[1].stock.purchase_costs, 0)

    def test_policy_c(self):
        breakable_components = [
            BreakableComponent(self.env, "Part A", TRA, ComponentStock(self.env, CA, LA, CHA, SA), 5, True),
            BreakableComponent(self.env, "Part B", TRB, ComponentStock(self.env, CB, LB, CHB, SB), 5, True),
        ]
        module = Module(self.env, TRAB, ComponentStock(self.env, CAB, LAB, CHAB, SAB), breakable_components)
        Factory(self.env, NUMBER_MAINTENANCE_MEN, module, CD, 1, MAINTENANCE_MAN_SALARY, OPERATOR_SALARY)
        time = 1000
        self.env.run(until=time)
        self.assertNotEqual(module.stock.purchase_costs, 0)
        self.assertEqual(module.breakable_components[0].stock.purchase_costs, 0)
        self.assertEqual(module.breakable_components[1].stock.purchase_costs, 0)