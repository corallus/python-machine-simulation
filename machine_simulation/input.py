__author__ = 'vincent'

# RANDOM_SEED = 42

# parameters
MA = 5   # mean of machine A
MB = 4   # mean of machine B
CA = 8  # cost part A
CB = 6  # cost part B
CAB = 15  # cost module AB
CD = 10  # lost net profit per unit downtime per machine
TRA = 3  # time required for replacing 1 part A by an operator
TRB = 3  # time required for replacing 1 part B by an operator
TRAB = 2  # time required for replacing 1 part AB by an operator
NUMBER_MACHINES = 15  # number of machines
SIMULATION_TIME = 1825  # time simulation has to run
OPERATOR_SALARY = 10

#situation2
NUMBER_MAINTENANCE_MEN = 3  # number of maintenance men
MAINTENANCE_MAN_SALARY = 5

#situation 3
LA = 1  # non-zero delivery time part A
LB = 2  # non-zero delivery time part B
LAB = 1  # non-zero delivery time part AB
CHA = 2  # unit inventory holding cost for A
CHB = 2  # unit inventory holding cost for B
CHAB = 3  # unit inventory holding cost for AB
SA = 1  # S of part A
SB = 1  # S of part B
SAB = 1  # S of module AB
