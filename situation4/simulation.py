__author__ = 'Vincent van Bergen'

import simpy
import random

RANDOM_SEED = 42
NUMBER_MACHINES = 15  # number of machines
SIMULATION_TIME = 1825  # time simulation has to run
NUMBER_MAINTENANCE_MEN = 3  # number of maintenance men


class Specification(object):
    """
    The specification of an item. This is used to specify modules as well as parts
    """

    def __init__(self, env, name, mean, standard_deviation, costs, delivery_time, holding_costs, time_replacement,
                 order_up_to):
        self.env = env
        self.name = name
        self.mean = mean
        self.standard_deviation = standard_deviation
        self.costs = costs
        self.delivery_time = delivery_time
        self.holding_costs = holding_costs
        self.time_replacement = time_replacement
        self.stock = simpy.Container(env, init=order_up_to)
        self.order_up_to = order_up_to

    def order(self):
        print('ordered %s' % self.name)
        yield self.env.timeout(self.delivery_time)
        yield self.stock.put(1)


class Part(object):
    def __init__(self, env, specification, machine, maintenance_men):
        self.specification = specification
        self.machine = machine
        self.maintenance_men = maintenance_men
        self.broken = False
        self.env = env

    def time_to_failure(self):
        """Return time until next failure"""
        return self.specification.mean

    def break_part(self):
        """Break the part every now and then."""
        while not self.broken:
            yield self.env.timeout(self.time_to_failure())
            if not self.broken and not self.machine.broken:
                # parts can not breakdown during repair
                self.broken = True
                self.machine.broken = True
                # machine not functioning during replacement
                print('%s breaks' % self.specification.name)
                self.machine.process.interrupt()

    def repair(self):
        print('replace %s' % self.specification.name)
        with self.specification.stock.get(1) as req:
            yield req
            print('part available')
            self.env.process(self.specification.order())
            self.machine.costs += self.specification.costs
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                print('%s is being replaced' % self.specification.name)
                yield self.env.timeout(self.specification.time_replacement)


class Machine(object):
    costs = 0

    def __init__(self, env, name, specification, part_specifications, downtime_costs, maintenance_men):
        self.parts_made = 0
        self.env = env
        self.name = name
        self.specification = specification
        self.part_specifications = part_specifications
        self.downtime_costs = downtime_costs
        self.maintenance_men = maintenance_men
        self.parts = [Part(self.env, part_specification, self, self.maintenance_men)
                      for part_specification in self.part_specifications]
        self.process = env.process(self.working())
        self.start()

    def start(self):
        self.broken = False
        print('%s starts running' % self.name)
        for part in self.parts:
            self.env.process(part.break_part())

    def working(self):
        while True:
            try:
                # Working on the part
                yield self.env.timeout(1)
            except simpy.Interrupt:
                print('%s breaks down' % self.name)
                broken_since = self.env.now
                yield self.env.process(self.repair())
                self.costs += (self.env.now - broken_since) * self.downtime_costs
                print('%s repaired after %d - %d time' % (self.name, self.env.now, broken_since))
                print('total costs: %d' % self.costs)
                self.start()

    def repair(self):
        raise NotImplementedError

    def replace_module(self):
        print('replace %s' % self.specification.name)
        with self.specification.stock.get(1) as req:
            yield req
            self.env.process(self.specification.order())
            print('%s available' % self.specification.name)
            self.costs += self.specification.costs
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                print('%s is being replaced' % self.specification.name)
                yield self.env.timeout(self.specification.time_replacement)


class PolicyO(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                yield self.env.process(part.repair())


class PolicyA(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.specification.name == "Part A":
                    yield self.env.process(self.replace_module())
                else:
                    yield self.env.process(part.repair())


class PolicyB(Machine):
    def repair(self):
        for part in self.parts:
            if part.broken:
                broken_part = part
                if broken_part.specification.name == "Part B":
                    yield self.env.process(self.replace_module())
                else:
                    yield self.env.process(part.repair())


class PolicyAB(Machine):
    def repair(self):
        yield self.env.process(self.replace_module())


def setup():
    # Setup and start the simulation
    print('Start simulation')
    random.seed(RANDOM_SEED)  # This helps reproducing the results

    # Create an environment and start the setup process
    env = simpy.Environment()

    #tuples of (mean, standard_deviation, costs, delivery_time, holding_costs, time_replacement, initial_stock)
    part_specifications = [
        Specification(env, "Part A", 5, 1, 8, 1, 2, 4, 100),
        Specification(env, "Part B", 4, 1, 6, 2, 2, 3, 100)
    ]

    maintenance_men = simpy.Resource(env, capacity=NUMBER_MAINTENANCE_MEN)
    machine_specification = Specification(env, "Machine", 5, 1, 15, 1, 3, 4, 50)
    machines = [PolicyAB(env, 'Machine %d' % i, machine_specification, part_specifications, 10, maintenance_men)
                for i in range(NUMBER_MACHINES)]

    # Execute!
    env.run(until=SIMULATION_TIME)

    # Analyis/results
    print('Results after %s time' % SIMULATION_TIME)
    for machine in machines:
        print('%s has lost %d profit due to breakdowns.' % (machine.name, machine.costs))
