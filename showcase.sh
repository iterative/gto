#!/bin/sh
echo "Clean workspace"
if [[ $(git --no-pager diff) ]]; then
    echo "Workspace is dirty, please commit or stash changes before running this script"
    exit 1
fi
git tag -d $(git tag --list)
git branch -D demo
set -exu
git checkout -b demo
rm -rf models gto.yaml artifacts.yaml

cat << EOF > gto.yaml
env_base: tag
versions_convention: numbers
# env_branch_mapping:
#   master: production
#   demo: demo
EOF

echo "Create new models"
mkdir models
echo "1st version" > models/random-forest.pkl
echo "1st version" > models/neural-network.pkl
gto add rf model models/random-forest.pkl
gto add nn model models/neural-network.pkl
gto add features dataset datasets/features.csv
git add artifacts.yaml models
git commit -am "Create models"

echo "Register new model"
gto register rf HEAD v1
gto register nn HEAD v1

echo "Update the model"
sleep 1
echo "2nd version" > models/random-forest.pkl
git commit -am "Update model"

echo "Register models"
gto register rf HEAD

echo "Promote models"
gto promote nn staging --version v1
sleep 1
gto promote rf production --version v1
sleep 1
gto promote rf staging --ref HEAD
sleep 1
gto promote rf production --ref `git rev-parse HEAD`
sleep 1
gto promote rf production --version v1

gto show -v
gto audit all


cat << EOF
Now you have your models registered and promoted.
Try to unregister and demote them and see what happens by running "gto show"
For example:
gto unregister rf v1
gto demote rf v2

Right now you can't delete tags to unregister/demote models.
Only create new tags which will do that.
EOF
