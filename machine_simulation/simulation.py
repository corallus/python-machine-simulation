__author__ = 'Vincent van Bergen'

import simpy
import random
import sys

class ComponentType(object):
    """
    The specification of a part/module. This class is used for keeping track of inventory of this item as well
    """
    purchase_costs = 0
    inventory_holding_costs = 0

    def __init__(self, env, name, mean, unit_purchase_costs, delivery_time, unit_holding_costs, time_replacement,
                 safety_stock):
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
        yield self.env.timeout(self.delivery_time)
        yield self.stock.put(1)
        self.purchase_costs += self.unit_purchase_costs

    def inventory(self):
        while True:
            self.inventory_holding_costs += self.stock.level * self.unit_holding_costs
            yield self.env.timeout(1)

    def time_to_failure(self):
        """Return time until next failure"""
        try:
            return random.expovariate(1.0/self.mean)
        except ZeroDivisionError:
            return sys.maxint


class Part(object):
    """

    """
    purchase_costs = 0

    def __init__(self, env, component_type, machine, maintenance_men):
        self.component_type = component_type
        self.machine = machine
        self.maintenance_men = maintenance_men
        self.broken = False
        self.env = env

    def break_part(self):
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
        self.env.process(self.component_type.order())
        with self.component_type.stock.get(1) as req:
            yield req
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                self.purchase_costs += self.component_type.unit_purchase_costs
                yield self.env.timeout(self.component_type.time_replacement)


class Machine(object):
    downtime_costs = 0

    def __init__(self, env, name, component_type, part_specifications, costs_per_unit_downtime, maintenance_men):
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
        self.broken = False
        for part in self.parts:
            self.env.process(part.break_part())

    def working(self):
        while True:
            try:
                # Machine processing
                yield self.env.timeout(1)
            except simpy.Interrupt:
                broken_since = self.env.now
                yield self.env.process(self.repair())
                self.downtime_costs += (self.env.now - broken_since) * self.costs_per_unit_downtime
                # print('%s repaired at %f' % (self.name, self.env.now))
                # print('total downtime costs: %f' % self.downtime_costs)
                self.start()

    def repair(self):
        raise NotImplementedError

    def replace(self):
        # print('replace %s' % self.component_type.name)
        with self.component_type.stock.get(1) as req:
            yield req
            self.env.process(self.component_type.order())
            # print('%s available' % self.component_type.name)
            with self.maintenance_men.request() as maintainer:
                yield maintainer
            # print('%s is being replaced' % self.component_type.name)
            yield self.env.timeout(self.component_type.time_replacement)

    def costs(self):
        total_costs = 0
        for part in self.parts:
            total_costs += part.purchase_costs
        return total_costs


class PolicyO(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                yield self.env.process(part.replace())


class PolicyA(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.component_type.name == "Part A":
                    yield self.env.process(self.replace())
                else:
                    yield self.env.process(part.replace())


class PolicyB(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.component_type.name == "Part B":
                    yield self.env.process(self.replace())
                else:
                    yield self.env.process(part.replace())


class PolicyAB(Machine):
    def repair(self):
        yield self.env.process(self.replace())