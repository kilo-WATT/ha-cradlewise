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

## Result

No REST endpoint for any requested crib control was found or verified. The Android
app implements these controls through AWS IoT Device Shadow updates over MQTT.
This is distinct from its REST API, which does contain generic POST, PUT, PATCH,
and DELETE support and several non-control write operations.

The MQTT transport is established by the following evidence:

- `RemoteMqttConnectionV2.publish` publishes control data.
- `RemoteMqttConnectionV2.subscribeUpdateAccepted` subscribes to
  `$aws/things/.../shadow/update/accepted`.
- `MqttUtilsV2.getTopics` and `Topics.<clinit>` construct the Device Shadow
  `get`, `update`, `update/accepted`, and `update/rejected` topics.
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
