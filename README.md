# gitj

1. `gitj auth` and follow the prompts (password is stored in system credential manager, eg keychain on mac and windows credential store on windows. it may or may not prompt a password/UAC check)
2. `gitj defaults` and follow the prompts
3. `gitj --create --title 'item with stuff'` makes a new Story with that summary in the configured jira instance (adding `--bug` in there makes it a bug)
4. `gitj --hotfix --title 'fix stuff I broke'` creates a new jira bug using the defaults, switches to master, gets latest master, and checks out a new branch of the form `hotfix/<item key>-<kebab-cased title>`, and can helpfully fail in many ways
