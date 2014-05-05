__author__ = 'Vincent van Bergen'

import unittest

from machine_simulation.simulation import *
from testsimulation import TestComponentType as ComponentType
from machine_simulation.input import *


class TestComponentType(unittest.TestCase):
    """
    Test whether component_type behaves like S-1 queue
    """

    def setUp(self):
        self.env = simpy.Environment()
        self.component_type = ComponentType(self.env, 'test part', 0, 10, 10, 10, 0, 10)

    def test_single_order(self):
        print('testing single order')
        stock = self.component_type.stock
        stock.get(1)
        self.env.process(self.component_type.order())
        self.assertEqual(stock.level, 9)
        self.env.run(until=self.component_type.delivery_time + 1)
        self.assertEqual(stock.level, 10)

    def test_multiple_orders(self):
        print('testing multiple orders')
        stock = self.component_type.stock
        stock.get(1)
        self.env.process(self.component_type.order())
        stock.get(1)
        self.env.process(self.component_type.order())
        stock.get(1)
        self.env.process(self.component_type.order())
        self.assertEqual(stock.level, 7)
        self.env.run(until=self.component_type.delivery_time + 1)
        self.assertEqual(stock.level, 10)


class TestSinglePart(unittest.TestCase):
    """
    Test the failure of a machine with a single part
    """

    def setUp(self):
        self.env = simpy.Environment()
        # the delivery time of a part has to be smaller then the replacement time, such that the stock level is stable
        # 1 < 5 + 3
        part_component_type = ComponentType(self.env, "Part A", 5, CA, 1, CHA, 3, 100)
        machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        machine = PolicyO(self.env, 'Test machine 1', machine_component_type, [part_component_type], 10, maintenance_men)
        self.part = machine.parts[0]

    def test_breaking(self):
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
        Setup a machine consisting of two parts
        """
        self.env = simpy.Environment()
        part_component_types = [
            ComponentType(self.env, "Part A", 5, CA, LA, CHA, TRA, 100),
            ComponentType(self.env, "Part B", 6, CB, LB, CHB, TRB, 100)
        ]
        machine_component_type = ComponentType(self.env, "Test machine", 5, 15, 1, 3, 4, 50)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_component_type, part_component_types, 10,
                               maintenance_men)

    def test_not_multiple_broken(self):
        """
        Tests whether multiple parts of a machine can be broken at the same time. Specifically this tests whether some
        part breaks when another part is already broken
        """
        self.env.run(until=max([part.component_type.mean for part in self.machine.parts]) + 1)
        self.assertNotEqual(self.machine.parts[0].broken, self.machine.parts[1].broken)

    def test_memorylessness(self):
        """
        This test succeeds when the breakdown of a part is independent of the past
        """
        first_part = self.machine.parts[0]
        second_part = self.machine.parts[1]
        first_simulation = first_part.component_type.mean + first_part.component_type.time_replacement + \
                           second_part.component_type.mean + 1
        self.env.run(
            until=first_simulation
        )
        self.assertTrue(second_part.broken)
        self.env.run(
            until=first_simulation+second_part.component_type.time_replacement
        )
        self.assertTrue(second_part.broken)

        self.env.run(until=100)


class TestMachine(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()
        self.part_component_types = [
            ComponentType(self.env, "Part A", 4, CA, LA, CHA, TRA, 1),
            ComponentType(self.env, "Part B", 5, CB, LB, CHB, TRB, 1)
        ]
        self.machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        self.maintenance_men = simpy.Resource(self.env, capacity=100)

    def test_policy_o(self):
        """
        Tests whether the repair actually repairs the machine with policy O
        """
        machine = PolicyO(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, 10,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + first_part.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_a(self):
        """
        Tests whether the repair actually repairs the machine with policy A
        """
        machine = PolicyA(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, 10,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + machine.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_b(self):
        """
        Tests whether the repair actually repairs the machine with policy B
        """
        machine = PolicyB(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, 10,
                          self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + first_part.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)

    def test_policy_ab(self):
        """
        Tests whether the repair actually repairs the machine with policy AB
        """
        machine = PolicyAB(self.env, 'Test machine 1', self.machine_component_type, self.part_component_types, 10,
                           self.maintenance_men)
        first_part = machine.parts[0]
        self.env.run(until=first_part.component_type.mean + machine.component_type.time_replacement + 1)
        self.assertFalse(first_part.broken)