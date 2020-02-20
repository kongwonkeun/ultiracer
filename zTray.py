#
#
#
import os
import sys
import threading
import win32api
import win32con
import win32gui_struct
import win32gui

import zBt
import zConfig
import zUtil

#================================
#
#
DRIVER = 'urd_drv.exe'
DRIVER_PROXY = 'urd_drv_proxy.exe'
ICON_CONNECTED = 'ultiracer_2.ico'
ICON_DISCONNECTED = 'ultiracer.ico'
HOVER_TEXT_CONNECTED = 'ultiracer is connected'
HOVER_TEXT_DISCONNECTED = 'ultiracer is not connected. power-on device and selects restart menu'

#================================
#
#
class Tray:

    def __init__(self, file, argv):
        self.file = file
        self.argv = argv
        if  zBt.G_connected:
            self.icon = os.path.join(os.path.dirname(file), ICON_CONNECTED)
            self.hover = HOVER_TEXT_CONNECTED
        else:
            self.icon = os.path.join(os.path.dirname(file), ICON_DISCONNECTED)
            self.hover = HOVER_TEXT_DISCONNECTED
        dir = os.path.dirname(file)
        self.driver = dir + fr'\{DRIVER}'
        self.driver_proxy = dir + fr'\{DRIVER_PROXY}'

        menu_options = (
            ('config', None, self.on_config),
            ('restart', None, self.on_restart),
            ('driver', None, self.on_driver),
            ('driver and proxy', None, self.on_proxy),
            ('hide', None, self.on_hide),
            ('show', None, self.on_show),
        )
        self.tray_icon = TrayIcon(self.icon, self.hover, menu_options, on_quit=self.on_quit)
        self.tray_icon.start()
    
    def quit(self):
        self.tray_icon.shutdown()
    
    #============================
    #
    #
    def on_config(self, tray_icon):
        print('config')
        zConfig.Config(zConfig.CONFIG_FILE).save()

    def on_restart(self, tray_icon):
        print(f'restart')
        zUtil.restart_app(self.file, self.argv)
    
    def on_driver(self, tray_icon):
        print('driver')
        zUtil.restart_app(self.driver, self.argv)
    
    def on_proxy(self, tray_icon):
        print('driver and proxy')
        zUtil.restart_app(self.driver_proxy, self.argv)
    
    def on_hide(self, tray_icon):
        print('hide')
        zUtil.hide_console()

    def on_show(self, tray_icon):
        print('show')
        zUtil.show_console()

    def on_quit(self, tray_icon):
        print('quit')
        zUtil.G_quit = True
        zUtil.raise_ctrl_c()
        self.tray_icon.shutdown_self()


#================================
#
#
class TrayIcon:

    FIRST_ID = 1023
    DEFAULT_MENU_INDEX = 1
    WIN_CLASS_NAME = 'UltiracerTrayIcon'
    NOTIFY = 20 # notify message id = WM_USER + NOTIFY
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]
    
    def __init__(self, icon, hover_text, menu_options=None, on_quit=None):
        self.icon = icon
        self.icon_shared = False
        self.hover_text = hover_text
        self.on_quit = on_quit

        menu_options = menu_options or ()
        menu_options = menu_options + (('quit', None, self.QUIT),)
        self.next_id = self.FIRST_ID

        self.menu_actions_by_id = set()
        self.menu_options = self.add_ids_to_menu_options(list(menu_options))
        self.menu_actions_by_id = dict(self.menu_actions_by_id)
        self.default_menu_index = self.DEFAULT_MENU_INDEX
        self.win_class_name = self.WIN_CLASS_NAME

        #---- wndProc callback ----
        #
        self.message_dict = {
            win32gui.RegisterWindowMessage("TaskbarCreated"): self.restart,
            win32con.WM_DESTROY: self.destroy,
            win32con.WM_CLOSE: self.destroy,
            win32con.WM_COMMAND: self.command,
            win32con.WM_USER + self.NOTIFY: self.notify,
        }
        self.notify_id = None
        self.message_loop_thread = None
        self.hwnd = None
        self.hicon = None
        self.menu = None
        # register the window class
        window_class = win32gui.WNDCLASS()
        self.hinst = window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = self.win_class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        window_class.lpfnWndProc = self.message_dict # could also specify a wndproc
        win32gui.RegisterClass(window_class)

    #============================
    #
    #
    def run_message_loop(self):
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindowEx(
            0,
            self.win_class_name,
            self.win_class_name,
            style,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            self.hinst,
            None
        )
        win32gui.UpdateWindow(self.hwnd)
        self.notify_id = None
        self.refresh_icon()
        win32gui.PumpMessages()

    #============================
    #
    #
    def start(self):
        if  self.hwnd:
            return # started
        self.message_loop_thread = threading.Thread(target=self.run_message_loop)
        self.message_loop_thread.start()

    def restart(self, hwnd, msg, wparam, lparam):
        self.refresh_icon()

    def shutdown(self):
        if  not self.hwnd:
            return # not started
        win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0) # terminate the app
        self.message_loop_thread.join()

    def shutdown_self(self):
        if  not self.hwnd:
            return # not started
        win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0) # terminate the app
        #self.message_loop_thread.join()

    def destroy(self, hwnd, msg, wparam, lparam):
        if  self.on_quit:
            self.on_quit(self)
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # terminate the app
        self.hwnd = None
        self.notify_id = None

    def notify(self, hwnd, msg, wparam, lparam):
        if  lparam == win32con.WM_LBUTTONUP:  # left up
            self.execute_menu_option(self.DEFAULT_MENU_INDEX + self.FIRST_ID)
        elif lparam == win32con.WM_RBUTTONUP: # right up
            self.show_menu()
        else:
            pass
        return True

    def command(self, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        self.execute_menu_option(id)

    def execute_menu_option(self, id):
        menu_action = self.menu_actions_by_id[id]
        if  menu_action == self.QUIT:
            win32gui.DestroyWindow(self.hwnd)
        else:
            menu_action(self)

    #============================
    #
    #
    def add_ids_to_menu_options(self, menu_options):
        result = []
        for menu_option in menu_options:
            opt_text, opt_icon, opt_action = menu_option
            if  callable(opt_action) or opt_action in self.SPECIAL_ACTIONS:
                self.menu_actions_by_id.add((self.next_id, opt_action))
                result.append(menu_option + (self.next_id,))
            elif self.is_iterable_and_not_string(opt_action):
                result.append((opt_text, opt_icon, self.add_ids_to_menu_options(opt_action), self.next_id))
            else:
                print(f'unknown item {opt_text} {opt_icon} {opt_action}')
            self.next_id += 1
        return result

    def refresh_icon(self):
        # try and find a custom icon
        hinst = win32gui.GetModuleHandle(None)
        if  os.path.isfile(self.icon):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst, self.icon, win32con.IMAGE_ICON, 0, 0, icon_flags)
        else:
            print('can not find icon file - using default')
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        if  self.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD
        self.notify_id = (
            self.hwnd, 0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            win32con.WM_USER + self.NOTIFY,
            hicon, self.hover_text
        )
        win32gui.Shell_NotifyIcon(message, self.notify_id)

    def show_menu(self):
        menu = win32gui.CreatePopupMenu()
        self.create_menu(menu, self.menu_options)
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu, win32con.TPM_LEFTALIGN,
            pos[0], pos[1], 0,
            self.hwnd,
            None
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def create_menu(self, menu, menu_options):
        for opt_text, opt_icon, opt_action, opt_id in menu_options[::-1]:
            if  opt_icon:
                opt_icon = self.prep_menu_icon(opt_icon)
            if  opt_id in self.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(text=opt_text, hbmpItem=opt_icon, wID=opt_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                self.create_menu(submenu, opt_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=opt_text, hbmpItem=opt_icon, hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)

    def prep_menu_icon(self, icon):
        # first load the icon
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)
        hdcBitmap = win32gui.CreateCompatibleDC(None)
        hdcScreen = win32gui.GetDC(None)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        # fill the background
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        # draw the icon
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        # no need to free the brush
        win32gui.DeleteDC(hdcBitmap)
        return hbm

    def is_iterable_and_not_string(self, obj):
        try:
            iter(obj)
        except TypeError:
            return False
        else:
            return not isinstance(obj, str)


#================================
#
#
if  __name__ == '__main__':

    file = os.path.realpath(__file__)
    tray = Tray(file, sys.argv)

    #zUtil.wait_user_input()
    #tray.quit()
    sys.exit()

#
#
#