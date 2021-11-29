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
versions: NumberedVersion  # or SemVer - but it's not supported yet
environments:  # prototype will ensure you can only promote to these environments
- production
- staging
EOF

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


cat << EOF
Now you have your models registered and promoted.
Try to unregister and demote them and see what happens by running "gitops show"
For example:
gitops unregister models/random-forest.pkl v1
gitops demote models/random-forest.pkl v2

Right now you can't delete tags to unregister/demote models.
Only create new tags which will do that.
EOF

gitops promote models/random-forest.pkl v1 production
gitops promote models/random-forest.pkl 123dabe5 production --name-version 1.0.1
