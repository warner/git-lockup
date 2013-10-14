
# Welcome to git-assure!

# By running this program, your git checkout will be configured to check
# per-revision signatures every time you fetch new changes. This will
# ensure that you only get changes from the upstream author of this
# project, preventing unauthorized commits injected at any intermediate
# repositories or hosting providers.

import os, sys, base64

def make_executable(tool):
    oldmode = os.stat(tool).st_mode & int("07777", 8)
    newmode = (oldmode | int("0555", 8)) & int("07777", 8)
    os.chmod(tool, newmode)

# this is filled in by "git-assure setup-publish", with a copy of git-assure.
git_assure_b64 = """
GIT_ASSURE_B64
"""

# First we install .git/git-assure
assert os.path.isdir(".git")
tool = os.path.abspath(".git/git-assure")
f = open(tool, "wb")
f.write(base64.b64decode(git_assure_b64))
f.close()
make_executable(tool)

# Then we run "git-assure setup-client" to configure everything. This will
# read assure.config to determine the branch/pubkey list before modifying
# .git/config
os.execv(sys.executable, [sys.executable, tool, "setup-client"])
