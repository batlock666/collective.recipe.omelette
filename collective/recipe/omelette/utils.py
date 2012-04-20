import sys, os, shutil

WIN32 = False
if sys.platform[:3].lower() == "win":
    WIN32 = True

if WIN32:
    import ntfsutils.junction
    
    symlink = ntfsutils.junction.create
    islink = ntfsutils.junction.isjunction
    def unlink(path):
        if ntfsutils.junction.isjunction(path):
            ntfsutils.junction.unlink(path)
    
    def rmtree(location, nonlinks=True):
        # Explicitly unlink all junction'd links
        for root, dirs, files in os.walk(location, topdown=False):
            for dir in dirs:
                path = os.path.join(root, dir)
                unlink(path)
        # Then get rid of everything else
        if nonlinks:
            shutil.rmtree(location)
        
else:
    symlink = os.symlink
    islink = os.path.islink
    rmtree = shutil.rmtree
    unlink = None
