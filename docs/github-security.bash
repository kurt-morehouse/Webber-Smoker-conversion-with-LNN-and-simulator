# set up a clean GitHub workflow.

git --version
# Then set your name and email.
git config --global user.name 'kurt morehouse' user.email 'kurt.morehouse@gmail.com'

#cThen we need an SSH key.
ssh-keygen -ed25519 -c kurt.morehouse@gmail.com

val $'ssh-agent -s'
ssh -add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
 # paste it into GitHub under SSH keys.
 # Then test
 ssh -T git@github.com.

# with a repo for this project?
# from your project folder,
git init
git remote add origin git@github.com:kurt-morehouse/repo.git
git pull origin main
# then commit and push.
# If origin already exists, we can just use git remote set-url instead.
# Want to paste the output of git remote dash v, so I can guide you precisely?

