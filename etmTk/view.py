#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
#import the 'tkinter' module
from idlelib.EditorWindow import get_accelerator
import os
import re
import uuid
from copy import deepcopy
import subprocess
from dateutil.tz import tzlocal
import codecs

import logging
import logging.config
logger = logging.getLogger()

import platform

if platform.python_version() >= '3':
    import tkinter
    from tkinter import Tk, Entry, INSERT, END, Label, Toplevel, Button, Frame, LEFT, Text, PanedWindow, OptionMenu, StringVar, IntVar, Menu, BooleanVar, ACTIVE, Radiobutton, W, X
    # from tkinter import messagebox as tkMessageBox
    from tkinter import ttk
    from tkinter import font as tkFont
    from tkinter.messagebox import askokcancel
    from tkinter.filedialog import askopenfilename
    utf8 = lambda x: x
    # from tkinter import simpledialog as tkSimpleDialog
else:
    import Tkinter as tkinter
    from Tkinter import Tk, Entry, INSERT, END, Label, Toplevel, Button, Frame, LEFT, Text, PanedWindow, OptionMenu, StringVar, IntVar, Menu, BooleanVar, ACTIVE, Radiobutton, W, X
    # import tkMessageBox
    import ttk
    import tkFont
    from tkMessageBox import askokcancel
    from tkFileDialog import askopenfilename
    # import tkSimpleDialog
    def utf8(s):
        return(s)

tkversion = tkinter.TkVersion

import etmTk.data as data
# from data import init_localization

from dateutil.parser import parse

from etmTk.data import (
    init_localization, fmt_weekday, fmt_dt, hsh2str, tstr2SCI, leadingzero, relpath, parse_datetime, s2or3, send_mail, send_text, fmt_period, get_changes, checkForNewerVersion, datetime2minutes, calyear, expand_template, sys_platform, id2Type, get_current_time, windoz, mac, setup_logging, uniqueId, gettz, commandShortcut, optionShortcut, BGCOLOR, rrulefmt, makeTree, tree2Text, checkForNewerVersion, date_calculator)

from etmTk.help import (ATKEYS, DATES, ITEMTYPES,  OVERVIEW, PREFERENCES, REPORTS)

from etmTk.edit import SimpleEditor

import gettext

_ = gettext.gettext

# used in hack to prevent dialog from hanging under os x
if mac:
    AFTER = 100
else:
    AFTER = 1

FOUND = "found"

from idlelib.WidgetRedirector import WidgetRedirector

from datetime import datetime, timedelta

ONEMINUTE = timedelta(minutes=1)
ONEHOUR = timedelta(hours=1)
ONEDAY = timedelta(days=1)
ONEWEEK = timedelta(weeks=1)

STOPPED = _('stopped')
PAUSED = _('paused')
RUNNING = _('running')

AGENDA = _('Agenda')
SCHEDULE = _('Schedule')
PATHS = _('Paths')
KEYWORDS = _('Keywords')
TAGS = _('Tags')

COPY = _("Copy")
EDIT = _("Edit")
DELETE = _("Delete")

SEP = "----"

LASTLTR = re.compile(r'([a-z])$')

def sanitize_id(id):
    return id.strip().replace(" ", "")

(_ADD, _DELETE, _INSERT) = range(3)
(_ROOT, _DEPTH, _WIDTH) = range(3)

class Node:

    def __init__(self, name, identifier=None, expanded=True):
        self.__identifier = (str(uuid.uuid1()) if identifier is None else
                sanitize_id(str(identifier)))
        self.name = name
        self.expanded = expanded
        self.__bpointer = None
        self.__fpointer = []

    @property
    def identifier(self):
        return self.__identifier

    @property
    def fpointer(self):
        return self.__fpointer

    def update_fpointer(self, identifier, mode=_ADD):
        if mode is _ADD:
            self.__fpointer.append(sanitize_id(identifier))
        elif mode is _DELETE:
            self.__fpointer.remove(sanitize_id(identifier))
        elif mode is _INSERT:
            self.__fpointer = [sanitize_id(identifier)]

class Tree:

    def __init__(self):
        self.nodes = []
        self.lst = []

    def get_index(self, position):
        for index, node in enumerate(self.nodes):
            if node.identifier == position:
                break
        return index

    def create_node(self, name, identifier=None, parent=None):
        logger.debug("name: {0}, identifier: {1}; parent: {2}".format(name, identifier, parent))

        node = Node(name, identifier)
        self.nodes.append(node)
        self.__update_fpointer(parent, node.identifier, _ADD)
        node.bpointer = parent
        return node

    def showMenu(self, position, level=_ROOT):
        queue = self[position].fpointer
        if level == _ROOT:
            self.lst = []
        else:
            s = "{0}{1}".format("    "*(level-1), self[position].name)
            self.lst.append(s)
        if self[position].expanded:
            level += 1
            for element in queue:
                self.showMenu(element, level)  # recursive call
        return "\n".join(self.lst)

    def __update_fpointer(self, position, identifier, mode):
        if position is None:
            return
        else:
            self[position].update_fpointer(identifier, mode)

    def __getitem__(self, key):
        return self.nodes[self.get_index(key)]


class Timer():
    def __init__(self):
        """

        """
        self.timer_delta = 0 * ONEMINUTE
        self.timer_active = False
        self.timer_status = STOPPED
        self.timer_last = None
        self.timer_hsh = None
        self.timer_summary = None


    def timer_start(self, hsh=None):
        if not hsh: hsh = {}
        self.timer_hsh = hsh
        text = hsh['_summary']
        if len(text) > 10:
            self.timer_summary = "{0}~".format(text[:9])
        else:
            self.timer_summary = text
        self.timer_toggle(self.timer_hsh)

    def timer_finish(self, create=True):
        if self.timer_status == STOPPED:
            return ()
        if self.timer_status == RUNNING:
            self.timer_delta += datetime.now() - self.timer_last

        self.timer_delta = max(self.timer_delta, ONEMINUTE)
        self.timer_status = STOPPED
        self.timer_last = None

    def timer_toggle(self, hsh=None):
        if not hsh: hsh = {}
        if self.timer_status == STOPPED:
            self.timer_delta = timedelta(seconds=0)
            self.timer_last = datetime.now()
            self.timer_status = RUNNING
        elif self.timer_status == RUNNING:
            self.timer_delta += datetime.now() - self.timer_last
            self.timer_status = PAUSED
        elif self.timer_status == PAUSED:
            self.timer_status = RUNNING
            self.timer_last = datetime.now()

    def get_time(self):
        if self.timer_status == PAUSED:
            elapsed_time = self.timer_delta
        elif self.timer_status == RUNNING:
            elapsed_time = (self.timer_delta + datetime.now() -
                       self.timer_last)
        else:
            elapsed_time = 0 * ONEMINUTE
        plus = ""
        self.timer_minutes = elapsed_time.seconds//60
        if self.timer_status == RUNNING:
            plus = "+"
        # ret = "{0}  {1}{2}".format(self.timer_summary, self.timer_time, s)
        ret = "{0}  {1}{2}".format(self.timer_summary, fmt_period(elapsed_time), plus)
        logger.debug("timer: {0}; {1}; {2}".format(ret, self.timer_last, elapsed_time))
        return ret


class ReadOnlyText(Text):
    # noinspection PyShadowingNames
    def __init__(self, *args, **kwargs):
        Text.__init__(self, *args, **kwargs)
        self.redirector = WidgetRedirector(self)
        self.insert = self.redirector.register("insert", lambda *args, **kw: "break")
        self.delete = self.redirector.register("delete", lambda *args, **kw: "break")
        self.configure(highlightthickness=0)


class MessageWindow():
    # noinspection PyShadowingNames
    def __init__(self, parent, title, prompt):
        self.win = Toplevel(parent)
        self.parent = parent
        self.win.title(title)
        Label(self.win, text=prompt).pack(fill=tkinter.BOTH, expand=1, padx=10, pady=10)
        b = Button(self.win, text=_('OK'), width=10, command=self.cancel,
                   default='active')
        b.pack()
        self.win.bind('<Return>', (lambda e, b=b: b.invoke()))
        self.win.bind('<Escape>', (lambda e, b=b: b.invoke()))
        self.win.focus_set()
        self.win.grab_set()
        self.win.transient(parent)
        self.win.wait_window(self.win)
        return

    def cancel(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.win.destroy()


class Dialog(Toplevel):

    def __init__(self, parent, title=None, prompt=None, opts=None, default=None, modal=True):

        Toplevel.__init__(self, parent, highlightbackground=BGCOLOR,
                    background=BGCOLOR)
        if modal:
            logger.debug('modal')
            self.transient(parent)
        else:
            logger.debug('non modal')

        if title:
            self.title(title)

        self.parent = parent
        self.prompt = prompt
        self.options = opts
        self.default = default
        self.value = ""

        self.error_message = None

        self.buttonbox()

        body = Frame(self, highlightbackground=BGCOLOR, background=BGCOLOR)
        self.initial_focus = self.body(body)
        # body.pack(side="top", fill=tkinter.BOTH, padx=5, pady=5, expand=1)
        body.pack(side="top", fill=tkinter.BOTH, padx=0, pady=0, expand=1)

        # self.buttonbox()

        if modal:
            self.grab_set()

            if not self.initial_focus:
                self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()

        if modal:
            self.wait_window(self)

    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = Frame(self)

        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack(side='bottom')

    # standard button semantics

    def ok(self, event=None):
        res = self.validate()
        logger.debug('validate: {0}, value: "{1}"'.format(res, self.value))
        if not res:
            if self.error_message:
                self.messageWindow('error', self.error_message)
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()
        self.quit()

    def cancel(self, event=None):
        # return the focus to the tree view in the main window
        self.value = None
        logger.debug('value: "{0}"'.format(self.value))
        self.quit()

    def quit(self, event=None):
        self.parent.tree.focus_set()
        self.destroy()

    # command hooks

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override

    def messageWindow(self, title, prompt):
        MessageWindow(self.parent, title, prompt)

class NotebookWindow(Dialog):

    def body(self, master):
        self.currIndex = 0
        self.tabIndex = -1
        self.tabText = {}
        self.nb = nb = ttk.Notebook(master, padding=8)
        self.nb.pack(side="top", fill=tkinter.BOTH, expand=1, padx=0, pady=0)
        self.nb.enable_traversal()
        self.nb.bind("<<NotebookTabChanged>>", self.tabChanged)
        l, c = commandShortcut('f')
        self.bind_all(c, lambda e: self.e.focus_set())
        l, c = commandShortcut('g')
        self.bind_all(c, lambda e: self.onFind())
        return self.nb

    def addTab(self, label="", content=""):
        self.tabIndex += 1
        frame = Frame(self.nb)
        # text = ReadOnlyText(
        text = Text(
            frame,
            wrap="word", padx=2, pady=2, bd=2, relief="sunken",
            font=tkFont.Font(family="Lucida Sans Typewriter"),
            height=30,
            width=52,
            takefocus=False)
        text.tag_configure(FOUND, background="lightskyblue")
        text.insert("1.0", content)
        text.pack(side='left', fill=tkinter.BOTH, expand=1, padx=0, pady=0)
        ysb = ttk.Scrollbar(frame, orient='vertical', command=text.yview, width=8)
        ysb.pack(side='right', fill=tkinter.Y, expand=0, padx=0, pady=0)
        text.configure(yscroll=ysb.set)
        self.nb.add(frame, text=label)
        self.tabText[self.tabIndex] = text
        logger.debug("tabIndex {0}: {1}".format(self.tabIndex, type(self.tabText[self
                                              .tabIndex])))

    # def setText(self, indx, content=""):
    #     text = self.tabText[indx]
    #     text.delete("1.0", END)
    #     text.insert("1.0", content)

    def buttonbox(self):
        box = Frame(self, highlightbackground=BGCOLOR, background=BGCOLOR)
        # find
        w = Button(box, text="OK", width=10, command=self.cancel,
                   default=ACTIVE, highlightbackground=BGCOLOR)
        w.pack(side="right", padx=10, anchor="n")
        Button(box, text='x', highlightbackground=BGCOLOR, command=self.clearFind, padx=8).pack(side="right", padx=0, anchor="n")
        self.find_text = StringVar(box)
        self.e = Entry(box, textvariable=self.find_text, width=20, highlightbackground=BGCOLOR)
        self.e.pack(side="right", padx=0, fill=X, expand=0, anchor="n")
        self.e.bind("<Return>", self.onFind)
        Button(box, text='>', command=self.onFind, padx=6, highlightbackground=BGCOLOR).pack(side="right", padx=0)
        # self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.ok)
        # box.pack(side='bottom', pady=0, fill='x', expand=0)
        separator = Frame(self, height=8, bd=0, relief='flat', highlightbackground=BGCOLOR, background=BGCOLOR)
        separator.pack(side='bottom')
        box.pack(side='bottom', pady=0,  expand=0)

    def tabChanged(self, e=None):
        self.currIndex = self.nb.index(self.nb.select())
        logger.debug("currIndex: {0}".format(self.currIndex))


    def clearFind(self, *args):
        self.tabText[self.currIndex].tag_remove(FOUND, "0.0", END)
        self.find_text.set("")

    def onFind(self, *args):
        target = self.find_text.get()
        logger.debug('target {0}: {1}'.format(target, self.tabText[self.currIndex]))
        # self.tabText[self.currIndex].insert(INSERT, target)
        if target:
            where = self.tabText[self.currIndex].search(target, INSERT, nocase=1)
            if where:
                pastit = where + ('+%dc' % len(target))
                logger.debug('pastit: {0}'.format(pastit))
                # self.text.tag_remove(SEL, '1.0', END)
                self.tabText[self.currIndex].tag_add(FOUND, where, pastit)
                self.tabText[self.currIndex].mark_set(INSERT, pastit)
                self.tabText[self.currIndex].see(INSERT)
                self.tabText[self.currIndex].focus()

    def ok(self, event=None):
        if self.find_text.get():
            self.clearFind()
            return "break"
        self.withdraw()
        self.quit()

#     def test(self):
#         self.addTab(label="One", content="""\
# Now is the time
# for all good men
#         """)
#         self.addTab(label="Two", content="""\
# to come to the aid
# of their country.
#         """)


class DialogWindow(Dialog):
    # master will be a frame in Dialog
    # noinspection PyAttributeOutsideInit
    def body(self, master):
        self.entry = Entry(master)
        self.entry.pack(side="bottom", padx=5, pady=5)
        Label(master, text=self.prompt, justify='left').pack(side="top", fill=tkinter.BOTH, expand=1, padx=10, pady=5)
        if self.default is not None:
            self.entry.insert(0, self.default)
            self.entry.select_range(0, END)
            # self.entry.pack(padx=5, pady=5)
        return self.entry

class TextDialog(Dialog):

    def body(self, master):
        self.text = ReadOnlyText(
            master, wrap="word", padx=2, pady=2, bd=2, relief="sunken",
            font=tkFont.Font(family="Lucida Sans Typewriter"),
            height=14,
            width=52,
            takefocus=False)
        self.text.insert("1.1", self.prompt)
        self.text.pack(side='left', fill=tkinter.BOTH, expand=1, padx=0,
                       pady=0)
        ysb = ttk.Scrollbar(master, orient='vertical', command=self.text
                            .yview,
                            width=8)
        ysb.pack(side='right', fill=tkinter.Y, expand=0, padx=0, pady=0)
        # t.configure(state="disabled", yscroll=ysb.set)
        self.text.configure(yscroll=ysb.set)
        return self.text

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.cancel,
                   default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.ok)

        box.pack(side='bottom')


class OptionsDialog():
    # noinspection PyShadowingNames
    def __init__(self, parent, title="", prompt="", opts=None):
        if not opts: opts = []
        self.win = Toplevel(parent)
        self.parent = parent
        self.options = opts
        self.win.title(title)
        Label(self.win, text=prompt, justify='left').pack(fill=tkinter.BOTH, expand=1, padx=10, pady=5)
        # self.sv = StringVar(parent)
        self.sv = IntVar(parent)
        # self.sv.set(opts[0])
        self.sv.set(1)
        # logger.debug('sv: {0}'.format(self.sv.get()))
        if self.options:
            self.value = opts[0]
            for i in range(min(9, len(self.options))):
                txt = self.options[i]
                val = i + 1
                # bind keyboard numbers 1-9 (at most) to options selection, i.e., press 1
                # to select option 1, 2 to select 2, etc.
                self.win.bind(str(val), (lambda e, x=val: self.sv.set(x)))
                Radiobutton(self.win,
                    text="{0}: {1}".format(val, txt),
                    padx=20,
                    indicatoron=True,
                    variable=self.sv,
                    command=self.getValue,
                    value=val).pack(padx=10, anchor=W)
        box = Frame(self.win)
        c = Button(box, text="Cancel", width=10, command=self.cancel)
        c.pack(side=LEFT, padx=5, pady=5)
        o = Button(box, text="OK", width=10, default='active', command=self.ok)
        o.pack(side=LEFT, padx=5, pady=5)
        box.pack()
        self.win.bind('<Return>', (lambda e, o=o: o.invoke()))
        self.win.bind('<Escape>', (lambda e, c=c: c.invoke()))
        # self.choice.focus_set()
        self.win.focus_set()
        self.win.grab_set()
        # self.choice.focus()
        self.win.transient(parent)
        self.win.wait_window(self.win)

    def getValue(self, e=None):
        v = self.sv.get()
        logger.debug("sv: {0}".format(v))
        if self.options:
            if v-1 in range(len(self.options)):
                o = self.options[v-1]
                logger.debug(
                    'OptionsDialog returning {0}: {1}'.format(v, o))
                return v, o
                # return o, v
            else:
                logger.debug(
                    'OptionsDialog returning {0}: {1}'.format(v,  None))
                return 0, None
        else: # askokcancel type dialog
            logger.debug(
                'OptionsDialog returning {0}: {1}'.format(v, None))
            return v, None

    def ok(self, event=None):
        self.parent.update_idletasks()
        self.quit()

    def cancel(self, event=None):
        self.sv.set(0)
        self.quit()

    def quit(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.win.destroy()


class GetInteger(DialogWindow):
    def validate(self):
        # print('integer validate', self.options)
        minvalue = maxvalue = None
        if len(self.options) > 0:
            minvalue = self.options[0]
            if len(self.options) > 1:
                maxvalue = self.options[1]
        res = self.entry.get()
        try:
            val = int(res)
            ok = (minvalue is None or val >= minvalue) and (
                maxvalue is None or val <= maxvalue)
        except:
            val = None
            ok = False

        if ok:
            self.value = val
            return True
        else:
            self.value = None
            msg = [_('an integer')]
            conj = ""
            if minvalue is not None:
                msg.append(_("no less than {0}".format(minvalue)))
                conj = _("and ")
            if maxvalue is not None:
                msg.append(_("{0}no greater than {0}").format(conj, maxvalue))
            msg.append(_("is required"))
            self.error_message = "\n".join(msg)
            return False


class GetDateTime(DialogWindow):
    def validate(self):
        res = self.entry.get()
        ok = False
        if not res.strip():
            # return the current time if ok is pressed with no entry
            val = get_current_time()
            ok = True
        else:
            try:
                val = parse(parse_datetime(res))
                ok = True
            except:
                val = None
        if ok:
            self.value = val
            return True
        else:
            self.value = False
            self.error_message = _('could not parse "{0}"').format(res)
            return False


class GetString(DialogWindow):
    def validate(self):
        nullok = False
        if 'nullok' in self.options and self.options['nullok']:
            nullok = True
            # an entry is required
        val = self.entry.get()
        ok = False
        if val.strip():
            self.value = val
            return True
        elif nullok:  # null and null is ok
            if self.value is None:
                return False
            else:
                self.value = val
                return True
        else:
            self.error_message = _('an entry is required')
            return False


class App(Tk):
    def __init__(self, path=None):
        Tk.__init__(self)
        # minsize: width, height
        self.minsize(430, 450)
        self.uuidSelected = None
        self.timerItem = None
        self.actionTimer = Timer()
        self.loop = loop
        self.configure(background=BGCOLOR)
        self.option_add('*tearOff', False)
        self.menu_lst = []
        self.menutree = Tree()

        root = "_"
        # create the root node for the menu tree
        self.menutree.create_node(root, root)
        # branch: (parent, child)
        # leaf: (parent, (option, [accelerator])
        menubar = Menu(self)
        logger.debug('AFTER: {0}'.format(AFTER))
        menu = _("Menubar")
        self.add2menu(root, (menu,))

        # File menu
        filemenu = Menu(menubar, tearoff=0)
        path = _("File")
        self.add2menu(menu, (path, ))

        ## open file

        # openmenu = Menu(filemenu, tearoff=0)

        # filemenu.add_command(label=_("Recently changed ..."),
        #                      underline=0, command=self.donothing)

        l, c = commandShortcut('F')
        label = _("Data file ...")
        filemenu.add_command(label=label, underline=0, command=self.editData)
        # self.bind_all(c, self.editData)
        self.add2menu(path, (label, l))

        filemenu.add_separator()
        self.add2menu(path, (SEP, ))


        l, c = commandShortcut('P')
        file = loop.options['config']
        # label = relpath(file, loop.options['etmdir'])
        label = _("Preferences")
        filemenu.add_command(label=label, underline=0, command=lambda e=None, x=file: self.editFile(e, file=x, config=True), )
        self.bind_all(c, lambda e, x=file:  self.editFile(file=x, config=True))
        self.add2menu(path, (label, l))

        l, c = commandShortcut('A')
        file = loop.options['auto_completions']
        # label = relpath(file, loop.options['etmdir'])
        label = _("Auto completions")
        filemenu.add_command(label=label, underline=0, command=lambda x=file: self.editFile(file=x))
        self.bind_all(c, lambda e, x=file:  self.editFile(file=x))
        self.add2menu(path, (label, l))

        l, c = commandShortcut('R')
        file = loop.options['report_specifications']
        # label = relpath(file, loop.options['etmdir'])
        label = _("Report specifications")
        filemenu.add_command(label=label, underline=0, command=lambda x=file: self.editFile(e=None, file=x))
        self.bind_all(c, lambda e, x=file:  self.editFile(file=x))
        self.add2menu(path, (label, l))

        l, c = commandShortcut('S')
        file = loop.options['scratchpad']
        # label = relpath(file, loop.options['etmdir'])
        label = _("Scratchpad")
        filemenu.add_command(label=label, underline=0, command=lambda x=file: self.editFile(file=x))
        self.bind_all(c, lambda e, x=file: self.editFile(file=x))
        self.add2menu(path, (label, l))

        filemenu.add_separator()
        self.add2menu(path, (SEP, ))

        ## export
        # l, c = commandShortcut('X')
        label = _("Export to iCal")
        filemenu.add_command(label=label, underline=1, command=self.donothing)
        # self.bind_all(c, self.donothing)
        self.add2menu(path, (label, ))

        filemenu.add_separator()
        self.add2menu(path, (SEP, ))

        ## quit
        # l, c = commandShortcut('q')
        label = _("Quit")
        filemenu.add_command(label=label, underline=0,
        command=self.quit)
        # self.bind(c, self.quit)  # w
        self.add2menu(path, (label, ))

        menubar.add_cascade(label=path, underline=0, menu=filemenu)

        # treetext = tree2Text(tree)
        # logger.debug('menu_tree:\n{0}'.format(self.tree.show(root)))
        # self.tree.show(root)
        # tree = make_tree(self.menu_lst)
        # logger.debug('tree:\n{0}'.format(tree))

        # view menu
        path = _("Commands")
        self.add2menu(menu, (path, ))
        viewmenu = Menu(menubar, tearoff=0)

        # go to date
        l, c = commandShortcut('j')
        label=_("Jump to date")
        viewmenu.add_command(
            label=label, underline=1, accelerator=l,
            command=self.goToDate)
        # needed for os x to prevent dialog hanging
        self.bind_all(c, lambda event: self.after(AFTER, self.goToDate))
        self.add2menu(path, (label, l))

        # expand to depth
        l, c = commandShortcut('o')
        label=_("Set outline depth")
        viewmenu.add_command(
            label=label, underline=1, accelerator=l,
            command=self.expand2Depth)
        # needed for os x to prevent dialog hanging
        self.bind_all(c, lambda event: self.after(AFTER, self.expand2Depth))
        self.add2menu(path, (label, l))

        # calendars
        label = _("Choose active calendars")
        calendarmenu = Menu(viewmenu, tearoff=0)
        self.calendars = deepcopy(loop.options['calendars'])
        logger.debug('{0}: {1}'.format(label, [x[:2] for x in self.calendars]))
        self.calendarValues = []
        for i in range(len(self.calendars)):
            # logger.debug('Adding calendar: {0}'.format(self.calendars[i][:2]))
            self.calendarValues.append(BooleanVar())
            self.calendarValues[i].set(self.calendars[i][1])
            self.calendarValues[i].trace_variable("w", self.updateCalendars)
            calendarmenu.add_checkbutton(label=self.calendars[i][0], onvalue=True, offvalue=False, variable=self.calendarValues[i])

        if self.calendars:
            viewmenu.add_cascade(label=label,
                                 menu=calendarmenu)
        else:
            viewmenu.add_cascade(label=label,
                                 menu=calendarmenu,
                                 state="disabled")
        self.add2menu(path, (label, ))

        viewmenu.add_separator()
        self.add2menu(path, (SEP, ))


        # busy times
        l, c = commandShortcut('b')
        label = _("Show busy periods")
        viewmenu.add_command(label=label, underline=1,
                             accelerator=l,
                             command=self.showBusyTimes)
        self.bind_all(c, lambda event: self.after(AFTER, self.showBusyTimes))
        self.add2menu(path, (label, l))

        # report
        l, c = commandShortcut('r')
        label=_("Create report")
        viewmenu.add_command(label=label, accelerator=l,
                             underline=1,
                             command=self.donothing)
        self.bind(c, self.donothing)
        self.add2menu(path, (label, l))

        viewmenu.add_separator()
        self.add2menu(path, (SEP, ))

        l, c = commandShortcut('y')
        label=_("Display yearly calendar")
        viewmenu.add_command(label=label, underline=1, accelerator=l,
                             command=self.showCalendar)
        self.bind_all(c, lambda event: self.after(AFTER, self.showCalendar))
        self.add2menu(path, (label, l))

        # date calculator
        l, c = commandShortcut('l')
        label=_("Open date calculator")
        viewmenu.add_command(label=label, underline=1, accelerator=l, command=self.dateCalculator)
        self.bind(c, lambda event: self.after(AFTER, self.dateCalculator))
        # c
        self.add2menu(path, (label, l))

        viewmenu.add_separator()
        self.add2menu(path, (SEP, ))

        # changes
        l, c = commandShortcut('h')
        label = _("Change history")
        viewmenu.add_command(label=label, underline=1,  accelerator=l, command=self
                             .showChanges)
        self.bind_all(c, lambda event: self.after(AFTER, self.showChanges))
        self.add2menu(path, (label, l))

        # label = _("Error log")
        # viewmenu.add_command(label=label, underline=1, command=self.donothing)
        # self.add2menu(path, (label, ))

        menubar.add_cascade(label=path, menu=viewmenu, underline=0)

        # logger.debug('menu_tree:\n{0}'.format(self.menutree.showMenu(root)))

        # TODO: add help topics
        # overview
        # data
        # views
        # X commands and shortcuts
        # preferences
        # reports

        helpmenu = Menu(menubar, tearoff=0)
        path = _("Help")
        self.add2menu(menu, (path, ))

        # search is built in
        self.add2menu(path, (_("Search"), ))

        label = _("Help")
        helpmenu.add_command(label=label, underline=1, accelerator="F1", command=self
                             .help)
        self.add2menu(path, (label, "F1"))
        self.bind_all("<F1>", lambda e: self.after(AFTER, self.help))


        label = _("About")
        helpmenu.add_command(label="About", accelerator="F2", command=self\
            .about)
        self.bind_all("<F2>", self.about)
        self.add2menu(path, (label, "F2"))

        # check for updates
        # l, c = commandShortcut('u')
        label = _("Check for update")
        helpmenu.add_command(label=label, underline=1, accelerator="F3", command=self.checkForUpdate)
        self.add2menu(path, (label, "F3"))
        self.bind_all("<F3>", self.checkForUpdate)




        # submenu = _("Topics")
        # topicsmenu = Menu(menubar, tearoff=0)
        # helpmenu.add_cascade(label=submenu, menu=topicsmenu)
        # self.add2menu(path, (submenu,))
        # self.bind_all("<F1>", helpmenu.invoke(4))
        #
        #
        # path = submenu
        #
        # label = _("Comands and shortcuts")
        # topicsmenu.add_command(label=label, command=self
        #                        .help)
        # # self.bind(c, self.help)
        # self.add2menu(path, (label, "F1"))



        menubar.add_cascade(label="Help", menu=helpmenu)

        self.config(menu=menubar)

        # self.configure(background="lightgrey")

        self.history = []
        self.index = 0
        self.count = 0
        self.count2id = {}
        self.now = get_current_time()
        self.today = self.now.date()
        self.options = loop.options
        self.popup = ''
        self.value = ''
        self.firsttime = True
        self.mode = 'command'   # or edit or delete
        self.item_hsh = {}
        self.depth2id = {}
        self.prev_week = None
        self.next_week = None
        self.curr_week = None
        self.week_beg = None
        self.itemSelected = None
        self.uuidSelected = None
        self.dtSelected = None
        self.rowSelected = None

        self.title("etm tk")
        # self.wm_iconbitmap(bitmap='etmlogo.gif')
        # self.wm_iconbitmap('etmlogo-4.xbm')
        self.call('wm', 'iconbitmap', self._w, '/Users/dag/etm-tk/etmTk/etmlogo.gif')

        # if sys_platform == 'Linux':
        #     logger.debug('using linux icon')
        #     self.wm_iconbitmap('@' + 'etmlogo.gif')
        #     # self.wm_iconbitmap('etmlogo-4.xbm')
        #     # self.call('wm', 'iconbitmap', self._w, '/Users/dag/etm-tk/etmlogo_128x128x32.ico')
        #     # self.iconbitmap(ICON_PATH)
        # elif sys_platform == 'Darwin':
        #     logger.debug('using darwin icon')
        #     self.wm_iconbitmap('etmlogo.icns')
        # else:
        #     logger.debug('using windows icon')
        #     self.wm_iconbitmap('etmlogo.ico')

        # TODO: add next(), prev() navigation to trees bound to right and left cursor keys

        self.columnconfigure(0, minsize=300, weight=1)
        self.rowconfigure(1, weight=2)

        toolbar = Frame(self)

        panedwindow = PanedWindow(self, orient="vertical",
                         # showhandle=True,
                         sashwidth=6, sashrelief='flat',
        )

        self.tree = ttk.Treeview(panedwindow, show='tree', columns=["#1"], selectmode='browse',
                                 # padding=(3, 2, 3, 2)
        )
        self.tree.column('#0', minwidth=200, width=260, stretch=1)
        self.tree.column('#1', minwidth=80, width=140, stretch=0, anchor='center')
        self.tree.bind('<<TreeviewSelect>>', self.OnSelect)
        self.tree.bind('<Double-1>', self.OnDoubleClick)
        self.tree.bind('<Return>', self.OnActivate)
        self.tree.bind('<Escape>', self.cleartext)
        self.tree.bind('<space>', self.goHome)
        # self.tree.bind('<j>', self.jumpToDate)

        for t in tstr2SCI:
            self.tree.tag_configure(t, foreground=tstr2SCI[t][1])

        self.date2id = {}
        # padx = 2

        self.root = (u'', u'_')

        toolbar.grid(row=0, column=0, sticky='ew', padx=3, pady=2)

        tbar = _("Toolbar")
        self.add2menu(root, (tbar,))
        path = tbar,

        menuwidth = 9

        # show menu
        self.viewLabel = _("View")
        self.add2menu(tbar, (self.viewLabel, ))
        path = self.viewLabel

        self.vm_options = [[AGENDA, 'a'],
                           [SCHEDULE, 's'],
                           [PATHS, 'p'],
                           [KEYWORDS, 'k'],
                           [TAGS, 't']]

        self.view2cmd = {'a': self.agendaView,
                         's': self.scheduleView,
                         'p': self.pathView,
                         'k': self.keywordView,
                         't': self.tagView}

        self.vm_opts = [x[0] for x in self.vm_options]
        self.view = self.vm_options[0][0]
        self.viewValue = StringVar(self)
        self.currentView = StringVar(self)
        self.currentView.set(self.view)
        self.viewValue.set(self.viewLabel)
        self.vm = OptionMenu(toolbar, self.viewValue, *self.vm_opts, command=self.setView)

        self.vm.configure(width=menuwidth)
        for i in range(len(self.vm_options)):
            label = self.vm_options[i][0]
            k = self.vm_options[i][1]
            l, c = commandShortcut(k)
            self.bind(c, self.view2cmd[k])  # a, s, p, k, t
            self.vm["menu"].entryconfig(i, accelerator=l)
            self.add2menu(path, (label, l))

        self.vm.pack(side="left")
        self.vm.configure(width=menuwidth, background=BGCOLOR, takefocus=False)

        # make
        self.newLabel = _("New")
        self.add2menu(tbar, (self.newLabel, ))
        path = self.newLabel

        self.newValue = StringVar(self)
        self.newValue.set(self.newLabel)
        self.nm_options = [[_('Item'), 'n'],
                           [_('Timer'), 'm'],
        ]
        self.nm_opts = [x[0] for x in self.nm_options]
        self.nm = OptionMenu(toolbar, self.newValue, *self.nm_opts)

        label = self.nm_options[0][0]
        l, c = commandShortcut(self.nm_options[0][1])
        logger.debug("new item: {0}, {1}".format(l, c))
        self.nm["menu"].entryconfig(0, accelerator=l, command=self.newItem)
        self.bind(c, self.newItem)  # n
        self.add2menu(path, (label, l))

        label = self.nm_options[1][0]
        l, c = commandShortcut(self.nm_options[1][1])
        self.nm["menu"].entryconfig(1, accelerator=l, command=self.startActionTimer)
        self.bind(c, self.startActionTimer)  # +
        self.add2menu(path, (label, l))


        self.nm.pack(side="left")
        self.nm.configure(width=menuwidth, background=BGCOLOR, takefocus=False)

        # edit
        self.editLabel = _("Edit")
        self.add2menu(tbar, (self.editLabel, ))
        path = self.editLabel

        self.editValue = StringVar(self)
        self.editValue.set(self.editLabel)
        self.em_options = [
            [_('Copy'), 'c'],
            [_('Delete'), 'd'],
            [_('Edit'), 'e'],
            [_('Finish'), 'f'],
            [_('Reschedule'), 'r'],
            [_('Open link'), 'g'],
        ]
        self.edit2cmd = {
            'c': self.copyItem,
            'd': self.deleteItem,
            'e': self.editItem,
            'f': self.finishItem,
            'r': self.rescheduleItem,
            'g': self.openWithDefault,
        }
        self.em_opts = [x[0] for x in self.em_options]
        em_cmds = [x[1] for x in self.em_options]

        self.em = OptionMenu(toolbar, self.editValue, *self.em_opts)

        for i in range(len(self.em_options)):
            label = self.em_options[i][0]
            k = self.em_options[i][1]
            l, c = commandShortcut(k)
            self.em["menu"].entryconfig(i, accelerator=l, command=lambda x=k: self.after(AFTER, self.edit2cmd[x]))
            self.bind_all(c, lambda event, x=k: self.after(AFTER, self.edit2cmd[x]))
            self.add2menu(path, (label, l))

        self.em.pack(side="left")
        self.em.configure(width=menuwidth, background=BGCOLOR, takefocus=False)

        self.helpBtn = Button(toolbar, bd=0, text="?", takefocus=False, command=self.help)
        self.helpBtn.pack(side="right")
        self.helpBtn.configure(highlightbackground=BGCOLOR, highlightthickness=0)

        self.filterValue = StringVar(self)
        self.filterValue.set('')
        self.filterValue.trace_variable("w", self.filterView)
        self.e = Entry(toolbar, width=8, textvariable=self.filterValue,
                       # relief="raised",
                       # highlightcolor=BGCOLOR,
                       # bd=4
                      )
        self.e.bind('<Return>', self.showView)
        self.e.bind('<Escape>', self.cleartext)
        # self.e.bind('<Up>', self.prev_history)
        # self.e.bind('<Down>', self.next_history)
        self.e.pack(side="left", fill=tkinter.BOTH, expand=1, padx=2)
        self.e.configure(width=menuwidth, highlightthickness=0)

        panedwindow.add(self.tree, padx=3, pady=0, stretch="first")

        self.l = ReadOnlyText(panedwindow, wrap="word", padx=3, bd=2, relief="sunken",
                              font=tkFont.Font(family="Lucida Sans Typewriter"), height=6,
                              width=46, takefocus=False)
        self.l.bind('<Escape>', self.cleartext)
        self.l.bind('<space>', self.goHome)
        self.l.bind('<Tab>', self.focus_next_window)

        panedwindow.add(self.l, padx=3, pady=0, stretch="never")

        panedwindow.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        panedwindow.configure(background=BGCOLOR)

        self.sf = Frame(self)
        toolbar.configure(background=BGCOLOR)
        # self.pendingAlerts = StringVar(self)
        # self.pendingAlerts.set("")

        showing = Label(self.sf, textvariable=self.currentView, bd=1, relief="flat",
                        anchor="w", padx=0, pady=0)
        showing.pack(side="left")
        showing.configure(width=menuwidth, background=BGCOLOR,
                          highlightthickness=0)

        self.nonDefaultCalendars = StringVar(self)
        self.nonDefaultCalendars.set("")
        nonDefCal = Label(self.sf, textvariable=self.nonDefaultCalendars, bd=0,
                          relief="flat", anchor="center", padx=0, pady=0)
        nonDefCal.pack(side="left")
        nonDefCal.configure(background=BGCOLOR)

        self.timerStatus = StringVar(self)
        self.timerStatus.set("")
        timer_status = Label(self.sf, textvariable=self.timerStatus, bd=0, relief="flat",
                             anchor="center", padx=4, pady=0)
        timer_status.pack(side="left", expand=1)
        timer_status.configure(background=BGCOLOR, highlightthickness=0)

        self.pendingAlerts = IntVar(self)
        self.pendingAlerts.set(0)
        self.pending = Button(self.sf, bd=0, width=1, takefocus=False, textvariable=self.pendingAlerts, command=self.showAlerts)
        self.pending.pack(side="right")
        self.pending.configure(highlightbackground=BGCOLOR,
                               highlightthickness=0, state="disabled")
        self.showPending = True

        self.currentTime = StringVar(self)
        currenttime = Label(self.sf, textvariable=self.currentTime, bd=1, relief="flat",
                            anchor="e", padx=4, pady=0)
        currenttime.pack(side="right")
        currenttime.configure(background=BGCOLOR)

        self.sf.grid(row=2, column=0, sticky="ew", padx=8, pady=4)
        self.sf.configure(background=BGCOLOR)

        self.grid()

        # self.e.select_range(0, END)

        # start clock
        self.updateClock()

        # show default view
        self.updateAlerts()
        self.showView()

    def add2menu(self, parent, child):
        if child == (SEP, ):
            id = uuid.uuid1()
        elif len(child) > 1 and child[1]:
            id = uuid.uuid1()
            m = LASTLTR.search(child[1])
            if m:
                child = list(child)
                v = child[1]
                l = m.group(1).upper()
                v = LASTLTR.sub("{0}".format(l), v, count=1)
                child[1] = v
                child = tuple(child)
        else:
            id = child[0]
        if len(child) == 2:
            leaf = "{0:<30} {1:^11}".format(child[0], child[1])
        else:
            leaf = "{0:<30}".format(child[0])
        logger.debug('create_node: {0}, {1}, parent = {2}'.format(leaf, id,  parent))
        self.menutree.create_node(leaf, id, parent=parent)


    def confirm(self, parent=None, title="", prompt="", instance="xyz"):
        ok, value = OptionsDialog(parent=self, title=_("confirm").format(instance), prompt=prompt).getValue()
        return ok


    def updateCalendars(self, *args):
        for i in range(len(loop.calendars)):
            loop.calendars[i][1] = self.calendarValues[i].get()
        if loop.calendars != loop.options['calendars']:
            cal_pattern = r'^%s' % '|'.join(
                [x[2] for x in loop.calendars if x[1]])
            loop.cal_regex = re.compile(cal_pattern)
            self.nonDefaultCalendars.set("*")
        else:
            cal_pattern = ''
            loop.cal_regex = None
            self.nonDefaultCalendars.set("")
            # print('updateCalendars', loop.calendars, cal_pattern, loop.cal_regex)
        self.showView()


    def quit(self, e=None):
        # ans = askokcancel(
        #     _('Quit'),
        #     _("Do you really want to quit?"),
        #     parent=self)
        ans = self.confirm(
            title=_('Quit'),
            prompt=_("Do you really want to quit?"),
            parent=self)
        if ans:
            self.destroy()

    def donothing(self, e=None):
        """For testing"""
        logger.debug('donothing')

    def openWithDefault(self):
        if 'g' not in self.itemSelected:
            return(False)
        path = self.itemSelected['g']

        if windoz:
            os.startfile(path)
            return()
        if mac:
            cmd = 'open' + " {0}".format(path)
        else:
            cmd = 'xdg-open' + " {0}".format(path)
        subprocess.call(cmd, shell=True)
        return True


    def dateCalculator(self, event=None):
        prompt = """\
Enter an expression of the form "x [+-] y" where x is a date
and y is either a date or a time period if "-" is used and
a time period if "+" is used."""
        value = GetString(parent=self, title=_('date calculator'),  prompt=prompt, opts={}).value
        if not value:
            return
        res = date_calculator(value, self.options)
        prompt = "{0}:\n\n{1}".format(value, res)
        MessageWindow(self, title=_("result"), prompt=prompt)


    def newItem(self, e=None):
        logger.debug('newItem')
        changed = SimpleEditor(parent=self, options=loop.options).changed
        if changed:
            logger.debug('changed, reloading data')
            loop.loadData()
            self.updateAlerts()
            self.showView()

    def which(self, act, instance="xyz"):
        prompt = "\n".join([
            _("You have selected an instance of a repeating"),
            _("item. What do you want to {0}?").format(act)])
        if act == DELETE:
            opt_lst = [
                _("this instance"),
                _("this and all subsequent instances"),
                _("all instances"),
                _("all previous instances")]
        else:
            opt_lst = [
                _("this instance"),
                _("this and all subsequent instances"),
                _("all instances")]

        indx, value = OptionsDialog(parent=self, title=_("instance: {0}").format(instance), prompt=prompt, opts=opt_lst).getValue()
        return indx, value

    # TODO: replace dt with dtn in copyItem and editItem?

    def copyItem(self, e=None):
        """
        newhsh = selected, rephsh = None
        """
        if 'r' in self.itemSelected:
            choice, value = self.which(COPY, self.dtSelected)
            logger.debug("{0}: {1}".format(choice, value))
            if not choice:
                self.tree.focus_set()
                return
            self.itemSelected['_dt'] = parse(self.dtSelected)
        else:
            # ans = DialogWindow(self, title=_('confirm'),
            #                    prompt=_("Clone this item?"))
            # ans = askokcancel('confirm', "Clone this item?", parent=self.tree, icon="question")
            ans = self.confirm(
                parent=self.tree,
                title=_('Confirm'),
                prompt=_("Open a copy of this item?"))
            if not ans:
                self.tree.focus_set()
                return
            choice = 3
        hsh_cpy = deepcopy(self.itemSelected)
        hsh_cpy['fileinfo'] = None
        # hsh_cpy['i'] = uniqueId()
        title = _("new item")
        self.mode = 'new'
        if choice in [1, 2]:
            # we need to modify the copy according to the choice
            dt = hsh_cpy['_dt'].replace(
                tzinfo=tzlocal()).astimezone(gettz(hsh_cpy['z']))
            dtn = dt.replace(tzinfo=None)

            if choice == 1:
                # this instance
                for k in ['_r', 'o', '+', '-']:
                    if k in hsh_cpy:
                        del hsh_cpy[k]
                hsh_cpy['s'] = dt
                # edit_str = hsh2str(hsh_cpy, loop.options)

            elif choice == 2:
                # this and all subsequent instances
                tmp = []
                if u'+' in hsh:
                    tmp_cpy = []
                    for d in hsh_cpy['+']:
                        if d >= dtn:
                            tmp_cpy.append(d)
                    hsh_cpy['+'] = tmp_cpy
                if u'-' in hsh_cpy:
                    tmp_cpy = []
                    for d in hsh_rev['-']:
                        if d >= dtn:
                            tmp_cpy.append(d)
                    hsh_cpy['-'] = tmp_cpy
                hsh_cpy['s'] = dt
                # edit_str = hsh2str(hsh_cpy, loop.options)

        changed = SimpleEditor(parent=self, newhsh=hsh_cpy, rephsh=None,
                         options=loop.options, title=title).changed

        if changed:
            loop.loadData()
            self.updateAlerts()
            self.showView(row=self.topSelected)
        else:
            self.tree.focus_set()

    def deleteItem(self, e=None):
        logger.debug('{0}: {1}'.format(self.itemSelected['_summary'], self.dtSelected))
        indx = 3
        if 'r' in self.itemSelected:
            indx, value = self.which(DELETE, self.dtSelected)
            logger.debug("{0}: {1}".format(indx, value))
            if not indx:
                self.tree.focus_set()
                return
            self.itemSelected['_dt'] = parse(self.dtSelected)
        else:
            # ans = askokcancel('Verify deletion', "Delete this item?", parent=self.tree)
            ans = self.confirm(
                title=_('Confirm'),
                prompt=_("Delete this item?"),
                parent=self.tree)
            if not ans:
                self.tree.focus_set()
                return
        loop.item_hsh = self.itemSelected
        loop.cmd_do_delete(indx)
        loop.loadData()
        self.updateAlerts()
        self.showView(row=self.topSelected)


    def editItem(self, e=None):
        logger.debug('{0}: {1}'.format(self.itemSelected['_summary'], self.dtSelected))
        choice = 3
        title = "etm tk"
        if 'r' in self.itemSelected:
            choice, value = self.which(EDIT, self.dtSelected)
            logger.debug("{0}: {1}".format(choice, value))
            if not choice:
                self.tree.focus_set()
                return
            self.itemSelected['_dt'] = parse(self.dtSelected)
        hsh_rev = hsh_cpy = None
        self.mode = 2  # replace
        if choice in [1, 2]:
            self.mode = 3  # new and replace - both newhsh and rephsh
            title = _("new item")
            hsh_cpy = deepcopy(self.itemSelected)
            hsh_rev = deepcopy(self.itemSelected)
            # we will be editing and adding hsh_cpy and replacing hsh_rev
            # hsh_cpy['i'] = uniqueId()

            dt = hsh_cpy['_dt'].replace(
                tzinfo=tzlocal()).astimezone(gettz(hsh_cpy['z']))
            dtn = dt.replace(tzinfo=None)

            if choice == 1:
                # this instance
                if '+' in hsh_rev and dtn in hsh_rev['+']:
                    hsh_rev['+'].remove(dtn)
                    if not hsh_rev['+'] and hsh_rev['r'] == 'l':
                        del hsh_rev['r']
                        del hsh_rev['_r']
                else:
                    hsh_rev.setdefault('-', []).append(dt)
                for k in ['_r', 'o', '+', '-']:
                    if k in hsh_cpy:
                        del hsh_cpy[k]
                hsh_cpy['s'] = dt

            elif choice == 2:
                # this and all subsequent instances
                tmp = []
                for h in hsh_rev['_r']:
                    if 'f' in h and h['f'] != u'l':
                        h['u'] = dt - ONEMINUTE
                    tmp.append(h)
                hsh_rev['_r'] = tmp
                if u'+' in hsh_rev:
                    tmp_rev = []
                    tmp_cpy = []
                    for d in hsh_rev['+']:
                        if d < dt:
                            tmp_rev.append(d)
                        else:
                            tmp_cpy.append(d)
                    hsh_rev['+'] = tmp_rev
                    hsh_cpy['+'] = tmp_cpy
                if u'-' in hsh_rev:
                    tmp_rev = []
                    tmp_cpy = []
                    for d in hsh_rev['-']:
                        if d < dt:
                            tmp_rev.append(d)
                        else:
                            tmp_cpy.append(d)
                    hsh_rev['-'] = tmp_rev
                    hsh_cpy['-'] = tmp_cpy
                hsh_cpy['s'] = dt
        else: # replace
            self.mode = 2
            hsh_rev = deepcopy(self.itemSelected)

        logger.debug("mode: {0}; newhsh: {1}; rephsh: {2}".format( self.mode, hsh_cpy is not None, hsh_rev is not None))
        changed = SimpleEditor(parent=self, newhsh=hsh_cpy, rephsh=hsh_rev,
                     options=loop.options, title=title).changed

        if changed:
            loop.loadData()
            self.updateAlerts()
            self.showView(row=self.topSelected)
        else:
            self.tree.focus_set()

    def editFile(self, e=None, file=None, config=False):
        if e is not None:
            logger.debug('event: {0}'.format(e))
            e = None
        relfile = relpath(file, self.options['etmdir'])
        logger.debug('file: {0}; config: {1}'.format(file, config))
        changed = SimpleEditor(parent=self, file=file, options=loop.options, title=relfile).changed
        if changed:
            logger.debug("config: {0}".format(config))
            if config:
                current_options = deepcopy(loop.options)
                (user_options, options, use_locale) = data.get_options(
                    d=loop.options['etmdir'])
                loop.options = options
                if options['calendars'] != current_options['calendars']:
                    self.updateCalendars()
            logger.debug("changed - calling loadData and updateAlerts")
            loop.loadData()
            self.updateAlerts()
            self.showView()

    def editData(self, e=None):
        initdir = self.options['datadir']
        fileops = {'defaultextension': '.txt',
                   'filetypes': [('text files', '.txt')],
                   'initialdir': initdir,
                   'initialfile': "",
                   'title': 'etmtk data files',
                   'parent': self}
        filename = askopenfilename(**fileops)
        if not (filename and os.path.isfile(filename)):
            return False
        self.editFile(e, file=filename)

    def finishItem(self, e=None):
        if not (self.itemSelected and self.itemSelected['itemtype'] in ['-', '+', '%']):
            return
        prompt = _("""\
Enter the completion date for the item or return an empty string to
use the current date. Relative dates and fuzzy parsing are supported.""")
        d = GetDateTime(parent=self, title=_('date'), prompt=prompt)
        chosen_day = d.value
        if chosen_day is None:
            return ()
        logger.debug('completion date: {0}'.format(chosen_day))
        loop.item_hsh = self.itemSelected
        loop.cmd_do_finish(chosen_day)
        loop.loadData()
        self.updateAlerts()
        self.showView(row=self.topSelected)


    def rescheduleItem(self, e=None):
        loop.item_hsh = item_hsh = self.itemSelected
        if self.dtSelected:
            loop.old_dt = old_dt = parse(self.dtSelected)
            title = _('rescheduling {0}').format(old_dt.strftime(
                rrulefmt))
        else:
            loop.old_dt = None
            title = _('scheduling an undated item')
        logger.debug('dtSelected: {0}'.format(self.dtSelected))
        prompt = _("""\
Enter the new date and time for the item or return an empty string to
use the current time. Relative dates and fuzzy parsing are supported.""")
        dt = GetDateTime(parent=self, title=title,
                         prompt=prompt)
        new_dt = dt.value
        if new_dt is None:
            return
        new_dtn = new_dt.astimezone(gettz(self.itemSelected['z'])).replace(tzinfo=None)
        logger.debug('rescheduled from {0} to {1}'.format(self.dtSelected, new_dtn))
        loop.cmd_do_reschedule(new_dtn)
        loop.loadData()
        self.updateAlerts()
        self.showView(row=self.topSelected)


    def showAlerts(self, e=None):
        t = _('remaining alerts for today')
        header = "{0:^7}\t{1:^7}\t{2:<8}{3:<26}".format(
            _('alert'),
            _('event'),
            _('type'),
            _('summary'))
        divider = '-' * 52
        if loop.alerts:
            # for alert in loop.alerts:
            s = '%s\n%s\n%s' % (
                header, divider, "\n".join(
                    ["{0:^7}\t{1:^7}\t{2:<8}{3:<26}".format(
                        x[1]['alert_time'], x[1]['_event_time'],
                        ", ".join(x[1]['_alert_action']),
                        utf8(x[1]['summary'][:26])) for x in loop.alerts]))
        else:
            s = _("none")
        self.textWindow(self, t, s)

    def agendaView(self, e=None):
        self.setView(AGENDA)

    def scheduleView(self, e=None):
        self.setView(SCHEDULE)

    def pathView(self, e=None):
        self.setView(PATHS)

    def keywordView(self, e=None):
        self.setView(KEYWORDS)

    def tagView(self, e=None):
        self.setView(TAGS)

    def setView(self, view, row=None):
        self.rowSelected = None
        logger.debug("view: {0}".format(view))
        self.view = view
        self.showView(row=row)

    def filterView(self, e, *args):
        self.depth2id = {}
        fltr = self.filterValue.get()
        cmd = "{0} {1}".format(
            self.vm_options[self.vm_opts.index(self.view)][1], fltr)
        self.mode = 'command'
        self.process_input(event=e, cmd=cmd)
        self.e.focus_set()


    def showView(self, e=None, row=None):
        self.depth2id = {}
        self.currentView.set(self.view)
        self.viewValue.set(self.viewLabel)
        fltr = self.filterValue.get()
        cmd = "{0} {1}".format(
            self.vm_options[self.vm_opts.index(self.view)][1], fltr)
        self.mode = 'command'
        self.process_input(event=e, cmd=cmd)
        if row:
            logger.debug("row: {0}".format(row))
            # self.tree.see(max(0, self.rowSelected))
            self.tree.yview(max(0, row - 1))
        # else:
        #     self.goHome()

    def showBusyTimes(self, event=None, chosen_day=None):
        prompt = _("""\
Busy times will be shown for the week containing the date you select.
Return an empty string for the current week. Relative dates and fuzzy
parsing are supported.""")
        d = GetDateTime(parent=self, title=_('date'), prompt=prompt)
        chosen_day = d.value
        logger.debug('chosen_day: {0}'.format(chosen_day))
        cal_regex = None
        # logger.debug('options: {0}'.format(loop.options))
        if loop.options['calendars']:
            cal_pattern = r'^%s' % '|'.join([x[2] for x in self.options['calendars'] if x[1]])
            cal_regex = re.compile(cal_pattern)
            logger.debug('cal_pattern: {0}'.format(cal_pattern))

        if chosen_day is None:
            return ()
            # chosen_day = self.today

        yn, wn, dn = chosen_day.isocalendar()
        self.prev_week = chosen_day - 7 * ONEDAY
        self.next_week = chosen_day + 7 * ONEDAY
        self.curr_week = chosen_day
        if dn > 1:
            days = dn - 1
        else:
            days = 0
        self.week_beg = weekbeg = chosen_day - days * ONEDAY
        weekend = chosen_day + (6 - days) * ONEDAY
        weekdays = []

        day = weekbeg
        busy_lst = []
        occasion_lst = []
        # matching = self.cal_regex is not None and self.default_regex is not None
        while day <= weekend:
            weekdays.append(fmt_weekday(day))
            isokey = day.isocalendar()
            # if isokey == iso_today:
            #     self.today_col = col_num

            if isokey in loop.occasions:
                bt = []
                for item in loop.occasions[isokey]:
                    it = list(item)
                    if cal_regex and not cal_regex.match(it[-1]):
                        continue
                    item = tuple(it)
                    bt.append(item)
                occasion_lst.append(bt)
            else:
                occasion_lst.append([])

            if isokey in loop.busytimes:
                bt = []
                for item in loop.busytimes[isokey][1]:
                    it = list(item)
                    if cal_regex and not cal_regex.match(it[-1]):
                        continue
                    item = tuple(it)
                    bt.append(item)
                busy_lst.append(bt)
            else:
                busy_lst.append([])
            day = day + ONEDAY

        ybeg = weekbeg.year
        yend = weekend.year
        mbeg = weekbeg.month
        mend = weekend.month
        if mbeg == mend:
            header = "{0} - {1}".format(
                fmt_dt(weekbeg, '%b %d'), fmt_dt(weekend, '%d, %Y'))
        elif ybeg == yend:
            header = "{0} - {1}".format(
                fmt_dt(weekbeg, '%b %d'), fmt_dt(weekend, '%b %d, %Y'))
        else:
            header = "{0} - {1}".format(
                fmt_dt(weekbeg, '%b %d, %Y'), fmt_dt(weekend, '%b %d, %Y'))
        header = leadingzero.sub('', header)

        lines = [_("Scheduled times for week {0}: {1}").format(wn, header)]
        ampm = loop.options['ampm']
        s1 = s2 = ''
        for i in range(7):
            times = []
            for tup in busy_lst[i]:
                t1 = max(7 * 60, tup[0])
                t2 = min(23 * 60, max(420, tup[1]))
                if t1 != t2:
                    t1h, t1m = (t1 // 60, t1 % 60)
                    t2h, t2m = (t2 // 60, t2 % 60)
                    if ampm:
                        if t1h == 12:
                            s1 = 'pm'
                        elif t1h > 12:
                            t1h -= 12
                            s1 = 'pm'
                        else:
                            s1 = 'am'
                        if t2h == 12:
                            s2 = 'pm'
                        elif t2h > 12:
                            t2h -= 12
                            s2 = 'pm'
                        else:
                            s2 = 'am'

                    T1 = "%d:%02d%s" % (t1h, t1m, s1)
                    T2 = "%d:%02d%s" % (t2h, t2m, s2)

                    times.append("%s-%s" % (T1, T2))
            if times:
                lines.append("   %s: %s" % (weekdays[i], "; ".join(times)))
        s = "\n".join(lines)
        self.textWindow(parent=self, title=_('busy times'), prompt=s)

    # noinspection PyShadowingNames
    def showCalendar(self, e=None):
        cal_year = 0
        opts = loop.options
        cal_pastcolor = '#FFCCCC'
        cal_currentcolor = '#FFFFCC'
        cal_futurecolor = '#99CCFF'

        def showYear(x=0):
            global cal_year
            if x:
                cal_year += x
            else:
                cal_year = 0
            cal = "\n".join(calyear(cal_year, options=opts))
            if cal_year > 0:
                col = cal_futurecolor
            elif cal_year < 0:
                col = cal_pastcolor
            else:
                col = cal_currentcolor
            t.configure(bg=col)
            t.delete("0.0", END)
            t.insert("0.0", cal)

        win = Toplevel()
        win.title(_("Calendar"))
        f = Frame(win)
        # pack the button first so that it doesn't disappear with resizing
        b = Button(win, text=_('OK'), width=10, command=win.destroy, default='active')
        b.pack(side='bottom', fill=tkinter.NONE, expand=0, pady=0)
        win.bind('<Return>', (lambda e, b=b: b.invoke()))
        win.bind('<Escape>', (lambda e, b=b: b.invoke()))

        t = ReadOnlyText(f, wrap="word", padx=2, pady=2, bd=2, relief="sunken",
                         font=tkFont.Font(family="Lucida Sans Typewriter"),
                         # height=14,
                         # width=52,
                         takefocus=False)
        win.bind('<Left>', (lambda e: showYear(-1)))
        win.bind('<Right>', (lambda e: showYear(1)))
        win.bind('<space>', (lambda e: showYear()))
        showYear()
        t.pack(side='left', fill=tkinter.BOTH, expand=1, padx=0, pady=0)
        ysb = ttk.Scrollbar(f, orient='vertical', command=t.yview, width=8)
        ysb.pack(side='right', fill=tkinter.Y, expand=0, padx=0, pady=0)
        # t.configure(state="disabled", yscroll=ysb.set)
        t.configure(yscroll=ysb.set)
        f.pack(padx=2, pady=2, fill=tkinter.BOTH, expand=1)
        win.focus_set()
        win.grab_set()
        win.transient(self)
        win.wait_window(win)

    def newCommand(self, e=None):
        newcommand = self.newValue.get()
        self.newValue.set(self.newLabel)
        print('newCommand', newcommand)

    def help(self, event=None):
        res = self.menutree.showMenu("_")
        # self.textWindow(parent=self, title='etm', prompt=res, modal=False)
        nb = NotebookWindow(self, title="etm Help", modal=False)
        nb.addTab(label=_("Shortcuts"), content=res)
        self.update_idletasks()
        nb.addTab(label=_("Overview"), content=OVERVIEW)
        nb.addTab(label=_("Types"), content=ITEMTYPES)
        nb.addTab(label=_("@ keys"), content=ATKEYS)
        nb.addTab(label=_("Dates"), content=DATES)
        nb.addTab(label=_("Preferences"), content=PREFERENCES)
        nb.addTab(label=_("Reports"), content=REPORTS)

    def about(self, event=None):
        res = loop.do_v("")
        self.textWindow(parent=self, title='etm', prompt=res, modal=False)

    def checkForUpdate(self, event=None):
        res = checkForNewerVersion()[1]
        self.textWindow(parent=self, title='etm', prompt=res)

    def showChanges(self, event=None):
        if self.itemSelected:
            f = self.itemSelected['fileinfo'][0]
            fn = " -f {0}".format(os.path.join(self.options['datadir'], f))
            title = _("Showing changes for {0}.").format(f)

        else:
            fn = ""
            title = _("Showing changes for all files.")

        prompt = _("""\
{0}

If an item is selected, changes will be shown for the file containing
the item. Otherwise, changes will be shown for all files.

Enter an integer number of changes to display
or 0 to display all changes.""").format(title)
        depth = GetInteger(
            parent=self,
            title=_("Changes"),
            prompt=prompt, opts=[0], default=10).value
        if depth is None:
            return ()
        if depth == 0:
            # all changes
            numstr = ""
        else:
            numstr = "-l {0}".format(depth)
        command = loop.options['hg_history'].format(
            repo=loop.options['datadir'],
            numchanges=numstr, rev="{rev}", desc="{desc}") + fn
        logger.debug('history command: {0}'.format(command))
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True,
                             universal_newlines=True).stdout.read()
        self.textWindow(parent=self, title=title, prompt=str(p))

    def focus_next_window(self, event):
        event.widget.tk_focusNext().focus()
        return "break"

    def goHome(self, event=None):
        if self.view == SCHEDULE:
            today = get_current_time().date()
            self.scrollToDate(today)
        else:
            self.tree.focus_set()
            self.tree.focus(1)
            self.tree.selection_set(1)
            self.tree.yview(0)
        return 'break'

    def OnSelect(self, event=None):
        """
        Tree row has gained selection.
        """
        item = self.tree.selection()[0]
        self.rowSelected = int(item)
        type_chr = self.tree.item(item)['text'][0]
        uuid, dt, hsh = self.getInstance(item)
        # self.l.configure(state="normal")
        self.l.delete("0.0", END)
        if uuid is not None:
            self.em.configure(state="normal")
            isRepeating = ('r' in hsh and dt)
            if isRepeating:
                item = "{0} {1}".format(_('selected'), dt)
                self.em["menu"].entryconfig(1, label="{0} ...".format(self.em_opts[1]))
                self.em["menu"].entryconfig(2, label="{0} ...".format(self.em_opts[2]))
            else:
                self.em["menu"].entryconfig(1, label=self.em_opts[1])
                self.em["menu"].entryconfig(2, label=self.em_opts[2])
                item = _('selected')
            isUnfinished = (type_chr in ['-', '+', '%'])
            hasLink = ('g' in hsh and hsh['g'])
            l1 = hsh['fileinfo'][1]
            l2 = hsh['fileinfo'][2]
            if l1 == l2:
                lines = "{0} {1}".format(_('line'), l1)
            else:
                lines = "{0} {1}-{2}".format(_('lines'), l1, l2)
            self.filetext = filetext = "{0}, {1}".format(hsh['fileinfo'][0],
                                                      lines)
            if 'errors' in hsh and hsh['errors']:
                text = "{1}\n\n{2}: {3}\n\n{4}: {5}".format(item, hsh['entry'].lstrip(), _("Errors"), hsh['errors'],  _("file"), filetext)
            else:
                text = "{1}\n\n{2}: {3}".format(item, hsh['entry'].lstrip(), _("file"), filetext)
            # self.nm["menu"].entryconfig(2, state='normal')
            for i in [0, 1, 2, 4]: # everything except finish
                self.em["menu"].entryconfig(i, state='normal')
                # self.em.configure(state="normal")
            if isUnfinished:
                self.em["menu"].entryconfig(3, state='normal')
            else:
                self.em["menu"].entryconfig(3, state='disabled')
            if hasLink:
                self.em["menu"].entryconfig(5, state='normal')
            else:
                self.em["menu"].entryconfig(5, state='disabled')
            self.uuidSelected = uuid
            self.itemSelected = hsh
            self.dtSelected = dt
            # logger.debug(('selected: {0}'.format(hsh)))
        else:
            self.em.configure(state="disabled")
            text = ""
            # self.nm["menu"].entryconfig(2, state='disabled')
            for i in range(5):
                self.em["menu"].entryconfig(i, state='disabled')
            self.itemSelected = None
            self.uuidSelected = None
            self.dtSelected = None
        r = self.tree.identify_row(1)
        logger.debug("top row: '{0}' {1}".format(r, type(r)))
        if r:
            self.topSelected = int(r)
        else:
            self.topSelected = 1

        logger.debug("top: {3}; row: '{0}'; uuid: '{1}'; instance: '{2}'".format(self.rowSelected, self.uuidSelected, self.dtSelected,  self.topSelected)); self.l.insert(INSERT, text)
        return "break"

    def OnActivate(self, event):
        """
        Return pressed with tree row selected
        """
        item = self.tree.selection()[0]
        uuid, dt, hsh = self.getInstance(item)
        if uuid is not None:
            self.editItem()
        return "break"

    def OnDoubleClick(self, event):
        """
        Double click on tree row
        """
        self.update_idletasks()

        item = self.tree.identify('item', event.x, event.y)
        uuid, dt, hsh = self.getInstance(item)
        if uuid is not None:
            self.editItem()
        return "break"

    def getInstance(self, item):
        instance = self.count2id[item]
        if instance is None:
            return None, None, None
        uuid, dt = self.count2id[item].split("::")
        hsh = loop.uuid2hash[uuid]
        logger.debug('item: {0}; uuid: {1}, dt: {2}'.format(item, uuid, dt))
        return uuid, dt, hsh

    def updateClock(self):
        # print('updateClock', loop.options)
        self.now = get_current_time()
        nxt = (60 - self.now.second) * 1000 - self.now.microsecond // 1000
        self.after(nxt, self.updateClock)
        nowfmt = "{0} {1}".format(
            s2or3(self.now.strftime(loop.options['reprtimefmt']).lower()),
            s2or3(self.now.strftime("%a %b %d %Z")))
        nowfmt = leadingzero.sub("", nowfmt)
        self.currentTime.set("{0}".format(nowfmt))
        today = self.now.date()
        newday = (today != self.today)
        self.today = today

        new, modified, deleted = get_changes(
            self.options, loop.file2lastmodified)
        if newday or new or modified or deleted:
            logger.debug('refreshing view: newday or changed')
            loop.loadData()
            self.showView()

        self.updateAlerts()

        if self.actionTimer.timer_status != STOPPED:
            self.timerStatus.set(self.actionTimer.get_time())
            if self.actionTimer.timer_minutes >= 1:
                if (self.options['action_interval'] and self.actionTimer.timer_minutes % loop.options['action_interval'] == 0):
                    logger.debug('action_minutes trigger: {0} {1}'.format(self.actionTimer.timer_minutes, self.actionTimer.timer_status))
                    if self.actionTimer.timer_status == 'running':
                        if ('running' in loop.options['action_timer'] and
                                loop.options['action_timer']['running']):
                            tcmd = loop.options['action_timer']['running']
                            logger.debug('running: {0}'.format(tcmd))
                            # process.startDetached(tcmd)
                            subprocess.call(tcmd, shell=True)

                    elif self.actionTimer.timer_status == 'paused':
                        if ('paused' in loop.options['action_timer'] and
                                loop.options['action_timer']['paused']):
                            tcmd = loop.options['action_timer']['paused']
                            # process.startDetached(tcmd)
                            logger.debug('running: {0}'.format(tcmd))
                            subprocess.call(tcmd, shell=True)

        logger.debug("next update in {0} milliseconds".format(nxt))

    def updateAlerts(self):
        self.update_idletasks()
        logger.debug('updateAlerts 1: {0}'.format(len(loop.alerts)))
        if loop.alerts:
            curr_minutes = datetime2minutes(self.now)
            td = -1
            while td < 0 and loop.alerts:
                td = loop.alerts[0][0] - curr_minutes
                logger.debug('curr_minutes: {0}; td: {1}'.format(
                    curr_minutes, td))
                if td < 0:
                    loop.alerts.pop(0)
            if td == 0:
                if ('alert_wakecmd' in loop.options and
                        loop.options['alert_wakecmd']):
                    cmd = loop.options['alert_wakecmd']
                    subprocess.call(cmd, shell=True)
                while td == 0:
                    hsh = loop.alerts[0][1]
                    loop.alerts.pop(0)
                    actions = hsh['_alert_action']
                    if 's' in actions:
                        if ('alert_soundcmd' in self.options and
                                self.options['alert_soundcmd']):
                            scmd = expand_template(
                                self.options['alert_soundcmd'], hsh)
                            subprocess.call(scmd, shell=True)
                        else:
                            self.textWindow(self,
                                "etm", _("""\
A sound alert failed. The setting for 'alert_soundcmd' is missing from \
your etmtk.cfg."""))
                    if 'd' in actions:
                        if ('alert_displaycmd' in self.options and
                                self.options['alert_displaycmd']):
                            dcmd = expand_template(
                                self.options['alert_displaycmd'], hsh)
                            subprocess.call(dcmd, shell=True)
                        else:
                            self.textWindow(self,
                                "etm", _("""\
A display alert failed. The setting for 'alert_displaycmd' is missing \
from your etmtk.cfg."""))
                    if 'v' in actions:
                        if ('alert_voicecmd' in self.options and
                                self.options['alert_voicecmd']):
                            vcmd = expand_template(
                                self.options['alert_voicecmd'], hsh)
                            subprocess.call(vcmd, shell=True)
                        else:
                            self.textWindow(self,
                                "etm", _("""\
An email alert failed. The setting for 'alert_voicecmd' is missing from \
your etmtk.cfg."""))
                    if 'e' in actions:
                        missing = []
                        for field in [
                            'smtp_from',
                            'smtp_id',
                            'smtp_pw',
                            'smtp_server',
                            'smtp_to']:
                            if not self.options[field]:
                                missing.append(field)
                        if missing:
                            self.textWindow(self,
                                "etm", _("""\
An email alert failed. Settings for the following variables are missing \
from your etmtk.cfg: %s.""" % ", ".join(["'%s'" % x for x in missing])))
                        else:
                            subject = hsh['summary']
                            message = expand_template(
                                self.options['email_template'], hsh)
                            arguments = hsh['_alert_argument']
                            recipients = [str(x).strip() for x in arguments[0]]
                            if len(arguments) > 1:
                                attachments = [str(x).strip()
                                               for x in arguments[1]]
                            else:
                                attachments = []
                            if subject and message and recipients:
                                send_mail(
                                    smtp_to=recipients,
                                    subject=subject,
                                    message=message,
                                    files=attachments,
                                    smtp_from=self.options['smtp_from'],
                                    smtp_server=self.options['smtp_server'],
                                    smtp_id=self.options['smtp_id'],
                                    smtp_pw=self.options['smtp_pw'])
                    if 'm' in actions:
                        MessageWindow(
                            self,
                            title=expand_template('!summary!', hsh),
                            prompt=expand_template(
                                self.options['alert_template'], hsh))

                    if 't' in actions:
                        missing = []
                        for field in [
                            'sms_from',
                            'sms_message',
                            'sms_phone',
                            'sms_pw',
                            'sms_server',
                            'sms_subject']:
                            if not self.options[field]:
                                missing.append(field)
                        if missing:
                            self.textWindow(self,
                                "etm", _("""\
A text alert failed. Settings for the following variables are missing \
from your 'emt.cfg': %s.""" % ", ".join(["'%s'" % x for x in missing])))
                        else:
                            message = expand_template(
                                self.options['sms_message'], hsh)
                            subject = expand_template(
                                self.options['sms_subject'], hsh)
                            arguments = hsh['_alert_argument']
                            if arguments:
                                sms_phone = ",".join([str(x).strip() for x in
                                                      arguments[0]])
                            else:
                                sms_phone = self.options['sms_phone']
                            if message:
                                send_text(
                                    sms_phone=sms_phone,
                                    subject=subject,
                                    message=message,
                                    sms_from=self.options['sms_from'],
                                    sms_server=self.options['sms_server'],
                                    sms_pw=self.options['sms_pw'])
                    if 'p' in actions:
                        arguments = hsh['_alert_argument']
                        proc = str(arguments[0][0]).strip()
                        cmd = expand_template(proc, hsh)
                        subprocess.call(cmd, shell=True)

                    if not loop.alerts:
                        break
                    td = loop.alerts[0][0] - curr_minutes

        logger.debug('updateAlerts 2: {0}'.format(len(loop.alerts)))
        self.pendingAlerts.set(len(loop.alerts))
        if len(loop.alerts) > 0:
            self.pending.configure(state="normal")
        else:
            self.pending.configure(state="disabled")

    # def prev_history(self, event):
    #     """
    #     Replace input with the previous history item.
    #     """
    #     print('up')
    #     if self.index >= 1:
    #         self.index -= 1
    #         self.e.delete(0, END)
    #         self.e.insert(0, self.history[self.index])
    #     return 'break'
    #
    # def next_history(self, event):
    #     """
    #     Replace input with the next history item.
    #     """
    #     print('down')
    #     if self.index + 1 < len(self.history):
    #         self.index += 1
    #         self.e.delete(0, END)
    #         self.e.insert(0, self.history[self.index])
    #     return 'break'

    def textWindow(self, parent, title=None, prompt=None, modal=True):
        d = TextDialog(parent, title=title, prompt=prompt, modal=modal)


    def goToDate(self, e=None):
        """


        :param e:
        :return:
        """
        prompt = _("""\
Return an empty string for the current date or a date to be parsed.
Relative dates and fuzzy parsing are supported.""")
        if self.view != self.vm_options[1][0]:
            self.view = self.vm_options[1][0]
            self.showView()
        d = GetDateTime(parent=self, title=_('date'), prompt=prompt)
        value = d.value
        logger.debug('value: {0}'.format(value))
        if value is not None:
            self.scrollToDate(value.date())
        return "break"

    def startActionTimer(self, event=None):
        """

        :param event:
        :return:
        """
        if self.actionTimer.timer_status == 'stopped':
            if self.uuidSelected:
                nullok = True
                # options = {'nullok': True}
                prompt = _("""\
    Enter a summary for the new action timer or return an empty string
    to create a timer based on the selected item.""")
            else:
                nullok = False
                # options = {'nullok': False}
                prompt = _("""\
    Enter a summary for the new action timer.""")
            options = {'nullok': nullok}
            value = GetString(parent=self, title=_('action timer'),  prompt=prompt, opts=options).value
            # value = d.value
            logger.debug('value: {0}'.format(value))
            if value is None:
                return "break"
            # if nullok and not value:
            #     return "break"
            if value:
                self.timerItem = None
                hsh = {'_summary': value}
            elif nullok:
                self.timerItem = self.uuidSelected
                # Based on item, 'entry' will be in hsh
                hsh = loop.uuid2hash[self.uuidSelected]
                if hsh['itemtype'] == '~' and hsh['s'].date() == datetime.today():
                    logger.debug('an action recorded today')
            else:
                # shouldn't happen
                return "break"
            logger.debug('item: {0}'.format(hsh))
            self.nm["menu"].entryconfig(1, label=_("toggle timer"))
            self.actionTimer.timer_start(hsh)
            if ('running' in loop.options['action_timer'] and
                    loop.options['action_timer']['running']):
                tcmd = loop.options['action_timer']['running']
                logger.debug('command: {0}'.format(tcmd))
                # process.startDetached(tcmd)
                subprocess.call(tcmd, shell=True)
        elif self.actionTimer.timer_status in [PAUSED, RUNNING]:
            self.actionTimer.timer_toggle()
            if (self.actionTimer.timer_status == RUNNING and 'running' in loop.options['action_timer'] and loop.options['action_timer']['running']):
                tcmd = loop.options['action_timer']['running']
                logger.debug('command: {0}'.format(tcmd))
                # process.startDetached(tcmd)
                subprocess.call(tcmd, shell=True)
            elif (self.actionTimer.timer_status == PAUSED and 'paused' in loop.options['action_timer'] and loop.options['action_timer']['paused']):
                tcmd = loop.options['action_timer']['paused']
                logger.debug('command: {0}'.format(tcmd))
                # process.startDetached(tcmd)
                subprocess.call(tcmd, shell=True)

        self.timerStatus.set(self.actionTimer.get_time())
        return "break"

    def stopTimer(self, event=None):
        if self.actionTimer.timer_status not in [RUNNING, PAUSED]:
            logger.info('stopping already stopped timer')
            return "break"
        self.timerStatus.set(self.actionTimer.get_time())


    def gettext(self, event=None):
        s = self.e.get()
        if s is not None:
            return s
        else:
            return ''

    def cleartext(self, event=None):
        if self.e.get():
            self.e.delete(0, END)
            self.showView()
        return 'break'

    def process_input(self, event=None, cmd=None):
        """
        This is called whenever enter is pressed in the input field.
        Action depends upon comand_mode.
        Append input to history, process it and show the result in output.
        :param event:
        :param cmd:
        """
        # if not cmd:
        #     cmd = self.e.get().strip()

        if not cmd:
            return True

        if self.mode == 'command':
            cmd = cmd.strip()
            if cmd[0] == 'w':
                self.editWhich()
                return ()
            elif cmd[0] in ['r', 't']:
                # simple command history for report commands
                if cmd in self.history:
                    self.history.remove(cmd)
                self.history.append(cmd)
                self.index = len(self.history) - 1
            else:
                parts = cmd.split(' ')
                if len(parts) == 2:
                    try:
                        i = int(parts[0])
                    except:
                        i = None
                    if i:
                        parts.pop(0)
                        parts.append(str(i))
                        cmd = " ".join(parts)
            try:
                res = loop.do_command(cmd)
            except:
                return _('could not process command "{0}"').format(cmd)

        elif self.mode == 'edit':
            print('edit', cmd)
            res = loop.cmd_do_edit(cmd)

        elif self.mode == 'delete':
            print('deleted', cmd)
            loop.cmd_do_delete(cmd)
            res = ''

        elif self.mode == 'finish':
            print('finish', cmd)
            loop.cmd_do_finish(cmd)
            res = ''

        elif self.mode == 'new_date':
            print('date', cmd)
            res = loop.new_date(cmd)

        if not res:
            res = _('command "{0}" returned no output').format(cmd)
            # MessageWindow(self, 'info', res)
            self.clearTree()
            return ()

        if type(res) == dict:
            self.showTree(res, event=event)
        else:
            # not a hash => not a tree
            self.textWindow(self, title='etm', prompt=res)
            return 0

    def expand2Depth(self, event=None):
        prompt = _("""\
Enter an integer depth to expand branches
or 0 to expand all branches completely.""")
        depth = GetInteger(
            parent=self,
            title=_("depth"), prompt=prompt, opts=[0], default=0).value
        if depth is None:
            return ()
        maxdepth = max([k for k in self.depth2id])
        logger.debug('expand2Depth: {0}/{1}'.format(depth, maxdepth))
        if depth == 0:
            # expand all
            for k in self.depth2id:
                for item in self.depth2id[k]:
                    self.tree.item(item, open=True)
        else:
            depth -= 1
            for i in range(depth):
                for item in self.depth2id[i]:
                    self.tree.item(item, open=True)
            for i in range(depth, maxdepth+1):
                for item in self.depth2id[i]:
                    self.tree.item(item, open=False)
                # return('break')

    def scrollToDate(self, date):
        # only makes sense for schedule
        logger.debug("SCHEDULE: {0}; date: {1}".format(self.view == SCHEDULE, date))
        if self.view != SCHEDULE or date not in loop.prevnext:
            return ()
        active_date = loop.prevnext[date][1]
        if active_date not in self.date2id:
            return ()
        uid = self.date2id[active_date]
        self.scrollToId(uid)

    def scrollToId(self, uid):
        self.update_idletasks()
        self.tree.focus_set()
        self.tree.focus(uid)
        self.tree.selection_set(uid)
        self.tree.yview(int(uid) - 1)

    def showTree(self, tree, event=None):
        self.date2id = {}
        self.clearTree()
        self.count = 0
        self.count2id = {}
        self.addToTree(u'', tree[self.root], tree)
        loop.count2id = self.count2id
        # self.l.configure(state="normal")
        self.l.delete("0.0", END)
        # self.l.configure(state="disabled")
        if event is None:
            # view selected from menu
            self.goHome()

    def clearTree(self):
        """
        Remove all items from the tree
        """
        for child in self.tree.get_children():
            self.tree.delete(child)

    def addToTree(self, parent, elements, tree, depth=0):
        max_depth = 100
        for text in elements:
            self.count += 1
            # print('text', text)
            # text is a key in the element (tree) hash
            # these keys are (parent, item) tuples
            if text in tree:
                # this is a branch
                item = " " + text[1]  # this is the label of the parent
                children = tree[text]  # this are the children tuples of item
                oid = self.tree.insert(parent, 'end', iid=self.count, text=item,
                                       open=(depth <= max_depth))
                # oid = self.tree.insert(parent, 'end', text=item, open=True)
                # print(self.count, oid, depth, item)
                self.depth2id.setdefault(depth, set([])).add(oid)
                # recurse to get children
                self.count2id[oid] = None
                self.addToTree(oid, children, tree, depth=depth + 1)
            else:
                # this is a leaf
                if len(text[1]) == 4:
                    uuid, item_type, col1, col2 = text[1]
                    dt = ''
                else:  # len 5 day view with datetime appended
                    uuid, item_type, col1, col2, dt = text[1]
                # logger.debug("leaf: {0}, {1}".format(item_type, tstr2SCI[item_type][1]))

                # This hack avoids encoding issues under python 2
                col1 = "{0} ".format(id2Type[item_type]) + col1

                if type(col2) == int:
                    col2 = '%s' % col2
                else:
                    col2 = s2or3(col2)

                oid = self.tree.insert(parent, 'end', iid=self.count, text=col1, open=(depth <= max_depth), value=[col2], tags=(item_type))
                # oid = self.tree.insert(parent, 'end', text=col1, open=True, value=[col2])
                # print(self.count, oid)
                # print(self.count, oid, depth, col1, depth<=max_depth)
                self.count2id[oid] = "{0}::{1}".format(uuid, dt)
                if dt:
                    # print('trying to parse', dt)
                    try:
                        d = parse(dt[:10]).date()
                        if d not in self.date2id:
                            self.date2id[d] = parent
                    except:
                        print('could not parse', dt)
                        print(text)


loop = None

log_levels = {
    '1': logging.DEBUG,
    '2': logging.INFO,
    '3': logging.WARN,
    '4': logging.ERROR,
    '5': logging.CRITICAL
}

def main(dir=None):  # debug, info, warn, error, critical
    global loop
    etmdir = ''
    # For testing override etmdir:
    if dir is not None:
        etmdir = dir
    init_localization()
    (user_options, options, use_locale) = data.get_options(etmdir)
    loop = data.ETMCmd(options=options)
    loop.tkversion = tkversion
    # app = App(path='/Users/dag/etm-tk')
    app = App()
    app.mainloop()

if __name__ == "__main__":
    setup_logging('3')
    main()
