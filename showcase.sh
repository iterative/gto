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
# env_branch_mapping:
#   master: production
#   demo: demo
EOF

echo "Create new models"
mkdir models
echo "1st version" > models/random-forest.pkl
echo "1st version" > models/neural-network.pkl
# cat << EOF > index.yaml
# - type: model
#   name: rf
#   path: models/random-forest.pkl
# - type: model
#   name: nn
#   path: models/neural-network.pkl
# - type: dataset
#   name: features
#   path: datasets/features.csv
# EOF
# cat << EOF > index.yaml
# rf:
#   type: model
#   path: models/random-forest.pkl
# nn:
#   type: model
#   path: models/neural-network.pkl
# features:
#   type: dataset
#   path: datasets/features.csv
# EOF
# cat << EOF > index_type.yaml
# model:
#   - name: rf
#     path: models/random-forest.pkl
#   - name: nn
#     path: models/neural-network.pkl
# dataset:
#   - name: features
#     path: datasets/features.csv
# EOF
gto add rf model models/random-forest.pkl
gto add nn model models/neural-network.pkl
gto add features dataset datasets/features.csv
git add artifacts.yaml models
git commit -am "Create models"

echo "Register new model"
gto register rf v1 HEAD
gto register nn v1 HEAD

echo "Update the model"
sleep 1
echo "2nd version" > models/random-forest.pkl
git commit -am "Update model"

echo "Register models"
gto register rf v2 HEAD

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

gto show
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
