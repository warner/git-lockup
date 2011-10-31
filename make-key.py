#! /usr/bin/python

import ed25519
import base64
import os, sys
import subprocess

if len(sys.argv) != 2:
    print "Usage: make-key.py REPO"
    sys.exit(0)

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

gitdir = os.path.join(sys.argv[1], ".git")
fullbranch = run(["git", "--git-dir", gitdir,
                  "rev-parse", "--symbolic-full-name", "HEAD"]).strip()
branch = remove_prefix(fullbranch, "refs/heads/")
if not branch:
    print "not commiting to refs/heads/ , ignoring"
    sys.exit(0)
pieces = branch.split("/")
if "." in pieces or ".." in pieces:
    print "scary branch name %s, ignoring" % branch
    sys.exit(0)
print branch

sk,vk = ed25519.create_keypair()
keyfile = os.path.join(gitdir, "Assure", "keys", *pieces)
if not os.path.isdir(os.path.dirname(keyfile)):
    os.makedirs(os.path.dirname(keyfile))
print keyfile
f = open(keyfile, "wb")
f.write("sign0-"+sk.to_string())
f.close()
print "signing key written to", keyfile
vk_s = "verf0-"+base64.b64encode(vk.to_string())
print "verifying key:", vk_s
