# Module Communication

## Purpose

Define local TCP exchanges, the shared telemetry snapshot, and recovery and confirmation behavior for a configured stove.

## Requirements

### Requirement: Local runtime transport

Each runtime exchange SHALL open an IPv4 TCP connection to the configured host on port 80, use a 10-second socket timeout, send one frame and decode one receive of up to 1,024 bytes before closing the socket. Blocking socket work SHALL run off the Home Assistant event loop. The coordinator SHALL apply a 15-second async budget to the executor poll or command operation, excluding time spent waiting to acquire the coordinator lock.

#### Scenario: Poll executes without blocking Home Assistant
- GIVEN a ready entry and a fake TCP peer
- WHEN a refresh is due
- THEN the integration sends its query over a local TCP connection on port 80 from an executor
- AND the connection is closed when the exchange exits

### Requirement: Bulk polling and error fallback

A poll SHALL request `["SEL","0"]`. An empty first token in the bulk reply SHALL fail the poll. If the first token is `ERR`, the poll SHALL perform one additional exchange with `["SEC","3","I30001000000000000","I30002000000000000","I30017000000000000"]` and use the fallback response in place of the bulk response. Normal polling SHALL NOT issue ad hoc reads for individual IDs.

#### Scenario: Module reports an error to the bulk request
- GIVEN the module replies to the bulk request with an `ERR` first token
- WHEN the coordinator polls
- THEN it sends the fixed fallback query for state, error, and boiler water
- AND parses readings from that response

#### Scenario: Empty bulk response
- GIVEN the bulk exchange decodes to an empty string
- WHEN the coordinator processes the response
- THEN it follows the poll failure path rather than publishing a fresh snapshot

### Requirement: Reading format and snapshot merge

The poll SHALL strip square brackets and double quotes and split the reply on commas. For each token longer than three characters it SHALL parse character one as the marker, characters two through six as the ID, and the substring starting at zero-based offset seven as an integer. Tokens with invalid integers SHALL be ignored.

#### Scenario: Parse a setpoint token
- WHEN the poll processes `J30138000000000020`
- THEN it extracts ID `30138`, marker `J`, and integer `20`

### Requirement: Snapshot merge

Readings SHALL be stored as `[integer, marker]`, keyed by reading ID. The latest valid token for an ID SHALL replace its previous value and marker; absent IDs SHALL remain in the snapshot. Room values SHALL be subject to room-probe filtering before publication.

#### Scenario: Poll updates one reading and leaves others intact
- GIVEN the snapshot contains room temperature `30006` and setpoint `30138`
- WHEN the reply contains a valid new token for `30006`, an invalid integer token for another reading, and no token for `30138`
- THEN the new `30006` value and marker are merged
- AND the malformed reading is ignored and `30138` is retained

### Requirement: Poll health and backoff

The normal poll interval SHALL be 120 seconds. A poll exception SHALL increase the interval to five minutes and increment the consecutive failure count. With cached successful data, the first two consecutive failures SHALL return it as a successful update. The third failure, or any attempted poll failure without a successful cache, SHALL clear that cache and report a failed update. A successful poll SHALL reset the count, record its answer time, and restore the normal interval.

#### Scenario: Module connection degrades and recovers
- GIVEN at least one poll succeeded and its answer time is recorded
- WHEN three consecutive poll attempts fail
- THEN the first two return cached data while using the five-minute interval
- AND the third reports a failed update without advancing the last successful answer time
- WHEN a subsequent poll succeeds
- THEN it resets the failure count, sets a new answer time and resumes the 120-second interval

### Requirement: Poll and command coordination

Runtime polls and commands for the same coordinator SHALL use one shared exchange lock. A command SHALL wait for the lock; a poll that starts while the lock is held SHALL return the last successful snapshot without starting a new exchange or counting a poll failure. If there is no cached successful snapshot in that case, it SHALL report an update failure instead. A failure to exchange a command SHALL be logged and reported as an unsuccessful send, not counted as a poll failure.

#### Scenario: Refresh requested during a command
- GIVEN a cached successful snapshot and a command exchange holding the lock
- WHEN a refresh reaches the polling path
- THEN no second exchange is opened
- AND the cached snapshot is returned without changing poll health counters

### Requirement: Post-command refresh

After a command send attempt completes, the coordinator SHALL schedule a refresh request for 25 seconds later, replacing any previously pending command refresh. This SHALL apply to both successful and unsuccessful sends. A send is considered successful when an exchange completes and decodes without an exception; the response body is not checked for a device acknowledgment. Switch actions can also request a refresh immediately; Home Assistant controls actual refresh scheduling.

#### Scenario: Commands are sent close together
- GIVEN a command refresh is scheduled and has not yet fired
- WHEN a second command attempt completes
- THEN the earlier timer is canceled
- AND a refresh request is due 25 seconds after the second attempt

#### Scenario: Decoded response does not acknowledge a command
- GIVEN a fake device replies to a write with a decoded `ERR` token
- WHEN the send completes without an exception
- THEN the command path treats the exchange as successful
- AND the delayed refresh is still requested to read back the stove state
