# Module Communication Delta

## MODIFIED Requirements

### Requirement: Post-command refresh

After a native control send attempt, its requested value SHALL remain provisional until confirmed or verified. If unconfirmed, the integration SHALL request a debounced refresh after 25 seconds even for an empty reply, `ERR`, or timeout. It SHALL notify only for a fresh mismatch and drop unchecked assumptions after 50 seconds. Other commands SHALL keep existing refresh and reply behavior.

#### Scenario: Commands are sent close together
- GIVEN a normal delayed command refresh is scheduled
- WHEN another send using the normal delayed refresh completes
- THEN the earlier timer is canceled
- AND a refresh request is due 25 seconds after the second attempt

#### Scenario: Decoded response does not acknowledge a command
- GIVEN a fake device replies to a legacy generic write with a decoded `ERR` token
- WHEN the send completes without an exception
- THEN the legacy path treats the exchange as successful
- AND the delayed refresh is still requested

#### Scenario: An opted-in command is explicitly rejected
- GIVEN a fake device replies to a guarded write with `ERR`
- WHEN the send completes
- THEN the delayed refresh is still requested without an immediate failure notification
- AND a matching fresh readback produces no failure notification

#### Scenario: Combustion power is confirmed before the scheduled check
- GIVEN a combustion power request and a scheduled verification check
- WHEN a fresh poll reports the requested power setting
- THEN the pending confirmation ends and the delayed check is canceled
- AND no setting command is resent

#### Scenario: Two different controls have pending confirmation
- GIVEN two accepted requests for different controls on one stove
- WHEN a fresh poll confirms only one of them
- THEN only the confirmed control's pending checks and notice end
- AND one bulk poll may confirm multiple controls when it contains their matching readings
