#!/bin/sh
gitops() {
    python main.py "$@"
}

echo "Clean workspace"
set -exu
if [[ $(git --no-pager diff) ]]; then
    echo "Workspace is dirty, please commit or stash changes before running this script"
    exit 1
fi
git tag -d $(git tag --list)
git branch -D demo
git checkout -b demo
rm -rf models

echo "Create new models"
mkdir models
echo "1st version" > models/random-forest.pkl
echo "1st version" > models/neural-network.pkl
git add models
git commit -am "Create models"

echo "Register new model"
gitops register models/random-forest.pkl v1
gitops register models/neural-network.pkl v1
# gitops register models/random-forest.pkl $COMMIT_HASH v1

echo "Update the model"
sleep 1
echo "2nd version" > models/random-forest.pkl
git commit -am "Update model"

echo "Register models"
gitops register models/random-forest.pkl v2

echo "Promote models"
gitops promote models/neural-network.pkl v1 staging
sleep 1
gitops promote models/random-forest.pkl v1 production
sleep 1
gitops promote models/random-forest.pkl v2 staging
sleep 1
gitops promote models/random-forest.pkl v2 production
sleep 1
gitops promote models/random-forest.pkl v1 production

gitops show


# model-models/random-forest.pkl-register-v1
# model-models/random-forest.pkl-unregister-v1

# model-models/random-forest.pkl-promote-production-1
# model-models/random-forest.pkl-demote-production-2
# model-models/random-forest.pkl-promote-production-3

# model-models/random-forest.pkl-promote-production-1
# model-models/random-forest.pkl-demote-production-1
# model-models/random-forest.pkl-promote-production-2


# gitops unregister models/random-forest.pkl v1
# gitops demote models/random-forest.pkl v1

# gitops destroy models/random-forest.pkl --version v1
# gitops destroy models/random-forest.pkl --label production

# gitops unregister models/random-forest.pkl v1 --destroy
# gitops demote models/random-forest.pkl v1 --destroy
