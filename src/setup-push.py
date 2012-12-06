
import base64

post_commit_b64 = """
#<-- post-commit-b64
"""
post_commit = base64.b64decode(post_commit_b64)

def setup_publish(args):
    create_keypair = False
    if args[0] == "--create-keypair":
        create_keypair = True
        args = args[1:]
    remote = "origin"
    branch = args[0]

    def set_hook():
        # once per repo
        pc = ".git/hooks/post-commit"
        if os.path.exists(pc):
            old = open(pc, "rb").read()
            if old == post_commit:
                return
            announce("old .git/hooks/post-commit is in the way")
            return
        f = open(pc, "wb")
        f.write(post_commit)
        f.close()
        oldmode = os.stat(pc).st_mode & int("07777", 8)
        newmode = (oldmode | int("0555", 8)) & int("07777", 8)
        os.chmod(pc, newmode)
    set_hook()

    # once per remote
    run_command(["git", "config", "--add", "remote.%s.push" % remote, ":"])
    run_command(["git", "config", "--add", "remote.%s.push" % remote,
                 "refs/notes/commits:refs/notes/commits"])

    # once per branch
    keykey = "branch.%s.assure-key" % branch
    old_key = get_config(keykey)
    if old_key:
        print "branch '%s' already has a key configured, ignoring" % branch
        sys.exit(0)

    keys = ed25519_keypair()
    run_command(["git", "config", keykey,
                 "sk0-%s vk0-%s" % (to_ascii(keys.sk), to_ascii(keys.vk))])
    print "the post-commit hook will now sign changes on branch '%s'" % branch
