"""
Provides user prompts for setting up shadow.
"""

import curses

from controller import *
from panel import *
from popup import *
from log import *

CONTROLLER = None

def test(l):
    v = LogLevels.values()
    for i in xrange(0, 10000):
        l.log(str(i), v[i%3])
        time.sleep(0.001)

def start(stdscr):
    global CONTROLLER
    
    # main controller that handles all the panels, popups, etc
    CONTROLLER = Controller(stdscr, "p: pause, h: help, q: quit")
    
#    page1 = []
#    l = LabelPanel(stdscr)
#    l.setVisible(True)
#    l.setMessage("page 1 message1")
#    CONTROLLER.addPagePanels(page1)
    
    lp = LogPanel(stdscr, LogLevels.DEBUG, CONTROLLER.getPopupManager())
    lp.setVisible(True)
    CONTROLLER.addPagePanels([lp])
    
    for p in CONTROLLER.getDaemonPanels(): p.start()
    lp.log("shadow-cli initialized", level=LogLevels.INFO)
    
    helpkey = None
    while not CONTROLLER.isDone():
        
        CONTROLLER.redraw(False)
        stdscr.refresh()

        key, helpkey = helpkey, None
        if key is None:
            # wait for user keyboard input until timeout
            curses.halfdelay(int(REFRESH_RATE * 10))
            key = stdscr.getch()

        if key == curses.KEY_RIGHT:
            CONTROLLER.nextPage()
        elif key == curses.KEY_LEFT:
            CONTROLLER.prevPage()
        elif key == ord('a') or key == ord('A'):
            CONTROLLER.getPopupManager().showAboutPopup()
        elif key == ord('h') or key == ord('H'):
            helpkey = CONTROLLER.getPopupManager().showHelpPopup()
        elif key == ord('p') or key == ord('P'):
            CONTROLLER.setPaused(not CONTROLLER.isPaused())
        elif key == ord('q') or key == ord('Q'):
            CONTROLLER.quit()
        else:
            for p in CONTROLLER.getDisplayPanels():
                isKeystrokeConsumed = p.handleKey(key)
                if isKeystrokeConsumed: break
    
def finish():
    HALT_ACTIVITY = True
    # stop and join threads
    if CONTROLLER:
        for p in CONTROLLER.getDaemonPanels(): p.stop()
        for p in CONTROLLER.getDaemonPanels(): p.join()