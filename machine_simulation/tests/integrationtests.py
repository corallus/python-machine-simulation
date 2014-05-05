__author__ = 'vincent'
import unittest

from machine_simulation.simulation import *
import sys
from machine_simulation.input import *


class TestSituation1(unittest.TestCase):
    """
    "Unlimited" stock and "unlimited" maintenance men
    """
    def setUp(self):
        self.env = simpy.Environment()
        part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, 0, 0, TRA, sys.maxint),
            ComponentType(self.env, "Part B", MB, CB, 0, 0, TRB, sys.maxint)
        ]
        machine_component_type = ComponentType(self.env, "Machine", 0, CAB, 0, 0, TRAB, sys.maxint)
        maintenance_men = simpy.Resource(self.env, capacity=sys.maxint)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_component_type, part_component_types, CD,
                               maintenance_men)

    def test_run(self):
        simulation_time = 1000
        self.env.run(until=simulation_time)
        downtime_costs = self.machine.downtime_costs
        purchase_costs_parts = sum([part.purchase_costs for part in self.machine.parts])
        purchase_costs_module = self.machine.component_type.purchase_costs
        purchase_costs = purchase_costs_parts + purchase_costs_module
        inventory_holding_costs = sum([part_specification.inventory_holding_costs
                                       for part_specification in self.machine.part_specifications])
        self.assertEqual(inventory_holding_costs, 0)
        self.assertNotEqual(purchase_costs, 0)
        self.assertNotEqual(downtime_costs, 0)
        total_costs = downtime_costs + purchase_costs + inventory_holding_costs

        # Analyis/results
        print('situation 1')
        print('Results after %s time' % simulation_time)
        print('Total costs are: %f' % total_costs)
        print('%f due to purchase costs' % purchase_costs)
        print('%f due to inventory holding costs' % inventory_holding_costs)
        print('%f due to machine downtime costs' % downtime_costs)
        print('')


class TestSituation2(unittest.TestCase):
    """
    "Unlimited" stock
    """
    def setUp(self):
        self.env = simpy.Environment()
        part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, 0, 0, TRA, sys.maxint),
            ComponentType(self.env, "Part B", MB, CB, 0, 0, TRB, sys.maxint)
        ]
        machine_component_type = ComponentType(self.env, "Machine", 0, CAB, 0, 0, TRAB, sys.maxint)
        maintenance_men = simpy.Resource(self.env, capacity=3)
        self.machines = [PolicyO(self.env, 'Machine %d' % i, machine_component_type, part_component_types, CD,
                                 maintenance_men) for i in range(NUMBER_MACHINES)]

    def test_single_machine(self):
        simulation_time = 1000
        self.env.run(until=simulation_time)
        downtime_costs = sum([machine.downtime_costs for machine in self.machines])
        purchase_costs = sum([part_specification.purchase_costs
                              for part_specification in self.machines[0].part_specifications])
        inventory_holding_costs = sum([part_specification.inventory_holding_costs
                                       for part_specification in self.machines[0].part_specifications])

        total_costs = downtime_costs + purchase_costs + inventory_holding_costs

        # Analyis/results
        print('situation 2')
        print('Results after %s time' % simulation_time)
        print('Total costs are: %f' % total_costs)
        print('%f due to purchase costs' % purchase_costs)
        print('%f due to inventory holding costs' % inventory_holding_costs)
        print('%f due to machine downtime costs' % downtime_costs)
        print('')


class TestSituation3(unittest.TestCase):
    """
    "Unlimited" maintenance men
    """
    def setUp(self):
        self.env = simpy.Environment()
        part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, LA, CHA, TRA, sys.maxint),
            ComponentType(self.env, "Part B", MB, CB, LB, CHB, TRB, sys.maxint)
        ]
        machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)
        maintenance_men = simpy.Resource(self.env, capacity=sys.maxint)
        self.machines = [PolicyO(self.env, 'Machine %d' % i, machine_component_type, part_component_types, CD,
                                 maintenance_men) for i in range(NUMBER_MACHINES)]

    def test_run(self):
        simulation_time = 1000
        self.env.run(until=simulation_time)
        downtime_costs = sum([machine.downtime_costs for machine in self.machines])
        purchase_costs = sum([part_specification.purchase_costs
                              for part_specification in self.machines[0].part_specifications])
        inventory_holding_costs = sum([part_specification.inventory_holding_costs
                                       for part_specification in self.machines[0].part_specifications])

        total_costs = downtime_costs + purchase_costs + inventory_holding_costs

        # Analyis/results
        print('situation 3')
        print('Results after %s time' % simulation_time)
        print('Total costs are: %f' % total_costs)
        print('%f due to purchase costs' % purchase_costs)
        print('%f due to inventory holding costs' % inventory_holding_costs)
        print('%f due to machine downtime costs' % downtime_costs)
        print('')


class TestSituation4(unittest.TestCase):
    """

    """