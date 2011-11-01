#! /usr/bin/python
import os, sys, subprocess
import ed25519
import base64
from StringIO import StringIO

def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    if p.returncode != 0:
        print >>sys.stderr, "Error running '%s': rc=%s" % \
              (" ".join(cmd), p.returncode)
        raise Exception()
    return stdout

def remove_prefix(s, prefix):
    if not s.startswith(prefix):
        return None
    return s[len(prefix):]

# check for a good signature on the current revision. Run this inside a git
# repo.
fullbranch = run(["git", "rev-parse", "--symbolic-full-name", "HEAD"]).strip()
branch = remove_prefix(fullbranch, "refs/heads/")
if not branch:
    print "not commiting to refs/heads/ , ignoring"
    sys.exit(0)
pieces = branch.split("/")
if "." in pieces or ".." in pieces:
    print "scary branch name %s, ignoring" % branch
    sys.exit(0)

gitdir = ".git"
keyfile = os.path.join(gitdir, "Assure", "verify", *pieces)
try:
    vk_expected_s = open(keyfile, "rb").read().strip()
except EnvironmentError:
    print "no key defined for '%s', exiting" % branch
    sys.exit(0)
vk_expected_s2 = remove_prefix(vk_expected_s, "verf0-")
if not vk_expected_s2:
    raise Exception("unrecognized verifying key in '%s'" % keyfile)

rev = run(["git", "rev-parse", "HEAD"]).strip()
notes = run(["git", "notes", "show", rev])
for line in StringIO(notes).readlines():
    if not line.startswith("assure:"):
        continue
    header, msg, sig_s, vk_s = line.split()
    if msg != "%s=%s" % (branch, rev):
        continue
    if vk_s != vk_expected_s:
        print "unusual: signed by unexpected key"
        continue
    sig = base64.b64decode(remove_prefix(sig_s, "sig0-"))
    vk = ed25519.VerifyingKey(base64.b64decode(vk_expected_s2))
    vk.verify(sig, msg)
    print "good sig"
    break
else:
    print "no sig found, BAD"
    sys.exit(0)
print "done"
sys.exit(0)
