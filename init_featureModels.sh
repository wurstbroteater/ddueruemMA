echo "[INFO] Removing old data..."
rm -rf ./examples/rawFMs
echo "[INFO] Done!"
# Extract all Feature Models to examples/FeatureModels
echo "[INFO] Extracting backup files..."
mkdir -p ./examples/rawFMs
pushd ./examples/rawFMs >/dev/null
unzip  -q ../featureModels.zip
cp -r ./FeatureModels/* .
rm -rf FeatureModels/
# model is broken / void
rm -rf WaterlooGenerated/
popd >/dev/null
echo "[INFO] Done!"

echo "[INFO] Preparing models..."
pushd ./examples/rawFMs >/dev/null
returnCode=0
for D in *; do
  if [ -d "${D}" ]; then
    pushd "./${D}" >/dev/null
    ## ,, is to lower case
    if [ "${D,,}" = "velvet" ]; then
      mv ./HelloWorldMPL-VELVET/model.xml .
    fi
    # remove all files expect files ending with model.xml
    find . -type f -not -name 'model.xml' -delete
    # remove all dirs
    find . -type d -exec rm -rf {} + 2>/dev/null
    mv 'model.xml' "${D}.xml" 2>/dev/null
    returnCode=$?
    if [ $returnCode -ne 0 ]; then
      echo "[WARN] Could not find model.xml in folder ${D}"
    fi
    popd >/dev/null
  fi
done
popd >/dev/null
echo "[INFO] Done!"

echo "[INFO] Moving into ddueruem workspace..."
rm -rf evaluation/ >/dev/null
mkdir evaluation
cp -r ./examples/rawFMs/* evaluation/
echo "[INFO] Done!"
echo "----Workspace is prepared!----"
