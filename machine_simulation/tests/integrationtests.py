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
        self.part_component_types = [
            ComponentType(self.env, "Part A", MA, CA, LA, CHA, TRA, SA),
            ComponentType(self.env, "Part B", MB, CB, LB, CHB, TRB, SB)
        ]
        self.machine_component_type = ComponentType(self.env, "Machine", 0, CAB, LAB, CHAB, TRAB, SAB)

    def test_zero_maintenance_men(self):
        maintenance_men = simpy.Resource(self.env, capacity=0)
        self.machines = [PolicyO(self.env, 'Machine %d' % i, self.machine_component_type, self.part_component_types, CD,
                                 maintenance_men) for i in range(NUMBER_MACHINES)]
        time = 1000
        self.env.run(until=time)
        self.assertEqual(self.machine_component_type.purchase_costs, 0)
        for component_type in self.part_component_types:
            self.assertEqual(component_type.purchase_costs, 0)

        self.assertEqual(self.machine_component_type.inventory_holding_costs,
                         self.machine_component_type.safety_stock * self.machine_component_type.unit_holding_costs * time)
        for component_type in self.part_component_types:
            self.assertEqual(component_type.inventory_holding_costs,
                             component_type.safety_stock * component_type.unit_holding_costs * time)