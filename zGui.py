#
#
#
import sys

from tkinter import * # pylint: disable=unused-wildcard-import
from tkinter import ttk
from tkinter.font import * # pylint: disable=unused-wildcard-import

#===============================
#
#
WIN_W = 400
WIN_H = 200

#===============================
#
#
class Gui:

    def __init__(self):

        self.callback = None

        self.win = Tk()
        self.win.title('win')
        self.w = self.win.winfo_screenwidth()
        self.h = self.win.winfo_screenheight()
        self.x = int(self.w/2 - WIN_W/2)
        self.y = int(self.h/2 - WIN_H/2)
        self.win.geometry(f'+{self.x}+{self.y}')
        self.win.withdraw()

        self.top = Toplevel()
        self.top.title('top')
        self.top.geometry(f'{WIN_W}x{WIN_H}+{self.x}+{self.y}')

        self.font20 = Font(family='맑은 고딕', size=20, weight='bold', slant='italic')
        self.font18 = Font(family='맑은 고딕', size=18, weight='bold', slant='italic')
        self.font16 = Font(family='맑은 고딕', size=16, weight='bold', slant='italic')
        self.font14 = Font(family='맑은 고딕', size=14, weight='bold', slant='italic')
        self.name = ''

    def quit(self):
        self.top.destroy()
        self.win.destroy()

    #===========================
    #
    #
    def ask_device_name(self, callback):
        self.callback = callback
        Label(self.top, text='enter device name', fg="green", font=self.font20).pack(padx=2, pady=2)
        self.entry = Entry(self.top, font=self.font14)
        self.entry.focus()
        self.entry.pack(padx=2, pady=2)
        Button(self.top, text='CANCEL', width=10, command=self.cancel_name).pack(padx=2, pady=2)
        Button(self.top, text='OK', width=10, command=self.ok_name).pack(padx=2, pady=2)
        self.top.mainloop()

    def ok_name(self):
        self.name = self.entry.get()
        if  self.callback != None:
            self.callback(self.name)
        self.top.destroy()
        self.win.destroy()

    def cancel_name(self):
        if  self.callback != None:
            self.callback(None)
        self.top.destroy()
        self.win.destroy()

    #===========================
    #
    #
    def gui_test(self):
        self.top.geometry(f'{WIN_W}x400+{self.x}+{self.y}')
        Button(self.top, text='CANCEL', width=10, command=self.cancel_name).pack(padx=2, pady=2)
        Button(self.top, text='OK', width=10, command=self.cancel_name).pack(padx=2, pady=2)
        ll = Listbox(self.top, selectmode='extended', height=0)
        ll.insert(0, '0000')
        ll.insert(1, '1111')
        ll.pack(padx=2, pady=2)
        i0 = IntVar()
        Checkbutton(self.top, text='click me', variable=i0).pack(padx=2, pady=2)
        i1 = IntVar()
        Radiobutton(self.top, text='click-me', value=1, variable=i1).pack(padx=2, pady=2)
        Radiobutton(self.top, text='click-me', value=2, variable=i1).pack(padx=2, pady=2)
        Message(self.top, text="MESSAGE", width=100).pack(padx=2, pady=2)
        tb = Text(self.top, height=3)
        tb.insert(tkinter.CURRENT, "하잉~~~ 안녕하세요\n")
        tb.insert("current", "반갑습니다")
        tb.pack(padx=2, pady=2)
        Spinbox(self.top, from_=0, to=50).pack(padx=2, pady=2)
        ii = [str(i)+'번' for i in range(1, 101)]
        ttk.Combobox(self.top, height=10, values=ii).pack(padx=2, pady=2)
        pb = ttk.Progressbar(self.top, maximum=100, mode='indeterminate')
        pb.pack(padx=2, pady=2)
        pb.start(50)
        self.top.mainloop()


#===============================
#
#
if  __name__ == '__main__':

    gui = Gui()
    #gui.ask_device_name(None)
    gui.gui_test()
    sys.exit()

#
#
#