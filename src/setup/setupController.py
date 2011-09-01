import os, time, curses

from core import panel, labelPanel, control, controlPanel, scrollPanel, popupPanel, textInput, tools

REDRAW_RATE = 5

class SetupController:
    def __init__(self, stdscr):
        self.screen = stdscr
        
        self.labelp = None
        self.controlp = None
        self.scrollp = None
        self.popupp = None
        
        self.controls = None
        self.isDone = False
        self.lastDrawn = 0
    
    def getScreen(self):
        return self.screen
    
    def redraw(self, force = True):
        # always force if too much time passed
        currentTime = time.time()
        if self.lastDrawn + REDRAW_RATE <= currentTime: force = True
        
        if self.labelp.isVisible(): self.labelp.redraw(force)
        if self.controlp.isVisible(): self.controlp.redraw(force)
        if self.scrollp.isVisible(): self.scrollp.redraw(force)
        if self.popupp.isVisible(): self.popupp.redraw(force)
        
        self.screen.refresh()
        
    def start(self):
         # allows for background transparency
        try: curses.use_default_colors()
        except curses.error: pass
        
        # makes the cursor invisible
        try: curses.curs_set(0)
        except curses.error: pass

        # setup panels
        self.labelp = labelPanel.LabelPanel(self.screen)
        self.labelp.setMessage("Shadow Setup Wizard -- q: quit")
        self.labelp.setVisible(True)
        
        self.controlp = controlPanel.ControlPanel(self.screen, 1, 0)
        self.controlp.setMessage("Welcome to the Shadow Setup Wizard. Please select "
                      "from the controls below to setup and install Shadow.")
        self.controlp.setVisible(True)
        
        self.controls = []
        self.controls.append(control.Control("Auto Setup", "Performs an automatic configuration of a Shadow installation by downloading, building, and installing Shadow and any missing dependencies to the user's home directory using default options."))
        self.controls.append(control.Control("Interactive Setup", "Interactively configure Shadow as above."))
        self.controls.append(control.Control("Uninstall Shadow", "Uninstall Shadow using cached installation options."))
        self.controls.append(control.Control("Quit", "Exit the Shadow Setup Wizard."))
        
        self.controlp.setControls(self.controls)

        self.scrollp = scrollPanel.ScrollPanel(self.screen, "Setup Log", 1, -1)
        self.scrollp.setVisible(False)
        
        self.popupp = popupPanel.PopupPanel(self.screen, 2, 2)
        self.popupp.setVisible(False)
        
        # used in case some commands want to chain execute another command
        chainKey = None
        
        while not self.isDone:
            self.redraw(True)
            
            # wait for user keyboard input until timeout, unless an override was set
            if chainKey:
                key, chainKey = chainKey, None
            else:
                curses.halfdelay(REDRAW_RATE * 10)
                key = self.screen.getch()
            
            if key == ord('q') or key == ord('Q'):
                self.stop()
            elif key == ord('h') or key == ord('H'):
                pass
            elif key == ord('s') or key == ord('S'):
                if self.scrollp.isVisible(): self.saveLog()
            elif key == ord('l') - 96:
                # force redraw when ctrl+l is pressed
                self.redraw(True)
            elif key == 27 and self.popupp.isVisible():
                self.popupp.setVisible(False)
            else:
                if self.controlp.isVisible():
                    isKeyConsumed = self.controlp.handleKey(key)
                    if isKeyConsumed:
                        if self.needsTransition(): self.doTransition()
                elif self.scrollp.isVisible():
                    self.scrollp.handleKey(key)
    
    def saveLog(self):
        self.popupp.setQuery("Please enter the path to save the log file:")
        self.popupp.setDefaultResponse(os.path.abspath(os.getenv("HOME") + "/.shadow/cli-" + str(int(time.time())) + ".log"))
        self.popupp.setVisible(True)
        self.popupp.redraw(True)
        path = self.popupp.getUserResponse()
        self.popupp.setVisible(False)
        
        if path is not None:
            path = os.path.abspath(path)
            d = os.path.dirname(path)
            if not os.path.exists(d): os.makedirs(d)
            with open(path, 'a') as f:
                for line in self.scrollp.get(): f.write(line)

    def needsTransition(self):
        for c in self.controls:
            if c.isExecuted(): return True
        return False
                
    def doTransition(self):
        self.controlp.setVisible(False)
        self.scrollp.setVisible(True)
        self.labelp.setMessage("Shadow Setup Wizard -- s: save log, q: quit")
        
        for c in self.controls:
            if c.isExecuted():
                n = c.getName()
                if n == "Auto Setup": self.doAutoSetup()
                elif n == "Interactive Setup": pass
                elif n == "Uninstall": self.doUninstall()
                elif n == "Quit": self.stop()
                
    def doAutoSetup(self):
        # spawn a thread to execute all the setup commands and fill the log
        pass
    
    def doInteractiveSetup(self):
        pass
    
    def doUninstall(self):
        # spawn a thread to execute the uninstall commands and fill the log
        pass
                        
    def stop(self):
        """
        Terminates after the input is processed.
        """
        self.isDone = True
