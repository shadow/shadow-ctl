import curses, os, time
from multiprocessing import Process, Pipe, RLock

from core import panel, popupPanel, tools

def pollPipe(conn, panel):
    pass
    #while True: panel.add(conn.recv())

class ScrollPanel(panel.Panel):
    
    def __init__(self, stdscr, name, top, backlog):
        panel.Panel.__init__(self, stdscr, name, top)
        self.data = []
        self.dataLock = RLock()
        self.backlog = backlog
        self.scrollTop = 0
        self.scrollBottom = 0
        self.scrollHeight = 0
        self.pipein, self.pipeout = Pipe()
        self.pipeProcess = Process(target=pollPipe, args=(self.pipein, self))
        self.pipeProcess.start()
        
    def add(self, output):
        self.dataLock.acquire()
        for line in output.split('\n'): self.data.append(line)
        if self.backlog > 0:
            while len(self.data) > self.backlog: self.data.pop(0)
        self.dataLock.release()
            
    def get(self):
        self.dataLock.acquire()
        copy = list(self.data)
        self.dataLock.release()
        return copy
        
    def draw(self, width, height):
        output = []
        self.dataLock.acquire()
        for item in self.data: 
            lines = tools.splitStr(item, width-2)
            for line in lines: output.append(line)
        self.dataLock.release()
        
        self.scrollLines = len(output)
        self.scrollHeight = height-1
        self.scrollBottom = min(self.scrollTop + self.scrollHeight, self.scrollLines)
        
        # dont draw unless we have data
        if self.scrollLines > 0:
            yoffset = 0
            if self.isTitleVisible(): 
                self.addstr(yoffset, 0, self.getName(), curses.A_STANDOUT)
                self.addstr(yoffset, len(self.getName()) + 1, "s: save log", curses.A_NORMAL)
                yoffset += 1
                
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
        
    def saveLog(self):
        query = "Please enter the path to save the log file:"
        default = os.path.abspath(os.getenv("HOME") + "/.shadow/cli-" + str(int(time.time())) + ".log")
        
        p = popupPanel.PopupPanel(self.parent, 2, 2)
        p.setVisible(True)
        p.setQuery(query)
        p.setDefaultResponse(default)
        p.redraw(True)
        path = p.getUserResponse()
        
        if path is not None:
            path = os.path.abspath(path)
            d = os.path.dirname(path)
            if not os.path.exists(d): os.makedirs(d)
            with open(path, 'a') as f:
                for line in self.get(): f.write(line)
                
            self.add("Log saved to " + path)
                
    def getPipe(self):
        return self.pipeout
    
    def join(self):
        self.pipein.close()
        self.pipeout.close()
        self.pipeProcess.join()
            