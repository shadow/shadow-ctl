"""
  Based on code from the arm project, developed by Damian Johnson under GPLv3
  (www.atagar.com - atagar@torproject.org)
"""

import curses
import threading

from panel import *
from popup import *

REFRESH_RATE = 1

class Controller:
  """
  Tracks the global state of the interface
  """

  def __init__(self, stdscr, defaultToolBarMessage):
    """
    Creates a new controller instance. Panel lists are ordered as they appear,
    top to bottom on the page.
    
    Arguments:
      stdscr                   - curses window
      defaultToolBarMessage    - default message for the toolbar
    """

    self._screen = stdscr
    self._stickyPanels = []
    self._pagePanels = []
    self._page = 0
    self._isPaused = False
    self._forceRedraw = False
    self._isDone = False
    self._lastDrawn = 0
    
    # add sticky title
    un = os.uname()
    head = LabelPanel(stdscr)
    head.setMessage("shadow-cli on %s (%s %s)" % (un[1], un[0], un[2]), curses.A_BOLD)
    self.addStickyPanel(head)
    head.setVisible(True)

    self._toolBar = LabelPanel(stdscr)
    self._toolBarMsg = defaultToolBarMessage
    self.setToolBarMessage()
    
    # toolbar is always shown on the top line
    self.addStickyPanel(self._toolBar)
    self._toolBar.setVisible(True)
    
    # popup manager for displaying messages on the controller toolbar
    self._popupManager = PopupManager(self)

  def getScreen(self):
    """
    Provides our curses window.
    """

    return self._screen

  def getPopupManager(self):
    return self._popupManager

  def addStickyPanel(self, panel):
    """
    panel - shown at the top of each page
    """
    
    self._stickyPanels.append(panel)
    
  def addPagePanels(self, page):
    """
    page   - list of the panels for this page
    """
    self._pagePanels.append(page)
    
  def getPageCount(self):
    """
    Provides the number of pages the interface has. This may be zero if all
    page panels have been disabled.
    """

    return len(self._pagePanels)

  def getPage(self):
    """
    Provides the number belonging to this page. Page numbers start at zero.
    """

    return self._page

  def setPage(self, pageNumber):
    """
    Sets the selected page, raising a ValueError if the page number is invalid.
    
    Arguments:
      pageNumber - page number to be selected
    """

    if pageNumber < 0 or pageNumber >= self.getPageCount():
      raise ValueError("Invalid page number: %i" % pageNumber)

    if pageNumber != self._page:
      # set the current page number
      self._page = pageNumber
      # set the message for the next page
      self.setToolBarMessage()
      # make sure the panels for the new page are visible      
      for p in self.getAllPanels(): p.setVisible(p in self.getDisplayPanels(pageNumber, True))
      # force a redraw, clearing the screen on the next refresh
      self._forceRedraw = True
      self._screen.clear()

  def nextPage(self):
    """
    Increments the page number.
    """

    self.setPage((self._page + 1) % len(self._pagePanels))

  def prevPage(self):
    """
    Decrements the page number.
    """

    self.setPage((self._page - 1) % len(self._pagePanels))

  def isPaused(self):
    """
    True if the interface is paused, false otherwise.
    """

    return self._isPaused

  def setPaused(self, isPause):
    """
    Sets the interface to be paused or unpaused.
    """

    if isPause != self._isPaused:
      self._isPaused = isPause
      self._forceRedraw = True
      self.setToolBarMessage()

      for panelImpl in self.getAllPanels():
        panelImpl.setPaused(isPause)

  def getPanel(self, name):
    """
    Provides the panel with the given identifier. This returns None if no such
    panel exists.
    
    Arguments:
      name - name of the panel to be fetched
    """

    for panelImpl in self.getAllPanels():
      if panelImpl.getName() == name:
        return panelImpl

    return None

  def getStickyPanels(self):
    """
    Provides the panels visibile at the top of every page.
    """

    return list(self._stickyPanels)

  def getDisplayPanels(self, pageNumber=None, includeSticky=True):
    """
    Provides all panels belonging to a page and sticky content above it. This
    is ordered they way they are presented (top to bottom) on the page.
    
    Arguments:
      pageNumber    - page number of the panels to be returned, the current
                      page if None
      includeSticky - includes sticky panels in the results if true
    """

    returnPage = self._page if pageNumber == None else pageNumber

    if self._pagePanels:
      if includeSticky:
        return self._stickyPanels + self._pagePanels[returnPage]
      else: return list(self._pagePanels[returnPage])
    else: return self._stickyPanels if includeSticky else []

  def getDaemonPanels(self):
    """
    Provides thread panels.
    """

    threadPanels = []
    for panelImpl in self.getAllPanels():
      if isinstance(panelImpl, threading.Thread):
        threadPanels.append(panelImpl)

    return threadPanels

  def getAllPanels(self):
    """
    Provides all panels in the interface.
    """

    allPanels = list(self._stickyPanels)

    for page in self._pagePanels:
      allPanels += list(page)

    return allPanels

  def redraw(self, force=True):
    """
    Redraws the displayed panel content.
    
    Arguments:
      force - redraws reguardless of if it's needed if true, otherwise ignores
              the request when there arne't changes to be displayed
    """

    force |= self._forceRedraw
    self._forceRedraw = False

    currentTime = time.time()
    if REFRESH_RATE != 0:
      if self._lastDrawn + REFRESH_RATE <= currentTime:
        force = True

    displayPanels = self.getDisplayPanels()

    occupiedContent = 0
    for panelImpl in displayPanels:
      panelImpl.setTop(occupiedContent)
      occupiedContent += panelImpl.getHeight()

    for panelImpl in displayPanels:
      panelImpl.redraw(force)

    if force: self._lastDrawn = currentTime

  def requestRedraw(self):
    """
    Requests that all content is redrawn when the interface is next rendered.
    """

    self._forceRedraw = True

  def getLastRedrawTime(self):
    """
    Provides the time when the content was last redrawn, zero if the content
    has never been drawn.
    """

    return self._lastDrawn

  def getToolBar(self):
    return self._toolBar

  def setToolBarMessage(self, msg=None, attr=None, redraw=False):
    """
    Sets the message displayed in the interfaces control panel. This uses our
    default prompt if no arguments are provided.
    
    Arguments:
      msg    - string to be displayed
      attr   - attribute for the label, normal text if undefined
      redraw - redraws right away if true, otherwise redraws when display
               content is next normally drawn
    """

    if msg == None:
      if self.isPaused():
        msg = "Paused"
        attr = curses.A_STANDOUT
      else:
        page, count = self.getPage()+1, self.getPageCount()
        if count > 1: msg = "page %s / %s - %s" % (page, count, self._toolBarMsg)
        else: msg = self._toolBarMsg
        attr = curses.A_NORMAL

    self._toolBar.setMessage(msg, attr)

    if redraw: self._toolBar.redraw(True)
    else: self.forceRedraw = True

  def getDataDirectory(self):
    """
    Provides the path where arm's resources are being placed. The path ends
    with a slash and is created if it doesn't already exist.
    """

    dataDir = os.path.expanduser(CONFIG["startup.dataDirectory"])
    if not dataDir.endswith("/"): dataDir += "/"
    if not os.path.exists(dataDir): os.makedirs(dataDir)
    return dataDir

  def isDone(self):
    """
    True if arm should be terminated, false otherwise.
    """

    return self._isDone

  def quit(self):
    """
    Terminates after the input is processed.
    """

    self._isDone = True
