#!/usr/bin/env python

import sys, os, subprocess

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

def get_remote_refs(url):
    # git-ls-remote returns tab-joined "SHA\tNAME", and we want to format it
    # differently. Return a list of (SHA, NAME) tuples.
    tab_text = run_command(["git", "ls-remote", url])
    return [tuple(line.split()) for line in tab_text.splitlines()]

def run_mid_fetch_hook(git_dir, remote_name, url, stdin):
    hook = os.path.join(git_dir, "hooks", "mid-fetch")
    if os.access(hook, os.X_OK):
        debug("running hook")
        debug("passing %d bytes to stdin" % len(stdin));
        out = run_command([hook, remote_name, url], stdin=stdin)
        if out is None:
            announce("mid-fetch hook threw error, aborting fetch")
            sys.exit(1)
        if out:
            sys.stderr.write(out) # hook can debug to its stdout
        debug("mid-fetch hook is happy")

def fetch_objects(url, orig_refspec, remote_name):
    temp_remote = remote_name + "-assure-temp"
    refspec = orig_refspec.replace("refs/remotes/%s/" % remote_name,
                                   "refs/remotes/%s/" % temp_remote)
    debug("fetching new refs")
    run_command(["git", "fetch", "--no-tags", "--update-head-ok", url, refspec],
                eat_stderr=True)
    debug("fetched refs")
    try:
        os.unlink(".git/FETCH_HEAD")
    except EnvironmentError:
        pass
    # and delete all the temporary tracking branches
    temp_refs = set()
    for line in run_command(["git", "branch", "--remote"]).splitlines():
        line = line.strip()
        if line.startswith(temp_remote):
            temp_refs.add(line.replace("%s/" % temp_remote, ""))
    for refname in temp_refs:
        run_command(["git", "update-ref", "-d",
                     "refs/remotes/%s/%s" % (temp_remote, refname)])
    debug("deleted temp refs")

debug("ARGS=%s" % (sys.argv,))
remote_name, url = sys.argv[1:3]
git_dir = os.path.abspath(os.environ["GIT_DIR"])
debug(git_dir)

# extract the 'fetch' config for the real remote
refspec = run_command(["git", "config", "remote.%s.fetch" % remote_name]).strip()
debug("REFSPEC: %s" % refspec)
debug("URL: %s" % url)

# all the mid-fetch hook work happens now, before we return the reference
# list to the "git fetch" driver.
all_refs = get_remote_refs(url)
debug("all refs: '%s'" % (all_refs,))

# then run the mid-fetch hook, allowing it to judge the raw remote. This will
# sys.exit(1) if the hook rejects what it sees.
run_mid_fetch_hook(git_dir, remote_name, url,
                   "\n".join([" ".join(ref) for ref in all_refs])+"\n")

# now fetch all objects into a temporary remote, so that the parent fetch
# won't need us to provide any actual objects.
fetch_objects(url, refspec, remote_name)

debug("returning full ref list")
# now return the full reflist
for (sha,name) in all_refs:
    line = "%s %s\n" % (sha, name)
    sys.stdout.write("%04x" % (4+len(line)))
    sys.stdout.write(line)
sys.stdout.write("0000")
sys.stdout.flush()
debug("finished returning full ref list")

while True:
    length = int(sys.stdin.read(4), 16)
    if length == 0:
        # graceful disconnect
        sys.exit(0)

    line = sys.stdin.read(length-4)
    debug("COMMAND=%s" % line)

    announce("Hey, don't fetch, you should already have everything")
    sys.exit(1)
