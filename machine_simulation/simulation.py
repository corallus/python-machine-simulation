__author__ = 'Vincent van Bergen'

import simpy
import sys
import random


class ComponentStock(simpy.Container):
    """
    Implementation of a (S-1,S) inventory management system
    """
    purchase_costs = 0
    inventory_holding_costs_saved = 0  # the amount saved
    in_order = 0
    last_order_at = 0

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

    @property
    def inventory_holding_costs(self):
        costs = self.env.now * self.unit_holding_costs - self.inventory_holding_costs_saved
        if self.in_order:
            costs -= (self.env.now - self.last_order_at) * (self.capacity - self.in_order) * self.unit_holding_costs
        return costs

    def get(self, amount):
        return super(ComponentStock, self).get(amount)

    def _do_get(self, event):
        """
        :param amount: the amount of stock requested
        :return: returns a ContainerGet event
        """
        if self._level >= event.amount:
            self.last_order_at = self.env.now
            self.env.process(self.order(event.amount))
            self.inventory_holding_costs_saved += (self.env.now - self.last_order_at) * (
                self.capacity - event.amount) * self.unit_holding_costs
            self._level -= event.amount
            event.succeed()

    def order(self, amount):
        """
        A process to order an amount of items
        :param amount: the number of items to order
        """
        self.in_order += amount
        self.purchase_costs += amount * self.unit_purchase_costs
        yield self.env.timeout(self.delivery_time)
        self.in_order -= amount
        yield self.put(amount)


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
    times_broken = 0

    def __init__(self, env, name, time_replacement, stock, mean, replace_module):
        """
        :param env: simulation environment
        :param name: string
        :param time_replacement: time required to replace itself
        :param stock: the stock of this item
        :param mean: the mean time to failure
        :param replace_module: whether to replace parent module when its broken
        """
        if replace_module:
            stock.unit_holding_costs = 0
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
            return random.expovariate(1.0 / self.mean)
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
        stock_costs = False
        for component in breakable_components:
            if component.replace_module:
                stock_costs = True
        if not stock_costs:
            stock.unit_holding_costs = 0
        super(Module, self).__init__(env, time_replacement, stock)
        self.breakable_components = breakable_components

    def run(self, machine):
        """
        Waits till first part gets broken and tells this to the machine
        :param machine: the machine which should be broken when this breaks
        """
        while True:
            if len(self.breakable_components) > 0:
                broken_component, time = self.get_first_broken_component()
                yield self.env.timeout(time)
                broken_component.times_broken += 1
                yield self.env.process(machine.repair(broken_component))

    def get_first_broken_component(self):
        return min([(component, component.time_to_failure()) for component in self.breakable_components],
                   key=lambda result: result[1])


class Machine(object):
    """
    A machine
    """
    downtime_costs = 0
    broken = False
    broken_since = 0

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
        self.env.process(self.module.run(self))

    def repair(self, broken_component):
        """
        Will repair machine by either replacing the module or the broken part
        """
        self.broken = True
        self.broken_since = self.env.now
        if self.factory.maintenance_men:
            with self.factory.maintenance_men.request() as req:
                yield req
                if broken_component.replace_module:
                    yield self.env.process(self.module.replace())
                else:
                    yield self.env.process(broken_component.replace())
        else:
            if broken_component.replace_module:
                yield self.env.process(self.module.replace())
            else:
                yield self.env.process(broken_component.replace())
        self.downtime_costs += (self.env.now - self.broken_since) * self.costs_per_unit_downtime
        self.broken = False

    @property
    def total_downtime_costs(self):
        costs = self.downtime_costs
        if self.broken:
            costs += (self.env.now - self.broken_since) * self.costs_per_unit_downtime
        return costs


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

    @property
    def costs(self):
        """
        Calculates total costs for this factory
        :return:
        """
        costs = self.module.stock.purchase_costs + self.module.stock.inventory_holding_costs
        costs += sum([machine.total_downtime_costs for machine in self.machines])
        costs += sum([component.stock.purchase_costs + component.stock.inventory_holding_costs
                      for component in self.module.breakable_components])
        costs += self.operators_salary + self.maintenance_men_salary
        return costs

    def track_salary(self):
        """
        A process which keeps track salary costs
        """
        while True:
            if self.maintenance_men:
                self.maintenance_men_salary += self.maintenance_man_salary * self.maintenance_men.capacity
            self.operators_salary += self.operator_salary * len(self.machines)
            yield self.env.timeout(1)