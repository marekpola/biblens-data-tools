import requests
from pathlib import Path

# GitHub API adresář se soubory jazyků
API_URL = "https://api.github.com/repos/openbibleinfo/Bible-Passage-Reference-Parser-Languages/contents/lang"

# kam se budou soubory ukládat
OUTPUT_DIR = Path("./data/raw/openbibleinfo/lang")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(API_URL)
    files = response.json()

    for item in files:
        name = item["name"]

        if not name.endswith(".js"):
            continue

        url = item["download_url"]
        print(f"Downloading {name}")

        data = requests.get(url).text

        out_file = OUTPUT_DIR / name
        out_file.write_text(data, encoding="utf-8")

    print("Done.")


if __name__ == "__main__":
    main()