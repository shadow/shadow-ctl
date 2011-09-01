class Control():
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.executed = False
    
    def getName(self): return self.name
    
    def getDescription(self): return self.description
    
    def setExecuted(self, executed): self.executed = executed
    
    def isExecuted(self): return self.executed
