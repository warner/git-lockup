
# needs post_commit

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
    pushes = get_all_config("remote.%s.push" % remote)
    if not pushes:
        run_command(["git", "config", "--add", "remote.%s.push" % remote, ":"])
    notes_push = "refs/notes/commits:refs/notes/commits"
    if notes_push not in pushes:
        run_command(["git", "config", "--add", "remote.%s.push" % remote,
                     notes_push])
    # set pushurl to url without the ext:: stuff
    old_pushurl = get_config("remote.%s.pushurl" % remote)
    if not old_pushurl:
        url = get_config("remote.%s.url" % remote)
        url.replace("ext::.git/assure-tool fetch %s " % remote, "")
        run_command(["git", "config", "remote.%s.pushurl" % remote, url])

    # once per branch
    keykey = "branch.%s.assure-sign-key" % branch
    old_key = get_config(keykey)
    if old_key:
        print "branch '%s' already has a key configured, ignoring" % branch
        sk = from_ascii(remove_prefix(old_key, "sk0-"))
    else:
        sk = ed25519_create_signing_key()
        run_command(["git", "config", keykey, "sk0-%s" % to_ascii(sk)])
        print "the post-commit hook will now sign changes on branch '%s'" % branch
    vk = ed25519_create_verifying_key(sk)
    print "verifykey: vk0-%s" % to_ascii(vk)
