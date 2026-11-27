#!/bin/bash
set -euo pipefail
umask 077

root="$(cd "$(dirname "$0")/../.." && pwd)"
output="${TELEKLAUS_BUILD_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/teleklaus-build.XXXXXX")}"
mkdir -p "$output"
output="$(cd "$output" && pwd)"
archive="$output/TeleKlaus.xcarchive"
ipa="$output/export/ClaudeRemote.ipa"
team=J3T7B3V6YJ
bundle=com.paulmakesstuff.teleklaus
profile="${TELEKLAUS_PROFILE_PATH:-}"

archive_app() {
    xcodebuild archive -project "$root/ios/ClaudeRemote.xcodeproj" -scheme ClaudeRemote \
        -configuration Debug -destination 'generic/platform=iOS' \
        -derivedDataPath "$output/DerivedData" -archivePath "$archive" "$@" -quiet
}

if [[ -n "$profile" ]]; then
    # Xcode 15 cannot select some installed profiles at archive time.
    security cms -D -i "$profile" > "$output/profile.plist"
    security find-identity -v -p codesigning > "$output/identities.txt"
    identity="$(python3 - "$output" "$team" "$bundle" <<'PY'
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import plistlib
import re
import sys

output, team, bundle = sys.argv[1:]
directory = Path(output)
profile = plistlib.loads((directory / "profile.plist").read_bytes())
entitlements = profile["Entitlements"]
expires = profile["ExpirationDate"].replace(tzinfo=timezone.utc)
if not (expires > datetime.now(timezone.utc) and profile.get("ProvisionedDevices")
        and entitlements.get("application-identifier") == f"{team}.{bundle}"
        and entitlements.get("com.apple.developer.team-identifier") == team
        and entitlements.get("aps-environment") == "development"
        and entitlements.get("get-task-allow") is True):
    sys.exit("An unexpired TeleKlaus development profile with APNs and registered devices is required.")
identities = set(re.findall(r'^\s*\d+\) ([A-F0-9]{40}) "[^"]+"[ \t]*$',
                            (directory / "identities.txt").read_text(), re.MULTILINE))
for certificate in profile["DeveloperCertificates"]:
    fingerprint = sha1(certificate).hexdigest().upper()
    if fingerprint in identities:
        break
else:
    sys.exit("No local code-signing identity matches the TeleKlaus profile.")
required = ("application-identifier", "com.apple.developer.team-identifier", "aps-environment", "get-task-allow")
(directory / "Entitlements.plist").write_bytes(plistlib.dumps({key: entitlements[key] for key in required}))
print(fingerprint)
PY
)"
    archive_app CODE_SIGNING_ALLOWED=NO
    app="$archive/Products/Applications/ClaudeRemote.app"
    cp "$profile" "$app/embedded.mobileprovision"
    codesign --force --sign "$identity" --entitlements "$output/Entitlements.plist" \
        --generate-entitlement-der "$app"
    codesign --verify --deep --strict "$app"
    mkdir -p "$output/export"
    staging="$(mktemp -d "$output/ipa.XXXXXX")"
    trap 'rm -rf "$staging"' EXIT
    mkdir "$staging/Payload"
    ditto "$app" "$staging/Payload/ClaudeRemote.app"
    ditto -c -k --norsrc --noextattr --noqtn --keepParent "$staging/Payload" "$ipa"
else
    archive_app
    method=development
    if [[ "$(xcodebuild -version | awk 'NR == 1 { split($2, v, "."); print v[1] }')" -ge 16 ]]; then
        method=debugging
    fi
    python3 - "$output/ExportOptions.plist" "$method" "$team" <<'PY'
import plistlib
import sys

path, method, team = sys.argv[1:]
with open(path, "wb") as stream:
    plistlib.dump({"method": method, "teamID": team}, stream)
PY
    xcodebuild -exportArchive -archivePath "$archive" -exportPath "$output/export" \
        -exportOptionsPlist "$output/ExportOptions.plist" -quiet
fi

printf 'Archive: %s\nIPA: %s\n' "$archive" "$ipa"
