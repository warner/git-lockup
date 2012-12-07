import re, sys, os, subprocess, base64

def from_ascii(s_ascii):
    s_ascii += "="*((8 - len(s_ascii)%8)%8)
    s_bytes = base64.b32decode(s_ascii.upper())
    return s_bytes

def to_ascii(s_bytes):
    s_ascii = base64.b32encode(s_bytes).rstrip("=").lower()
    return s_ascii

def remove_prefix(s, prefix, require_prefix=False):
    if not s.startswith(prefix):
        if require_prefix:
            raise ValueError("no prefix '%s' in string '%s'" % (prefix, s))
        return None
    return s[len(prefix):]

def announce(s):
    print >>sys.stderr, s

def debug(s):
    #print >>sys.stderr, s
    return

def make_executable(tool):
    oldmode = os.stat(tool).st_mode & int("07777", 8)
    newmode = (oldmode | int("0555", 8)) & int("07777", 8)
    os.chmod(tool, newmode)

def run_command(args, cwd=None, stdin="", eat_stderr=False, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        stderr = None
        if eat_stderr:
            stderr = subprocess.PIPE
        p = subprocess.Popen(args,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=stderr,
                             cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            debug("unable to run %s" % args[0])
            debug(e)
        return None
    stdout = p.communicate(stdin)[0]
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            debug("unable to run %s (error)" % args[0])
        return None
    return stdout

def get_config(key):
    cmd = ["git", "config", key]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    if p.returncode == 1:
        return None
    if p.returncode != 0:
        print >>sys.stderr, "Error running '%s': rc=%s" % \
              (" ".join(cmd), p.returncode)
        raise Exception()
    return stdout.strip()

def get_all_config(key):
    cmd = ["git", "config", "--get-all", key]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    if p.returncode == 1:
        return []
    if p.returncode != 0:
        print >>sys.stderr, "Error running '%s': rc=%s" % \
              (" ".join(cmd), p.returncode)
        raise Exception()
    return stdout.splitlines()

def get_config_regexp(regexp):
    cmd = ["git", "config", "--get-regexp", regexp]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    if p.returncode == 1:
        return None
    if p.returncode != 0:
        print >>sys.stderr, "Error running '%s': rc=%s" % \
              (" ".join(cmd), p.returncode)
        raise Exception()
    return stdout.splitlines()

def get_config_verifykeys():
    # these are the branches we're configured to care about
    branches = {} # maps branch name to set of keys
    keylines = get_config_regexp(r"^branch\..*\.assure-key$")
    for line in keylines:
        mo = re.search(r'^branch\.([^.]*)\.assure-key\s+([\w\-]+)$', line)
        if not mo:
            announce("confusing assure-key line: '%s'" % line)
            continue
        branch = mo.group(1)
        if "/" not in branch:
            branch = "refs/heads/"+branch
        if branch not in branches:
            branches[branch] = set()
        branches[branch].add(mo.group(2))
    return branches

def set_config_raw_urls(remote):
    rawurl = get_config("remote.%s.assure-raw-url" % remote)
    rawpushurl = get_config("remote.%s.assure-raw-pushurl" % remote)
    if not rawurl:
        rawurl = get_config("remote.%s.url" % remote)
        assert rawurl
        rawpushurl = get_config("remote.%s.pushurl" % remote)
        run_command(["git", "config",
                     "remote.%s.assure-raw-url" % remote, rawurl])
        if rawpushurl:
            run_command(["git", "config",
                         "remote.%s.assure-raw-pushurl" % remote, rawpushurl])
    return rawurl, rawpushurl
