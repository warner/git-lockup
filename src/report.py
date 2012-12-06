
def report(args):
    print "REPORT"

    # for every branch mentioned in .git/config, report whether we sign
    # commits, and whether we require signatures. Also check on the proxy
    # config and the post-commit hook.

    current_branch = None
    all_branches = set()
    for line in run_command(["git", "branch", "--list"]).splitlines():
        name = line.strip("* ")
        if line.startswith("*"):
            current_branch = name
        all_branches.add(name)

    configured_branches = set()
    for line in get_config_regexp("^branch\."):
        configured_branches.add(line.split(".")[1])

    remotes = set()
    for line in get_config_regexp("^remote\."):
        remotes.add(line.split(".")[1])

    hook_ready = True
    try:
        contents = open(".git/hooks/post-commit", "rb").read()
        if contents != post_commit:
            print "post-commit hook exists, but differs from what I expected"
            hook_ready = False
        if not os.access(".git/hooks/post-commit", os.X_OK):
            print "post-commit hook exists, but is not executable"
            hook_ready = False
    except EnvironmentError:
        print ".git/hooks/post-commit doesn't exist"
        hook_ready = False
    if hook_ready:
        print "post-commit hook is correct and executable"

    for branch in sorted(all_branches):
        desc = []
        if branch in configured_branches:
            configured = True
            signkey = get_config("branch.%s.assure-sign-key" % branch)
            if signkey:
                sk = from_ascii(remove_prefix(signkey, "sk0-"))
                vk_s = "vk0-"+to_ascii(ed25519_create_verifying_key(sk))
                desc.append("will sign (%s)" % vk_s)
            verifykeys = get_all_config("branch.%s.assure-key" % branch)
            for key in set(verifykeys):
                desc.append("will verify (%s)" % key)
        else:
            desc.append("no configuration")

        print "branch %s: %s" % (branch, ", ".join(desc))
