import logging

import cocotb
from cocotb.triggers import *
from cocotb.queue import *
#from queue import Queue
from cocotb_coverage.coverage import *
from cocotb_coverage.crv import *


class transaction(Randomized):
    # declaring the transaction items
    def __init__(self, name = "TRANSACTION"):
        Randomized.__init__(self)
        self.a = 0
        self.b = 0
        self.op = 0
        self.c = 0
        self.out = 0
        self.add_rand("a", list(range(0, 16)))
        self.add_rand("b", list(range(0, 16)))
        self.add_rand("op", list(range(0, 4)))

    def display(self, name):  # Displaying at each phase
        cocotb.log.info("["+name+"]")
        cocotb.log.info("a= " + str(self.a))
        cocotb.log.info("b= " + str(self.b))
        cocotb.log.info("op= " + str(self.op))
        cocotb.log.info("c= " + str(self.c))
        cocotb.log.info("out= " + str(self.out))
        cocotb.log.info("----------------------------")


class generator:
    def __init__(self):
        self.gen2driv = Queue(maxsize=1)  # replacement for mailbox in SV
        self.trans = transaction()  # declaring a transaction item
        #self.my_event2 = Event(name=None)  # event indicates that driver is ready to take values from generator
        self.scr_gen = Event(name=None)  # event indicates that scoreboard finished reading from dut and ready for next transaction
    async def gen_task(self):#-------------------
        for i in range(900):
            #self.my_event2.clear()
            self.scr_gen.clear()

            self.trans.randomize()  # randomize
            sample(self.trans.a, self.trans.b, self.trans.op)  # sample

            await self.gen2driv.put(self.trans)  # send to driver using queue #-------------------

            self.trans.display("Generator")
            #await self.my_event2.wait()
            await self.scr_gen.wait()


class driver:
    def __init__(self):

        self.trans = transaction()  # declaring a transaction item
        self.gen2driv = Queue(maxsize=1)  # replacement for mailbox in SV
        #self.my_event = Event(name=None)  # event indicates that driver is ready to take values from generator
        self.monitor_start = Event(name=None)  # event indicates that driver sent values to dut and scoreboard can start checking output of dut

    async def driv_task(self, dut_driver):#-------------------
        while True:#(self.gen2driv.empty()) is False

            self.trans = await self.gen2driv.get()  # receive from generator using queue

            #self.trans.display("Driver")

            # passing randomized values to the dut:
            #cocotb.log.info("passing randomized values to the dut")
            dut_driver.a.value = self.trans.a
            dut_driver.b.value = self.trans.b
            dut_driver.op.value = self.trans.op

            #await Timer(1, "ns")
            self.monitor_start.set()
            #cocotb.log.info("end of driver")
            #self.my_event.set()
            #await Timer(1, "ns")
            self.trans.display("Driver")


class monitor:
    def __init__(self):
        self.monitor = Event(name=None)  # event indicates that driver sent values to dut and scoreboard can start checking output of dut
        self.mon2scr = Queue(maxsize=1)  # replacement for mailbox in SV
        self.trans = transaction()  # declaring a transaction item

    async def mon_task(self, dut):
        while True:
            self.monitor.clear()
            await Timer(1, "ns")
            # receive from the dut:
            #cocotb.log.info("receive from the dut")
            self.trans.a = dut.a.value
            self.trans.b = dut.b.value
            self.trans.op = dut.op.value

            self.trans.c = dut.c.value
            self.trans.out = dut.out.value

            self.trans.display("Monitor")
            await self.mon2scr.put(self.trans)
            #cocotb.log.info("done putting trans in mon2scr queue")
            await self.monitor.wait()
            #cocotb.log.info("end of monitor")


class scoreboard:
    def __init__(self):
        self.mon2scr = Queue(maxsize=1)  # replacement for mailbox in SV
        #self.monitor = Event(name=None)  # event indicates that driver sent values to dut and scoreboard can start checking output of dut
        self.scr_gen2 = Event(name=None)  # event indicates that scoreboard finished reading from dut and ready for next transaction
        self.trans = transaction()  # declaring a transaction item
        self.passed = 0  # counting number of passed tests
        self.failed = 0  # counting number of failed tests
        self.bugs_count = 0  # count number of unique bugs in the dut
        self.bugs = []  # list to append all errors happened
        self.bugs_final = []  # list to put the unique bugs in it

    async def scr_task(self, dut):
        #await Timer(1, "ns")
        while True:
            #await Timer(1, "ns")

            #self.monitor.clear()
            self.trans = await self.mon2scr.get()
            # receive from the dut:
            '''self.trans.a = dut.a.value
            self.trans.b = dut.b.value
            self.trans.op = dut.op.value

            self.trans.c = dut.c.value
            self.trans.out = dut.out.value'''

            self.trans.display("Scoreboard")

            # Scoreboard part where we check the output of the dut:
            if (int(self.trans.op)) == 0:
                if int(self.trans.a) + int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))

            elif (int(self.trans.op)) == 1:
                if int(self.trans.a) ^ int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))

            elif (int(self.trans.op)) == 2:
                if int(self.trans.a) & int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))

            elif (int(self.trans.op)) == 3:
                if int(self.trans.a) | int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))

            self.bugs_final = list(dict.fromkeys(self.bugs))  # removing duplicates to get the unique bugs
            self.bugs_count = len(self.bugs_final)  # counting the unique bugs
            self.scr_gen2.set()
            #await self.monitor.wait()


# coverage calculations:
Coverage = coverage_section(
    CoverPoint("top.a", vname="a", bins=list(range(0, 16))),
    CoverPoint("top.b", vname="b", bins=list(range(0, 16))),
    CoverPoint("top.op", vname="op", bins=list(range(0, 4))),
    CoverCross("top.all_cases", items=["top.a", "top.b", "top.op"])

)


@Coverage
def sample(a, b, op):
    cocotb.log.info("The randomized values are a= " + bin(int(a)) + " b= " + bin(int(b)) + " op= " + bin(int(op)))


@cocotb.test()
async def my_test(dut):

    # creating objects of our classes:
    g = generator()
    d = driver()
    m = monitor()
    s = scoreboard()

    # Connecting the events in each class:
    m.monitor = d.monitor_start  # event connecting between driver and monitor
    g.scr_gen = s.scr_gen2  # event connecting between generator and scoreboard
    #g.my_event2 = d.my_event  # event connecting between driver and generator

    g.gen2driv = d.gen2driv  # Connecting the queue between generator and driver

    m.mon2scr = s.mon2scr  # Connecting the queue between monitor and scoreboard

    # Starting our tasks in each class:
    cocotb.start_soon((g.gen_task()))
    cocotb.start_soon(d.driv_task(dut))
    cocotb.start_soon(m.mon_task(dut))
    cocotb.start_soon(s.scr_task(dut))

    '''await cocotb.start((g.gen_task()))
    await cocotb.start(d.driv_task(dut))
    await cocotb.start(m.mon_task(dut))
    await cocotb.start(s.scr_task(dut))'''

    await Timer(80000, "ns")

    cocotb.log.info("passed = " + str(s.passed))
    cocotb.log.info("failed = " + str(s.failed))
    cocotb.log.info("unique bugs= "+str(s.bugs_count))

    # Print coverage:
    coverage_db.export_to_xml(filename="coverage.xml")
