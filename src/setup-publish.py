
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
        make_executable(pc)
    set_hook()

    # once per remote
    pushes = get_all_config("remote.%s.push" % remote)
    if not pushes:
        run_command(["git", "config", "--add", "remote.%s.push" % remote, ":"])
    notes_push = "refs/notes/commits:refs/notes/commits"
    if notes_push not in pushes:
        run_command(["git", "config", "--add", "remote.%s.push" % remote,
                     notes_push])
    rawurl, rawpushurl = set_config_raw_urls(remote)

    # once per branch
    signkey_key = "branch.%s.assure-sign-key" % branch
    verfkey_key = "branch.%s.assure-key" % branch
    old_key = get_config(signkey_key)
    if old_key:
        print "branch '%s' already has a key configured, ignoring" % branch
        sk = from_ascii(remove_prefix(old_key, "sk0-"))
        vk_s = "vk0-%s" % to_ascii(ed25519_create_verifying_key(sk))
    else:
        sk = ed25519_create_signing_key()
        sk_s = "sk0-%s" % to_ascii(sk)
        run_command(["git", "config", signkey_key, sk_s])
        print "the post-commit hook will now sign changes on branch '%s'" % branch
        vk_s = "vk0-%s" % to_ascii(ed25519_create_verifying_key(sk))
        run_command(["git", "config", verfkey_key, vk_s])
    print "verifykey: %s" % vk_s

    # now create setup-assure, including this. quine!

