import urllib2

def download(url, target_path):
    try:
        u = urllib2.urlopen(url)
        localfile = open(target_path, 'w')
        localfile.write(u.read())
        localfile.close()
        return 0
    except urllib2.URLError:
        return -1