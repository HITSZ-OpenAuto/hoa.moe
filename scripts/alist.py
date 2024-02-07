import http.client
import json
import argparse
import urllib.parse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("token", help="your alist token")
    parser.add_argument("--path", help="path to list", default="")
    args = parser.parse_args()
    return args

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
        
    return abs_paths, rel_paths

if __name__ == "__main__":
    args = parse_args()
    abs_paths, rel_paths = get_alist_files(args.token, args.path)
    for abs_path in abs_paths:
        print(abs_path)
    for rel_path in rel_paths:
        print(rel_path)