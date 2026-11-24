# Module Communication Delta

## MODIFIED Requirements

### Requirement: Post-command refresh

After a send attempt the coordinator SHALL schedule a refresh for 25 seconds later, replacing any pending command refresh, even on failure. Legacy commands SHALL count any decoded reply as send success. Opted-in boiler and power commands SHALL treat an empty reply or `ERR` as failure; other replies do not confirm a setting was applied. Switch actions can also request an immediate refresh, subject to Home Assistant scheduling.

#### Scenario: Commands are sent close together
- GIVEN a command refresh is scheduled and has not yet fired
- WHEN a second command attempt completes
- THEN the earlier timer is canceled
- AND a refresh request is due 25 seconds after the second attempt

#### Scenario: Decoded response does not acknowledge a command
- GIVEN a fake device replies to a legacy write with a decoded `ERR` token
- WHEN the send completes without an exception
- THEN the legacy command path treats the exchange as successful
- AND the delayed refresh is still requested to read back the stove state

#### Scenario: An opted-in command is explicitly rejected
- GIVEN a fake device replies to an opted-in boiler or power write with `ERR`
- WHEN the send completes
- THEN the integration reports the failure without changing the displayed state
- AND the delayed refresh is still requested
