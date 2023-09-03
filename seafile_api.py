import requests
import json
def login_sf(sf_host_url, sf_username, sf_password):
    sf_url = sf_host_url + "/api2/auth-token/"
    data = {
        'username': sf_username,
        'password': sf_password
    }
    response = requests.request("POST", sf_url, data=data)
    assert response.ok
    print('登录SF成功')
    return response.json()['token']


def is_uploaded_to_sf(token, host_url, repo_id, path, filename):
    headers = {
        'Authorization': 'Token ' + token
    }
    url = host_url + '/api2/repos/' + repo_id + '/dir/'
    r = requests.get(url, headers=headers, params={'p': path })
    assert r.ok
    for file in r.json():
        if file['name'] == filename and file['size'] > 0:
            return True
    return False


def upload_to_sf(token, host_url, repo_id, path, filename):
    headers = {
        'Authorization': 'Token ' + token
    }
    url = host_url + '/api2/repos/' + repo_id + '/upload-link/'
    r = requests.get(url, headers=headers, params={'p': "/"})
    assert r.ok
    upload_url = r.text.replace('"', '')
    f = {'file': open(filename, 'rb')}
    data = {
        "parent_dir": "/",
        "relative_path": path,
        "replace": 1
    }

    response = requests.post(
        upload_url, data=data, files=f,
        params={'ret-json': 1}, headers=headers)
    assert response.ok
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

def download_from_sf(token, host_url, repo_id, path, filename):
    headers = {
        'Authorization': 'Token ' + token
    }
    url = host_url + '/api2/repos/' + repo_id + '/file/'
    r = requests.get(url, headers=headers, params={'p': path})
    assert r.ok
    download_url = r.text.replace('"', '')
    with open(filename, 'wb') as f:
        response = requests.get(
            download_url, headers=headers)
        assert response.ok
        f.write(response.content)