__author__ = 'Vincent van Bergen'

import simpy
import random
import sys


class ComponentType(object):
    """
    The specification of a part/module. This class is used for keeping track of inventory of this kind of component as
    well. Implementation of a (S-1,S) queue for inventory management
    """
    purchase_costs = 0
    inventory_holding_costs = 0

    def __init__(self, env, name, mean, unit_purchase_costs, delivery_time, unit_holding_costs, time_replacement,
                 safety_stock):
        """
        Starts the inventory tracking process
        :param env: simulation environment
        :param name: name
        :param mean: 1/failure rate
        :param unit_purchase_costs: costs for purchasing one
        :param delivery_time: time between order and delivery
        :param unit_holding_costs: costs for holding one unit of stock for 1 time unit
        :param time_replacement: time to replace
        :param safety_stock: level of stock to order up to
        """
        self.env = env
        self.name = name
        self.mean = mean
        self.unit_purchase_costs = unit_purchase_costs
        self.delivery_time = delivery_time
        self.unit_holding_costs = unit_holding_costs
        self.time_replacement = time_replacement
        self.stock = simpy.Container(env, init=safety_stock)
        self.safety_stock = safety_stock
        self.env.process(self.inventory())

    def order(self):
        """
        A process to order an item
        """
        yield self.env.timeout(self.delivery_time)
        yield self.stock.put(1)
        self.purchase_costs += self.unit_purchase_costs

    def inventory(self):
        """
        A process which keeps track if inventory holding costs
        """
        while True:
            self.inventory_holding_costs += self.stock.level * self.unit_holding_costs
            yield self.env.timeout(1)

    def time_to_failure(self):
        """
        Returns the time until next failure if this component, using the mean time to failure of this component.
        """
        try:
            return random.expovariate(1.0/self.mean)
        except ZeroDivisionError:
            return sys.maxint


class Part(object):
    """
    An "instance" of a ComponentType. Belongs to a machine.
    """
    purchase_costs = 0

    def __init__(self, env, component_type, machine, maintenance_men):
        """
        :param env: simulation environment
        :param component_type: ComponentType
        :param machine: Machine
        :param maintenance_men: Resource
        """
        self.component_type = component_type
        self.machine = machine
        self.maintenance_men = maintenance_men
        self.broken = False
        self.env = env

    def break_part(self):
        """
        A one time process breaking a part after a while
        """
        self.broken = False
        while not self.broken and not self.machine.broken:
            yield self.env.timeout(self.component_type.time_to_failure())
            if not self.broken and not self.machine.broken:
                # parts can not breakdown during repair
                self.broken = True
                # print('%s breaks @ %f' % (self.component_type.name, self.env.now))
                self.machine.broken = True
                # machine not functioning during replacement
                self.machine.process.interrupt()

    def replace(self):
        """
        A process to replace this part by a new part
        """
        self.env.process(self.component_type.order())
        with self.component_type.stock.get(1) as req:
            yield req
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                self.purchase_costs += self.component_type.unit_purchase_costs
                yield self.env.timeout(self.component_type.time_replacement)


class Machine(object):
    """

    """
    downtime_costs = 0
    purchase_costs = 0

    def __init__(self, env, name, component_type, part_specifications, costs_per_unit_downtime, maintenance_men):
        """
        Starts the inventory tracking process for the module and generates parts according to there component types
        :param env: simulation environment
        :param name: name
        :param component_type: ComponentType
        :param part_specifications: list of ComponentTypes
        :param costs_per_unit_downtime: Int
        :param maintenance_men: simpy.Resource
        """
        self.env = env
        self.name = name
        self.component_type = component_type
        self.part_specifications = part_specifications
        self.costs_per_unit_downtime = costs_per_unit_downtime
        self.maintenance_men = maintenance_men
        self.parts = [Part(self.env, part_specification, self, self.maintenance_men)
                      for part_specification in self.part_specifications]
        self.process = env.process(self.working())
        self.start()

    def start(self):
        """
        Starts the machine
        """
        self.broken = False
        for part in self.parts:
            self.env.process(part.break_part())

    def working(self):
        """
        Main machine production process
        """
        while True:
            try:
                yield self.env.timeout(1)
            except simpy.Interrupt:
                broken_since = self.env.now
                yield self.env.process(self.repair())
                self.downtime_costs += (self.env.now - broken_since) * self.costs_per_unit_downtime
                self.start()

    def repair(self):
        raise NotImplementedError

    def replace(self):
        """
        A process to replace this machine by a new one
        """
        with self.component_type.stock.get(1) as req:
            yield req
            self.env.process(self.component_type.order())
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                self.purchase_costs += self.component_type.unit_purchase_costs
            yield self.env.timeout(self.component_type.time_replacement)

    def costs(self):
        """
        Keeps track of the total costs of this machine, consisting of purchase costs of parts and modules as well as
        downtime costs
        :return: Int
        """
        total_costs = 0
        for part in self.parts:
            total_costs += part.purchase_costs
        total_costs += self.component_type.unit_purchase_costs + self.downtime_costs
        return total_costs


class PolicyO(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self):
        """
        Always replace parts individually
        """
        for part in self.parts:
            if part.broken:
                yield self.env.process(part.replace())


class PolicyA(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self):
        """
        Replace module if part A broken, else replace part
        """
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.component_type.name == "Part A":
                    yield self.env.process(self.replace())
                else:
                    yield self.env.process(part.replace())


class PolicyB(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self):
        """
        Replace module if part B broken, else replace part
        """
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.component_type.name == "Part B":
                    yield self.env.process(self.replace())
                else:
                    yield self.env.process(part.replace())


class PolicyAB(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self):
        """
        Always replace module
        """
        yield self.env.process(self.replace())