#
#
#
import bluetooth # pylint: disable=import-error
import pywintypes
import subprocess
import sys
import threading
import time
import win32file

import zPipe
import zUtil

#================================
#
#
UUID_RFCOMM = '00000003-0000-1000-8000-00805F9B34FB'
UUID_SPP = '00001101-0000-1000-8000-00805F9B34FB'

BT_NAME = 'HC-05'

G_connected = False
G_found = False

#================================
#
#
class Bt:

    def __init__(self):
        self.sock = None
        self.s = 0
        self.r = 0
        self.d = 0

    def quit(self):
        print('BT: quit rx thread')
        self.thread.quit()

    #============================
    #
    #
    def connect(self, target=BT_NAME):

        global G_found
        print('BT: start inquiry')
        # duration > 4 period (1.28 x 4 = 5.12 sec)
        devices = bluetooth.discover_devices(duration=6, lookup_names=True, flush_cache=True, lookup_class=False)
        print(f'BT: found {len(devices)} neighbor devices')

        n = 1
        for addr, name in devices:
            try:
                print(f'{n}: {addr} - {name}')
            except UnicodeEncodeError:
                print(f'{n}: {addr} + {name.encode("utf-8", "replace")}')
            n += 1

        n = 1
        for addr, name in devices:
            if  name == target:
                break
            n += 1
            if  n > len(devices):
                G_found = False
                print('BT: not found ultiracer device')
                return

        G_found = True
        self.addr = devices[n-1][0]
        self.name = devices[n-1][1]
        print(f'BT: trying to connect to {self.name}')
        self.spp_client()

    #============================
    #
    #
    def sdp(self, target):

        print('BT: sdp begin')
        if  target == 'all':
            target = None
        services = bluetooth.find_service(address=target)

        if  len(services) > 0:
            print(f'BT: found {len(services)} services on {target}')
        else:
            print('BT: no services found')

        for s in services:
            print(f'service name: {s["name"]}')
            print(f'host: {s["host"]}')
            print(f'description: {s["description"]}')
            print(f'provider: {s["provider"]}')
            print(f'protocol: {s["protocol"]}')
            print(f'channel/psm: {s["port"]}') # psm - protocol and service multiplexer
            print(f'profiles: {s["profiles"]}')
            print(f'service classes: {s["service-classes"]}')
            print(f'service id: {s["service-id"]}')

        print('BT: sdp end')

    #============================
    #
    #
    def spp_client(self):

        global G_connected
        print(f'BT: search for spp server on {self.name}')
        uuid = UUID_SPP
        services = bluetooth.find_service(uuid=uuid, address=self.addr)

        if  len(services) == 0:
            print('BT: could not find spp server')
            G_connected = False
            return

        s = services[0]
        port = s['port']
        name = s['name']
        host = s['host']
        
        #---- auto pairing ----
        #
        try:
            subprocess.run(['urb_netfr.exe', host], check=True)
        except subprocess.CalledProcessError:
            print('BT: pairing error')

        self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.sock.connect((host, port))
        print('BT: connected')
        G_connected = True

        #---- receiver thread ----
        #
        self.thread = BtReceiver(self.sock)
        self.thread.start()


#================================
#
#
class BtReceiver(threading.Thread):

    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.rotation = 0
        self.speed = 0
        self.dir = 0
        self.s = 0
        self.r = 0
        self.v = 0
        self.d = 0
        self.f = True

    def quit(self):
        self.f = False
        self.sock.close()

    #============================
    #
    #
    def run(self):
        #---- rx loop ----
        #
        while self.f:
            try:
                rx = self.sock.recv(1024) # rx is byte stream
            except Exception:
                print(f'BT: stop rx')
                break
            try:
                if  zPipe.G_server[zPipe.PIPE_FOO] != None:
                    win32file.WriteFile(zPipe.G_server[zPipe.PIPE_FOO], rx)
            except pywintypes.error as e: # pylint: disable=E1101
                if  e.args[0] == 232:
                    zPipe.G_server[zPipe.PIPE_FOO] = None
            try:
                if  zPipe.G_server[zPipe.PIPE_FOOBAR] != None:
                    win32file.WriteFile(zPipe.G_server[zPipe.PIPE_FOOBAR], rx)
            except pywintypes.error as e: # pylint: disable=E1101
                if  e.args[0] == 232:
                    zPipe.G_server[zPipe.PIPE_FOOBAR] = None

            #---- for future usage ----
            # if rx:
            #    rd = rx.decode() # rd is str
            #    for i in range(len(rd)):
            #        self.state_machine(rd[i])
            #----

    def state_machine(self, d):
        b = ord(d)
        if   b == 86: self.s = 1; self.v = 0 # 86 = 'V' of 'Vnnnnn'
        elif b == 68: self.s = 7; self.d = 0 # 68 = 'D' of 'Dnnn'
        else:
            if    self.s == 1: self.s = 2;  self.v = (b - 48)
            elif  self.s == 2: self.s = 3;  self.v = (self.v * 10) + (b - 48)
            elif  self.s == 3: self.s = 4;  self.v = (self.v * 10) + (b - 48)
            elif  self.s == 4: self.s = 5;  self.v = (self.v * 10) + (b - 48)
            elif  self.s == 5: self.s = 6;  self.v = (self.v * 10) + (b - 48)
            elif  self.s == 7: self.s = 8;  self.d = (b - 48)
            elif  self.s == 8: self.s = 9;  self.d = (self.d * 10) + (b - 48)
            elif  self.s == 9: self.s = 10; self.d = (self.d * 10) + (b - 48)
            else: pass

        if  self.s == 6:
            self.speed = self.v
            # print(f'R:{self.speed}')

        if  self.s == 10:
            self.dir = self.d
            # print(f'D:{self.dir}')


#================================
#
#
if  __name__ == '__main__':

    bt = Bt()
    bt.connect()
    time.sleep(1)

    zUtil.wait_user_input()
    bt.quit()
    sys.exit()

#
#
#