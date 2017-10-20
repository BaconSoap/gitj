import sys
import keyring
import argparse
import os
from getpass import getpass
import json
import jira
from jira import JIRA, JIRAError
import subprocess

home_dir = os.path.expanduser('~')

parser = argparse.ArgumentParser('gitj', description='ties git and jira together')
parser.add_argument('--auth', action='store_true')
parser.add_argument('--create', action='store_true')
parser.add_argument('--hotfix', action='store_true')
parser.add_argument('--defaults', action='store_true')
parser.add_argument('--debug-auth', action='store_true')
parser.add_argument('-b', '--bug', action='store_true')
parser.add_argument('-t', '--title')
args = parser.parse_args()

def get_data_filename(filename: str) -> str:
    return os.path.join(home_dir, '.local/share/gitj/' + filename)

def get_auth():
    with open(get_data_filename('auth'), 'r') as username_file:
        auth = json.load(username_file)
    auth['password'] = keyring.get_password('gitj', auth['username'])
    return auth

def get_defaults():
    with open(get_data_filename('defaults'), 'r') as defaults_file:
        defaults = json.load(defaults_file)
    return defaults

def get_jira() -> jira.client:
    auth = get_auth()
    return JIRA(auth['server'], basic_auth=(auth['username'], auth['password']))


def create_issue(title: str, issueType: str) -> jira.Issue:
    defaults = get_defaults()
    jira = get_jira()
    issue = jira.create_issue(project=defaults['project'],
                              summary=title,
                              issuetype={'name': issueType})
    issue.update(fields={'customfield_10800': [{'value': defaults['team']}]})
    return issue

os.makedirs(get_data_filename(''), exist_ok=True)

if args.auth:
    jira_url = input('jira url (ex `https://jira.atlassian.com`):')
    user = input('username:')
    pw = getpass('password:')
    print('testing connection:')

    try:
        authedJira = JIRA(jira_url, basic_auth=(user, pw), max_retries=0)

    except JIRAError as err:
        raise Exception('failed to authenticate') from err

    print('connection succeeded')
    keyring.set_password('gitj', user, pw)
    with open(get_data_filename('auth'), 'w+') as username_file:
        data = {'username': user, 'server': jira_url}
        json.dump(data, username_file)


if args.debug_auth:
    auth = get_auth()
    print(auth['username'])
    print(len(auth['password']))
    print(auth['server'])


if args.defaults:
    project = input('default project:')
    team = input('default team:')
    data = {'project': project, 'team': team}
    with open(get_data_filename('defaults'), 'w+') as defaults_file:
        json.dump(data, defaults_file)

if args.create:
    if args.title is None:
        print('--title (-t) must be specified when creating an issue')
        raise Exception

    defaults = get_defaults()

    issueType = 'Story'
    if args.bug:
        issueType = 'Bug'

    issue = create_issue(args.title, issueType)

    print('created issue: ' + issue.key + ' in project: ' + issue.fields.project.raw['name'])

def run_unchecked(commands: [str]) -> subprocess.CompletedProcess:
    return subprocess.run(commands, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run(commands: [str], fail_text: str):
    res = run_unchecked(commands)
    if res.returncode != 0:
        print(fail_text)
        print(res.stdout)
        print(res.stderr)
        raise Exception

if args.hotfix:
    title: str = args.title
    if title is None:
        print('--title (-t) must be specified when running hotfix')
        raise Exception

    # verify clean repo state
    is_clean = run_unchecked(['git', 'diff-index', '--quiet', 'HEAD']).returncode
    if is_clean != 0:
        print('can only run hotfix on a clean repo. stash or discard changes before running again')
        raise Exception

    untracked = run_unchecked(['git', 'ls-files', '--exclude-standard', '--others', '--'])
    if len(untracked.stdout) != 0:
        print('can only run hotfix on a clean repo and there are currently new files. stash or discard changes before running again')
        raise Exception

    print('switching to master...')
    run(['git', 'checkout', 'master'], 'failed to switch to master')

    print('fetching latest...')
    run(['git', 'fetch', '-p'], 'failed to fetch latest')

    print('resetting to origin/master...')
    run(['git', 'reset', '--hard', 'origin/master'], 'failed to reset to origin/master')

    print('creating jira issue...')
    issue = create_issue(title, 'Bug')
    print('created ' + issue.key + ': ' + title)

    key = issue.key.lower()
    kebab_title = title.lower()\
        .replace(' ', '-')\
        .replace('_', '-')\
        .replace('?', '')\
        .replace(':', '')\
        .replace('/', '')\
        .replace('!', '')
    branch_name = 'hotfix/' + key + '-' + kebab_title

    print('creating and switching to new branch ' + branch_name + '...')
    run(['git', 'checkout', '-b', branch_name], 'failed to checkout new branch')
