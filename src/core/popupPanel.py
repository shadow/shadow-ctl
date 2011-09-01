import curses

from core import panel, tools

class PopupPanel(panel.Panel):
    """
    Panel that just displays a single line of text.
    """
    
    def __init__(self, stdscr, width, height):
        panel.Panel.__init__(self, stdscr, "popup", width, height)
        self.queryText = None
        self.queryAttr = curses.A_BOLD
        self.defaultResponse = None
        self.topUserResponse = 0
        self.leftUserResponse = 0
        self.userResponseMaxWidth = 0
  
    def setQuery(self, query, attr = None):
        """
        Sets the message being displayed by the panel.
        
        Arguments:
          msg  - string to be displayed
          attr - attribute for the label, normal text if undefined
        """

        if attr == None: attr = curses.A_BOLD
        self.queryText = query
        self.queryAttr = attr
        
    def setDefaultResponse(self, response):
        self.defaultResponse = response
        
    def getUserResponse(self):
        if self.defaultResponse is not None:
            return self.getstr(self.topUserResponse, self.leftUserResponse, self.defaultResponse, 
                           format=curses.A_STANDOUT, maxWidth = self.userResponseMaxWidth)
        else: return None
  
    def draw(self, width, height):
        tools.drawBox(self, 0, 0, width-2, height-2)
        
        yoffset = 2
        
        if self.queryText is not None:
            m = tools.splitStr(self.queryText, width-2)
            for line in m:
                self.addstr(yoffset, 2, line, self.queryAttr)
                yoffset += 1
            
        self.topUserResponse = yoffset + 2
        self.leftUserResponse = 2
        self.userResponseMaxWidth = width-6
