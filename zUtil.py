#
#
#
import ctypes
import getpass
import msvcrt
import os
import shutil
import signal
import subprocess
import sys
import win32com.client
import winreg

#================================
#
#
USER_NAME = getpass.getuser() # login user name
DESKTOP_PATH = r'C:\Users\Public\Desktop'
STARTUP_PATH = fr'C:\Users\{USER_NAME}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup'
STARTUP_BAT_FILE = 'ultiracer.bat'
STARTUP_LNK_FILE = 'ultiracer.lnk'
ICO_FILE = 'ultiracer.ico'
REG_KEY = winreg.HKEY_CURRENT_USER
REG_SUB_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
REG_VALUE_NAME = 'ultiracer'
PROCESS_PER_EXEC = 2 # an app and its loader
WIN_SHOW = 1
WIN_HIDE = 0

G_autostartup = False
G_running = False
G_quit = False

#================================
#
#
def check_q():
    if  msvcrt.kbhit():
        c = msvcrt.getch()
        if  c == b'q':
            return True
    return False

def wait_user_input():
    global G_quit
    print('--- type q to quit ---')
    while True:
        if  check_q() == True or G_quit == True:
            break

def add_batch_to_startup(file):
    global G_autostartup
    target = STARTUP_PATH + '\\' + STARTUP_BAT_FILE
    if  os.path.isfile(target):
        print('batch file already exists')
    else:
        with open(target, 'w+') as f:
            f.write(fr'start "" {file}')
    G_autostartup = True

def add_lnk_to_startup(file):
    global G_autostartup
    target = STARTUP_PATH + '\\' + STARTUP_LNK_FILE
    if  os.path.isfile(target):
        print('link file already exists')
    else:
        make_lnk_file(file)
        dir = os.path.dirname(file)
        source = dir + fr'\{STARTUP_LNK_FILE}'
        shutil.copyfile(source, target)
    G_autostartup = True

def add_to_registry(file):
    global G_autostartup
    key = REG_KEY
    sub_key = REG_SUB_KEY
    reg = winreg.OpenKey(key, sub_key, 0, winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(reg, REG_VALUE_NAME, 0, winreg.REG_SZ, file)
    winreg.CloseKey(reg)
    G_autostartup = True

def make_lnk_file(file):
    shell = win32com.client.Dispatch('WScript.Shell')
    dir = os.path.dirname(file)
    base, ext = os.path.splitext(file)
    lnk = shell.CreateShortCut(os.path.join(dir, STARTUP_LNK_FILE))
    lnk.Targetpath = base + '.exe'
    lnk.WorkingDirectory = dir
    lnk.IconLocation = dir + fr'\{ICO_FILE}'
    lnk.save()

def is_running(file):
    global G_running
    base, ext = os.path.splitext(os.path.basename(file))
    call = 'TASKLIST', '/FI', f'imagename eq {base}.exe'
    output = subprocess.check_output(call)
    output = output.decode('euc-kr')
    print(output)
    names = output.strip().split('\r\n')
    names = names[2:] # remove table form
    n = names[-1]
    if  n.lower().startswith(base.lower()):
        G_running = True
        return len(names)
    else:
        return 0

def restart_app(file, argv):
    base, ext = os.path.splitext(os.path.basename(file))
    appx = f'{base}.exe'
    os.execv(appx, argv)

def kill_all(file):
    base, ext = os.path.splitext(os.path.basename(file))
    win_mgmt = win32com.client.GetObject('winmgmts:')
    all_proc = win_mgmt.InstancesOf('Win32_Process')
    for p in all_proc:
        if  p.Properties_('Name').Value == f'{base}.exe':
            pid = p.Properties_('ProcessID').Value
            os.kill(pid, 9)

def show_console():
    k32 = ctypes.WinDLL('kernel32')
    u32 = ctypes.WinDLL('user32')
    win = k32.GetConsoleWindow()
    u32.ShowWindow(win, WIN_SHOW)

def hide_console():
    k32 = ctypes.WinDLL('kernel32')
    u32 = ctypes.WinDLL('user32')
    win = k32.GetConsoleWindow()
    u32.ShowWindow(win, WIN_HIDE)

def raise_ctrl_c():
    os.kill(os.getpid(), signal.CTRL_C_EVENT)

#================================
#
#
if  __name__ == '__main__':

    file = os.path.realpath(__file__)
    print(file)

    #make_lnk_file(file)
    #add_batch_to_startup(file)
    #add_lnk_to_startup(file)
    #print(is_running(file))
    #kill_all(file)

    #wait_user_input()
    #restart_app(file, sys.argv)

    wait_user_input()
    sys.exit()

#
#
#