#!/bin/sh
# Release helper for this project

PROJECT=bacpypes
CHANGELOG=ChangeLog
FRS_URL=skarg,bacpypes@frs.sourceforge.net:/home/frs/project/b/ba/bacpypes

if [ -z "$1" ]
then
  echo "Usage: `basename $0` 0.0.0"
  echo "Creates the ChangeLog."
  echo "Creates the release files."
  echo "Tags the current version in subversion."
  echo "Uploads the release files to SourceForge.net."
  exit 1
fi

# convert 0.0.0 to 0-0-0
DOTTED_VERSION="$1"
DASHED_VERSION="$(echo "$1" | sed 's/[\.*]/-/g')"

echo "Creating the release files for version ${DOTTED_VERSION}"

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

ARCHIVE_NAME=${PROJECT}-${DOTTED_VERSION}
TAGGED_NAME=${PROJECT}-${DASHED_VERSION}
SVN_BASE_URL=https://${PROJECT}.svn.sourceforge.net/svnroot/${PROJECT}

SVN_TRUNK_NAME=${SVN_BASE_URL}/trunk
SVN_TAGGED_NAME=${SVN_BASE_URL}/tags/${TAGGED_NAME}
echo "Tagging the trunk as ${TAGGED_NAME}"
svn copy ${SVN_TRUNK_NAME} ${SVN_TAGGED_NAME} -m "Created version ${ARCHIVE_NAME}" 
echo "done."

echo "Getting a clean version out of subversion for Linux gzip"
svn export ${SVN_TAGGED_NAME} ${ARCHIVE_NAME}
echo "done."

GZIP_FILENAME=${ARCHIVE_NAME}.tgz
echo "tar and gzip the clean directory"
tar -cvvzf ${GZIP_FILENAME} ${ARCHIVE_NAME}/
echo "done."

if [ -z "${GZIP_FILENAME}" ]
then
echo "Failed to create ${GZIP_FILENAME}"
else
echo "${GZIP_FILENAME} created."
fi

rm -rf ${ARCHIVE_NAME}

echo "Getting another clean version out of subversion for Windows zip"
svn export --native-eol CRLF ${SVN_TAGGED_NAME} ${ARCHIVE_NAME}
ZIP_FILENAME=${ARCHIVE_NAME}.zip
echo "done."
echo "Zipping the directory exported for Windows."
zip -r ${ZIP_FILENAME} ${ARCHIVE_NAME}

if [ -z "${ZIP_FILENAME}" ]
then
echo "Failed to create ${ZIP_FILENAME}"
else
echo "${ZIP_FILENAME} created."
fi

rm -rf ${ARCHIVE_NAME}

echo "Sending to SourceForge..."

mkdir ${ARCHIVE_NAME}
mv ${ZIP_FILENAME} ${ARCHIVE_NAME}
mv ${GZIP_FILENAME} ${ARCHIVE_NAME}
mv ${CHANGELOG} ${ARCHIVE_NAME}
scp -r ${ARCHIVE_NAME} ${FRS_URL}

echo "Complete!"
