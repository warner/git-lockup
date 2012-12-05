import sys, os, subprocess, base64

def from_ascii(s_ascii):
    s_ascii += "="*((8 - len(s_ascii)%8)%8)
    s_bytes = base64.b32decode(s_ascii.upper())
    return s_bytes

def to_ascii(s_bytes):
    s_ascii = base64.b32encode(s_bytes).rstrip("=").lower()
    return s_ascii

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
