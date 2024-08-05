import os
import requests
import json
from datetime import datetime

# Configuration
owner = "arribada"
repo = "geoseals-app-zephyr"
base_dir = "firmware"

# You'll need to set this environment variable with your GitHub token
github_token = os.environ.get("GITHUB_TOKEN")

if not github_token:
    print("Please set the GITHUB_TOKEN environment variable.")
    exit(1)


def process_release(release):
    try:
        print(f"Processing release: {release['name']} (ID: {release['id']})")

        release_id = release["id"]
        release_name = release.get("tag_name") or f"draft-{release_id}"
        is_draft = release["draft"]

        # Determine the target directory
        target_dir = os.path.join(base_dir, "develop" if is_draft else "main")

        # Check if we've already processed this release
        try:
            with open("last_processed_releases.json", "r") as f:
                processed_releases = json.load(f)
        except FileNotFoundError:
            print("last_processed_releases.json not found. Creating new file.")
            processed_releases = {}

        if str(release_id) in processed_releases:
            print(f"Release {release_name} already processed.")
            return False

        # Create the target directory
        os.makedirs(target_dir, exist_ok=True)

        # Download all assets
        if release["assets"]:
            for asset in release["assets"]:
                asset_url = asset["url"]  # Use the API URL, not browser_download_url
                asset_name = asset["name"]
                print(f"Downloading asset: {asset_name}")

                # Make an authenticated request to get the asset
                headers = {
                    "Accept": "application/octet-stream",
                    "Authorization": f"token {github_token}",
                }
                response = requests.get(
                    asset_url, headers=headers, allow_redirects=True
                )

                if response.status_code == 200:
                    asset_path = os.path.join(target_dir, asset_name)
                    with open(asset_path, "wb") as f:
                        f.write(response.content)
                    print(f"Downloaded asset: {asset_name} to {target_dir}")
                    print(f"File size: {len(response.content)} bytes")
                else:
                    print(
                        f"Failed to download {asset_name}. Status code: {response.status_code}"
                    )
                    print(f"Response: {response.text}")

        else:
            print(f"No assets found for release {release_name}")

        if is_draft:
            release_name = release["name"]
        # Update the processed releases
        processed_releases[str(release_id)] = {
            "name": release_name,
            "processed_at": datetime.now().isoformat(),
            "is_draft": is_draft,
        }
        with open("last_processed_releases.json", "w") as f:
            json.dump(processed_releases, f, indent=2)

        return True
    except Exception as e:
        print(f"Error processing release: {str(e)}")
        return False


def update_versions():
    # Define the paths to the JSON files
    version_file_path = "last_processed_releases.json"
    build_file_path_1 = "manifest_geoseals_dev.json"
    build_file_path_2 = "manifest_geoseals.json"

    # Step 1: Open and read the JSON file containing the version objects
    with open(version_file_path, "r") as version_file:
        version_data = json.load(version_file)

    # Step 2: Extract the `name` values from the highest level objects
    version_names = [info["name"] for info in version_data.values()]
    version_draft = [info["is_draft"] for info in version_data.values()]

    # Step 3: Open and read the first build JSON file
    with open(build_file_path_1, "r") as build_file_1:
        build_data_1 = json.load(build_file_1)

    # Step 4: Open and read the second build JSON file
    with open(build_file_path_2, "r") as build_file_2:
        build_data_2 = json.load(build_file_2)

    # Step 5: Update the version in each build data, checking if is_draft is true
    for index, name in enumerate(version_names):
        if version_draft[index]:
            build_data_1["version"] = name
        else:
            build_data_2["version"] = name

    # Step 6: Overwrite the existing build files with the modified data
    with open(build_file_path_1, "w") as build_file_1:
        json.dump(build_data_1, build_file_1, indent=4)

    with open(build_file_path_2, "w") as build_file_2:
        json.dump(build_data_2, build_file_2, indent=4)

    print(f"Build files updated: {build_file_path_1} and {build_file_path_2}")


# Get all releases including drafts
url = f"https://api.github.com/repos/{owner}/{repo}/releases"
headers = {"Authorization": f"token {github_token}"}
response = requests.get(url, headers=headers)
data = response.json()

if isinstance(data, dict):
    if "message" in data:
        print(f"API returned an error: {data['message']}")
        exit(1)
    else:
        print("Unexpected response format. Expected a list of releases.")
        exit(1)

releases = data  # At this point, we're sure it's a list

changes_made = False

for release in releases:
    if process_release(release):
        changes_made = True

if changes_made:
    print("New releases were processed.")
    update_versions()
else:
    print("No new releases to process.")
