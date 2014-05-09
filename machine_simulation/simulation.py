__author__ = 'Vincent van Bergen'

import simpy
import sys
import random


class ComponentStock(simpy.Container):
    """
    Implementation of a (S-1,S) inventory management system
    """
    purchase_costs = 0
    inventory_holding_costs = 0
    in_order = 0

    def __init__(self, env, unit_purchase_costs, delivery_time, unit_holding_costs, capacity=float('inf')):
        """
        :param env: simulation environment
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
        """
        :param amount: the amount of stock requested
        :return: returns a ContainerGet event
        """
        if self.level - amount + self.in_order < self.capacity:
            self.env.process(self.order(amount))
        return super(ComponentStock, self).get(amount)

    def order(self, amount):
        """
        A process to order an amount of items
        :param amount: the number of items to order
        """
        self.in_order += amount
        yield self.env.timeout(self.delivery_time)
        self.in_order -= amount
        self.purchase_costs += self.unit_purchase_costs
        yield self.put(amount)

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

    def __init__(self, env, time_replacement, stock):
        """
        Starts the inventory tracking process
        :param env: simulation environment
        :param time_replacement: time required to replace itself
        :param stock: the stock of this item
        """
        self.env = env
        self.time_replacement = time_replacement
        self.stock = stock

    def replace(self):
        """
        A process which replaces this component by a new one
        """
        with self.stock.get(1) as req:
            yield req
            yield self.env.timeout(self.time_replacement)


class BreakableComponent(Component):
    """
    A component that breaks down every once in a while
    """

    def __init__(self, env, name, time_replacement, stock, mean, replace_module):
        """
        :param env: simulation environment
        :param name: string
        :param time_replacement: time required to replace itself
        :param stock: the stock of this item
        :param mean: the mean time to failure
        :param replace_module: whether to replace parent module when its broken
        """
        super(BreakableComponent, self).__init__(env, time_replacement, stock)
        self.name = name
        self.mean = mean
        self.replace_module = replace_module

    def time_to_failure(self):
        """
        Returns the time until next failure if this component, using the mean time to failure of this component.
        :return: float
        """
        try:
            return random.expovariate(1.0/self.mean)
        except ZeroDivisionError:
            return sys.maxint


class Module(Component):
    """
    A container for multiple breakable components
    """

    def __init__(self, env, time_replacement, stock, breakable_components):
        """
        :param env: simulation environment
        :param time_replacement: time required to replace itself
        :param stock: the stock of this item
        :param breakable_components: list of BreakableComponent
        """
        super(Module, self).__init__(env, time_replacement, stock)
        self.breakable_components = breakable_components

    def break_module(self, machine):
        """
        Waits till first part gets broken and tells this to the machine
        :param machine: the machine which should be broken when this breaks
        """
        if len(self.breakable_components) > 0:
            broken_component, time = min([(component, component.time_to_failure())
                                          for component in self.breakable_components], key=lambda result: result[1])
            yield self.env.timeout(time)
            self.env.process(machine.repair(broken_component))


class Machine(object):
    """
    A machine
    """
    downtime_costs = 0

    def __init__(self, env, module, costs_per_unit_downtime, factory):
        """
        Starts the inventory tracking process for the module and generates parts according to there component types
        :param factory: Factory the machine belongs to
        :param module: Module inside the machine
        :param env: simulation environment
        :param costs_per_unit_downtime: integer
        """
        self.factory = factory
        self.env = env
        self.module = module
        self.costs_per_unit_downtime = costs_per_unit_downtime
        self.broken = False
        self.run()
        self.env.process(self.process_downtime_costs())

    def run(self):
        """
        Break machine every once in while
        """
        self.env.process(self.module.break_module(self))

    def repair(self, broken_component):
        """
        Will repair machine by either replacing the module or the broken part
        """
        if self.factory.maintenance_men:
            with self.factory.maintenance_men.request() as req:
                yield req
        if broken_component.replace_module:
            yield self.env.process(self.module.replace())
        else:
            yield self.env.process(broken_component.replace())
        self.run()

    def process_downtime_costs(self):
        """
        Keeps track of downtime costs of machine
        """
        self.downtime_costs += self.costs_per_unit_downtime
        yield self.env.timeout(1)


class Factory(object):
    """
    Factory consisting of multiple Machines, operators and maintenance men
    """
    maintenance_men_salary = 0
    operators_salary = 0
    maintenance_men = False

    def __init__(self, env, number_maintenance_men, module, costs_per_unit_downtime,
                 number_of_machines, operator_salary, maintenance_man_salary):
        """
        :param maintenance_man_salary: integer
        :param module: Module of which Machines consist
        :param costs_per_unit_downtime: downtime costs for machines
        :param env: simulation environment
        :param number_maintenance_men: integer
        :param number_of_machines: integer
        :param operator_salary: integer
        """
        self.env = env
        if number_maintenance_men:
            self.maintenance_men = simpy.Resource(self.env, number_maintenance_men)
            env.process(self.track_salary())
        self.machines = [Machine(env, module, costs_per_unit_downtime, self)
                         for i in range(number_of_machines)]
        self.operator_salary = operator_salary
        self.maintenance_man_salary = maintenance_man_salary
        self.module = module


    def costs(self):
        """
        Calculates total costs for this factory
        :return:
        """
        costs = self.module.stock.purchase_costs + self.module.stock.inventory_holding_costs
        costs += sum([machine.downtime_costs for machine in self.machines])
        costs += sum([component.stock.purchase_costs+component.stock.inventory_holding_costs
                      for component in self.module.breakable_components])
        costs += self.operators_salary + self.maintenance_men_salary
        return costs

    def track_salary(self):
        """
        A process which keeps track salary costs
        """
        while True:
            self.maintenance_men_salary += self.maintenance_man_salary * self.maintenance_men.capacity
            self.operators_salary += self.operator_salary * len(self.machines)
            yield self.env.timeout(1)