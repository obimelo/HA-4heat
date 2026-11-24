# Integration Setup Delta

## MODIFIED Requirements

### Requirement: User-configured entry

The UI flow SHALL accept a display name, host and legacy command mode, initially `Stove`, `192.168.0.0`, and `false`. For a new host it SHALL probe with `["SEL","0"]` over TCP port 80 off the event loop. It SHALL require at least one valid reading, using only the fixed error fallback if the bulk reply is `ERR`. On success it SHALL use the name as the title and save the host, mode and valid reading tokens as monitored conditions. On failure it SHALL show `cannot_connect` on the host field.

#### Scenario: Successful UI setup
- GIVEN `192.168.1.20` is not configured
- WHEN the user submits the name `Living room`, that host and legacy mode `false`, and the module returns a decoded probe reply containing one valid reading
- THEN the entry is titled `Living room` and stores the host and mode
- AND its monitored conditions are taken from the probe response

#### Scenario: Connection fails before entry creation
- GIVEN the user is configuring a new host
- WHEN the connection fails or the probe produces no usable reading
- THEN the form shows `cannot_connect` without creating an entry
- AND a retry with a usable reply can complete setup

#### Scenario: Probe falls back after an error
- GIVEN the initial query receives `ERR`
- WHEN the fixed fallback query returns a valid reading
- THEN the entry is created using the fallback reading inventory
- AND no other query is sent
