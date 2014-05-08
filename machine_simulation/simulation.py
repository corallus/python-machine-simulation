__author__ = 'Vincent van Bergen'

import simpy
import random
import sys


class ComponentStock(simpy.Container):
    """
    Implementation of a (S-1,S) inventory management system
    """
    purchase_costs = 0
    inventory_holding_costs = 0
    in_order = 0

    def __init__(self, env, unit_purchase_costs, delivery_time, unit_holding_costs, capacity=float('inf')):
        """
        :param env:
        :param unit_purchase_costs: costs for purchasing one
        :param delivery_time: time between order and delivery
        :param unit_holding_costs: costs for holding one unit of stock for 1 time unit
        :param capacity:
        """
        super(ComponentStock, self).__init__(env, capacity=capacity, init=capacity)
        self.env = env
        self.unit_purchase_costs = unit_purchase_costs
        self.delivery_time = delivery_time
        self.unit_holding_costs = unit_holding_costs
        self.env.process(self.inventory())

    def get(self, amount):
        if self.level - 1 + self.in_order < self.capacity:
            self.env.process(self.order())
        return super(ComponentStock, self).get(amount)

    def order(self):
        """
        A process to order an item
        """
        self.in_order += 1
        yield self.env.timeout(self.delivery_time)
        self.in_order -= 1
        self.purchase_costs += self.unit_purchase_costs
        yield self.put(1)

    def inventory(self):
        """
        A process which keeps track if inventory holding costs
        """
        while True:
            self.inventory_holding_costs += self.level * self.unit_holding_costs
            yield self.env.timeout(1)


class Component(object):
    """
    The specification of a part/module.
    """

    def __init__(self, env, name, time_replacement, stock):
        """
        Starts the inventory tracking process
        :param time_replacement:
        :param stock:
        :param name: name
        """
        self.env = env
        self.name = name
        self.time_replacement = time_replacement
        self.stock = stock

    def replace(self):
        with self.stock.get(1) as req:
            yield req
            yield self.env.timeout(self.time_replacement)


class BreakableComponent(Component):
    """
    A component that breaks down every once in a while
    """

    def __init__(self, env, name, time_replacement, stock, mean):
        super(BreakableComponent, self).__init__(env, name, time_replacement, stock)
        self.mean = mean

    def time_to_failure(self):
        """
        Returns the time until next failure if this component, using the mean time to failure of this component.
        """
        try:
            return random.expovariate(1.0/self.mean)
        except ZeroDivisionError:
            return sys.maxint


class Module(Component):
    """
    A container for multiple breakable components
    """
    def __init__(self, env, name, time_replacement, stock, breakable_components):
        super(Module, self).__init__(env, name, time_replacement, stock)
        self.breakable_components = breakable_components

    def break_module(self, machine):
        if len(self.breakable_components) > 0:
            broken_component, time = min([(component, component.time_to_failure())
                                          for component in self.breakable_components], key=lambda result: result[1])
            yield self.env.timeout(time)
            self.env.process(machine.repair(broken_component))


class Machine(object):
    downtime_costs = 0
    down = False

    def __init__(self, env, name, module, costs_per_unit_downtime, factory):
        """
        Starts the inventory tracking process for the module and generates parts according to there component types
        :param module:
        :param env: simulation environment
        :param name: name
        :param costs_per_unit_downtime: Int
        """
        self.factory = factory
        self.env = env
        self.name = name
        self.module = module
        self.costs_per_unit_downtime = costs_per_unit_downtime
        self.broken = False
        self.run()
        self.env.process(self.process_downtime_costs())

    def run(self):
        """
        Main machine production process
        """
        self.env.process(self.module.break_module(self))

    def repair(self, broken_component):
        raise NotImplementedError

    def process_downtime_costs(self):
        self.downtime_costs += self.costs_per_unit_downtime
        yield self.env.timeout(1)


class Factory(object):
    maintenance_men_salary = 0
    operators_salary = 0

    def __init__(self, env, number_maintenance_men, module, costs_per_unit_downtime,
                 number_of_machines, operator_salary, maintenance_man_salary, policy_class):
        """

        :param module:
        :param costs_per_unit_downtime:
        :param env:
        :param number_maintenance_men: int
        :param number_of_machines: int
        :param operator_salary: int
        """
        self.env = env
        self.maintenance_men = simpy.Resource(self.env, number_maintenance_men)
        self.machines = [policy_class(env, "Machine %d" % i, module, costs_per_unit_downtime, self)
                         for i in range(number_of_machines)]
        self.operator_salary = operator_salary
        self.maintenance_man_salary = maintenance_man_salary
        self.module = module
        env.process(self.track_salary())

    def costs(self):
        costs = self.module.stock.purchase_costs + self.module.stock.inventory_holding_costs
        costs += sum([machine.downtime_costs for machine in self.machines])
        costs += sum([component.stock.purchase_costs+component.stock.inventory_holding_costs
                      for component in self.module.breakable_components])
        costs += self.operators_salary + self.maintenance_men_salary
        return costs

    def track_salary(self):
        """
        A process which keeps track if inventory holding costs
        """
        while True:
            self.maintenance_men_salary += self.maintenance_man_salary * self.maintenance_men.capacity
            self.operators_salary += self.operator_salary * len(self.machines)
            yield self.env.timeout(1)


class PolicyO(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self, broken_component):
        """
        Always replace parts individually
        """
        with self.factory.maintenance_men.request() as req:
            yield req
            yield self.env.process(broken_component.replace())
            self.run()


class PolicyA(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self, broken_component):
        """
        Replace module if part A broken, else replace part
        """
        with self.factory.maintenance_men.request() as req:
            yield req
            if broken_component.name == "Part A":
                yield self.env.process(self.module.replace())
            else:
                yield self.env.process(broken_component.replace())
            self.run()


class PolicyB(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self, broken_component):
        """
        Replace module if part B broken, else replace part
        """
        with self.factory.maintenance_men.request() as req:
            yield req
            if broken_component.name == "Part B":
                yield self.env.process(self.module.replace())
            else:
                yield self.env.process(broken_component.replace())
            self.run()


class PolicyAB(Machine):
    """
    Implementation of the repair method of a machine
    """
    def repair(self, broken_component):
        """
        Always replace module
        """
        with self.factory.maintenance_men.request() as req:
            yield req
            yield self.env.process(self.module.replace())
            self.run()