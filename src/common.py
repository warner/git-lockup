import sys, os, subprocess, base64

def from_ascii(s_ascii):
    s_ascii += "="*((8 - len(s_ascii)%8)%8)
    s_bytes = base64.b32decode(s_ascii.upper())
    return s_bytes

def to_ascii(s_bytes):
    s_ascii = base64.b32encode(s_bytes).rstrip("=").lower()
    return s_ascii

def remove_prefix(s, prefix):
    if not s.startswith(prefix):
        return None
    return s[len(prefix):]

def announce(s):
    print >>sys.stderr, s

def debug(s):
    #print >>sys.stderr, s
    return

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
