"""
Provides user prompts for setting up shadow.
"""

import curses

from controller import *
from panel import *
from popup import *
from log import *
from config import *

CONTROLLER = None

def test(l):
    v = LogLevels.values()
    for i in xrange(0, 10000):
        l.log(str(i), v[i % 3])
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

    # setup the log panel as its own page
    lp = LogPanel(stdscr, LogLevels.DEBUG, CONTROLLER.getPopupManager())
    CONTROLLER.addPagePanels([lp])

    # start the threaded panels (e.g. log panel)
    for p in CONTROLLER.getDaemonPanels(): p.start()
    lp.log("shadow-cli initialized", level=LogLevels.INFO)

    # make sure toolbar is drawn
    CONTROLLER.redraw(True)

    # launch the setup wizard to configure and collect setup options
    options = wizard(stdscr, lp)

    # use the configured options to launch the setup worker thread that will
    # actually do the downloads, configure, make, etc
    pass

    # now we want the log to be shown
    lp.setVisible(True)

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
            # if push h twice, use it to toggle help off
            if helpkey == ord('h') or helpkey == ord('H'): helpkey = None
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

def wizard(stdscr, logger):
    cp = ControlPanel(stdscr, 1, 0)
    cp.setMessage("Welcome to the Shadow Setup Wizard. Please select "
                  "from the controls below to setup and install Shadow.")
    cp.setVisible(True)

    config = loadConfig()

    choices = []
    choices.append(("Auto Setup", "Performs an automatic configuration of a Shadow installation by downloading, building, and installing Shadow and any missing dependencies to the user's home directory using default options. A build-cache is created in " + config.get("setup", "build") + " and not cleared. Future Auto Setups will re-use this cache."))
    choices.append(("Interactive Setup", "Interactively configure Shadow as above. This option first clears the build-cache that may have been previously created in " + config.get("setup", "build") + "."))
    choices.append(("Uninstall Shadow", "Uninstall Shadow and clear cache."))

    cp.setControls(choices)

    curses.cbreak()

    # get the selected method of setup from the choices
    selection = None
    while True:
        cp.redraw(True)
        key = stdscr.getch()
        selection = cp.handleKey(key)
        if selection is not None: break

    logger.log("wizard selected option \'%s\'" % (selection))
