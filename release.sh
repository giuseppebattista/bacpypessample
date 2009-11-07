#!/bin/sh
# Release helper for this project

PROJECT=bacpypes
CHANGELOG=ChangeLog-$1
FRS_URL=skarg,bacpypes@frs.sourceforge.net:/home/frs/project/b/ba/bacpypes

if [ -z "$1" ]
then
  echo "Usage: `basename $0` datecode"
  echo "Creates the ChangeLog."
  echo "Creates the release files."
  echo "Tags the current version in subversion."
  echo "Uploads the release files to SourceForge.net."
  exit 1
fi

VERSION=$1

echo "Creating the release files for version ${VERSION}"

echo "Creating the ${PROJECT} change log..."
rm ${CHANGELOG}
svn update
svn log --xml --verbose | xsltproc svn2cl.xsl - > ${CHANGELOG}
if [ -z "${CHANGELOG}" ]
then
echo "Failed to create ${CHANGELOG}"
else
echo "${CHANGELOG} created."
fi

VERSION_NAME=${PROJECT}-${VERSION}
SVN_BASE_URL=https://${PROJECT}.svn.sourceforge.net/svnroot/${PROJECT}

SVN_TRUNK_NAME=${SVN_BASE_URL}/trunk
SVN_TAGGED_NAME=${SVN_BASE_URL}/tags/${VERSION_NAME}
echo "Tagging the trunk as ${VERSION_NAME}"
svn copy ${SVN_TRUNK_NAME} ${SVN_TAGGED_NAME} -m "Created version ${VERSION_NAME}" 
echo "done."

echo "Getting a clean version out of subversion for Linux gzip"
svn export ${SVN_TAGGED_NAME} ${VERSION_NAME}
echo "done."

GZIP_FILENAME=${VERSION_NAME}.tgz
echo "tar and gzip the clean directory"
tar -cvvzf ${GZIP_FILENAME} ${VERSION_NAME}/
echo "done."

if [ -z "${GZIP_FILENAME}" ]
then
echo "Failed to create ${GZIP_FILENAME}"
else
echo "${GZIP_FILENAME} created."
fi

rm -rf ${VERSION_NAME}

echo "Getting another clean version out of subversion for Windows zip"
svn export --native-eol CRLF ${SVN_TAGGED_NAME} ${VERSION_NAME}
ZIP_FILENAME=${VERSION_NAME}.zip
echo "done."
echo "Zipping the directory exported for Windows."
zip -r ${ZIP_FILENAME} ${VERSION_NAME}

if [ -z "${ZIP_FILENAME}" ]
then
echo "Failed to create ${ZIP_FILENAME}"
else
echo "${ZIP_FILENAME} created."
fi

rm -rf ${VERSION_NAME}

echo "Sending to SourceForge..."

mkdir ${VERSION_NAME}
mv ${ZIP_FILENAME} ${VERSION_NAME}
mv ${GZIP_FILENAME} ${VERSION_NAME}
mv ${CHANGELOG} ${VERSION_NAME}
scp -r ${VERSION_NAME} ${FRS_URL}

echo "Complete!"
