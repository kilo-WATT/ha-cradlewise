# Cradlewise control endpoint research

## Scope and provenance

This note records offline static analysis of `Cradlewise_2.57.8_APKPure.xapk` only.
No application code was executed, no network requests were made, and no credentials
or live devices were used.

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
| Cognito user session | Amplify/Cognito login | Authenticated REST and Storage session | Yes; pycradlewise already performs equivalent Cognito login and IAM exchange | APK: `CradlewiseApplication.setupAmplify`, `PostAuthBootstrapUseCaseImpl`; pycradlewise 0.3.1: `auth.py:CradlewiseAuth` | High | Account credentials and short-lived tokens must remain protected |
| Cognito-derived IAM credentials | Cognito Identity Pool | API Gateway SigV4 in pycradlewise; Amplify services in app | Yes, short-lived credentials are already obtained | pycradlewise `auth.py:_exchange_for_iam`, `client.py:_api_request` | High | Their effective IoT permissions are unknown; possession does not prove MQTT authorization |
| IoT endpoint/region | App DEX constant | AWS IoT broker selection | Yes; public configuration, already extracted | APK `RemoteMqttConnectionV2.connect`; pycradlewise `bootstrap.py:_extract_iot_endpoint` | High | Endpoint correctness alone does not grant access |
| Backend app-device ID | Backend device registration/local repository | Device assignment and certificate provisioning; likely MQTT client ID | Not safely established for HA without a supported registration lifecycle | `GeneralRepository.getDeviceId`; `GetDeviceCertificatesUseCaseImpl.invoke`; `DeviceConfig.deviceId` | High for provisioning use; medium for client-ID mapping | Registering another client may consume a device slot or alter assignment state |
| Provisioning REST call | Authenticated app REST API | Requests IoT device configuration | Technically reachable through signed REST, but not safely reusable yet | `MqttBackendService.fetchDeviceCertsV3$2.invokeSuspend`; POST `/cradles/pairedUsers/v3` | High | Requires app-specific device/FCM/account context and has assignment/limit side effects |
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
server provisioning path. However, it is not yet safe to call from HA because its
device-registration and FCM semantics, quota impact, certificate rotation, and
revocation behavior are unknown.

Corrected Cognito WebSocket authentication remains only a hypothesis. A corrected
client ID may still fail if the Cognito role lacks IoT actions, and static analysis
cannot resolve that. The best current classification is:

> Potentially possible through proper server provisioning, but currently too
> fragile and security-sensitive for a Home Assistant integration.

### Next safe test plan for authentication

1. Keep this phase offline. Do not call `/cradles/pairedUsers/v3`, Storage, or IoT.
2. Before any live work, document the expected lifecycle for a new HA app-device
   registration: stable device ID, optional/required FCM token, device quota,
   unpair/revoke operation, and certificate refresh behavior.
3. Seek vendor confirmation that third-party clients may use the provisioning
   endpoint and that creating a dedicated HA device identity is supported.
4. If vendor confirmation is unavailable, perform only a separately approved,
   connection-only IAM test first. Use existing short-lived Cognito IAM credentials,
   expose no values, publish nothing, and record only the normalized broker result.
5. A failed IAM connection should end the WebSocket approach; do not vary random
   client IDs or probe policies.
6. Consider a provisioning test only with explicit approval after quota and
   revocation are understood. It must create a dedicated HA identity rather than
   reuse or extract the phone's certificate, and private material must never enter
   logs, diagnostics, backups, or source control.
7. Validate certificate revocation/removal before any control test. A credential
   that cannot be reliably revoked is unsuitable for production HA support.
8. Only then test a read-only mTLS connection and shadow `get` in an isolated
   harness. Control publishing remains a later, separately approved phase.
