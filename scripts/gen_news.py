import os
import requests
import datetime
import certifi
import openai
from pytz import timezone
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

TOKEN = os.environ.get('TOKEN')
ORG_NAME = os.environ.get('ORG_NAME')
NEWS_TYPE = os.environ.get('NEWS_TYPE')

# Set the SSL certificates path
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

def chinese_weekday(date):
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    return weekdays[date.weekday()]

# Function to get an HTTP session with retry logic
def get_http_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    return session

# Use the session with retry logic for API requests
session = get_http_session()

# Headers for authentication
headers = {
    'Authorization': f'token {TOKEN}'
}

# Generate a funny summary using GPT-3.5-turbo
def generate_summary(report_text):
    prompt = f"Generate a summary for the weekly commit report in Chinese:\n\n{report_text}\n\n---\n\nSummary:"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    openai.base_url = "https://aihubmix.com/v1/"
    openai.default_headers = {"x-foo": "true"}
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
            ],
        )
        return completion.choices[0].message.content
    except:
        return None

# Function to get all public repos in the organization
def get_org_public_repos(url):
    repos = []
    while url:
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            repos.extend([repo for repo in response.json() if not repo['private']])
            # Check if there's a next page of results
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
        else:
            print(f'Failed to fetch repositories: {response.status_code}')
            url = None
    return repos

# Function to get commits from a given period of time
def get_filtered_commits(owner, repo, since):
    commits_url = f'https://api.github.com/repos/{owner}/{repo}/commits'
    params = {'since': since.isoformat()}
    response = session.get(commits_url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to fetch commits for {repo}: {response.status_code}')
        return []

# Calculate the date
if NEWS_TYPE == "weekly":
    start_time_precise = datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=1) # search: UTC
    b = datetime.time(start_time_precise.hour, 0, 0, 0)
    start_time = datetime.datetime.combine(start_time_precise.date(), b)
    display_start_time = datetime.datetime.now(timezone('Etc/GMT-8')) - datetime.timedelta(weeks=1) # display: GMT-8
elif NEWS_TYPE == "daily":
    start_time_precise = datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=1) # search: UTC
    b = datetime.time(start_time_precise.hour,0,0,0)
    start_time = datetime.datetime.combine(start_time_precise.date(),b)
    display_start_time = datetime.datetime.now(timezone('Etc/GMT-8')) - datetime.timedelta(days=1) # display: GMT-8


# Get all public repositories in the organization
repos = get_org_public_repos(f'https://api.github.com/orgs/{ORG_NAME}/repos')

if NEWS_TYPE == "weekly":
    # YAML front matter for the markdown file
    yaml_front_matter = yaml.dump({
        "title": f"AUTO 周报 {display_start_time.date()} - {datetime.datetime.now(timezone('Etc/GMT-8')).date()}", # title: GMT-8
        "date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"), # date: UTC
        "authors": [
            {
                "name": "ChatGPT",
                "link": "https://github.com/openai",
                "image": "https://github.com/openai.png"
            }
        ],
        "excludeSearch": False,
        "draft": False
    }, default_flow_style=False, allow_unicode=True)
elif NEWS_TYPE == "daily":
    yaml_front_matter = yaml.dump({
        "title": f"AUTO 更新速递",
        "date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"),  # date: UTC
        "authors": [
            {
                "name": "github-actions[bot]",
                "link": "https://github.com/features/actions",
                "image": "https://avatars.githubusercontent.com/in/15368"
            }
        ],
        "description": "时间跨度：（北京时间）{} {:02}时至今".format(display_start_time.date(), display_start_time.hour),
        "excludeSearch": False,
        "draft": False
    }, default_flow_style=False, allow_unicode=True)

# Store commits in a given period of time
filtered_commits = []
org_course_name = {}

# Fetch and filter commits from the given period of time
for repo in tqdm(repos):
    commits = get_filtered_commits(ORG_NAME, repo['name'], start_time)
    contain_manual = False
    if commits and repo['name'] != 'hoa.moe':
        for commit in commits:
            filtered_commits.append({
                'author': commit['commit']['author']['name'],
                'date': datetime.datetime.strptime(commit['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=8), # UTC-8
                'message': commit['commit']['message'],
                'repo_name': repo['name']
            })
            if contain_manual == False and commit['commit']['author']['name'] != "github-actions":
                contain_manual = True
    if contain_manual:
        repo_name = repo['name']
        tag_url = f'https://raw.githubusercontent.com/{ORG_NAME}/{repo_name}/main/tag.txt'
        response = session.get(tag_url)
        if response.status_code == 200: # check if https://github.com/{ORG_NAME}/{repo_name}/blob/main/tag.txt exists, if exists, extract the tag start with "name:" as the repo name
            org_course_name[repo_name] = response.text.split("name:")[1].strip()


if filtered_commits:
    filtered_commits.sort(key=lambda a:a['date'], reverse=True)
    markdown_report = ""

    prev_date = None
    for commit in tqdm(filtered_commits):
        try:
            title = org_course_name[commit['repo_name']]
        except KeyError:
            title = commit['repo_name']
        repo_name = commit['repo_name']

        if commit["author"] != "github-actions": # Exclude commits authored by github-actions
            datetime_object = commit['date']
            chinese_day = chinese_weekday(datetime_object)

            if prev_date != datetime_object.date():
                markdown_report += f'#### {chinese_day}（{datetime_object.month}.{datetime_object.day}）\n\n'
                prev_date = datetime_object.date()

            message_lines = commit["message"].split('\n')
            course_name_line = f'[{title}](https://github.com/{ORG_NAME}/{repo_name})'
            heading = message_lines[0]
            markdown_report += '- （{}:{:02}）{}：（{}）{}\n'.format(datetime_object.hour,datetime_object.minute,course_name_line,commit["author"],heading)
            markdown_report += '\n'

    final_markdown_report = f'---\n{yaml_front_matter}---\n\n'

    summary = None
    if NEWS_TYPE == "weekly":
        summary = generate_summary(markdown_report)

    if summary:
        final_markdown_report += f'## ✨AI 摘要\n\n{summary}\n\n'

    # final_markdown_report += markdown_report

    if NEWS_TYPE == "weekly":
        with open(f'content/news/weekly-{display_start_time.date()}.md', 'w') as file:
            file.write(final_markdown_report)
    elif NEWS_TYPE == "daily":
        with open(f'content/news/daily.md', 'w') as file:
            file.write(final_markdown_report)

else:
    print('No commits found in the given period of time')
