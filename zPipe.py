#
#
#
import pywintypes
import sys
import threading
import time
import win32api
import win32file
import win32pipe

import zUtil

#================================
#
#
PIPE_FOO = r'\\.\pipe\foo'
PIPE_FOOBAR = r'\\.\pipe\foobar'
PIPE_RDT = r'\\.\pipe\RDTLauncherPipe'

SERVER_FOO = 'foo'
SERVER_FOOBAR = 'foobar'
SERVER_RDT = 'rdt'

ROLE_RECEIVER = 'receiver'
ROLE_SENDER = 'sender'

SHOW_ON = 'on'
SHOW_OFF = 'off'

PIPE_OPEN_MODE = win32pipe.PIPE_ACCESS_DUPLEX
PIPE_MODE = win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT
PIPE_MAX_INSTANCE = 10
PIPE_BUF_SIZE = 65536
PIPE_TIMEOUT = 0
PIPE_SECURITY = None

PIPE_SET_MODE = win32pipe.PIPE_READMODE_MESSAGE
PIPE_SET_COLLECTION_MAX_COUNT = None
PIPE_SET_COLLECTION_TIMEOUT = None

FILE_ACCESS = win32file.GENERIC_READ | win32file.GENERIC_WRITE
FILE_SHARE_MODE = win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE
FILE_SECURITY = None
FILE_CREATION = win32file.OPEN_EXISTING
FILE_FLAGS = 0
FILE_TEMPLATE = None

G_server = { PIPE_FOO: None, PIPE_FOOBAR: None, PIPE_RDT: None }

#================================
#
#
class Pipe:

    def __init__(self):
        pass

#================================
#
#
class PipeServer(Pipe):

    def __init__(self, callback=None):
        self.callback = callback
        self.count = 0
        self.q = False
        self.launcher()
    
    def launcher(self):
        threading.Thread(target=self.server, args=(), daemon=True).start()
        threading.Thread(target=self.server, args=(PIPE_FOOBAR,), daemon=True).start()
        # threading.Thread(target=self.server, args=(PIPE_RDT, ROLE_RECEIVER), daemon=True).start()

    def quit(self):
        self.q = True

    #============================
    #
    #
    def server(self, pipe=PIPE_FOO, role=ROLE_SENDER):
        global G_server
        print(f'{pipe} server begin')
        while not self.q:
            if  G_server[pipe] == None:
                p = win32pipe.CreateNamedPipe(
                    pipe,        # pipe name
                    PIPE_OPEN_MODE,     # pipe open mode
                    PIPE_MODE,          # pipe mode
                    PIPE_MAX_INSTANCE,  # max instance
                    PIPE_BUF_SIZE,      # out buffer size
                    PIPE_BUF_SIZE,      # in  buffer size
                    PIPE_TIMEOUT,       # timeout
                    PIPE_SECURITY       # secuity attributes
                )
                print(f'{pipe} waiting for client')
                win32pipe.ConnectNamedPipe(p, None) #---- blocking ----
                print(f'{pipe} got client')
                G_server[pipe] = p

                try:
                    while not self.q:
                        #============================
                        #
                        if  role == ROLE_SENDER:
                            self.count += 1
                            # print(f'send {self.count}')
                            d = str.encode(f'{self.count}') # encode to byte stream
                            win32file.WriteFile(p, d) # send
                            time.sleep(1)

                        if  role == ROLE_RECEIVER:
                            d = win32file.ReadFile(p, PIPE_BUF_SIZE) #---- blocking ----
                            # print(f'receive {d[1].decode()}') # decide to string
                            if  self.callback != None:
                                self.callback(d[1].decode())
                        #
                        #============================

                except pywintypes.error as e: # pylint: disable=E1101
                    if  e.args[0] == 232:
                        print(f'{pipe} is being closed')

                G_server[pipe] = None
            time.sleep(1)
        print(f'{pipe} server end')


#================================
#
#
class PipeClient(Pipe):

    def __init__(self, pipe=PIPE_FOO, role=ROLE_RECEIVER, show=SHOW_ON, callback=None):
        self.pipe = pipe
        self.role = role
        self.show = show
        self.callback = callback
        self.count = 0
        self.q = False
        threading.Thread(target=self.client, args=()).start()
    
    def quit(self):
        self.q = True

    #============================
    #
    #
    def client(self):
        print(f'{self.pipe} client begin')
        while not self.q:
            try:
                h = win32file.CreateFile(
                    self.pipe,          # pipe file name
                    FILE_ACCESS,        # desired access mode
                    FILE_SHARE_MODE,    # share mode
                    FILE_SECURITY,      # security attributes
                    FILE_CREATION,      # creation disposition
                    FILE_FLAGS,         # flag and attributes
                    FILE_TEMPLATE       # template file
                )

                r = win32pipe.SetNamedPipeHandleState(
                    h,                              # pipe handle
                    PIPE_SET_MODE,                  # mode
                    PIPE_SET_COLLECTION_MAX_COUNT,  # max collection count
                    PIPE_SET_COLLECTION_TIMEOUT     # collection data timeout
                )

                if  r == 0:
                    e = win32api.GetLastError()
                    print(f'SetNamedPipeHandleState = {e}')
            
                #============================
                #
                while not self.q:

                    if  self.role == ROLE_RECEIVER:
                        d = win32file.ReadFile(h, PIPE_BUF_SIZE) #---- blocking ----
                        if  self.show == SHOW_ON:
                            print(f'receive {d[1].decode()}') # decide to string
                        if  self.callback != None:
                            self.callback(d[1].decode())

                    if  self.role == ROLE_SENDER:
                        self.count += 1
                        if  self.show == SHOW_ON:
                            print(f'send {self.count}')
                        d = str.encode(f'{self.count}') # encode to byte stream
                        win32file.WriteFile(h, d) # send
                        time.sleep(1)
                #
                #============================

            except pywintypes.error as e: # pylint: disable=E1101
                if  e.args[0] == 2:
                    print('there is no pipe (try again in a sec)')
                    time.sleep(1)
                elif e.args[0] == 109:
                    print('broken pipe')
                    self.q = True

        print(f'{self.pipe} client end')

#================================
#
#
if  __name__ == '__main__':

    '''
    client = PipeClient()
    zUtil.wait_user_input()
    client.quit()
    '''

    server = PipeServer()
    zUtil.wait_user_input()
    server.quit()
    sys.exit()

#
#
#