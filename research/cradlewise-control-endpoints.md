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
