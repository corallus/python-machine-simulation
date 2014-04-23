__author__ = 'Vincent van Bergen'

import unittest
import simpy

from simulation import Specification, Part, PolicyAB, PolicyA, PolicyB, PolicyO, Machine


class TestSpecification(unittest.TestCase):
    """
    Test whether specification behaves like S-1 queue
    """

    def setUp(self):
        self.env = simpy.Environment()
        self.specification = Specification(self.env, 'test part', 0, 0, 10, 10, 10, 0, 10)

    def test_single_order(self):
        print('testing single order')
        stock = self.specification.stock
        stock.get(1)
        self.env.process(self.specification.order())
        self.assertEqual(stock.level, 9)
        self.env.run(until=self.specification.delivery_time + 1)
        self.assertEqual(stock.level, 10)

    def test_multiple_orders(self):
        print('testing multiple orders')
        stock = self.specification.stock
        stock.get(1)
        self.env.process(self.specification.order())
        stock.get(1)
        self.env.process(self.specification.order())
        stock.get(1)
        self.env.process(self.specification.order())
        self.assertEqual(stock.level, 7)
        self.env.run(until=self.specification.delivery_time + 1)
        self.assertEqual(stock.level, 10)


class TestSinglePart(unittest.TestCase):
    """
    Test the failure of a machine with a single part
    """

    def setUp(self):
        self.env = simpy.Environment()
        part_specification = Specification(self.env, "Test part", 5, 1, 8, 1, 2, 4, 100)
        machine_specification = Specification(self.env, "Test machine", 5, 1, 15, 1, 3, 4, 50)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        machine = PolicyO(self.env, 'Test machine 1', machine_specification, [part_specification], 10, maintenance_men)
        self.part = machine.parts[0]

    def test_breaking(self):
        self.env.run(until=self.part.specification.mean+1)
        self.assertEqual(self.part.broken, True)


class TestMultipleParts(unittest.TestCase):
    """
    Test the relation between breakdowns of multiple parts of the same machine
    """

    def setUp(self):
        self.env = simpy.Environment()
        part_specifications = [
            Specification(self.env, "Test part 1", 5, 1, 8, 1, 2, 4, 100),
            Specification(self.env, "Test part 2", 5, 1, 8, 1, 2, 4, 100)
        ]
        machine_specification = Specification(self.env, "Test machine", 5, 1, 15, 1, 3, 4, 50)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_specification, part_specifications, 10,
                               maintenance_men)

    def test_not_multiple_broken(self):
        self.env.run(until=max([part.specification.mean for part in self.machine.parts])+1)
        self.assertNotEqual(self.machine.parts[0].broken, self.machine.parts[1].broken)


class TestMachine(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()

    def no_breakdowns(self):
        part_specifications = [
            Specification(self.env, "Test part 1", 1000, 0, 8, 1, 2, 4, 1000),
            Specification(self.env, "Test part 2", 1000, 0, 8, 1, 2, 4, 1000)
        ]
        machine_specification = Specification(self.env, "Test machine", 5, 1, 15, 1, 3, 4, 50)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_specification, part_specifications, 10,
                               maintenance_men)
        self.env.run(until=1000)
        self.assertEqual(self.machine.costs, 0)


class TestPolicyO(unittest.TestCase):

    def setUp(self):
        self.env = simpy.Environment()

    def no_breakdowns(self):
        part_specifications = [
            Specification(self.env, "Test part 1", 5, 0, 8, 1, 2, 4, 10),
            Specification(self.env, "Test part 2", 5, 0, 8, 1, 2, 4, 10)
        ]
        machine_specification = Specification(self.env, "Test machine", 5, 1, 15, 1, 3, 4, 50)
        maintenance_men = simpy.Resource(self.env, capacity=100)
        self.machine = PolicyO(self.env, 'Test machine 1', machine_specification, part_specifications, 10,
                               maintenance_men)

    def test_repair(self):
        raise NotImplementedError


class TestPolicyA(unittest.TestCase):

    def test_repair(self):
        raise NotImplementedError


class TestPolicyB(unittest.TestCase):

    def test_repair(self):
        raise NotImplementedError


class TestPolicyAB(unittest.TestCase):
    def test_repair(self):
        raise NotImplementedError