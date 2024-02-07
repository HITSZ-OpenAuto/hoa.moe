import requests
import argparse
import http.client
import json
import urllib.parse
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Generate download links of files from a GitHub repository or Alist.")
    parser.add_argument("owner", help="GitHub repository owner")
    parser.add_argument("repo", help="GitHub repository name")
    parser.add_argument("--username", help="GitHub username", default="")
    parser.add_argument("--gh_token", help="GitHub token", default="")
    parser.add_argument("--alist_token", help="Alist token", default="")

    args = parser.parse_args()
    return args

def get_gh_files(owner, repo, username, gh_token, path=''):
    paths = []
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    response = requests.get(url)
    if response.status_code == 200:
        contents = response.json()
        for content in contents:
            if content['type'] == 'file':
                paths.append(content['path'])
            elif content['type'] == 'dir':
                paths.extend(get_gh_files(owner, repo, username, gh_token, content['path']))
    else:
        print(f"Failed to retrieve files. Status code: {response.status_code}")
        print(response.text)
    return paths

def get_alist_files(token, path=""):
    conn = http.client.HTTPSConnection("open.osa.moe")
    payload = json.dumps({
    "path": f"{path}",
    "password": "",
    "page": 1,
    "per_page": 0,
    "refresh": False
    })
    headers = {
    'Authorization': f'{token}',
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json'
    }
    conn.request("POST", "/api/fs/list", payload, headers)
    res = conn.getresponse()
    files = res.read()
    files = json.loads(files.decode("utf-8"))

    abs_paths = []
    
    if files["code"] == 200:
        for file in files["data"]["content"]:
            if file["is_dir"]:
                temp_path = path + "/" + file["name"]
                # abs_paths.extend(get_alist_files(token, temp_path))
                temp_abs_paths, _ = get_alist_files(token, temp_path)
                abs_paths.extend(temp_abs_paths)
            else:
                abs_paths.append(path + "/" + file["name"])
    else:
        print(f"list {path} failed")
        print(files["message"])

    rel_paths = [abs_path.replace(path, "").lstrip("/") for abs_path in abs_paths]
        
    return rel_paths

class File:
    def __init__(self, path, url):
        self.path = path
        self.url = url

def generate_filetree_shortcode(files, base_path):
    shortcode = f'{{< filetree/container >}}\n'
    current_folder = ""

    for file in files:
        if file.is_child_of(base_path):
            if file.path != base_path:
                relative_path = os.path.relpath(file.path, base_path)
                folders = relative_path.split(os.path.sep)
                for i in range(len(folders) - 1):
                    current_folder = os.path.join(current_folder, folders[i])
                    shortcode += f'  {{< filetree/folder name="{folders[i]}" state="open" >}}\n'
                shortcode += f'    {file.generate_shortcode(base_path)}\n'

    shortcode += f'{{< /filetree/container >}}'
    return shortcode

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Generate download links of files from a GitHub repository.")
    # parser.add_argument("owner", help="GitHub repository owner")
    # parser.add_argument("repo", help="GitHub repository name")
    # parser.add_argument("--username", help="GitHub username", default="")
    # parser.add_argument("--gh_token", help="GitHub token", default="")
    # parser.add_argument("--alist_token", help="Alist token", default="")

    # args = parser.parse_args()

    # # Get files from GitHub
    # gh_files = get_gh_files(args.owner, args.repo, args.username, args.gh_token)
    
    # # Get files from Alist
    # alist_files = get_alist_files(args.alist_token, args.repo)

    # # Generate download links
    # gh_files = [File(path, f'https://gh.hoa.moe/github.com/{args.owner}/{args.repo}/raw/main/{path}') for path in gh_files]
    # alist_files = [File(path, f'https://open.osa.moe/d/openauto/{args.repo}/{path}') for path in alist_files]

    # for file in gh_files:
    #     print(file.url)
    #     print(file.path)

    # for file in alist_files:
    #     print(file.url)
    #     print(file.path)

    
