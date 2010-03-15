import sys, os, shutil

WIN32 = False
if sys.platform[:3].lower() == "win":
    WIN32 = True

if WIN32:

    def _run(cmd):
        stdout = os.popen(cmd)
        output = stdout.read()
        stdout.close()
        return output

    # find the junction utility; warn if missing
    JUNCTION = "junction.exe"
    found = False
    for path in os.environ['PATH'].split(';'):
        if os.path.exists(os.path.join(path, JUNCTION)):
            found = True
            break
    if not found:
        raise EnvironmentError("Junction.exe not found in path.  "
            "Collective.recipe.omelette cannot continue.  See omelette's "
            "README.txt.")

    def symlink(src, dest):
        cmd = "%s %s %s" % (JUNCTION, os.path.abspath(dest), os.path.abspath(src),)
        _run(cmd)

    def unlink(dest):
        cmd = "%s -d %s" % (JUNCTION, os.path.abspath(dest),)
        _run(cmd)

    def islink(dest):
        cmd = "%s %s" % (JUNCTION, os.path.abspath(dest),)
        output = _run(cmd)
        return "Substitute Name:" in output

    def rmtree(location, nonlinks=True):
        # Explicitly unlink all junction'd links
        for root, dirs, files in os.walk(location, topdown=False):
            for dir in dirs:
                path = os.path.join(root, dir)
                if islink(path):
                    unlink(path)
        # Then get rid of everything else
        if nonlinks:
            shutil.rmtree(location)

else:
    symlink = os.symlink
    islink = os.path.islink
    rmtree = shutil.rmtree
    unlink = None

def rmitem(location):
    if islink(location):
        os.remove(location)
    elif os.path.isdir(location):
        rmtree(location)
    else:
        os.remove(location)

NAMESPACE_STANZA = """# See PEP 382: http://www.python.org/dev/peps/pep-0382/
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
"""

def makedirs(target, is_namespace=False):
    """ Similar to os.makedirs, but adds __init__.py files as it goes.  Returns a boolean
        indicating success.
    """
    drive, path = os.path.splitdrive(target)
    parts = path.split(os.path.sep)
    current = drive + os.path.sep
    for part in parts:
        current = os.path.join(current, part)
        if islink(current):
            return False
        if not os.path.exists(current):
            os.mkdir(current)
            init_filename = os.path.join(current, '__init__.py')
            if not os.path.exists(init_filename):
                init_file = open(init_filename, 'w')
                if is_namespace or part == 'Products':
                    init_file.write(NAMESPACE_STANZA)
                else:
                    init_file.write('# mushroom')
                init_file.close()
    return True
