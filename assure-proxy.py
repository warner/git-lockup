#!/usr/bin/env python

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


# single-file pure-python ed25519 digital signatures, rearranged to minimize
# the namespace pollution so this can be embedded in another file. Adapted
# from https://bitbucket.org/dholth/ed25519ll


# Ed25519 digital signatures
# Based on http://ed25519.cr.yp.to/python/ed25519.py
# See also http://ed25519.cr.yp.to/software.html
# Adapted by Ron Garret
# Sped up considerably using coordinate transforms found on:
# http://www.hyperelliptic.org/EFD/g1p/auto-twisted-extended-1.html
# Specifically add-2008-hwcd-4 and dbl-2008-hwcd

def Ed25519():
    # don't add many names to the file we're copied into

    try: # pragma nocover
        unicode
        PY3 = False
        def asbytes(b):
            """Convert array of integers to byte string"""
            return ''.join(chr(x) for x in b)
        def joinbytes(b):
            """Convert array of bytes to byte string"""
            return ''.join(b)
        def bit(h, i):
            """Return i'th bit of bytestring h"""
            return (ord(h[i//8]) >> (i%8)) & 1

    except NameError: # pragma nocover
        PY3 = True
        asbytes = bytes
        joinbytes = bytes
        def bit(h, i):
            return (h[i//8] >> (i%8)) & 1

    import hashlib

    b = 256
    q = 2**255 - 19
    l = 2**252 + 27742317777372353535851937790883648493

    def H(m):
        return hashlib.sha512(m).digest()

    def expmod(b, e, m):
        if e == 0: return 1
        t = expmod(b, e // 2, m) ** 2 % m
        if e & 1: t = (t * b) % m
        return t

    # Can probably get some extra speedup here by replacing this with
    # an extended-euclidean, but performance seems OK without that
    def inv(x):
        return expmod(x, q-2, q)

    d = -121665 * inv(121666)
    I = expmod(2,(q-1)//4,q)

    def xrecover(y):
        xx = (y*y-1) * inv(d*y*y+1)
        x = expmod(xx,(q+3)//8,q)
        if (x*x - xx) % q != 0: x = (x*I) % q
        if x % 2 != 0: x = q-x
        return x

    By = 4 * inv(5)
    Bx = xrecover(By)
    B = [Bx % q,By % q]

    #def edwards(P,Q):
    #    x1 = P[0]
    #    y1 = P[1]
    #    x2 = Q[0]
    #    y2 = Q[1]
    #    x3 = (x1*y2+x2*y1) * inv(1+d*x1*x2*y1*y2)
    #    y3 = (y1*y2+x1*x2) * inv(1-d*x1*x2*y1*y2)
    #    return (x3 % q,y3 % q)

    #def scalarmult(P,e):
    #    if e == 0: return [0,1]
    #    Q = scalarmult(P,e/2)
    #    Q = edwards(Q,Q)
    #    if e & 1: Q = edwards(Q,P)
    #    return Q

    # Faster (!) version based on:
    # http://www.hyperelliptic.org/EFD/g1p/auto-twisted-extended-1.html

    def xpt_add(pt1, pt2):
        (X1, Y1, Z1, T1) = pt1
        (X2, Y2, Z2, T2) = pt2
        A = ((Y1-X1)*(Y2+X2)) % q
        B = ((Y1+X1)*(Y2-X2)) % q
        C = (Z1*2*T2) % q
        D = (T1*2*Z2) % q
        E = (D+C) % q
        F = (B-A) % q
        G = (B+A) % q
        H = (D-C) % q
        X3 = (E*F) % q
        Y3 = (G*H) % q
        Z3 = (F*G) % q
        T3 = (E*H) % q
        return (X3, Y3, Z3, T3)

    def xpt_double (pt):
        (X1, Y1, Z1, _) = pt
        A = (X1*X1)
        B = (Y1*Y1)
        C = (2*Z1*Z1)
        D = (-A) % q
        J = (X1+Y1) % q
        E = (J*J-A-B) % q
        G = (D+B) % q
        F = (G-C) % q
        H = (D-B) % q
        X3 = (E*F) % q
        Y3 = (G*H) % q
        Z3 = (F*G) % q
        T3 = (E*H) % q
        return (X3, Y3, Z3, T3)

    def pt_xform (pt):
        (x, y) = pt
        return (x, y, 1, (x*y)%q)

    def pt_unxform (pt):
        (x, y, z, _) = pt
        return ((x*inv(z))%q, (y*inv(z))%q)

    def xpt_mult (pt, n):
        if n==0: return pt_xform((0,1))
        _ = xpt_double(xpt_mult(pt, n>>1))
        return xpt_add(_, pt) if n&1 else _

    def scalarmult(pt, e):
        return pt_unxform(xpt_mult(pt_xform(pt), e))

    def encodeint(y):
        bits = [(y >> i) & 1 for i in range(b)]
        e = [(sum([bits[i * 8 + j] << j for j in range(8)]))
                                        for i in range(b//8)]
        return asbytes(e)

    def encodepoint(P):
        x = P[0]
        y = P[1]
        bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
        e = [(sum([bits[i * 8 + j] << j for j in range(8)]))
                                        for i in range(b//8)]
        return asbytes(e)

    def publickey(sk):
        h = H(sk)
        a = 2**(b-2) + sum(2**i * bit(h,i) for i in range(3,b-2))
        A = scalarmult(B,a)
        return encodepoint(A)

    def Hint(m):
        h = H(m)
        return sum(2**i * bit(h,i) for i in range(2*b))

    def signature(m,sk,pk):
        sk = sk[:32]
        h = H(sk)
        a = 2**(b-2) + sum(2**i * bit(h,i) for i in range(3,b-2))
        inter = joinbytes([h[i] for i in range(b//8,b//4)])
        r = Hint(inter + m)
        R = scalarmult(B,r)
        S = (r + Hint(encodepoint(R) + pk + m) * a) % l
        return encodepoint(R) + encodeint(S)

    def isoncurve(P):
        x = P[0]
        y = P[1]
        return (-x*x + y*y - 1 - d*x*x*y*y) % q == 0

    def decodeint(s):
        return sum(2**i * bit(s,i) for i in range(0,b))

    def decodepoint(s):
        y = sum(2**i * bit(s,i) for i in range(0,b-1))
        x = xrecover(y)
        if x & 1 != bit(s,b-1): x = q-x
        P = [x,y]
        if not isoncurve(P): raise Exception("decoding point that is not on curve")
        return P

    def checkvalid(s, m, pk):
        if len(s) != b//4: raise Exception("signature length is wrong")
        if len(pk) != b//8: raise Exception("public-key length is wrong")
        R = decodepoint(s[0:b//8])
        A = decodepoint(pk)
        S = decodeint(s[b//8:b//4])
        h = Hint(encodepoint(R) + pk + m)
        v1 = scalarmult(B,S)
    #  v2 = edwards(R,scalarmult(A,h))
        v2 = pt_unxform(xpt_add(pt_xform(R), pt_xform(scalarmult(A, h))))
        return v1==v2


    import warnings
    import os

    from collections import namedtuple

    __all__ = ['crypto_sign', 'crypto_sign_open', 'crypto_sign_keypair', 'Keypair',
               'PUBLICKEYBYTES', 'SECRETKEYBYTES', 'SIGNATUREBYTES']

    PUBLICKEYBYTES=32
    SECRETKEYBYTES=64
    SIGNATUREBYTES=64

    Keypair = namedtuple('Keypair', ('vk', 'sk')) # verifying key, secret key

    def crypto_sign_keypair(seed=None):
        """Return (verifying, secret) key from a given seed, or os.urandom(32)"""
        if seed is None:
            seed = os.urandom(PUBLICKEYBYTES)
        else:
            warnings.warn("ed25519ll should choose random seed.",
                          RuntimeWarning)
        if len(seed) != 32:
            raise ValueError("seed must be 32 random bytes or None.")
        # XXX should seed be constrained to be less than 2**255-19?
        skbytes = seed
        vkbytes = publickey(skbytes)
        return Keypair(vkbytes, skbytes+vkbytes)


    def crypto_sign(msg, sk):
        """Return signature+message given message and secret key.
        The signature is the first SIGNATUREBYTES bytes of the return value.
        A copy of msg is in the remainder."""
        if len(sk) != SECRETKEYBYTES:
            raise ValueError("Bad signing key length %d" % len(sk))
        vkbytes = sk[PUBLICKEYBYTES:]
        skbytes = sk[:PUBLICKEYBYTES]
        sig = signature(msg, skbytes, vkbytes)
        return sig + msg


    def crypto_sign_open(signed, vk):
        """Return message given signature+message and the verifying key."""
        if len(vk) != PUBLICKEYBYTES:
            raise ValueError("Bad verifying key length %d" % len(vk))
        rc = checkvalid(signed[:SIGNATUREBYTES], signed[SIGNATUREBYTES:], vk)
        if not rc:
            raise ValueError("rc != 0", rc)
        return signed[SIGNATUREBYTES:]


    return crypto_sign_keypair, crypto_sign, crypto_sign_open

ed25519_keypair, ed25519_sign, ed25519_verify = Ed25519()

## k = ed25519_keypair()
## msg = "hello world"
## sm = ed25519_sign(msg, k.sk)
## print len(sm)
## m2 = ed25519_verify(sm, k.vk)
## print "ok", m2 == msg


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
            assert key.startswith("vk0-")
            vk = from_ascii(key.replace("vk0-", ""))
            assert s_sig.startswith("sig0-")
            sig = from_ascii(s_sig.replace("sig0-", ""))
            try:
                ed25519_verify(sig+s_body, vk)
                found_good_signature = True
                debug("good signature found for branch %s (rev %s)" % (branch, proposed_branch_revid))
                break
            except ValueError:
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
