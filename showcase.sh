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
rm -rf models gitops_config.yaml

cat << EOF > gitops_config.yaml
ENV_BASE: tag
# ENV_BRANCH_MAPPING:
#   master: production
#   demo: demo
EOF

echo "Create new models"
mkdir models
echo "1st version" > models/random-forest.pkl
echo "1st version" > models/neural-network.pkl
cat << EOF > index.yaml
- type: model
  name: rf
  path: models/random-forest.pkl
- type: model
  name: nn
  path: models/neural-network.pkl
- type: dataset
  name: features
  path: datasets/features.csv
EOF
git add index.yaml models
git commit -am "Create models"

echo "Register new model"
gitops register rf v1
gitops register nn v1

echo "Update the model"
sleep 1
echo "2nd version" > models/random-forest.pkl
git commit -am "Update model"

echo "Register models"
gitops register rf v2

echo "Promote models"
gitops promote nn staging --version v1
sleep 1
gitops promote rf production --version v1
sleep 1
gitops promote rf staging --commit `git rev-parse HEAD`
sleep 1
gitops promote rf production --commit `git rev-parse HEAD`
sleep 1
gitops promote rf production --version v1

gitops show


cat << EOF
Now you have your models registered and promoted.
Try to unregister and demote them and see what happens by running "gitops show"
For example:
gitops unregister rf v1
gitops demote rf v2

Right now you can't delete tags to unregister/demote models.
Only create new tags which will do that.
EOF
