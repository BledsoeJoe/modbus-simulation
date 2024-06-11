import os
import sys
import time
import threading
import colorama

from pymodbus.server import StartTcpServer, ServerStop
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from random import randint, uniform


class server:
    """
        Creates a modbus server object capable of retaining, simulating, and communicating values via 100 modbus registers.
    """
    def __init__(self):

        # Define Modbus datastore (initial values for registers). For this example, it'll hold values from 0 to 10.
        self.store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*100),   # Discrete Inputs Initialize
            co=ModbusSequentialDataBlock(0, [0]*100),   # Coils Initialize
            hr=ModbusSequentialDataBlock(0, [0]*100),   # Holding Registers Initialize
            ir=ModbusSequentialDataBlock(0, [0]*100)    # Input Registers Initialize
        )
        # Set identity for our Modbus server
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'pymodbus'
        self.identity.ProductCode = 'PM'
        self.identity.ProductName = 'pymodbus Server'
        self.identity.ModelName = 'pymodbus Model'
        self.identity.MajorMinorRevision = '1.0'

        #booleans for sim registers
        self.randSims = [False]*100

        #lock for concurrency
        self.lock = threading.Lock()

    def run_server(self, port=502):
        """
        Starts the communication of the server object.
            Args:
                port: the host port for server communication

        """
        def start_server_thread():
            context = ModbusServerContext(slaves=self.store, single=True)
            # Start the server
            StartTcpServer(context=context, identity=self.identity, address=('0.0.0.0', port))

        #start the server in its own thread
        self.server_thread = threading.Thread(target=start_server_thread)
        self.server_thread.start()

    def sim_rand(self, reg=0, num_range=100, t=1, max_spread=2):
        """
        Starts simulation of random positive integer values.
            Args:
                reg: the register in which to simulate random values (default = 0)
                num_range: the upper range of values (default = 100, max = 65535)
                t: the average time in seconds in which values should update (default = 1)
                max_spread: the maximum difference (+/-) in the next generated value (default=2)
        """
        #set sim value for specified register to True
        self.randSims[reg] = True
        self.store.setValues(3,reg, [randint(0,num_range)])
        def sim_rand_thread():
            ##sim values
            while(self.randSims[reg]):
                with self.lock:
                    curVal = self.store.getValues(3,reg)
                    self.store.setValues(3,reg, [max(min(curVal[0]+randint(-max_spread,max_spread),num_range),0)])
                time.sleep(t+uniform(-t/2,2*t))
        self.sim_rand_thread = threading.Thread(target=sim_rand_thread)
        self.sim_rand_thread.start()

    def stop_sim_rand(self, reg=-1):
        """
        Stops updating the registers with random values.
            Args:
                reg: the number of the register to stop generating, -1 stops all (default = -1)
        """
        with self.lock:
            if reg == -1:
                for i,_ in enumerate(self.randSims):
                    self.randSims[i] = False
            elif reg < 0 or reg > 100:
                return
            else:
                self.randSims[reg] = False


    def stop_server(self):
        """
        Stops the server communication.
        """
        self.stop_sim_rand()
        ServerStop()

    def set_value(self, val, reg=0):
        """
        Sets the value of a specified register.
            Args:
                val: the value to be set.
                reg: the register to set the value of. (default = 0)
        """
        self.store.setValues(3,reg,[val,0])

    def get_value(self, reg=0):
        """
        Returns the value of a register
            Args:
                reg: the register to retreive the value of. (default = 0)
            Returns:
                the value of the specified register.
        """
        return self.store.getValues(3,reg)





    def display(self,regs=[]):
        """
        Displays live values of the modbus server.
            Args:
                regs: list of registers to diplay. (default = all values)
        """
        colorama.init() #for translating ANSI escape sequences in windows environments
        HIDE_CURSOR = "\033[?25l"
        SHOW_CURSOR = "\033[?25h"

        if len(regs) == 0:
            regs = list(range(0,98))
        elif any(n < 0 for n in regs) or any(n > 100 for n in regs):
            print("Invalid register! Registers must be between 0 and 100.")
            return
        try:
            print(HIDE_CURSOR, end="")
            print(colorama.ansi.clear_screen())
            rows, columns = os.get_terminal_size()
            rows -= 1  # Adjust for zero-based indexing or to leave space at the bottom
            num_per_row = 5
            while True:
                for start in range(0, len(regs), num_per_row * rows):
                    print("\033[H", end="")  # Move cursor to top left
                    for i in range(start, min(start + num_per_row * rows, len(regs)), num_per_row):
                        print(("\033[K" + ' '.join(f"r{regs[j]:<2}: {self.store.getValues(3,regs[j])[0]:^5}" for j in range(i, min(i + num_per_row, len(regs))))).ljust(columns))
                        if i + num_per_row >= len(regs):
                            break
                    # Clear remaining lines if any
                    for _ in range(len(regs) // num_per_row + 1 - rows):
                        print("\033[K")
                    time.sleep(.001)  # Pause for a bit before updating again
        except KeyboardInterrupt:
            print(colorama.ansi.clear_screen())
            print(SHOW_CURSOR, end="")
            colorama.deinit()
            print("\nStopped.")
