"""
Simple one line panel that holds a label.

Taken from the arm project, developed by Damian Johnson under GPLv3
(www.atagar.com - atagar@torproject.org)
"""

import curses

from core import panel

class LabelPanel(panel.Panel):
  """
  Panel that just displays a single line of text.
  """
  
  def __init__(self, stdscr):
    panel.Panel.__init__(self, stdscr, "msg", 0, height=1)
    self.msgText = ""
    self.msgAttr = curses.A_NORMAL
  
  def setMessage(self, msg, attr = None):
    """
    Sets the message being displayed by the panel.
    
    Arguments:
      msg  - string to be displayed
      attr - attribute for the label, normal text if undefined
    """
    
    if attr == None: attr = curses.A_NORMAL
    self.msgText = msg
    self.msgAttr = attr
  
  def draw(self, width, height):
    self.addstr(0, 0, self.msgText, self.msgAttr)