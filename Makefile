create-sample:
	git init sample
	ln -s ../../../hooks/post-commit sample/.git/hooks/post-commit
	chmod +x hooks/post-commit

commit:
	date >>sample/date.txt
	cd sample && git add date.txt && git commit -m "commit"

