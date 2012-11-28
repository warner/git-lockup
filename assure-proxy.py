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

def validate(git_dir, remote_name, url, all_refs):
    all_refs = dict([(name, sha) for (sha, name) in all_refs])
    debug("got %d refs" % len(all_refs))

    # these are the branches we're configured to care about
    keys = {}
    out = run_command(["git", "config", "--get-all",
                       "remote.%s.assure" % remote_name])
    for line in out.splitlines():
        key, _, branch = line.strip().split()
        if "/" not in branch:
            branch = "refs/heads/"+branch
        keys[branch] = key

    # update our list of signatures. We use both the local copy and the current
    # upstream.
    out = run_command(["git", "rev-parse", "refs/notes/commits"],
                      eat_stderr=True)
    if out is None:
        print >>sys.stderr, "Could not find local refs/notes/commits."
        print >>sys.stderr, "Maybe you need to pull some."
        local_notes_revid = None
    else:
        local_notes_revid = out.strip()

    out = run_command(["git", "fetch", "--no-tags", url,
                       "refs/notes/commits"], eat_stderr=False)
    if out is None:
        print >>sys.stderr, "Could not find refs/notes/commits in the upstream repo."
        print >>sys.stderr, "Maybe you (or someone else) needs to push some signatures to it?"
        upstream_notes_revid = None
    else:
        upstream_notes_revid = run_command(["git", "rev-parse", "FETCH_HEAD"]).strip()
        os.unlink(".git/FETCH_HEAD")

    def get_all_signatures(revid):
        remote_lines = run_command(["git", "show",
                                    "%s:%s" % (upstream_notes_revid, revid)],
                                   eat_stderr=True) or ""
        local_lines =  run_command(["git", "show",
                                    "%s:%s" % (local_notes_revid, revid)],
                                   eat_stderr=True) or ""
        lines = set()
        lines.update(remote_lines.splitlines())
        lines.update(local_lines.splitlines())
        return [line.replace("assure: ", "")
                for line in lines
                if line.startswith("assure:")]

    import ed25519

    for branch,key in keys.items():
        if branch not in all_refs:
            # tolerate missing branches. This allows assure= lines to be set up
            # in the config file before the named branches are actually
            # published. I *think* this is safe and useful, but could be
            # convinced otherwise.
            continue
        proposed_branch_revid = all_refs[branch]
        found_good_signature = False
        signatures = get_all_signatures(proposed_branch_revid)
        for sigline in signatures:
            s_body, s_sig, s_key = sigline.split()
            if s_key != key:
                debug("wrong key")
                continue # signed by a key we don't recognize
            if s_body != ("%s=%s" % (branch, proposed_branch_revid)):
                debug("wrong branch or wrong revid")
                continue # talking about the wrong branch or revid
            vk = ed25519.VerifyingKey(key, prefix="vk0-", encoding="base32")
            try:
                vk.verify(s_sig, s_body, prefix="sig0-", encoding="base32")
                found_good_signature = True
                debug("good signature found for branch %s (rev %s)" % (branch, proposed_branch_revid))
                break
            except ed25519.BadSignatureError:
                debug("bad signature")
                continue

        if not found_good_signature:
            print >>sys.stderr, "no valid signature found for branch %s (rev %s)" % (branch, proposed_branch_revid)
            sys.exit(1)

    # validation good



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

# use git-ls-remote to obtain the real list of references. We'll do our
# validation on this list, then return the list to the "git fetch" driver.
all_refs = get_remote_refs(url)
debug("all refs: '%s'" % (all_refs,))

# now validate the references. This is the core of git-assure. It will
# sys.exit(1) if it rejects what it sees.
validate(git_dir, remote_name, url, all_refs)

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
