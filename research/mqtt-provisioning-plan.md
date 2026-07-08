# Cradlewise MQTT provisioning validation plan

The validation should be a standalone research harness, never imported by Home
Assistant. Certificate provisioning and MQTT connectivity should remain separate
approval gates.

## Proposed layout

```text
research/
├── mqtt-provisioning-plan.md
├── mqtt_probe/
│   ├── README.md
│   ├── auth_probe.py
│   ├── provisioning_probe.py
│   ├── storage_probe.py
│   ├── metadata.py
│   ├── redaction.py
│   └── safety.py
└── .gitignore.example
```

This is a proposed layout only. The `mqtt_probe/` harness is not part of this
plan commit.

## Validation phases

### 1. Authentication dry run

- Read credentials only from `CRADLEWISE_EMAIL` and `CRADLEWISE_PASSWORD`.
- Reuse the existing Cognito authentication flow.
- Never display credentials, tokens, AWS keys, headers, or full exceptions.
- Report only:
  - authentication success/failure category;
  - region;
  - credential expiration present: yes/no;
  - configuration fields present: yes/no.

### 2. Provisioning request preview

Before making any request, construct and validate a redacted preview of:

```text
POST /cradles/pairedUsers/v3
```

Show only field names and value types:

```json
{
  "baby_id": "<redacted>",
  "email": "<redacted>",
  "fcm_token": "<redacted-or-missing>",
  "device": {
    "app_version": "string",
    "device_name": "<generic>",
    "os": "string",
    "os_version": "string"
  }
}
```

The live provisioning request must require a separate explicit flag such as:

```text
--allow-provisioning-request
```

Default behavior must be dry-run.

### 3. Provisioning-response inspection

Inspect only response structure:

- `deviceConfig` present;
- `s3Bucket` present;
- number of `s3ObjectKeys`;
- `deviceId` present;
- `cradleId` present;
- `groupCaCert` present;
- role/baby association present.

Never print actual values.

### 4. Storage validation

Downloading certificate material requires another explicit gate:

```text
--allow-certificate-download
```

Requirements:

- Use a newly created temporary directory with restrictive permissions.
- Reject paths outside that directory.
- Never read secret contents into logs.
- Record only:
  - file count;
  - file sizes;
  - detected file category: certificate/private-key/unknown;
  - SHA-256 fingerprint computed locally.
- Store fingerprints only as truncated, keyed comparison values.
- Delete temporary material on normal exit and exceptions.
- Never follow symlinks.

To test uniqueness, compare opaque fingerprints across authorized runs:

```text
same account + same crib + same installation identity
same account + different crib
different authorized account + same shared crib
```

Do not retain raw files between runs.

### 5. Identity mapping

Confirm metadata relationships without exposing values:

| Property | Validation |
|---|---|
| IoT endpoint | Compare exact public endpoint with APK constant |
| Region | Confirm `us-east-1` |
| Thing name | Compare redacted cradle-ID hashes with topic identifier |
| MQTT client ID | Compare redacted backend device-ID hash with configured client ID |
| Certificate scope | Compare fingerprints across crib/device/account combinations |

Use session-local keyed hashes so identifiers cannot be correlated across reports.

### 6. MQTT read-only validation

Under the current "no MQTT publish" rule, only connection and passive
subscriptions can be tested:

- Connect using mTLS.
- Subscribe to shadow accepted/rejected and cradle-state topics.
- Do not publish to `/shadow/get`.
- Do not publish `{}` or any desired-state document.
- Wait briefly for unsolicited state, then disconnect.

A true shadow GET requires publishing `{}` to:

```text
$aws/things/{thingName}/shadow/get
```

Therefore it is outside this phase. It is read-only in effect, but still
technically an MQTT publish and needs separate approval.

## Exact safety checks

The harness must abort when:

- dry-run is not the default;
- credentials appear in CLI arguments;
- output is redirected to a repository file;
- the output directory is inside the repository;
- certificate files already exist at the destination;
- destination permissions are broader than the current user;
- a symlink or path traversal is detected;
- an MQTT topic ends in `/shadow/update`;
- any code attempts `publish()`;
- a payload contains `desired`;
- the endpoint or thing name differs from provisioned metadata;
- the client ID is randomly substituted without evidence;
- provisioning returns device-limit or assignment warnings;
- cleanup of temporary secret material fails.

Install signal and exception handlers so cleanup runs on interruption.

## Exact redaction rules

Always redact:

- email addresses and usernames;
- passwords;
- Cognito tokens and identity IDs;
- AWS access keys, secret keys, and session tokens;
- HTTP authorization, cookie, and signing headers;
- baby IDs, cradle IDs, device IDs, role IDs, and serial numbers;
- FCM tokens and notification ARNs;
- S3 bucket names, object keys, and signed URLs;
- certificate PEM/DER content;
- private-key content;
- keystore passwords and paths containing identifiers;
- full certificate fingerprints;
- raw API request and response bodies.

Permitted output:

- field names;
- primitive types;
- boolean presence indicators;
- collection counts;
- file sizes;
- public AWS region and IoT endpoint;
- normalized error categories;
- session-local opaque labels such as `crib_A`;
- truncated keyed hashes used only within one run.

The redactor must recursively sanitize dictionaries, lists, exception text, URLs,
and dictionary keys before logging.

## Home Assistant security implications

Certificate support would require:

- encrypted-at-rest private-key storage;
- exclusion from diagnostics and backups unless explicitly encrypted;
- certificate refresh and revocation handling;
- stable client identity;
- device-quota awareness;
- clear deletion during config-entry removal;
- no certificate exposure through debug logging;
- strict file permissions.

Given those requirements, MQTT control should be a separate advanced, opt-in
feature. REST polling should remain the default and operate independently when
MQTT setup or authentication fails.
