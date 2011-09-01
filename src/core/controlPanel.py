import curses

from core import panel, tools, control

class ControlPanel(panel.Panel):
    """
    Panel that displays selectable controls.
    """
    def __init__(self, stdscr, width, height):
        panel.Panel.__init__(self, stdscr, "Controls", width, height)
        # holds a list of Options to display in this panel
        self.controls = None
        # display attributes for each option name
        self.controlNameAttributes = curses.A_BOLD | curses.COLOR_RED
        # display attributes for each option description
        self.controlDescriptionAttributes = curses.COLOR_RED
        # a message displayed before the option list
        self.message = None
        # display attributes for the message
        self.messageAttributes = self.controlNameAttributes
        # the option that is selected
        self.selectedIndex = None
      
    def setMessage(self, message):
        self.message = message
    
    def setControls(self, controls):
        """
          Sets the controls being displayed by the panel.
      
          Arguments:
            controls  - list of controls
        """
        
        self.controls = controls
        if controls is not None and len(self.controls) > 0: self.selectedIndex = 0
    
    def draw(self, width, height):
        tools.drawBox(self, 0, 0, width, height)
        
        # breakup the message and draw it inside the box
        msgLines = tools.splitStr(self.message, 54)
        for i in range(len(msgLines)): self.addstr(i + 1, 2, msgLines[i], self.messageAttributes)
        
        # track position for each option on the screen
        y, offset = len(msgLines) + 1, 0
 
        for o in self.controls:
            # selected controls stand out from the rest
            extraAttributes = 0
            if o is self.controls[self.selectedIndex]: extraAttributes = curses.A_STANDOUT
            
            # draw the option name and description
            offset += 1
            label = o.getName()
            self.addstr(y + offset, 2, label, 
                        self.controlNameAttributes | extraAttributes)
            # set whitespace as non-bold due to curses pixel alignment bug
            self.addstr(y + offset, 2 + len(label), " " * (54 - len(label)), 
                        self.controlDescriptionAttributes | extraAttributes)
            y+=1
            
            description = tools.splitStr(o.getDescription(), 54)
            for line in description:
                self.addstr(y + offset, 2, tools.padStr(line, 54),
                            self.controlDescriptionAttributes | extraAttributes)
                offset += 1
                
    def handleKey(self, key):
        # if the iopanel is currently active, pass key there
        if self.selectedIndex is not None:
            if key == curses.KEY_UP: 
                self.selectedIndex = (self.selectedIndex - 1) % len(self.controls)
                return True
            elif key == curses.KEY_DOWN: 
                self.selectedIndex = (self.selectedIndex + 1) % len(self.controls)
                return True
            elif tools.isSelectionKey(key):
                self.controls[self.selectedIndex].setExecuted(True)
                return True
        return False
