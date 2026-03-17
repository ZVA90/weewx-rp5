#!/bin/bash
#    WeeWX-RP5  macOS (v0.5)

set -e

# 
VERSION="0.5"
ARCHIVE_NAME="weewx-rp5-${VERSION}.tar.gz"

#  Locale
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export COPYFILE_DISABLE=1

echo "Cleaning up..."
rm -f *.tar.gz
find . -name ".DS_Store" -depth -exec rm {} \;

echo "Building version ${VERSION}..."

#     macOS
tar --exclude='.DS_Store' \
    --exclude='.git' \
    --exclude='.gitignore' \
    --exclude='make_release.sh' \
    -czvf "${ARCHIVE_NAME}" \
    bin/ \
    changelog \
    install.py \
    readme.txt

echo "Archive created: ${ARCHIVE_NAME}"

read -p "Push to GitHub? (y/n): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    #   
    git add bin/user/rp5.py install.py readme.txt changelog .gitignore make_release.sh
    #   ,    .gitignore
    git add -f "${ARCHIVE_NAME}"
    
    git commit -m "Release version ${VERSION}: Python 3 support"
    
    #       upstream   
    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "master")
    if ! git config "branch.$BRANCH.merge" >/dev/null; then
        git push -u origin "$BRANCH"
    else
        git push origin "$BRANCH"
    fi
    echo "Successfully pushed to $BRANCH"
fi
