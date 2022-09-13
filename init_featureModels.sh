echo "[INFO] Removing old data..."
rm -rf ../data/FeatureModels
echo "[INFO] Done!"
# Extract all Feature Models to data/FeatureModels
echo "[INFO] Extracting backup files..."
pushd ../data/backup > /dev/null
unzip -q featureModels.zip -d ./..
popd > /dev/null
echo "[INFO] Done!"

echo "[INFO] Preparing models..."
pushd ../data/FeatureModels > /dev/null
returnCode=0
for D in *; do
    if [ -d "${D}" ]; then
        # remove everything expect files ending with model.xml
        pushd "./${D}" > /dev/null
        find . -type f -not -name 'model.xml' -delete
        mv 'model.xml' "${D}.xml" 2>/dev/null
        returnCode=$?
        if [ $returnCode -ne 0 ]; then
            echo "[WARN] Could not find model.xml in folder ${D}"
        fi
        popd > /dev/null
    fi
done
popd > /dev/null
echo "[INFO] Done!"
echo "[INFO] Moving into ddueruem workspace..."
rm -rf evaluation/ > /dev/null
mkdir evaluation
cp -r ../data/FeatureModels/* evaluation/
echo "[INFO] Done!"
echo "----Workspace is prepared!----"