# Install HA-4heat in Home Assistant Container

HA-4heat is a **custom integration**, not a separate Docker service or a Home Assistant app/add-on. Install it in your existing Home Assistant container's persistent `/config/custom_components/4heat` directory. You do not need to build a Home Assistant image, change your Compose file, or install the Windows controller on the Docker host.

The command examples below use a Bash shell on the Docker host (or an SSH session to it) unless marked **PowerShell**. Replace the example container name, host address, and paths with yours.

## 1. Identify the container and its configuration mount

On the machine that runs Docker:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
HA=homeassistant                    # Use your actual container name
docker exec "$HA" python -m homeassistant --version
docker inspect --format '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Type}} {{.Source}} -> {{.Destination}} (writable={{.RW}}){{println}}{{end}}{{end}}' "$HA"
```

- The project declares Home Assistant **2025.1 or later** as its minimum. The integration has been tested against Home Assistant Core 2025.1.4 and 2026.11.3 with simulated stove replies, not every Home Assistant release or stove model.
- **`bind`**: The source is your host configuration directory, e.g. `/srv/homeassistant/config`. It should contain `configuration.yaml`. Use the existing mount; don't create a new one for HA-4heat.
- **`volume`**: `/config` lives in a Docker-managed volume. Use the container commands in this guide instead of editing Docker's internal volume directory.
- If there is **no `/config` mount**, stop here: a copy inside the container alone might disappear when it is recreated. Back up the existing configuration and set up a persistent mount using the [official Home Assistant Container guide](https://www.home-assistant.io/installation/linux/#install-home-assistant-container) before installing. If the mount is read-only inside the container, install on the host side of a writable bind mount instead.

Take a [Home Assistant backup](https://www.home-assistant.io/common-tasks/general/backups/) before installing or upgrading. Keep that backup outside the container.

## 2. Choose the source version

Use the **manual install** below to test the boiler and combustion controls from this checkout. A repository download sees only what has been published: it cannot install local, uncommitted implementation changes. Even if this local manifest and a published package both say `0.7.0`, they may contain different code.

If you want a **published** version instead, use the [Home Assistant Marketplace](https://www.hacs.xyz/docs/marketplace/) or [HACS](https://www.hacs.xyz/docs/use/repositories/dashboard/) if available for your Home Assistant version. Search for **4Heat**, verify the repository and version, download it, and restart Home Assistant. Use one install method per integration: a future Marketplace/HACS update can overwrite a manually installed copy.

For manual installation, the only files you need are **`custom_components/4heat/` and its contents**. Do not copy the entire repository or `4heat-controller.exe`.

### If the source is on your Windows PC

Package the current working files, then upload the ZIP to your Docker host. The example assumes SSH/SCP access; an existing file share or other transfer method works too.

```powershell
Set-Location 'C:\Source\Repos\obimelo\HA-4heat'
$package = Join-Path $env:TEMP 'HA-4heat-component.zip'
Compress-Archive -LiteralPath '.\custom_components\4heat' -DestinationPath $package -Force
$dockerHost = 'your-user@your-docker-host'
scp $package "${dockerHost}:~/HA-4heat-component.zip"
```

On the Docker host, unpack it into a temporary directory:

```bash
unpack_dir=$(mktemp -d)
unzip "$HOME/HA-4heat-component.zip" -d "$unpack_dir"
SRC="$unpack_dir/4heat"
```

If the correct source checkout is already on the Docker host, skip packaging and unpacking. Set `SRC` to its `custom_components/4heat` path instead, e.g. `SRC=/srv/repos/HA-4heat/custom_components/4heat`.

## 3. Install in `/config` and restart

The following Bash block works with a normal writable `/config` bind mount or named volume. It stages the new files before replacing the active copy and keeps the previous integration directory outside `custom_components` for rollback. Run it with `HA` and `SRC` set in the same shell. If a step fails, review the output before trying again.

```bash
(
    set -euo pipefail
    test -f "$SRC/manifest.json"
    test -f "$SRC/__init__.py"
    stage_dir=$(docker exec "$HA" mktemp -d /config/.4heat-stage.XXXXXX)
    backup_dir=$(docker exec "$HA" mktemp -d /config/.4heat-backup.XXXXXX)
    tar -C "$SRC" -cf - . | docker exec -i "$HA" tar -xf - -C "$stage_dir"
    docker exec "$HA" sh -eu -c '
        test -r "$1/manifest.json"
        test -r "$1/__init__.py"
        mkdir -p /config/custom_components
        if [ -e /config/custom_components/4heat ]; then
            mv /config/custom_components/4heat "$2/4heat"
        fi
        mv "$1" /config/custom_components/4heat
    ' sh "$stage_dir" "$backup_dir"
    printf 'Backup of previous integration (if installed): %s/4heat\n' "$backup_dir"
)
```

If your container mounts `/config` read-only from a host directory, do the same operation on the **host**: copy the whole integration directory into `<config_dir>/custom_components/4heat` and move any existing copy out of `custom_components` first. The container still needs permission to read the copied files.

Verify the layout and restart **only** Home Assistant:

```bash
docker exec "$HA" ls -l /config/custom_components/4heat/manifest.json
docker restart -t 60 "$HA"
docker logs --since 10m "$HA" 2>&1 | grep -Ei '4heat|custom_components'
```

For Compose, you can use `docker compose restart -t 60 homeassistant` from the Compose project directory instead; `homeassistant` in that command is the **service name**, which can differ from the container name. The log filter may print nothing on a normal start. Inspect the unfiltered logs if the frontend does not come back. Do not recreate the container just to load these files.

## 4. Connect a stove in Home Assistant

1. Find the local IPv4 address of the stove's **4Heat Wi-Fi module** in your router or the address you already use in 4Heat Controller. A router DHCP reservation helps keep that address stable.
2. Close or disconnect 4Heat Controller while setting up or testing Home Assistant. Some modules struggle if multiple apps query them at once.
3. For a **new** stove, go to **Settings → Devices & services → Add integration**, search for **4Heat** or **4Heat Stove**, and enter the stove's name and the module address. Enter only the IP address or hostname, not `http://`, a URL, or the Docker host address. Leave legacy command mode off unless your stove specifically requires it. No `configuration.yaml` edit is needed.
4. For an **existing** stove, do not add it again. After restarting Home Assistant, use its existing entry and confirm that it reports fresh readings before testing controls.
5. **Enable boiler water and five-level combustion controls** is on by default unless you previously turned it off. In **Configure**, turn it off if the stove offers a sixth manual power level or you aren't sure it is compatible.

The option adds a **Boiler Target** slider (60–80 °C, or a tighter range reported by the stove) and a **Combustion Power** dropdown (**Auto, P5, P4, P3, P2, P1**) to the stove's device page. Changing either setting does not start the stove. The integration no longer adds the room thermostat or sensors outside the supported readings listed in the [README](../README.md#configuration).

All four controls (**Power ON/OFF**, **Clear Error**, **Boiler Target**, and **Combustion Power**) immediately show the requested value. The integration verifies it against a fresh stove reading, requesting a check after about 25 seconds if needed. It corrects the control and sends a notification only if the stove reports a different value. The read-only sensors are not updated optimistically.

The two controls replace the duplicate read-only displays on the device page. The read-only sensor entities are hidden, not disabled, so existing automations can still use them.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| **4Heat** is not in Add integration | Verify `/config/custom_components/4heat/manifest.json` exists, not a nested `4heat/4heat` path. Confirm the files are readable inside the container, restart Home Assistant, and check the logs for integration errors. |
| The flow cannot reach the module | Verify the IP address, that the Wi-Fi module is online, and that the container can reach the module over local TCP port **80**. Check Docker/LAN routes, VLAN firewall rules, and Wi-Fi guest or client isolation. |
| The stove works in the Windows app but not in Home Assistant | The Windows PC and Docker host may reach different networks. Test from inside the Home Assistant container, not from your web browser or the Windows PC. Disconnect other stove clients before retrying. |
| **Configure** does not show the boiler option | Check that you installed the local build containing `number.py` and `select.py` under `/config/custom_components/4heat/`, and restarted Home Assistant after replacing the files. An older published version may not contain the option. |
| The new entities are missing or unavailable | Confirm the option is enabled for that entry, the entry has reloaded, and the stove has reported usable readings. A failed poll can leave old readings visible while blocking writes. |
| Settings disappear after recreating the container | Verify that the same persistent host folder or named volume is still mounted at `/config`. |

To test connectivity once, from the Docker host (substitute your module's address):

```bash
STOVE_IP=192.168.1.50
docker exec "$HA" python -c 'import socket, sys; s = socket.create_connection((sys.argv[1], 80), timeout=5); s.close(); print("TCP connection succeeded")' "$STOVE_IP"
```

This opens and closes a TCP connection without sending a stove command. Success confirms network reachability, not protocol compatibility. **Do not** set up a Docker port mapping or internet port forwarding for the stove. Normal Docker bridge networking can work if the container can route to the stove; do not change a working network mode just for this integration.

## Roll back a manual upgrade

If you need to revert, use the `backup_dir` path printed during installation. The example first checks that the saved copy exists, then moves the new copy aside and restores the old one. It does not delete your Home Assistant configuration or entity history.

```bash
BACKUP=/config/.4heat-backup.XXXXXX    # Replace with the actual path, without /4heat
docker exec "$HA" sh -eu -c '
    test -r "$1/4heat/manifest.json"
    if [ -e /config/custom_components/4heat ]; then
        replaced=$(mktemp -d /config/.4heat-replaced.XXXXXX)
        mv /config/custom_components/4heat "$replaced/4heat"
    fi
    mv "$1/4heat" /config/custom_components/4heat
' sh "$BACKUP"
docker restart -t 60 "$HA"
```

If there was no previous copy, disable or remove the 4Heat entry in Home Assistant if it exists, move the `4heat` folder out of `custom_components`, and restart. Do not edit Home Assistant's `.storage` files by hand.
