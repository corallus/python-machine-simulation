__author__ = 'Vincent van Bergen'

import simpy
import random

RANDOM_SEED = 42

# parameters
MA = 5   # mean of machine A
MB = 4   # mean of machine B
CA = 8  # cost part A 
CB = 6  # cost part B
CAB = 15  # cost module AB
CD = 10  # lost net profit per unit downtime per machine
TRAO = 3  # time required for replacing 1 part A by an operator
TRBO = 3  # time required for replacing 1 part B by an operator
TRABO = 2  # time required for replacing 1 part AB by an operator
NUMBER_MACHINES = 15  # number of machines
SIMULATION_TIME = 1825  # time simulation has to run

#situation2
NUMBER_MAINTENANCE_MEN = 3  # number of maintenance men
TRAM = 3  # time required for replacing 1 part A by a maintenance man
TRBM = 3  # time required for replacing 1 part B by a maintenance man
TRABM = 2  # time required for replacing 1 part AB by a maintenance man

#situation 3

#situation4
LA = 1  # non-zero delivery time part A
LB = 2  # non-zero delivery time part B
LAB = 1  # non-zero delivery time part AB
CHA = 2  # unit inventory holding cost for A
CHB = 2  # unit inventory holding cost for B
CHAB = 3  # unit inventory holding cost for AB
SA = 1  # safety stock part A
SB = 1  # safety stock part B
SAB = 1  # safety stock module AB


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
        return random.expovariate(self.mean)


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
        while not self.broken:
            yield self.env.timeout(self.component_type.time_to_failure())
            if not self.broken and not self.machine.broken:
                # parts can not breakdown during repair
                self.broken = True
                self.machine.broken = True
                # machine not functioning during replacement
                self.machine.process.interrupt()

    def replace(self):
        self.env.process(self.component_type.order())
        with self.component_type.stock.get(1) as req:
            yield req
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                yield self.env.timeout(self.component_type.time_replacement)
                self.purchase_costs += self.component_type.unit_purchase_costs


class Machine(object):
    downtime_costs = 0

    def __init__(self, env, name, component_type, part_specifications, costs_per_unit_downtime, maintenance_men):
        self.parts_made = 0
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
                print('%s repaired after %d - %d time' % (self.name, self.env.now, broken_since))
                print('total costs: %d' % self.downtime_costs)
                self.start()

    def repair(self):
        raise NotImplementedError

    def replace(self):
        print('replace %s' % self.component_type.name)
        with self.component_type.stock.get(1) as req:
            yield req
            self.env.process(self.component_type.order())
            print('%s available' % self.component_type.name)
            with self.maintenance_men.request() as maintainer:
                yield maintainer
                print('%s is being replaced' % self.component_type.name)
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


def setup():
    # Setup and start the simulation
    print('Start simulation')
    random.seed(RANDOM_SEED)  # This helps reproducing the results

    # Create an environment and start the setup process
    env = simpy.Environment()

    part_specifications = [
        ComponentType(env, "Part A", MA, CA, LA, CHA, TRAM, SA),
        ComponentType(env, "Part B", MB, CB, LB, CHB, TRBM, SB)
    ]

    maintenance_men = simpy.Resource(env, capacity=NUMBER_MAINTENANCE_MEN)
    machine_specification = ComponentType(env, "Machine", 0, CAB, LAB, CHAB, TRABM, SAB)
    machines = [PolicyAB(env, 'Machine %d' % i, machine_specification, part_specifications, CD, maintenance_men)
                for i in range(NUMBER_MACHINES)]

    # Execute!
    env.run(until=SIMULATION_TIME)

    machine_costs = sum([machine.costs() for machine in machines])
    inventory_holding_costs = sum([part_specification.inventory_holding_costs
                                   for part_specification in part_specifications])

    # Analyis/results
    print('Results after %s time' % SIMULATION_TIME)
    print('Total costs are: %d')
    print('%d due to purchase costs and downtime' % machine_costs)
    print('%d due to inventory holding costs' % inventory_holding_costs)
