import curses

from core import panel, tools, control

class ScrollPanel(panel.Panel):
    
    def __init__(self, stdscr, name, top, backlog):
        panel.Panel.__init__(self, stdscr, name, top)
        self.data = []
        self.backlog = backlog
        self.scrollTop = 0
        self.scrollBottom = 0
        self.scrollHeight = 0
        
    def add(self, output):
        for line in output.split('\n'): self.data.append(line)
        if self.backlog > 0:
            while len(self.data) > self.backlog: self.data.pop(0)
            
    def get(self):
        return self.data
        
    def draw(self, width, height):
        yoffset = 0
        if self.isTitleVisible(): 
            self.addstr(yoffset, 0, self.getName(), curses.A_STANDOUT)
            yoffset += 1
        
        output = tools.splitStr(self.data, width-2)
        
        self.scrollLines = len(output)
        self.scrollHeight = height-1
        self.scrollBottom = min(self.scrollTop + self.scrollHeight, self.scrollLines)
        
        # dont draw unless we have data
        if self.scrollLines > 0:
            self.addScrollBar(self.scrollTop, self.scrollBottom, self.scrollLines, drawTop = yoffset, drawScrollBox = True)
    
            for i in xrange(self.scrollTop, min(self.scrollBottom, len(output))):
                line = output[i]
                self.addstr(yoffset, 3, tools.padStr(line, width-3))
                yoffset += 1
        
    def handleKey(self, key):
        if tools.isScrollKey(key):
            newScroll = tools.getScrollPosition(key, self.scrollTop, self.scrollHeight, self.scrollLines)
            if self.scrollTop != newScroll:
                #self.valsLock.acquire()
                self.scrollTop = newScroll
                self.redraw(True)
                #self.valsLock.release()
            return True
        else: return False
