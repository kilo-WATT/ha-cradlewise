# Cradlewise control endpoint research

## Scope and provenance

This note records offline static analysis of `Cradlewise_2.57.8_APKPure.xapk`,
plus the explicitly noted gated live probe results below. Except for those gated
research probes, no application code was executed, no network requests were made,
and no credentials or live devices were used.

- XAPK SHA-256: `70F333259FAA45F14D2E6064F4D5C2E1E4370604CD431A8EBE500E04CFA2D7F9`
- Base APK: `com.cradlewise.nini.app.apk`
- Relevant application code: `classes11.dex`
- Analysis: XAPK/APK extraction plus offline DEX string, annotation, and method
  cross-reference inspection
- Additional evidence index: `apk-analysis-output/cradlewise-search-results.txt`
  static-search output, summarized here without copying the full raw output

## Result

No REST endpoint for any requested crib control was found or verified. The Android
app implements these controls through AWS IoT Device Shadow updates over MQTT.
This is distinct from its REST API, which does contain generic POST, PUT, PATCH,
and DELETE support and several non-control write operations.

The MQTT transport is established by the following evidence:

- `RemoteMqttConnectionV2.publish` publishes control data.
- `RemoteMqttConnectionV2.subscribeUpdateAccepted` subscribes to
  `$aws/things/.../shadow/update/accepted`.
- `MqttUtilsV2.getTopics` and `Topics.<clinit>` construct the classic unnamed
  Device Shadow `get`, `update`, `accepted`, and `rejected` topic family.
- The actuator, light, music, sound-synth, and control request/state models are
  under `com.cradlewise.nini.core.mqtt`.

The table deliberately distinguishes model fields observed in the MQTT path from
REST payloads. Those fields are **not** evidence of REST request bodies.

| Feature | HTTP method | Endpoint | Payload fields | Response model | Confidence | Evidence file/function |
|---|---|---|---|---|---|---|
| Bounce on/off | Not found | No REST endpoint verified | No REST payload verified. MQTT actuator model contains `on`; reported state also contains bounce state. | No REST response model. MQTT shadow update accepted/rejected topics observed. | High that the app uses MQTT; no REST control claim | `classes11.dex`: `MqttMessage$Actuator.toString`; `RemoteMqttConnectionV2.publish`; `VideoViewModel.setBounceOn` |
| Bounce amplitude | Not found | No REST endpoint verified | No REST payload verified. MQTT actuator model contains `amplitude`; reported state contains bounce level/setting fields. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Actuator.toString`; `MqttMessage$State$Reported.toString`; `VideoViewModel.setBounceManual` |
| Bounce mode | Not found | No REST endpoint verified | No REST payload verified. MQTT actuator/reported-state models contain `bounceMode`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Actuator.toString`; `MqttMessage$State$Reported.toString` |
| Start/stop soothing | Not found | No REST endpoint verified | No REST payload verified. MQTT models expose actuator/control and recipe-related state; the exact write body was not reconstructed. | No REST response model. MQTT shadow acknowledgement observed. | High for MQTT transport; medium for the precise model path | `classes11.dex`: `VideoViewModel.onSoothingCardClick`; `MqttMessage$Control.toString`; `MqttMessage$State$Reported.toString` |
| Night light on/off | Not found | No REST endpoint verified | No REST payload verified. MQTT light model contains `lightOn`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Light.toString`; `RemoteMqttConnectionV2.publish` |
| Light intensity | Not found | No REST endpoint verified | No REST payload verified. MQTT light model contains `lightIntensity`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Light.toString`; `RemoteMqttConnectionV2.publish` |
| Sound/music on/off | Not found | No REST endpoint verified | No REST payload verified. MQTT music and sound-synth models contain `play`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Music.toString`; `MqttMessage$SoundSynth.toString` |
| Sound volume | Not found | No REST endpoint verified | No REST payload verified. MQTT music and sound-synth models contain `volume`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Music.toString`; `MqttMessage$SoundSynth.toString`; `VideoViewModel.setCradleVolume` |
| Sound track | Not found | No REST endpoint verified | No REST payload verified. MQTT models contain `currentTrack`, `song_id`, `trackName`, `mood`, and `playlist`. | No REST response model. MQTT shadow acknowledgement observed. | High that the app uses MQTT | `classes11.dex`: `MqttMessage$Music.toString`; `MqttMessage$SoundSynth.toString` |
| Responsiveness | Not found | No REST endpoint verified | No REST payload verified. MQTT reported state contains `responsivitySetting`; control model contains `crySensitivity`. | No REST response model. MQTT shadow acknowledgement observed. | High for MQTT state/model; medium for the exact write field | `classes11.dex`: `MqttMessage$State$Reported.toString`; `MqttMessage$Control.toString` |
| Schedules | Not found | No REST control endpoint verified | No REST control payload verified. Recipe and keep-on-during-sleep fields occur in MQTT reported state. | No REST response model identified. | Medium: state fields are verified, but a write path was not isolated | `classes11.dex`: `MqttMessage$State$Reported.toString` (`startRecipe*`, `keepBounceOnDuringSleep*`, `keepMusicOnDuringSleep*`) |
| Soothing windows | Not found | No REST endpoint verified | No REST payload or dedicated window model verified. | No REST response model identified. | High that no endpoint was established by this analysis | `classes11.dex`: API path-string and write-method cross-reference results |

## REST write capability found in the app

`com.cradlewise.nini.core.api.base.ApiService` and `ApiServiceImpl` expose generic
`post`, `put`, `patch`, and `delete` methods accepting a path and body. Verified
call sites use those methods for operations such as baby-profile updates, sleep
track changes, calibration status, firmware update requests, pairing, and updating
the analytics day-start time. None is a crib-control endpoint.

Examples of verified non-control REST path construction include:

- `AwsBackendService.updateBabyProfile`: `/babyProfiles/...`
- `CommonsBackendService.addSleepTrack` and `modifySleepTrack`:
  `/babyProfiles/.../sleeptracks`
- `CommonsBackendService.calibrationStatusUpdate`:
  `/cradles/.../calibrationStatus`
- `CommonsBackendService.firmwareUpdatePost`:
  `/cradles/.../firmwareUpdate`
- `CommonsBackendService.updateDayStartTime`:
  `/sleep-analytics/.../update-day-start-time`

## pycradlewise compatibility assessment

`CradlewiseClient._api_request` already accepts an HTTP method, path, optional
JSON body, and query parameters, then signs the request using AWS SigV4 for the
API Gateway service. It should therefore be technically capable of calling a
verified write endpoint on the same REST API and authentication boundary.

That is only a transport-capability assessment. The APK supplied no verified REST
control path, request body, or response model to give pycradlewise. Reusing the
client for crib control would currently require guessing, which is out of scope.

## Recommendation

Do not add Home Assistant control entities from this evidence. Doing so would
require reintroducing an MQTT Device Shadow client or obtaining a separately
verified REST control contract from vendor documentation or a later app version.
The existing REST-polling integration should remain unchanged.

## Device Shadow transport details

Further offline inspection verified the classic (unnamed) AWS IoT Device Shadow
transport used by app version 2.57.8.

- AWS IoT endpoint: `a2bby18smixe1f-ats.iot.us-east-1.amazonaws.com`
- Region: `us-east-1`
- Thing name: the cradle ID passed to the app's MQTT methods
- Update topic: `$aws/things/{cradleId}/shadow/update`
- Get topic: `$aws/things/{cradleId}/shadow/get`
- Get result: `$aws/things/{cradleId}/shadow/get/accepted`
- Update result: `$aws/things/{cradleId}/shadow/update/accepted`
- Rejections included by `MqttUtilsV2.getTopics`:
  `.../shadow/get/rejected` and `.../shadow/update/rejected`
- State stream: `/cradle/{cradleId}/cradle_state`
- Other custom topic suffixes observed: `/beacon` and
  `/update_request/{new,progress,succeeded,failed}`, plus Janus video
  request/response topics. Their complete prefixes were not reconstructed, so no
  exact full custom-topic claim is made here.

No `/shadow/name/{shadowName}/...` string or named-shadow construction was found.
The app uses the classic unnamed shadow in the analyzed build.

`SendEvents.prePareDesiredAndPublish(JSONObject)` wraps each partial update as:

```json
{
  "state": {
    "desired": {
      "component-or-setting": "partial update"
    }
  }
}
```

It then calls `MqttManager.publish(String)`, which ultimately calls
`RemoteMqttConnectionV2.publish(cradleId, message)` and publishes to the update
topic above. Each setter sends a partial desired-state document rather than a
complete copy of the shadow.

### APK static-search cross-check

The static-search output confirms the prior Device Shadow finding and does not
reveal a REST control endpoint. It also tightens the evidence attribution for
topic and payload names:

- `jadx-out/sources/com/cradlewise/nini/core/mqtt/utils/Topics.java` defines
  classic shadow suffix constants including `/shadow/get`,
  `/shadow/get/accepted`, `/shadow/update`, and `/shadow/update/accepted`.
- `apktool-out/smali_classes11/com/cradlewise/nini/core/mqtt/utils/MqttUtilsV2.smali`
  contains the broader subscription topic construction, including
  `/shadow/get/rejected`, `/shadow/update/rejected`, and the custom
  `/cradle/{cradleId}/cradle_state` state stream.
- `apktool-out/smali_classes11/com/cradlewise/nini/core/mqtt/remote/RemoteMqttConnectionV2.smali`
  calls the cradle-state subscription helper and uses the AWS IoT MQTT manager.
- `jadx-out/sources/com/cradlewise/nini/app/wireless/SendEvents.java` and
  `apktool-out/smali_classes11/com/cradlewise/nini/app/wireless/SendEvents.smali`
  show that app controls funnel through `prePareDesiredAndPublish(JSONObject)`.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/viewmodel/BounceSettingsViewModel.smali`
  calls `SendEvents` methods for `alwaysOnBounce`, `bounceMode`,
  `bounceDuration`, `bounceAmplitude`, `bounceSetting`,
  `bounceResponsivitySetting`, `disableBounce`, and `superGentleBounce`.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/VideoViewModel.smali`
  calls `SendEvents` for dashboard bounce, sound-synth, music duration, and
  bounce-intensity updates.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/viewmodel/SettingsStartRecipeViewModel.smali`
  calls `SendEvents.updateStartRecipeEnabled`,
  `updateStartRecipeBounceLevel`, `updateStartRecipeMusicLevel`, and
  `updateStartRecipeLockDuration`.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/viewmodel/SettingsSoothingViewModel.smali`
  calls `SendEvents` for max bounce limit, bounce duration, music play, and
  keep-bounce-on-during-sleep settings.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/hiltViewModel/SleepTrackListViewModel.smali`,
  `apktool-out/smali_classes11/com/cradlewise/nini/app/utils/AppUtils.smali`,
  and `apktool-out/smali_classes11/com/cradlewise/nini/app/viewmodel/SpotifySpeakerViewModel.smali`
  provide additional music and sound-synth call sites.

Confirmed desired-state field names from the search output include:

- `actuator.on`
- `actuator.amplitude`
- `actuator.disableBouncing`
- `actuatorBounceAlwaysOnIntensity`
- `bounceMode`
- `bounceDuration`
- `bounceTimeRemaining`
- `bounceSetting`
- `responsivitySetting`
- `control.crySensitivity`
- `music.play`
- `music`
- `musicLevel`
- `musicDuration`
- `soundSynth`
- `light.indicatorBrightness`
- `indicatorBrightnessMode`
- `keepBounceOnDuringSleep`
- `keepBounceOnDuringSleepLevel`
- `keepMusicOnDuringSleep`
- `keepMusicOnDuringSleepLevel`
- `startRecipeEnabled`
- `startRecipeBounceLevel`
- `startRecipeMusicLevel`
- `startRecipeLockDuration`
- `autoModeLockDuration`
- `adaptiveSoothingEnabled`

Still inferred rather than verified by the static-search output:

- Exact value ranges and enum meanings for bounce level, volume, responsiveness,
  music selections, and recipe durations.
- Whether app DTO names and final JSON names differ for some nested music fields,
  such as `songId` versus reported `song_id`.
- Atomic sequencing for multi-field actions such as "start soothing".
- Runtime AWS IoT policy behavior, accepted/rejected responses, and whether a
  non-app client can authenticate safely.
- Night-light writes for `lightOn` or `lightIntensity`; the app search output
  verifies indicator-brightness writers, but not a night-light on/off writer.

## Control field matrix

The field paths below are exact where `SendEvents` constructs a `JSONObject`.
Values and enumerations are not asserted unless their type or mapping was also
visible. "Not verified" means the reported model contains a field but no matching
write constructor was found.

| Feature | Shadow topic | Desired payload field | Reported payload field | Evidence file/function | Confidence | Risk |
|---|---|---|---|---|---|---|
| Bounce on/off | `$aws/things/{cradleId}/shadow/update` | `state.desired.actuator.on` (boolean) | `state.reported.actuator.on` | `classes11.dex`: `SendEvents.actuatorOn`; `MqttMessage$Actuator.getOn`; `RemoteMqttConnectionV2.publish` | High | Physical motion; unsafe without state/range validation and acknowledgement handling |
| Bounce amplitude | Same | `state.desired.actuator.amplitude` (integer); the newer dashboard also writes `state.desired.bounceLevel` | `state.reported.actuator.amplitude`; `state.reported.bounceLevel` | `SendEvents.bounceAmplitude`; `SendEvents.updateBounceIntensity`; `MqttMessage$Actuator.getAmplitude`; `MqttMessage$State$Reported.getBounceLevel` | High for fields; value range unverified | Physical motion and firmware-dependent ranges |
| Bounce mode | Same | `state.desired.bounceMode` (boolean passed by app); OFF additionally uses `state.desired.actuator.disableBouncing` | `state.reported.bounceMode`; `state.reported.actuator.disableBouncing` | `SendEvents.bounceMode`; `SendEvents.disableBounce`; `SettingsSoothingViewModel.updateBounceStatus` | High for fields; semantic values need confirmation | A boolean mode is not self-describing; wrong mapping could enable motion |
| Soothing start/stop | Same | No unified soothing field verified. App controls actuator and audio fields separately. | `state.reported.isCribHelping` and individual actuator/audio state | `VideoViewModel.onSoothingCardClick`; `SendEvents.actuatorOn`; `SendEvents.musicPlay`; reported-state model | Medium | Treating several writes as one transaction could leave mixed state |
| Sound/music on/off | Same | `state.desired.music.play` or `state.desired.soundSynth.play`, depending on audio subsystem | `state.reported.music.play`; `state.reported.soundSynth.play` | `SendEvents.musicPlay`; `SendEvents.musicUpdate`; `SendEvents.soundSynthUpdate` | High | Two distinct audio paths; selecting the wrong one may not affect the active source |
| Sound volume | Same | `state.desired.music.volume`, `state.desired.soundSynth.volume`, or `state.desired.musicLevel` | Corresponding music/sound-synth fields and `state.reported.musicLevel` | `SendEvents.musicPlay`; `SendEvents.musicUpdate`; `SendEvents.soundSynthUpdate`; `SendEvents.updateSoundIntensity` | High for fields; ranges unverified | Excessive volume if units/ranges are assumed |
| Sound track | Same | `state.desired.music.songId` and `state.desired.music.mood`; sound synth uses `state.desired.soundSynth.trackName` plus ambience/color fields | Music model exposes `song_id`, `mood`, and current-track data; sound synth exposes `trackName` | `SendEvents.musicUpdate`; `SendEvents.soundSynthUpdate`; `SleepTrackListViewModel.onTrackSelected` | High for constructed desired keys; IDs require server/app catalog | Invalid IDs, user-uploaded content, and subsystem mismatch |
| Night light on/off | Same transport, write not verified | Not verified. No `SendEvents` writer for `lightOn` was found. | `state.reported.light.lightOn` | `MqttMessage$Light.getLightOn`; absence from `SendEvents` method/string cross-references | Medium-high that it is read in this build; no write claim | Guessing the desired field violates the research constraint |
| Light intensity | Same transport, write not verified | Not verified for `lightIntensity`. Verified app writes exist only for `state.desired.light.indicatorBrightness` and `indicatorBrightnessMode`. | `state.reported.light.lightIntensity`, `indicatorBrightness`, `indicatorBrightnessMode` | `MqttMessage$Light`; `SendEvents.lightIndicatorBrightness`; `SendEvents.lightIndicatorMode` | High for indicator fields; no confidence for night-light write | Indicator brightness may not be the night-light control |
| Responsiveness | Same | `state.desired.responsivitySetting` (integer); cry response separately uses `state.desired.control.crySensitivity` | `state.reported.responsivitySetting`; `state.reported.control.crySensitivity` | `SendEvents.bounceResponsivitySetting`; `SendEvents.crySensitivitySetting`; `SettingsSoothingViewModel.updateSensitivity/updateCrySensitivity` | High for fields; ranges/mapping unverified | Wrong mapping changes automatic soothing behavior |
| Start recipe | Same | `state.desired.startRecipeEnabled`, `startRecipeBounceLevel`, `startRecipeMusicLevel`, `startRecipeLockDuration` | Same names under `state.reported`; reported model also has `startRecipeOn` and `startRecipeLockEndTime` | `SendEvents.updateStartRecipe*`; `SettingsStartRecipeViewModel` update methods | High for fields; units/enums partly unverified | Multi-field sequencing and duration units require confirmation |
| Schedules | Same transport, clock schedule not found | No clock/calendar schedule payload verified. Start-recipe duration fields are not evidence of a schedule. | No dedicated schedule field verified | `SendEvents` and reported-model field inventory | High that no schedule contract was established | Do not reinterpret recipe timers as schedules |
| Soothing windows | Not verified | No payload field verified | No dedicated field verified | APK-wide string/method cross-reference search | High that this analysis found none | Any implementation would be speculative |

## MQTT connection and identity evidence

The Android app does **not** use Cognito IAM WebSocket signing for its remote MQTT
connection. `RemoteMqttConnectionV2.connect` constructs
`AWSIotMqttManager(clientId, endpoint)` and calls
`connect(KeyStore, statusCallback)`. `CertificateUtilsV3.loadKeyStore(cradleId)`
loads a per-cradle certificate and private key. Auto-reconnect and keepalive are
configured on the AWS SDK manager.

Certificate provisioning is itself backed by a signed app REST call:

- `MqttBackendService.fetchDeviceCertsV3`
- Path: `/cradles/pairedUsers/v3`
- Request context includes the selected baby/cradle relationship, user email,
  app-device information, and an FCM token.
- The response supplies a device configuration containing an S3 bucket and object
  keys; `CertificateUtilsV3` downloads and stores the certificate material in a
  keystore.

No certificate, private key, token, bucket name, or object key was extracted or
recorded during this research.

The app's MQTT client ID appears to be the app installation's device ID, while the
thing/topic identifier is the cradle ID. This mapping follows the constructor and
connection flow, but the optimized DEX lacks source-level parameter names, so the
client-ID assignment remains an inference pending runtime confirmation.

## Assessment of the historical pycradlewise MQTT failure

The historical client gets short-lived IAM credentials from the same Cognito
identity flow used for REST, then connects with SigV4-signed MQTT over WebSockets.
It uses a random client ID (`ha-cradlewise-...`) and subscribes to:

- `$aws/things/{cradleId}/shadow/get/accepted` (matches the app)
- `{cradleId}/cradle_state` (does **not** match the app's verified
  `/cradle/{cradleId}/cradle_state`)

Its extracted endpoint and region match the APK. The custom state-topic mismatch
would prevent those state messages but cannot explain a hangup during connection,
which occurs before subscription.

The strongest explanation for `AWS_ERROR_MQTT_UNEXPECTED_HANGUP` is an
authentication/policy or client-ID mismatch: the production app authenticates
with a provisioned X.509 device certificate and likely policy-constrained device
ID, whereas pycradlewise uses a Cognito IAM principal and random client ID. This
is an inference, not a verified server-side diagnosis. Static analysis cannot
inspect the effective IoT policy attached to either principal.

## What still requires live confirmation

- Whether the Cognito IAM role has any `iot:Connect`, `iot:Subscribe`,
  `iot:Receive`, or `iot:Publish` permissions.
- The exact client ID allowed by the IoT policy.
- Numeric ranges and enum meanings for bounce, volume, responsiveness, and recipe
  settings.
- Whether desired updates are accepted for every verified field on current crib
  firmware, and how quickly reported state converges.
- Whether certificate provisioning permits a non-app client, consumes a device
  slot, or changes caregiver/device assignments.
- Whether `lightOn` and `lightIntensity` have write paths absent from this app
  version.

## Recommended next safe test plan

1. Keep Home Assistant REST-only and make no changes to the integration.
2. In a separate, disposable research client, first inspect only locally available
   auth metadata and avoid logging credential values.
3. With explicit approval for a later live phase, test connection only—no
   subscriptions or publishes—using the existing IAM credentials and the verified
   endpoint. Record only the normalized success/error category.
4. If IAM connection is denied or hung up, stop. Do not attempt certificate
   provisioning automatically. Review the implications of
   `/cradles/pairedUsers/v3`, including device limits and handling of private key
   material, before any request.
5. If an authorized connection succeeds, subscribe read-only to the classic
   shadow accepted/rejected topics, publish only an empty shadow `get`, and compare
   the returned schema to the static model. This still requires separate explicit
   approval because it is a live request.
6. Only after ranges and acknowledgement behavior are confirmed should a single,
   reversible low-risk control be considered in an isolated harness. Physical
   motion controls should be last and require an observer at the crib.
7. Any future Home Assistant MQTT support should be opt-in, control-only,
   independently failure-contained, and must never reduce REST polling reliability.
   Certificate/private-key storage would require a dedicated security review.

## Authentication flow and Home Assistant feasibility

### Verified Android flow

The app uses Cognito and X.509 credentials for different layers:

1. The user signs in through AWS Amplify/Cognito. The resulting authenticated
   session authorizes app REST and Amplify Storage operations.
2. `GetDeviceCertificatesUseCaseImpl.invoke` checks for a certificate stored for
   the selected cradle. When one is absent, it obtains the app installation's
   backend device ID and calls `MqttBackendService.fetchDeviceCertsV3`.
3. `fetchDeviceCertsV3` sends an authenticated POST to
   `/cradles/pairedUsers/v3`. Its inputs include baby/account context, email, FCM
   token, and a `DeviceInfoCert` describing the app device.
4. The response `DeviceConfig` contains `cradleId`, `babyId`, `roleId`,
   `deviceId`, a group/root CA value, and S3 location metadata for the client
   certificate and private key.
5. `CertificateUtilsV3.downloadCertificates` obtains the two client files through
   Amplify Storage. The private key is parsed as RSA; it is not generated by the
   app. The certificate/private-key pair is saved with
   `AWSIotKeystoreHelper.saveCertificateAndPrivateKey` in a keystore named per
   cradle.
6. CA/file material is encrypted at rest with AES-GCM keys created in Android
   Keystore. `CertificateEncryptionHelper` uses an alias scoped by cradle ID.
7. `RemoteMqttConnectionV2.connect` creates
   `AWSIotMqttManager(clientId, endpoint)`, loads the per-cradle keystore, and
   calls `connect(KeyStore, callback)`. Cognito IAM credentials are not passed to
   this MQTT connection.

No client certificate or private key is bundled statically in the base APK. No
IoT keypair generation call was found. The backend provisions an existing
certificate/private-key pair through authenticated API and Storage operations.

### Live-auth-only probe result

A gated `research/mqtt_probe` live-auth-only probe was run from a disposable
Debian LXC research environment. The probe used credentials only from environment
variables, reported only redacted metadata, and the environment variables were
unset immediately after the run.

Result summary:

| Field | Result |
|---|---|
| `result` | `success` |
| `region` | `us-east-1` |
| `network_attempted` | `true` |
| `app_config_present` | `true` |
| `authentication_attempted` | `true` |
| `cradle_count` | `1` |
| `discovery_failure_category` | `null` |
| `credential_expiration_present` | `false` |

This validates that the existing Cradlewise account authentication and safe
cradle discovery path can succeed from the research harness. It does **not**
validate MQTT authorization or certificate provisioning.

The probe did not make a provisioning request, did not call
`POST /cradles/pairedUsers/v3`, did not download certificates, did not access S3,
did not connect/subscribe/publish over MQTT, and did not send crib commands. No
credentials, tokens, certificates, keys, identifiers, raw responses, or exception
messages were recorded in this note.

### Live provisioning-inspect probe result

A gated `research/mqtt_probe` provisioning-inspect probe was run twice from a
disposable Debian LXC research environment. The probe used credentials only from
environment variables. The environment variables were unset immediately after the
run in both cases.

Latest result summary, with safe HTTP status metadata:

| Field | Result |
|---|---|
| `result` | `failed` |
| `failure_category` | `ClientResponseError` |
| `failure_stage` | `provisioning_request` |
| `app_config_present` | `true` |
| `auth_success` | `true` |
| `cradle_count` | `1` |
| `provisioning_request_attempted` | `true` |
| `provisioning_request_count` | `1` |
| `http_status` | `400` |
| `http_status_class` | `4xx` |

Redacted response-structure summary:

| Response structure field | Result |
|---|---|
| `deviceConfig_present` | `false` |
| `s3Bucket_present` | `false` |
| `s3ObjectKeys_count` | `0` |
| `deviceId_present` | `false` |
| `cradleId_present` | `false` |
| `groupCaCert_present` | `false` |
| `role_association_present` | `false` |
| `baby_association_present` | `false` |

Each probe run attempted `POST /cradles/pairedUsers/v3` at most once. In the
latest run, the request was attempted exactly once and failed before any
certificate/storage/MQTT phase. The endpoint was reachable after successful
authentication. The latest failure was HTTP 400 Bad Request, not 401/403, which
suggests the current research payload shape, body fields, or app-device context
is invalid or incomplete.

This does not prove MQTT/control is impossible. It also does not prove
certificate provisioning is safe or reusable from a non-app client.

No certificate download occurred, no S3 access occurred, no MQTT
connect/subscribe/publish occurred, no shadow get/update occurred, and no crib
controls were sent. No credentials, tokens, certificates, keys, identifiers, raw
responses, URLs, headers, exception messages, logs, bucket names, or object names
were recorded in this note.

### Static provisioning request-shape evidence

Offline static-search output gives a stronger explanation for the HTTP 400
provisioning-inspect result. The Android app does not build the
`POST /cradles/pairedUsers/v3` request with the snake_case field names used by
the first probe. It constructs a typed `GetDeviceCertV3Request` object.

Current probe payload shape, redacted:

```json
{
  "baby_id": "<redacted>",
  "email": "<redacted>",
  "fcm_token": null,
  "device": {
    "app_version": "research-probe",
    "device_name": "research-probe",
    "os": "python",
    "os_version": "unknown"
  }
}
```

APK-observed top-level request model:

| Field | APK model/type evidence | Current probe field | Confidence | Notes |
|---|---|---|---|---|
| `emailId` | `GetDeviceCertV3Request.emailId: String` | `email` | High | The app model uses camelCase `emailId`, not `email`. Treat as identifying and redact in all output. |
| `babyId` | `GetDeviceCertV3Request.babyId: BigDecimal` | `baby_id` string/object value from discovery | High | The app model uses camelCase `babyId` and a numeric `BigDecimal` type, not snake_case `baby_id`. Treat as identifying and redact. |
| `fcmToken` | `GetDeviceCertV3Request.fcmToken: String` | `fcm_token: null` | High for field name/type; medium for runtime requirement | The Kotlin metadata shows a non-null `String` constructor parameter. A null FCM token is a likely 400 cause, but the server-side requirement is not proven. |
| `device` | `GetDeviceCertV3Request.device: DeviceInfoCert` | `device` with guessed snake_case keys | High for wrapper; low for nested key details from the saved output | The wrapper is verified. The saved static-search output did not include enough `DeviceInfoCert` body detail to prove all nested JSON names. |
| `cradleId` | Not present in `GetDeviceCertV3Request` constructor evidence | Not sent | High that it is not a top-level field in this request model | Cradle association may be inferred server-side from `babyId`, role/account context, or the device assignment flow. |
| `roleId` / `userId` | Not present in `GetDeviceCertV3Request` constructor evidence | Not sent | Medium | These identifiers appear in response/association context elsewhere, but not as verified top-level request fields here. |
| Additional wrapper object | No wrapper around `GetDeviceCertV3Request` was observed | None | Medium | The app constructs the request DTO directly before calling the endpoint. |
| Headers/content type | No provisioning-specific header evidence found in the saved static-search output | Normal pycradlewise JSON request | Low | No special content type was proven. This remains a follow-up item if full decompiled sources are available. |

Exact evidence references from `apk-analysis-output/cradlewise-search-results.txt`:

- `apktool-out/smali_classes11/com/cradlewise/nini/core/mqtt/api/MqttBackendService$fetchDeviceCertsV3$2.smali`
  lines 16250-16254: loads `emailId`, `babyId`, `fcmToken`, and `device`, then
  constructs `GetDeviceCertV3Request(String, BigDecimal, String, DeviceInfoCert)`.
- Same file line 16262: uses endpoint path `/cradles/pairedUsers/v3`.
- `apktool-out/smali_classes11/com/cradlewise/nini/core/mqtt/api/model/GetDeviceCertV3Request.smali`
  lines 16303-16306: stores fields named `emailId`, `babyId`, `fcmToken`, and
  `device`.
- `jadx-out/sources/com/cradlewise/nini/core/mqtt/api/model/GetDeviceCertV3Request.java`
  line 19806: Kotlin metadata names the constructor parameters and types:
  `emailId: String`, `babyId: BigDecimal`, `fcmToken: String`, and
  `device: DeviceInfoCert`.
- `jadx-out/sources/com/cradlewise/nini/core/mqtt/api/model/GetDeviceCertV3Request.java`
  lines 19814 and 19820: decompiled copy/constructor signatures repeat the
  same four-argument shape.
- `apktool-out/smali_classes11/com/cradlewise/nini/app/usecases/GetDeviceCertificatesUseCaseImpl.smali`
  line 28797 and `apktool-out/smali_classes11/com/cradlewise/nini/core/mqtt/repository/MqttRepository.smali`
  line 14257: app/repository call sites invoke
  `MqttBackendService.fetchDeviceCertsV3(String, String, String, DeviceInfoCert, ...)`.

Likely reasons the current probe received HTTP 400:

1. Top-level field names are wrong: `email`/`baby_id`/`fcm_token` should be
   `emailId`/`babyId`/`fcmToken`.
2. `babyId` may need to be serialized as the numeric value used by the app
   model, not as a string-like identifier.
3. `fcmToken` was sent as null even though the app request model expects a
   non-null string.
4. The `device` object was guessed. Its snake_case keys are not verified as
   matching `DeviceInfoCert`.
5. The app may generate or persist a stable backend device identity before
   provisioning. The saved search output confirms a `DeviceInfoCert` parameter
   but does not prove the nested fields needed to recreate it safely.

Proposed corrected redacted payload shape for a future probe, not yet
implemented:

```json
{
  "emailId": "<redacted-email-like-identifier>",
  "babyId": "<redacted-numeric-baby-id>",
  "fcmToken": "<redacted-fcm-token-or-safe-test-equivalent-if-proven-valid>",
  "device": {
    "<DeviceInfoCert field names>": "<redacted values; unresolved from saved output>"
  }
}
```

Do not run another live provisioning test until the `DeviceInfoCert` constructor,
serializer annotations, and the app's backend device-ID generation path are
verified from fuller decompiled material. The current evidence is sufficient to
say the first probe payload shape was wrong, but not sufficient to safely
construct the complete `DeviceInfoCert` body.

### DeviceInfoCert static extraction (confirmed)

Offline DEX bytecode decoding (constructor `iput-object` order, `toString`
concatenation order, and the argument order used at both real call sites)
confirms the `DeviceInfoCert` class body that the prior section left
unresolved.

Confirmed class: `Lcom/cradlewise/nini/core/mqtt/api/model/DeviceInfoCert;`

Confirmed constructor:

```kotlin
DeviceInfoCert(
  registrationDate: String,
  appVersion: String,
  country: String,
  os: String,
  deviceName: String,
  osVersion: String,
  timezone: String,
  type: String,
  resolution: String
)
```

Confirmed fields, in constructor/declaration order:

- `registrationDate`
- `appVersion`
- `country`
- `os`
- `deviceName`
- `osVersion`
- `timezone`
- `type`
- `resolution`

Notes:

- No `deviceId` field exists on `DeviceInfoCert`.
- It is a Kotlin `data class` (has `copy`, `component1`..`component9`,
  `equals`, `hashCode`, `toString`).
- Field order was recovered from the `<init>` `iput-object` sequence and
  cross-checked against `toString()`'s literal concatenation order and
  against the argument order used at both real call sites. All three agree.

Value sources, from the call site used by the actual provisioning flow
(`MqttRepository.refreshDeviceCertificates`):

| Field | Source | Confidence |
|---|---|---|
| `registrationDate` | `SharedPreferences` key `CRIB_ACTIVATION_DATE`, default empty string | High |
| `appVersion` | Android `PackageManager` `packageInfo.versionName` | High |
| `country` | Hardcoded literal `"IN"` | High |
| `os` | Hardcoded literal `"android"` | High |
| `deviceName` | `Build.MODEL + "_" + Settings.Secure.ANDROID_ID` | High |
| `osVersion` | `Build.VERSION.SDK_INT` as a string | High |
| `timezone` | `TimeZone.getDefault().getDisplayName()` (human-readable name, not a TZ ID) | High |
| `type` | Phone/tablet classification from `DeviceType`, derived via `WindowManager`/`DisplayMetrics` | Medium |
| `resolution` | `DisplayMetrics` formatted as `"{width,height}"` | High |

Confirmed wrapper:

```kotlin
GetDeviceCertV3Request(
  emailId: String,
  babyId: BigDecimal,
  fcmToken: String,
  device: DeviceInfoCert
)
```

Wrapper notes:

- The public `fetchDeviceCertsV3` function signature takes `babyId` as a
  `String`.
- The app converts that `babyId` `String` to `java.math.BigDecimal` before
  constructing the `GetDeviceCertV3Request` DTO.
- On the wire, `babyId` therefore likely serializes as a JSON number, not a
  quoted string.
- `emailId`, `babyId`, and `fcmToken` are all read from
  `CradlewiseSharedPreference` under keys `USER_EMAIL`, `BABY_ID`, and
  `FCM_TOKEN` respectively (cached local preferences, not fetched live at
  call time).

Likely explanation for the prior HTTP 400, updated with this evidence:

1. Top-level field names were wrong: `email`/`baby_id`/`fcm_token` instead
   of `emailId`/`babyId`/`fcmToken`.
2. `babyId` was likely sent as a JSON string instead of a JSON number.
3. `fcmToken` was sent as `null`, but the app's request model expects a
   non-null string.
4. The guessed `device` object used snake_case keys and placeholder values
   that do not match any of the nine confirmed `DeviceInfoCert` field names.
5. The `DeviceInfoCert` body sent by the prior probe was incomplete and
   used the wrong shape entirely.

Proposed corrected redacted payload shape — **statically inferred, not yet
live-tested**:

```json
{
  "emailId": "<redacted-email-like-identifier>",
  "babyId": 0,
  "fcmToken": "<redacted-fcm-token-or-safe-test-equivalent-if-proven-valid>",
  "device": {
    "registrationDate": "<redacted>",
    "appVersion": "<redacted>",
    "country": "<redacted>",
    "os": "<redacted>",
    "deviceName": "<redacted>",
    "osVersion": "<redacted>",
    "timezone": "<redacted>",
    "type": "<redacted>",
    "resolution": "<redacted>"
  }
}
```

This shape is derived entirely from offline DEX bytecode decoding of the
already-extracted APK. It has not been sent over the network. Do not run it
without separate explicit approval, per the research constraints in this
document.

### Corrected gated provisioning payload builder (research/mqtt_probe)

The `research/mqtt_probe` scaffold now builds the corrected, statically
confirmed provisioning request instead of the earlier wrong snake_case body.
This is payload-construction code only; it has **not** been run live.

- The live payload builder emits the confirmed `GetDeviceCertV3Request` shape:
  `emailId` (string), `babyId` (JSON number, converted from the discovered
  identifier before POST), `fcmToken` (string), and `device`.
- The `device` object uses the confirmed 9-field `DeviceInfoCert` shape:
  `registrationDate`, `appVersion`, `country`, `os`, `deviceName`,
  `osVersion`, `timezone`, `type`, `resolution`, in constructor order.
- `country` and `os` are the two statically confirmed hardcoded literals
  (`"IN"`, `"android"`). Every other `device` value and the `fcmToken` are
  read only from explicit, safe environment variables — nothing is invented
  silently.
- The builder blocks before any POST if required inputs are missing:
  `missing_fcm_token_for_provisioning` when `CRADLEWISE_FCM_TOKEN` is absent,
  and `missing_device_info_for_provisioning` when any required
  `CRADLEWISE_DEVICE_*` value is absent.
- The builder remains behind the existing triple gate. Live provisioning
  still requires all of `--allow-live-auth`, `--allow-live-provisioning`, and
  `--acknowledge-provisioning-side-effect`; without the acknowledgement the
  command blocks with `provisioning_side_effect_ack_required` before any
  network activity.
- All probe output remains redacted. `emailId`, `babyId`, and `fcmToken`
  redact to the fixed marker in any emitted structure; the built payload
  itself is never placed in a report.

A future corrected live provisioning attempt would require env-provided FCM
and device metadata (`CRADLEWISE_FCM_TOKEN` and the `CRADLEWISE_DEVICE_*`
variables) and separate explicit approval to pass the triple gate. No
certificate download, S3 access, MQTT connection, shadow get/update, or crib
control code has been added; the scaffold remains limited to the gated
provisioning-inspect path.

### Credential scope

The strongest supported interpretation is that an IoT identity is scoped to an
app installation/device assignment and associated with a cradle/account role:

- provisioning consumes or validates a backend `deviceId`;
- `DeviceConfig` binds device, cradle, baby, and role identifiers;
- keystore, CA encryption alias, and local files are partitioned by cradle ID;
- provisioning has explicit `MAX_DEVICE_LIMIT_REACHED`,
  `DEVICE_ASSIGNMENT_FAILED`, and `REGISTRATION_NOT_COMPLETED` outcomes.

This rules out a static app-wide certificate and makes a purely account-wide
certificate unlikely. Exact AWS IoT policy conditions remain server-side and
cannot be proven from the APK.

### Authentication evidence matrix

| Auth piece | Source | Used for | Available to HA? | Evidence | Confidence | Risk |
|---|---|---|---|---|---|---|
| Cognito user session | Amplify/Cognito login | Authenticated REST and Storage session | Yes; live-auth-only probe succeeded with redacted metadata | APK: `CradlewiseApplication.setupAmplify`, `PostAuthBootstrapUseCaseImpl`; pycradlewise 0.3.1: `auth.py:CradlewiseAuth`; `research/mqtt_probe` live-auth-only result | High | Account credentials and short-lived tokens must remain protected |
| Cognito-derived IAM credentials | Cognito Identity Pool | API Gateway SigV4 in pycradlewise; Amplify services in app | Yes for REST/auth discovery; IoT permissions remain unproven | pycradlewise `auth.py:_exchange_for_iam`, `client.py:_api_request`; live-auth-only probe reached app config/auth/discovery successfully | High for REST/auth discovery; unknown for IoT | Their effective IoT permissions are unknown; possession does not prove MQTT authorization |
| IoT endpoint/region | App DEX constant | AWS IoT broker selection | Yes; public configuration, already extracted | APK `RemoteMqttConnectionV2.connect`; pycradlewise `bootstrap.py:_extract_iot_endpoint` | High | Endpoint correctness alone does not grant access |
| Backend app-device ID | Backend device registration/local repository | Device assignment and certificate provisioning; likely MQTT client ID | Not safely established for HA without a supported registration lifecycle | `GeneralRepository.getDeviceId`; `GetDeviceCertificatesUseCaseImpl.invoke`; `DeviceConfig.deviceId` | High for provisioning use; medium for client-ID mapping | Registering another client may consume a device slot or alter assignment state |
| Provisioning REST call | Authenticated app REST API | Requests IoT device configuration | Endpoint was reachable after auth but returned HTTP 400 with the current research payload/context; response structure was empty in the safe summary | `MqttBackendService.fetchDeviceCertsV3$2.invokeSuspend`; POST `/cradles/pairedUsers/v3`; gated provisioning-inspect result | High that endpoint exists; low that HA can safely reuse it | Requires app-specific device/FCM/account context and has assignment/limit side effects |
| S3 object metadata | `DeviceConfig` response | Locates certificate and private-key files | Only after successful provisioning and authorized Storage access | `DeviceConfig.getS3Bucket/getS3ObjectKeys`; `CertificateUtilsV3.downloadCertificates` | High | Metadata and downloaded material are sensitive; authorization may be narrowly scoped |
| X.509 client certificate | Server-selected S3 object | Mutual-TLS MQTT authentication | Not currently available to HA without provisioning; phone extraction is neither required nor recommended | `CertificateUtilsV3.downloadCertificates`, `saveCertificatesAndPrivateKey`; `AWSIotKeystoreHelper` | High | Long-lived device credential; compromise may enable crib control |
| RSA private key | Server-selected S3 object | Mutual-TLS proof of possession | Same as certificate: only through a supported provisioning flow | `CertificateUtilsV3.generatePrivateKeyFromString`; `saveCertificatesAndPrivateKey` | High | Highest-sensitivity artifact; requires encrypted storage, rotation, and revocation handling |
| Android Keystore AES key | Generated locally by Android | Encrypts certificate-related files at rest | No, and it should not be copied. HA would need its own secure-storage design | `CertificateEncryptionHelper.createSecretKey/getOrCreateSecretKey`; `AES/GCM/NoPadding`; per-cradle alias | High | Platform-bound protection cannot be transferred to HA |
| Java IoT keystore | Built locally from downloaded client pair | Input to `AWSIotMqttManager.connect(KeyStore, ...)` | Could be constructed independently only after legitimate provisioning | `CertificateUtilsV3.loadKeyStore`; `AWSIotKeystoreHelper.getIotKeystore` | High | File/password lifecycle and backups can expose the client identity |
| Static bundled certificate | None found in APK assets/resources | Not used | No | APK file inventory and certificate-loading flow | High | Treating public CA material as a client certificate would fail authentication |
| Shadow/topic authorization | AWS IoT policy attached server-side | Limits connect/subscribe/publish resources | Unknown | Not present in APK; inferred from standard AWS IoT authorization and observed failure | High that policy exists; no confidence about its exact clauses | May constrain client ID, thing name, topics, principal, or all four |

### Failure-cause ranking for historical pycradlewise

| Candidate | Assessment | Evidence |
|---|---|---|
| Wrong endpoint/region | Unlikely | The extracted ATS endpoint and `us-east-1` match the Android app. |
| Wrong authentication mode / missing certificate | Most likely | App uses `connect(KeyStore, ...)`; pycradlewise uses SigV4 WebSockets with Cognito IAM credentials. No evidence shows the Cognito role has IoT permissions. |
| Wrong client ID | Plausible and potentially simultaneous | App provisioning returns a backend `deviceId`; pycradlewise uses a random `ha-cradlewise-*` ID. The exact IoT policy condition is not visible. |
| Topic policy mismatch | Plausible after connection | App policies may restrict resources to the assigned cradle. Static analysis cannot inspect the policy. |
| Wrong custom state topic | Verified bug, but not the connect failure | App uses `/cradle/{cradleId}/cradle_state`; pycradlewise uses `{cradleId}/cradle_state`. Subscription happens only after connection. |
| Wrong Device Shadow topics | Unlikely | The classic shadow get/update paths match. |

### Feasibility conclusion

Home Assistant MQTT control is not proven impossible, and extracting credentials
from a phone should not be part of any design. The APK exposes a legitimate
server provisioning path. However, a gated research call to that provisioning
path failed with HTTP 400 and did not return device configuration structure. That
points to an invalid or incomplete research payload/context rather than
authorization failure. It is not yet safe to call from HA because its device-registration and
FCM semantics, quota impact, certificate rotation, and revocation behavior are
unknown.

Corrected Cognito WebSocket authentication remains only a hypothesis. A corrected
client ID may still fail if the Cognito role lacks IoT actions, and static analysis
cannot resolve that. The best current classification is:

> Potentially possible through proper server provisioning, but currently too
> fragile and security-sensitive for a Home Assistant integration.

### Next safe test plan for authentication

1. Keep Home Assistant REST-only and do not add integration MQTT/control code.
2. Do not retry `/cradles/pairedUsers/v3` from the harness until the
   HTTP 400 can be investigated without exposing raw response data, URLs,
   headers, identifiers, or other sensitive material.
3. Continue to avoid Storage, certificate download, IoT/MQTT connect, MQTT
   subscribe, MQTT publish, shadow get/update, and crib controls.
4. Before any further provisioning work, document the expected lifecycle for a new HA app-device
   registration: stable device ID, optional/required FCM token, device quota,
   unpair/revoke operation, and certificate refresh behavior.
5. Seek vendor confirmation that third-party clients may use the provisioning
   endpoint and that creating a dedicated HA device identity is supported.
5. If vendor confirmation is unavailable, perform only a separately approved,
   connection-only IAM test first. Use existing short-lived Cognito IAM credentials,
   expose no values, publish nothing, and record only the normalized broker result.
6. A failed IAM connection should end the WebSocket approach; do not vary random
   client IDs or probe policies.
7. Consider a provisioning test only with explicit approval after quota and
   revocation are understood. It must create a dedicated HA identity rather than
   reuse or extract the phone's certificate, and private material must never enter
   logs, diagnostics, backups, or source control.
8. Validate certificate revocation/removal before any control test. A credential
   that cannot be reliably revoked is unsuitable for production HA support.
9. Only then test a read-only mTLS connection and shadow `get` in an isolated
   harness. Control publishing remains a later, separately approved phase.
