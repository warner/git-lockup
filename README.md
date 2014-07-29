git-lockup : sign and verify author signatures on git commits
=============================================================

[![Build Status](https://travis-ci.org/warner/git-lockup.png?branch=master)](https://travis-ci.org/warner/git-lockup)

This tool makes it easy to "lock" your git checkout to the author's signing key, meaning you'll get the correct commits even if the network (or an intermediate repository like Github) is trying to convince you otherwise.

If you're just following a repository:

* do your `git clone`
* you'll find a script named `./setup-lockup` in the new tree
* run it
* that will configure git-lockup with the author's embedded public key
* now every `git fetch` or `git pull` you do from the origin repository will check signatures before allowing the fetch to go through

If you're publishing a tree:

* run `git-lockup setup-publish` in your source tree
* that will create a keypair and configure a post-commit hook to sign commits
* it will also create `setup-lockup` and git-add it for inclusion in your tree

## Dependencies

git-lockup is a self-contained python program. All crypto uses a pure-python implementation of the ed25519 signature system by djb. All python dependencies are in the standard library.

## Compatibility

git-lockup has been tested against python2.6 and python2.7 . It might work on other versions, I don't know yet.

## Security Model

## Implementation Details

git-lockup creates a short Ed25519 signature for each (branch, commitid) pair. The signature is stored in a "git note" associated with the commit id, in a line that looks like:

    lockup: refs/heads/$BRANCH=$COMMITID sig0-$SIG vk0-$VERFKEY

(you can use `git notes show HEAD` to see the signature for the current revision).

The publisher's .git/hooks/post-commit hook is modified to run `git-lockup post-commit` after each commit, which examines .git/config to see what key should be used to sign the current branch (if any). The .git/config `[remote]` section is also modified to push the notes (`refs/notes/commits`) in addition to the usual matching branches, so the signatures get pushed to upstream repos any time the commits get pushed.

On the receiving side, the git checkout's .git/config is modified to replace the remote URL with a special proxy (url=`ext::.git/git-lockup ARGS`) that gets control whenever you try to fetch from that remote. The proxy fetches everything (commits and notes) to a temporary remote (`$NAME-lockup-temp`) and checks the signatures. If it likes what it sees, the proxy reports the new branch heads back to the caller, which then looks at the local object store and discovers that all the necessary objects are already present, so it doesn't ask the proxy to fetch any objects (simplifying the code considerably).

The signature verification asserts that:

* the new branch head is signed by one of the keys listed in the receiver's config file
* the new branch head is a descendant of the current branch head (to prevent rollback attacks)

To minimize deployment problems, git-lockup is distributed as a single file executable. It is assembled from multiple source files, and when run, it copies all or part of itself into the git tree (`.git/git-lockup` and `setup-lockup`). It's not exactly a quine, but it comes close.

## Tricks

If you need to bypass the fetch-time verification checks, just use the explicit-URL form, e.g. `git fetch https://github.com/USER/REPO BRANCH`, which puts the results in a special reference named `FETCH_HEAD`. Once it's in FETCH_HEAD, you can merge it into your current branch. git-lockup only gets involved when you do `git fetch REMOTENAME`.

If you need to allow multiple authors to sign commits, you have two options. The first is to have them all to share a single signing key (which lives in .git/config, in `[branch NAME].lockup-sign-key`). The second is to use multiple signing keys: put multiple `[branches].NAME` lines (one per key) into the distributed `lockup.config` file.

To manually add a new author to an existing checkout, edit .git/config and add the additional verifying keys to (multple) `[branch NAME].lockup-key` entries. You can also re-run `./setup-lockup` and it will change your .git/config to use the current contents of `lockup.config`.

## Contact

Please file bugs and patches at the Github project: http://github.com/warner/git-lockup

git-lockup is:

* by Brian Warner
* released into the [public domain](https://creativecommons.org/publicdomain/zero/1.0/) to enable no-fuss embedding
