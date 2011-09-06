import os

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
    name = targetDirectory + "/" + name[:name.rindex(".tar.gz")]
    if not os.path.exists(name):
        if tarfile.is_tarfile(targetFile):
            tar = tarfile.open(targetFile, "r:gz")
            tar.extractall(path=targetDirectory)
            tar.close()
        else: return None

    # either the path already existed, or we downloaded and successfully extracted
    return name

