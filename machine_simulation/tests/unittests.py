__author__ = 'Vincent van Bergen'

import unittest

from machine_simulation.simulation import *
from testsimulation import TestComponentType as ComponentType
from machine_simulation.input import *


class TestComponentType(unittest.TestCase):
    """
    Tests whether component_type behaves like S-1 queue and tests the inventory holding costs
    """

    def setUp(self):
        """
        Initialises a simulation environment and a ComponentType
        """
        self.env = simpy.Environment()
        self.component_type = ComponentType(self.env, 'test part', MA, CA, LA, CHA, TRA, SA)

    def test_single_order(self):
        """
        Tests whether the stock is refilled after a single order
        """
        stock = self.component_type.stock
        stock.get(1)
        self.env.process(self.component_type.order())
        self.assertEqual(stock.level, self.component_type.order_up_to-1)
        self.env.run(until=self.component_type.delivery_time+1)
        self.assertEqual(stock.level, self.component_type.order_up_to)

    def test_multiple_orders(self):
        """
        Tests whether stock is refilled after multiple orders
        """
        stock = self.component_type.stock
        stock.get(1)
        self.env.process(self.component_type.order())
        stock.get(1)
        self.env.process(self.component_type.order())
        stock.get(1)
        self.env.process(self.component_type.order())
        self.assertEqual(stock.level, max(0, self.component_type.order_up_to-3))
        self.env.run(until=self.component_type.delivery_time + 1)
        self.assertEqual(stock.level, self.component_type.order_up_to)

    def test_inventory(self):
        """
        Tests whether ComponentType keeps track of correct inventory costs
        """
        self.env.process(self.component_type.inventory())
        stock = self.component_type.stock
        stock.get(1)
        self.env.process(self.component_type.order())
        self.env.run(until=self.component_type.delivery_time + 1)
        self.assertEqual(self.component_type.inventory_holding_costs,
                         self.component_type.delivery_time * (
                             self.component_type.inventory_holding_costs * (self.component_type.order_up_to - 1)
                         ) + self.component_type.order_up_to * self.component_type.inventory_holding_costs)


class TestSinglePart(unittest.TestCase):
    """
    Tests machine with a single part
    """

    def setUp(self):
        """
        Initialises a simulation environment and a Machine with one Part
        """
        self.env = simpy.Environment()
        # the delivery time of a part has to be smaller then the replacement time, such that the stock level is stable
        # 1 < 5 + 3
        part_component_type = ComponentType(self.env, "Part A", MA, CA, LA, CHA, TRA, SA)
        machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        maintenance_men = simpy.Resource(self.env, capacity=NUMBER_MAINTENANCE_MEN)
        machine = PolicyO(self.env, 'Test machine 1', machine_component_type, [part_component_type], CD, maintenance_men)
        self.part = machine.parts[0]

    def test_break_part(self):
        """
        Tests whether a part breaks after its' breakdown time
        """
        self.env.run(until=self.part.component_type.mean + 1)
        self.assertEqual(self.part.broken, True)

    def test_replace(self):
        """
        Tests whether the replace actually replaces the part
        """
        component_type = self.part.component_type
        self.env.run(until=component_type.mean + component_type.time_replacement + 1)
        self.assertFalse(self.part.broken)

    def test_inventory_costs(self):
        """
        Tests whether the inventory costs are added to a product component_types' costs
        """
        component_type = self.part.component_type
        periods = 10
        run_until = component_type.mean + periods * (component_type.mean + component_type.time_replacement)
        self.assertTrue((run_until - component_type.mean) / (component_type.mean + component_type.time_replacement) == periods)

        self.env.run(until=run_until)
        expected_costs = component_type.unit_holding_costs * (
            component_type.mean * component_type.safety_stock +
            periods * (
                (component_type.safety_stock - 1) * component_type.delivery_time +
                (component_type.mean + component_type.time_replacement - component_type.delivery_time) *
                component_type.safety_stock
            )
        )
        self.assertEqual(component_type.inventory_holding_costs, expected_costs)


class TestMultipleParts(unittest.TestCase):
    """
    Test the relation between breakdowns of multiple parts of the same machine
    """

    def setUp(self):
        """
        Initialises a simulation environment and a Machine consisting of 2 parts
        """
        self.env = simpy.Environment()
        part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, LA, CHA, TRA, SA),
            ComponentType(self.env, "Part B", MB, CB, LB, CHB, TRB, SB)
        ]
        machine_component_type = ComponentType(self.env, "Test machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        maintenance_men = simpy.Resource(self.env, capacity=NUMBER_MAINTENANCE_MEN)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_component_type, part_component_types, CD,
                               maintenance_men)

    def test_not_multiple_broken(self):
        """
        Tests whether multiple parts of a machine can be broken at the same time. Specifically this tests whether some
        part breaks when another part is already broken
        """
        self.env.run(until=max([part.component_type.mean for part in self.machine.parts]) + 1)
        self.assertNotEqual(self.machine.parts[0].broken, self.machine.parts[1].broken)


class TestMachine(unittest.TestCase):
    """
    Tests behaviour of a single machine
    """

    def setUp(self):
        """
        Initialises a simulation environment and 2 Parts
        """
        self.env = simpy.Environment()
        self.part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, LA, CHA, TRA, SA),
            ComponentType(self.env, "Part B", MB, CB, LB, CHB, TRB, SB)
        ]
        self.machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        self.maintenance_men = simpy.Resource(self.env, capacity=NUMBER_MAINTENANCE_MEN)

    def test_policy_o(self):
        """
        Tests whether the repair actually repairs the machine with policy O
        """
        machine = PolicyO(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, CD,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + first_part.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_a(self):
        """
        Tests whether the repair actually repairs the machine with policy A
        """
        machine = PolicyA(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, CD,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + machine.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_b(self):
        """
        Tests whether the repair actually repairs the machine with policy B
        """
        machine = PolicyB(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, CD,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + first_part.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_ab(self):
        """
        Tests whether the repair actually repairs the machine with policy AB
        """
        machine = PolicyAB(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, CD,
                           self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + machine.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)