import os, subprocess, shlex, urllib2, tarfile

def download(url, target_path):
    try:
        u = urllib2.urlopen(url)
        localfile = open(target_path, 'w')
        localfile.write(u.read())
        localfile.close()
        return 0
    except urllib2.URLError:
        return -1
    
def getTGZResource(url, downloadPathPrefix, extractPathPrefix):
    # setup paths
    downloadPathPrefix = os.path.abspath(downloadPathPrefix)
    if not os.path.exists(downloadPathPrefix): os.makedirs(downloadPathPrefix)
    extractPathPrefix = os.path.abspath(extractPathPrefix)
    if not os.path.exists(extractPathPrefix): os.makedirs(extractPathPrefix)
    
    targetFile = os.path.abspath(downloadPathPrefix + "/" + os.path.basename(url))
    targetDirectory = os.path.abspath(extractPathPrefix)
    
    # download if not cached
    if not os.path.exists(targetFile):
        if download(url, targetFile) != 0: return None
        
    # extract it locally if not already done
    name = os.path.basename(targetFile)
    # TODO - this only guesses the directory inside the tar, but could be wrong!!
    name = targetDirectory+"/"+name[:name.rindex(".tar.gz")]
    if not os.path.exists(name):
        if tarfile.is_tarfile(targetFile):
            tar = tarfile.open(targetFile, "r:gz")
            tar.extractall(path=targetDirectory)
            tar.close()
        else: return None
        
    # either the path already existed, or we downloaded and successfully extracted
    return name

def callCollect(commandString, outQ):
    outQ.put("Executing command: \'"+commandString+"\'")
    
    # run the command in a separate process
    # use shlex.split to avoid breaking up single args that have spaces in them into two args
    p = subprocess.Popen(shlex.split(commandString), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # while the command is executing, watch its output and push to the queue
    while True:
        line = p.stdout.readline()
        if not line: break
        outQ.put(line)
    
    # return the finished processes returncode
    r = p.wait()
    outQ.put("Command: \'"+commandString+"\' returned "+str(r))
    
    return r