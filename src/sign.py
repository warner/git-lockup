
# needs common
# needs ed25519

def sign(args):
    # this is called from .git/hooks/post-commit . The post-commit hook gets
    # no arguments, so neither do we.
    print "--"
    print "IN POST-COMMIT"
    print "CWD is", os.getcwd()
    for name in sorted(os.environ):
        if name.startswith("GIT"):
            print "%s: %s" % (name, os.environ[name])
    print "--"
    rev = run_command(["git", "rev-parse", "HEAD"]).strip()
    fullbranch = run_command(["git", "rev-parse", "--symbolic-full-name", "HEAD"]).strip()
    branch = remove_prefix(fullbranch, "refs/heads/")
    if not branch:
        print "not commiting to refs/heads/ , ignoring"
        sys.exit(0)
    pieces = branch.split("/")
    if "." in pieces or ".." in pieces:
        print "scary branch name %s, ignoring" % branch
        sys.exit(0)
    print "branch:", branch
    print "HEAD:", rev
    msg = "%s=%s" % (fullbranch, rev)
    print "MSG:", msg

    keys = get_config("branch.%s.assure-sign-key" % branch)
    if not keys:
        print "No signing key in .git/config, ignoring"
        sys.exit(0)
    key_pieces = keys.split()
    if not keys[0].startswith("sk0-"):
        raise Exception("Unrecognized signing key format")
    sk = from_ascii(remove_prefix(keys[0], "sk0-"))
    if not keys[1].startswith("vk0-"):
        raise Exception("Unrecognized verifying key format")
    vk = from_ascii(remove_prefix(keys[1], "vk0-"))

    sig_and_msg = ed25519_sign(msg, sk)
    sig = sig_and_msg[:32]
    sig_s = "sig0-"+to_ascii(sig)
    line = "assure: %s %s %s" % (msg, sig_s, keys[1])
    print line

    run_command(["git", "notes", "append", "-m", line, rev])
    print "note added"
