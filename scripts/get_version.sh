#!/bin/sh

commit=$(git rev-parse --short HEAD)

# This is true if there is a tag on current HEAD
if git describe --exact-match > /dev/null 2>&1
then
		tag_val=$(git describe --dirty=DIRTY --exact-match)
		case "$tag_val" in 
				*DIRTY)
						echo "git=$commit-changes"
						;;
				v*) # Only consider tags starting with v
						echo "$tag_val"
						;;
				*)
						echo "git-$commit"
		esac
else
		tag_val=$(git describe --dirty=DIRTY)
		case "$tag_val" in 
				*DIRTY)
						echo "git-$commit-changes"
						;;
				*)
						echo "git-$commit"
		esac
fi

