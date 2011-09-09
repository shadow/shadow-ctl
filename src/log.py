"""
  Based on code from the arm project, developed by Damian Johnson under GPLv3
  (www.atagar.com - atagar@torproject.org)
"""

import curses
import threading
from time import gmtime, strftime

from panel import *
from enum import *
from tools import *

LogLevels = Enum("ERROR", "INFO", "DEBUG")
LogColors = {LogLevels.ERROR : "red",
             LogLevels.INFO : "green",
             LogLevels.DEBUG : "yellow", }
LogShortcuts = {LogLevels.ERROR : "e",
                LogLevels.INFO : "i",
                LogLevels.DEBUG : "d", }
LogDescriptions = {LogLevels.ERROR : "displays only error messages",
                   LogLevels.INFO : "displays error and information messages (recommended)",
                   LogLevels.DEBUG : "displays all messages (most verbose)", }

# The height of the drawn content is estimated based on the last time we redraw
# the panel. It's chiefly used for scrolling and the bar indicating its
# position. Letting the estimate be too inaccurate results in a display bug, so
# redraws the display if it's off by this threshold.
CONTENT_HEIGHT_REDRAW_THRESHOLD = 3
# spaces an entry's message is indented after the first line
ENTRY_INDENT = 2

class LogEntry():
    """
    Individual log file entry, having the following attributes:
      timestamp - unix timestamp for when the event occurred
      level - log level ("INFO", "DEBUG", etc)
      msg       - message that was logged
      color     - color of the log entry
    """

    def __init__(self, timestamp, level, msg, color):
        self.timestamp = timestamp
        self.level = level
        self.msg = msg
        self.color = color
        self._displayMessage = None

    def getDisplayMessage(self, includeDate=False):
        """
        Provides the entry's message for the log.

        Arguments:
          includeDate - appends the event's date to the start of the message
        """

        if includeDate:
            # not the common case so skip caching
            entryTime = time.localtime(self.timestamp)
            timeLabel = "%i/%i/%i %02i:%02i:%02i" % (entryTime[1], entryTime[2], entryTime[0], entryTime[3], entryTime[4], entryTime[5])
            return "%s [%s] %s" % (timeLabel, self.level, self.msg)

        if not self._displayMessage:
            entryTime = time.localtime(self.timestamp)
            self._displayMessage = "%02i:%02i:%02i [%s] %s" % (entryTime[3], entryTime[4], entryTime[5], self.level, self.msg)

        return self._displayMessage

class LogPanel(Panel, threading.Thread):
    """
    Listens for and displays logs.
    """

    def __init__(self, stdscr, level, popupManager):
        Panel.__init__(self, stdscr, "log", 0)
        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.popupManager = popupManager

        self.setPauseAttr("msgLog")         # tracks the message log when we're paused
        self.msgLog = []                    # log entries, sorted by the timestamp
        self.backlog = []                   # all events for all levels
        self.level = level                  # events we display
        self.lastContentHeight = 0          # height of the rendered content when last drawn
        self.scroll = 0

        self._lastUpdate = -1               # time the content was last revised
        self._halt = False                  # terminates thread if true
        self._cond = threading.Condition()  # used for pausing/resuming the thread

        # restricts concurrent write access to attributes used to draw the display
        # and pausing:
        # msgLog, backlog, level, scroll
        self.valsLock = threading.RLock()

        # cached parameters (invalidated if arguments for them change)
        # last set of events we've drawn with
        self._lastLoggedEvents = []

        # leaving lastContentHeight as being too low causes initialization problems
        self.lastContentHeight = len(self.msgLog)

    def repopulate(self):
        """
        Clears the event log and repopulates it from the backlog.
        """

        self.valsLock.acquire()

        # clears the event log
        self.msgLog = []

        # refill from the master backlog if the level is correct
        for entry in self.backlog:
            if LogLevels.indexOf(entry.level) <= LogLevels.indexOf(self.level): self.msgLog.append(entry)

        self.valsLock.release()

    def _log(self, message, level):
        """
        Notes message and redraws log. If paused it's held in a temporary buffer.

        Arguments:
          level - log level for this log entry
          message = message to log
        """

        if not level in LogLevels.values() or not level in LogColors: return

        # strips control characters to avoid screwing up the terminal
        entry = LogEntry(time.time(), level, getPrintable(message), LogColors[level])

        self.valsLock.acquire()

        # always into the backlog
        self.backlog.insert(0, entry)

        # only in the actual log based on the level
        if LogLevels.indexOf(entry.level) <= LogLevels.indexOf(self.level):
            self.msgLog.insert(0, entry)

            # notifies the display that it has new content
            self._cond.acquire()
            self._cond.notifyAll()
            self._cond.release()

        self.valsLock.release()
        
    def error(self, message):
        self._log(message, LogLevels.ERROR)

    def info(self, message):
        self._log(message, LogLevels.INFO)
        
    def debug(self, message):
        self._log(message, LogLevels.DEBUG)
        
    def setLevel(self, level):
        """
        Sets the event types recognized by the panel.

        Arguments:
          eventTypes - event types to be logged
        """

        if level == self.level: return

        self.valsLock.acquire()
        self.level = level
        self.valsLock.release()

        self.debug("set new log level '%s'" % (level))

        # must release valsLock for repopulate
        self.repopulate()

        self.valsLock.acquire()
        self.redraw(True)
        self.valsLock.release()

    def showLevelSelectionPrompt(self):
        """
        Prompts the user to select the events being listened for.
        """

        # allow user to enter new types of events to log - unchanged if left blank
        popup, width, height = self.popupManager.prepare(12, 80)

        if popup:
            try:
            # displays the available flags
                popup.win.box()
                popup.addstr(0, 0, "Select a log level:", curses.A_STANDOUT)

                flags = []
                for f in LogLevels.values():
                    flags.append(LogShortcuts[f] + " : " + LogDescriptions[f])
                flags.append("ESC : keep current level")

                for i in range(len(flags)):
                    popup.addstr((i + 1) * 2, 2, flags[i])
                    
                popup.addstr((len(flags) + 1) * 2, 2, "Press any key...")
                popup.win.refresh()

                # get new level
                curses.cbreak()
                key = self.parent.getch()

                # validate input and make sure its an actual level
                level = None
                for k in LogShortcuts:
                    if key == ord(LogShortcuts[k]) or key == ord(LogShortcuts[k].upper()):
                        level = k
                        break
                    
                popup.setVisible(False)
                self.redraw(True)

                if level is not None: self.setLevel(level)
                elif key == 27: self.popupManager.showMsg("Cancelled log level selection", 2)
                else: self.popupManager.showMsg("Invalid log level selection: %s" % str(curses.keyname(key)), 2)
            finally: self.popupManager.finalize()

    def showSnapshotPrompt(self):
        """
        Lets user enter a path to take a snapshot, canceling if left blank.
        """
        id = strftime("%Y%m%d%H%M%S", gmtime())
        suggestion = os.path.abspath(os.path.expanduser("~/shadow-cli." + id + ".log"))
        pathInput = self.popupManager.inputPopup("Path to save log snapshot: ", initialValue=suggestion)

        if pathInput:
            try:
                self.saveSnapshot(pathInput)
                self.popupManager.showMsg("Saved log as: %s" % pathInput, 2)
            except IOError, exc:
                self.popupManager.showMsg("Unable to save snapshot: %s" % getFileErrorMsg(exc), 2)

    def clear(self):
        """
        Clears the contents of the event log.
        """

        self.valsLock.acquire()
        self.msgLog = []
        self.redraw(True)
        self.valsLock.release()

    def saveSnapshot(self, path):
        """
        Saves the log events currently being displayed to the given path.This
        overwrites the file if it already exists, and raises an IOError if
        there's a problem.

        Arguments:
          path - path where to save the log snapshot
        """

        # make dir if the path doesn't already exist
        baseDir = os.path.dirname(path)
        if not os.path.exists(baseDir): os.makedirs(baseDir)

        snapshotFile = open(path, "w")
        self.valsLock.acquire()
        try:
            # we want to save the log top-down instead of bottom-up like its displayed
            i = len(self.msgLog) - 1
            while i >= 0:
                entry = self.msgLog[i]
                snapshotFile.write(entry.getDisplayMessage(True) + "\n")
                i -= 1

            self.valsLock.release()
        except Exception, exc:
            self.valsLock.release()
            raise exc

    def handleKey(self, key):
        isKeystrokeConsumed = True
        if isScrollKey(key):
            pageHeight = self.getPreferredSize()[0] - 1
            newScroll = getScrollPosition(key, self.scroll, pageHeight, self.lastContentHeight)

            if self.scroll != newScroll:
                self.valsLock.acquire()
                self.scroll = newScroll
                self.redraw(True)
                self.valsLock.release()
        elif key == ord('c') or key == ord('C'):
            msg = "This will clear the log. Are you sure (c again to confirm)?"
            keyPress = self.popupManager.showMsg(msg, attr=curses.A_BOLD)
            if keyPress in (ord('c'), ord('C')): self.clear()
        elif key == ord('l') or key == ord('L'):
            self.showLevelSelectionPrompt()
        elif key == ord('s') or key == ord('S'):
            self.showSnapshotPrompt()
        else: isKeystrokeConsumed = False

        return isKeystrokeConsumed

    def getHelp(self):
        options = []
        options.append(("up arrow", "scroll log up a line", None))
        options.append(("down arrow", "scroll log down a line", None))
        options.append(("c", "clear log", None))
        options.append(("l", "change log level displayed", None))
        options.append(("s", "save log snapshot", None))
        return options

    def draw(self, width, height):
        """
        Redraws message log. Entries stretch to use available space and may
        contain up to two lines. Starts with newest entries.
        """

        currentLog = self.getAttr("msgLog")

        # we will be messing with the backlog
        self.valsLock.acquire()
        self._lastLoggedEvents, self._lastUpdate = list(currentLog), time.time()

        # we'll be editing the screen
        CURSES_LOCK.acquire()

        # draws the top label
        if self.isTitleVisible():
            self.addstr(0, 0, self._getTitle(width), curses.A_UNDERLINE | curses.A_BOLD)

        # restricts scroll location to valid bounds
        self.scroll = max(0, min(self.scroll, self.lastContentHeight - height + 1))

        # draws left-hand scroll bar if content's longer than the height
        msgIndent = 1 # offsets for scroll bar
        isScrollBarVisible = self.lastContentHeight > height - 1
        if isScrollBarVisible:
            msgIndent = 3
            self.addScrollBar(self.scroll, self.scroll + height - 1, self.lastContentHeight, 1)

        # draws log entries
        lineCount = 1 - self.scroll

        for entry in currentLog:
            # entry contents to be displayed, tuples of the form:
            # (msg, formatting, includeLinebreak)
            displayQueue = []

            msgComp = entry.getDisplayMessage().split("\n")
            for i in range(len(msgComp)):
                font = curses.A_BOLD if entry.level is LogLevels.ERROR else curses.A_NORMAL # emphasizes ERR messages
                displayQueue.append((msgComp[i].strip(), font | getColor(entry.color), i != len(msgComp) - 1))

            cursorLoc, lineOffset = msgIndent, 0
            maxEntriesPerLine = 2
            while displayQueue:
                msg, format, includeBreak = displayQueue.pop(0)
                drawLine = lineCount + lineOffset
                if lineOffset == maxEntriesPerLine: break

                maxMsgSize = width - cursorLoc - 1
                if len(msg) > maxMsgSize:
                # message is too long - break it up
                    if lineOffset == maxEntriesPerLine - 1:
                        msg = cropStr(msg, maxMsgSize)
                    else:
                        msg, remainder = cropStr(msg, maxMsgSize, 4, 4, Ending.HYPHEN, True)
                        displayQueue.insert(0, (remainder.strip(), format, includeBreak))

                    includeBreak = True

                if drawLine < height and drawLine >= 1:
                    self.addstr(drawLine, cursorLoc, msg, format)

                cursorLoc += len(msg)

                if includeBreak or not displayQueue:
                    lineOffset += 1
                    cursorLoc = msgIndent + ENTRY_INDENT

            lineCount += lineOffset

        # redraw the display if...
        # - lastContentHeight was off by too much
        # - we're off the bottom of the page
        newContentHeight = lineCount + self.scroll - 1
        contentHeightDelta = abs(self.lastContentHeight - newContentHeight)
        forceRedraw, forceRedrawReason = True, ""

        # done with locks
        CURSES_LOCK.release()
        self.valsLock.release()

        if contentHeightDelta >= CONTENT_HEIGHT_REDRAW_THRESHOLD:
            forceRedrawReason = "estimate was off by %i" % contentHeightDelta
        elif newContentHeight > height and self.scroll + height - 1 > newContentHeight:
            forceRedrawReason = "scrolled off the bottom of the page"
        elif not isScrollBarVisible and newContentHeight > height - 1:
            forceRedrawReason = "scroll bar wasn't previously visible"
        elif isScrollBarVisible and newContentHeight <= height - 1:
            forceRedrawReason = "scroll bar shouldn't be visible"
        else: forceRedraw = False

        self.lastContentHeight = newContentHeight
        if forceRedraw:
            forceRedrawReason = "redrawing the log panel with the corrected content height (%s)" % forceRedrawReason
            self.debug("forced redraw: " + forceRedrawReason)
            self.redraw(True)

    def redraw(self, forceRedraw=False, block=False):
        # determines if the content needs to be redrawn or not
        Panel.redraw(self, forceRedraw, block)

    def run(self):
        """
        Redraws the display, coalescing updates if events are rapidly logged (for
        instance running at the DEBUG runlevel) while also being immediately
        responsive if additions are less frequent.
        """

        while not self._halt:
            timeSinceReset = time.time() - self._lastUpdate
            maxLogUpdateRate = 1.0

            sleepTime = 0
            if (self.msgLog == self._lastLoggedEvents) or self.isPaused():
                sleepTime = 5
            elif timeSinceReset < maxLogUpdateRate:
                sleepTime = max(0.05, maxLogUpdateRate - timeSinceReset)

            if sleepTime:
                self._cond.acquire()
                if not self._halt: self._cond.wait(sleepTime)
                self._cond.release()
            else:
                self.redraw(True)

                # makes sure that we register this as an update, otherwise lacking the
                # curses lock can cause a busy wait here
                self._lastUpdate = time.time()

    def stop(self):
        """
        Halts further resolutions and terminates the thread.
        """

        self._cond.acquire()
        self._halt = True
        self._cond.notifyAll()
        self._cond.release()

    def _getTitle(self, width):
        """
        Provides the label used for the panel, looking like:
          Events (ARM NOTICE - ERR, BW - filter: prepopulate):

        This truncates the attributes (with an ellipse) if too long, and condenses
        runlevel ranges if there's three or more in a row (for instance ARM_INFO,
        ARM_NOTICE, and ARM_WARN becomes "ARM_INFO - WARN").

        Arguments:
          width - width constraint the label needs to fix in
        """

        # usually the attributes used to make the label are decently static, so
        # provide cached results if they're unchanged
        self.valsLock.acquire()
        titleLabel = "Log (%s level)" % str(self.level)
        self.valsLock.release()

        return titleLabel
