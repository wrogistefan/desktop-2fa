USER = "wrogistefan"
REPO = "desktop-2fa"
BRANCH = "main"

RAW = f"https://raw.githubusercontent.com/{USER}/{REPO}/{BRANCH}/"

with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

# Zamiana ścieżek względnych
content = content.replace("](screenshots/", f"]({RAW}screenshots/")
content = content.replace("](./screenshots/", f"]({RAW}screenshots/")
content = content.replace("](../screenshots/", f"]({RAW}screenshots/")

# Zamiana blob/main na raw
content = content.replace(
    f"https://github.com/{USER}/{REPO}/blob/{BRANCH}/",
    RAW
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(content)

print("README.md został poprawiony.")
