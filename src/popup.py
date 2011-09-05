"""
Functions for displaying popups in the interface.

Based on code from the arm project, developed by Damian Johnson under GPLv3
(www.atagar.com - atagar@torproject.org)
"""

import curses

import version
from panel import *
from controller import *
from tools import *

class PopupManager():
    def __init__(self, controller):
        self.controller = controller

    def prepare(self, height= -1, width= -1, top=0, left=0):
      """
      Preparation for displaying a popup. This creates a popup with a valid
      subwindow instance. If that's successful then the curses lock is acquired
      and this returns a tuple of the...
      (popup, draw width, draw height)
      Otherwise this leaves curses unlocked and returns None.
      
      Arguments:
        height      - maximum height of the popup
        width       - maximum width of the popup
        top         - top position, relative to the sticky content
        left        - left position from the screen
      """

      popup = Panel(self.controller.getScreen(), "popup", top, left, height, width)
      popup.setVisible(True)

      # Redraws the popup to prepare a subwindow instance. If none is spawned then
      # the panel can't be drawn (for instance, due to not being visible).
      popup.redraw(True)
      if popup.win != None:
        CURSES_LOCK.acquire()
        return (popup, popup.maxX - 1, popup.maxY)
      else: return (None, 0, 0)

    def finalize(self):
      """
      Cleans up after displaying a popup, releasing the cureses lock and redrawing
      the rest of the display.
      """

      self.controller.requestRedraw()
      CURSES_LOCK.release()

    def inputPrompt(self, msg, initialValue=""):
      """
      Prompts the user to enter a string on the control line (which usually
      displays the page number and basic controls).
      
      Arguments:
        msg          - message to prompt the user for input with
        initialValue - initial value of the field
      """

      CURSES_LOCK.acquire()
      toolBarPanel = self.controller.getToolBar()
      toolBarPanel.setMessage(msg)
      toolBarPanel.redraw(True)
      userInput = toolBarPanel.getstr(0, len(msg), initialValue)
      self.controller.setToolBarMessage()
      CURSES_LOCK.release()
      return userInput

    def showMsg(self, msg, maxWait= -1, attr=curses.A_STANDOUT):
      """
      Displays a single line message on the control line for a set time. Pressing
      any key will end the message. This returns the key pressed.
      
      Arguments:
        msg     - message to be displayed to the user
        maxWait - time to show the message, indefinite if -1
        attr    - attributes with which to draw the message
      """

      CURSES_LOCK.acquire()
      self.controller.setToolBarMessage(msg, attr, True)

      if maxWait == -1: curses.cbreak()
      else: curses.halfdelay(maxWait * 10)
      keyPress = self.controller.getScreen().getch()
      self.controller.setToolBarMessage()
      CURSES_LOCK.release()

      return keyPress

    def showAboutPopup(self):
      """
      Presents a popup with author and version information.
      """

      popup, _, height = self.prepare(9, 80)
      if not popup: return

      try:
        popup.win.box()
        popup.addstr(0, 0, "About:", curses.A_STANDOUT)
        popup.addstr(1, 2, "shadow-cli, version %s (released %s)" % (version.VERSION, version.RELEASE_DATE), curses.A_BOLD)
        popup.addstr(2, 4, "Written by Rob Jansen (jansen@cs.umn.edu)")
        popup.addstr(3, 4, "shadow.cs.umn.edu, github.com/shadow/shadow-cli")
        popup.addstr(5, 2, "Released under the GPL v3 (http://www.gnu.org/licenses/gpl.html)")
        popup.addstr(7, 2, "Press any key...")
        popup.win.refresh()

        curses.cbreak()
        self.controller.getScreen().getch()
      finally: self.finalize()
      
    def showHelpPopup(self):
      """
      Presents a popup with instructions for the current page's hotkeys. This
      returns the user input used to close the popup. If the popup didn't close
      properly, this is an arrow, enter, or scroll key then this returns None.
      """
      
      popup, _, height = self.prepare(9, 80)
      if not popup: return
      
      exitKey = None
      try:
        pagePanels = self.controller.getDisplayPanels()
        
        helpOptions = []
        for entry in pagePanels:
          helpOptions += entry.getHelp()
        helpOptions.append(("a", "about shadow-cli", None))
        
        # test doing afterward in case of overwriting
        popup.win.box()
        popup.addstr(0, 0, "Page %i Commands:" % (self.controller.getPage() + 1), curses.A_STANDOUT)
        
        for i in range(len(helpOptions)):
          if i / 2 >= height - 2: break
          
          # draws entries in the form '<key>: <description>[ (<selection>)]', for
          # instance...
          # u: duplicate log entries (hidden)
          key, description, selection = helpOptions[i]
          if key: description = ": " + description
          row = (i / 2) + 1
          col = 2 if i % 2 == 0 else 41
          
          popup.addstr(row, col, key, curses.A_BOLD)
          col += len(key)
          popup.addstr(row, col, description)
          col += len(description)
          
          if selection:
            popup.addstr(row, col, " (")
            popup.addstr(row, col + 2, selection, curses.A_BOLD)
            popup.addstr(row, col + 2 + len(selection), ")")
        
        # tells user to press a key if the lower left is unoccupied
        if len(helpOptions) < 13 and height == 9:
          popup.addstr(7, 2, "Press any key...")
        
        popup.win.refresh()
        curses.cbreak()
        exitKey = self.controller.getScreen().getch()
      finally: self.finalize()
      
      if not isSelectionKey(exitKey) and \
        not isScrollKey(exitKey) and \
        not exitKey in (curses.KEY_LEFT, curses.KEY_RIGHT):
        return exitKey
      else: return None

    def showMenu(self, title, options, oldSelection):
      """
      Provides menu with options laid out in a single column. User can cancel
      selection with the escape key, in which case this proives -1. Otherwise this
      returns the index of the selection.
      
      Arguments:
        title        - title displayed for the popup window
        options      - ordered listing of options to display
        oldSelection - index of the initially selected option (uses the first
                       selection without a carrot if -1)
      """

      maxWidth = max(map(len, options)) + 9
      popup, _, _ = self.prepare(len(options) + 2, maxWidth)
      if not popup: return
      key, selection = 0, oldSelection if oldSelection != -1 else 0

      try:
        curses.cbreak()   # wait indefinitely for key presses (no timeout)

        while not isSelectionKey(key):
          popup.win.erase()
          popup.win.box()
          popup.addstr(0, 0, title, curses.A_STANDOUT)

          for i in range(len(options)):
            label = options[i]
            format = curses.A_STANDOUT if i == selection else curses.A_NORMAL
            tab = "> " if i == oldSelection else "  "
            popup.addstr(i + 1, 2, tab)
            popup.addstr(i + 1, 4, " %s " % label, format)

          popup.win.refresh()

          key = self.controller.getScreen().getch()
          if key == curses.KEY_UP: selection = max(0, selection - 1)
          elif key == curses.KEY_DOWN: selection = min(len(options) - 1, selection + 1)
          elif key == 27: selection, key = -1, curses.KEY_ENTER # esc - cancel
      finally:
        self.finalize()

      return selection

