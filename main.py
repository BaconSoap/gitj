import sys
import keyring
import argparse
import os
from getpass import getpass
import json
import jira
from jira import JIRA, JIRAError

home_dir = os.path.expanduser('~')

parser = argparse.ArgumentParser('gitj', description='ties git and jira together')
parser.add_argument('--auth', action='store_true')
parser.add_argument('--create', action='store_true')
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
    print(args.title)
    if args.title is None:
        print('--title (-t) must be specified when creating an issue')
        raise Exception

    defaults = get_defaults()

    issueType = 'Story'
    if args.bug:
        issueType = 'Bug'

    jira = get_jira()
    issue = jira.create_issue(project=defaults['project'], summary=args.title, issuetype={'name': issueType})
    print('created issue: ' + issue.key + ' in project: ' + issue.fields.project.raw['name'])
    issue.delete()
    print('successfully deleted test issue')