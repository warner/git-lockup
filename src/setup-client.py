
def setup_client(remote, branch, key):
    rawurl, rawpushurl = set_config_raw_urls(remote)
    ext_url = "ext::.git/assure-tool fetch %s %s" % (remote, rawurl)
    run_command(["git", "config", "remote.%s.url" % remote, ext_url])
    # we must make sure pushurl is set too, since our proxy doesn't know how
    # to push anything. If they already had a pushurl, stick with it.
    # Otherwise set pushurl equal to the old raw url.
    if not get_config("remote.%s.pushurl" % remote):
        run_command(["git", "config", "remote.%s.pushurl" % remote, rawurl])
    print "remote '%s' configured to use verification proxy" % remote

    verfkeys = get_all_config("branch.%s.assure-key" % branch)
    if key in verfkeys:
        print "branch '%s' was already configured to verify with key %s" % (branch, key)
    else:
        run_command(["git", "config", "--add", "branch.%s.assure-key" % branch, key])
        print "branch '%s' configured to verify with key %s" % (branch, key)
