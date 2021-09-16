import requests


def chunked_download(url: str, filename: str):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(filename, "wb") as fd:
        for chunk in resp.iter_content(chunk_size=512):
            fd.write(chunk)


def parse_boolean(input: str) -> bool:
    return input in {"1", "true", "True"}
