# Cradlewise MQTT provisioning probe

This is a research-only, dry-run scaffold. It does not authenticate, make
network requests, provision devices, download certificates, connect to MQTT, or
publish messages.

Do not import this package from the Home Assistant integration.

## Safety guarantees

- Dry-run mode is mandatory.
- Network access is blocked at runtime.
- Credentials are read only as environment-variable presence checks.
- Credential values are never printed.
- Provisioning output contains only a fixed, redacted request shape.
- Certificate download functions are disabled.
- MQTT functionality is not implemented.
- Exceptions are reduced to normalized categories without message text.

Never add credentials, tokens, certificates, private keys, identifiers, raw API
responses, or signed URLs to this directory.

## Environment variables

Future authenticated phases may use:

```text
CRADLEWISE_EMAIL
CRADLEWISE_PASSWORD
```

The current scaffold checks only whether these variables are present and
non-empty. It does not use their values.

Do not place credentials in command-line arguments, `.env` files in the
repository, source files, logs, or shell history.

## Usage

Run from the repository root:

```shell
python -m research.mqtt_probe
```

Show the authentication preflight:

```shell
python -m research.mqtt_probe auth-preview
```

Show the fixed provisioning request shape:

```shell
python -m research.mqtt_probe provisioning-preview
```

Machine-readable output:

```shell
python -m research.mqtt_probe --json
```

## Explicitly unsupported

The scaffold intentionally has no options for:

- live authentication;
- `POST /cradles/pairedUsers/v3`;
- certificate or private-key download;
- MQTT connection or subscription;
- shadow GET;
- shadow update;
- crib controls.

A true AWS IoT shadow GET requires an MQTT publish to the shadow GET topic. That
operation remains outside this scaffold.

Any future live phase requires separate approval and must preserve dry-run as the
default.
