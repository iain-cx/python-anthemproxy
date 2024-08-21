# python-anthemproxy

## Rationale

[Anthem](https://anthemav.com/) devices such as MRX and AVM receivers and processors, as well as STR amplifiers, offer a network control protocol used by clients such as the official Anthem mobile app, Anthem ARC software, and a [Python module](https://github.com/nugget/python-anthemav) designed to support a [Home Assistant](https://home-assistant.io/) plugin.

The protocol defines a discovery process whereby the device responds to a query packet sent to UDP port 14999, as well as a simple control protocol using TCP port 14999.

However, the implementation has some shortcomings.  It is not clear whether these are due to bugs or design decisions.

### Local subnet discovery only

An Anthem device may respond to unicast discovery packets sent specifically to the device's own IP address, or broadcast packets sent either to the subnet broadcast address or to 255.255.255.255.  However, no response will be sent unless the client sending the discovery packet is on the same subnet as the target device.

For example, if the device has IP address 192.168.0.123/24, it will not respond to a discovery request from, eg 192.168.1.100, even if that that client connects directly to the device or broadcast packets are forwarded between the two networks.

Official Anthem apps send discovery packets to 255.255.255.255 and will only attempt to control devices which they previously discovered.  They cannot be configured to connect directly to an IP address.

This means that you cannot use the official apps to control a device on a different subnet even if you know its IP address and are able to route packets to and from that subnet.

This proxy can be run on the same subnet as the clients, so it can be discovered by them, and forward commands to a real device on a different routable subnet.

### No concurrent client connections

When a client connects to an Anthem device's control port, it can send commands and receive response back from the device only for as long and the connection remains open and no other client connects.

As soon as a second client connects to the device, no further data will be sent to the first client, even if the connection remains open.

Essentially, this means that each new connection terminates any previous connection, and can be seen by concurrently using the official app on two mobile devices, or the app and Python client.  When the device's status changes, for instance by increasing or decreasing the volume, only the most recently connected client will see the new volume level.

This proxy maintains a single connection to the target device and accepts any number of client connections.  A command received from any client is sent to the target, and data sent back from the target is relayed to all connected clients.

Taking advantage of the local subnet discovery property, you could connect your Anthem device to a separate subnet and run the proxy on the same subnet as your clients, so there is no risk that a client would accidentally connect to the real device and terminate another client's connection.

## Usage

The proxy can be run in either of two modes.

### Discovery mode

In discovery mode, the proxy sends discovery packets and prints a JSON representation of each unique device which responds.

Run it as follows:

```shell
anthemproxy [options] discover
```

### Proxy mode

In proxy mode, the proxy connects to the specified Anthem device and listens for connections from clients.  Any command received by a client is forwarded to the target device, and any status messages from the target are relayed to all clients.  The proxy will also respond to discovery packets it receives, advertising its services.

Run it as follows:

```shell
anthemproxy [options] proxy
```

## Options

### Specifying options

Options can be specified either as command line flags or as environment variables.  To pass an option via a flag, use the flag name described below, eg `--host 192.168.0.123`.  To pass an option via an environment variable, convert the flag name to uppercase and prefix `ANTHEMPROXY_`, eg `ANTHEMPROXY_HOST=192.168.0.123`.

Boolean options, such as `--debug`, don't require values when passed on the command line, but should be specified as `true` or `1` in the environment, eg `--debug` or `ANTHEMPROXY_DEBUG=true`.

### Supported options

* `--alias <name>`: Sets the name of the proxy as advertised in discovery responses.  Optional, but it is advisable to set it if the target device is on the same subnet, otherwise both the real device and the proxy will appear under the same name to clients.  Restricted to 16 characters by the protocol.

* `--bind <address>`: Sets the local IP address to which the proxy will bind a socket.  Default is `0.0.0.0`.

* `--debug`: Enable debug logging.  Note that the environment variable `DEBUG` can also be set (to any non-empty string) to enable debugging.

* `--forward`: Respond to discovery requests from other proxies.

* `--host <address>`: Sets the hostname or IP address of the target device.  The proxy will send a discovery packet if no value is provided, and use the first device which responds.

* `--listen <port>`: Sets the port on which the proxy will listen.  Default is `14999` and should probably not be changed.

* `--model <model>`: Sets the device model which the proxy will advertise itself as.  Refer to the Startup section for more details.  The proxy will attempt to discover it if no value is provided.  Restricted to 16 characters by the protocol.

* `--name <name>` Sets the target device name.  Refer to the Startup section for more details.  The proxy will attempt to discover it if no value is provided.  Restricted to 16 characters by the protocol.

* `--port <port>`: Sets the port on which the target device (not the proxy) is listening.  Default is `14999`.

* `--serial <serial>` Sets the target device serial.  Refer to the Startup section for more details.  The proxy will attempt to discover it if no value is provided.  Restricted to 16 characters by the protocol.

## Startup

The proxy needs four pieces of information about the target device in order to appear correctly in the official apps.

Most important is the **host**, the hostname or IP address of the target device.  If you only have one device on your network, you can allow the proxy to discover it, but be aware that doing so could cause confusion if you later add another Anthem device, and that discovery is only possible if the proxy is on the same subnet as the target.

Also important is the **model**, which is a string representing the type of device being proxied.  Known values include:

* `AVM 60`: AVM 60 processor

* `AVM 70`: AVM 70 processor

* `AVM 90`: AVM 90 processor

* `MRX 510`: MRX 510 receiver

* `MRX 520`: MRX 520 receiver

* `MRX 540`: MRX 540 receiver

* `MRX 710`: MRX 710 receiver

* `MRX 720`: MRX 720 receiver

* `MRX 740`: MRX 740 receiver

* `MRX 1120`: MRX 1120 receiver

* `MRX 1140`: MRX 1140 receiver

* `MRX SLM`: MRX SLM receiver

* `SA141117`: STR integrated amplifier

* `SP141117`: STR preamplifier

If the specified model is not known to the official app, the proxy will not appear even if it is discovered correctly.  If the specified model is not correct for the proxied device, the app may claim to be unable to connect to the proxy, or may connect but not function correctly.  You can specify the model if you know it, otherwise the proxy will send a discovery request to try to learn it automatically.

If you have a device not listed above, please consider raising a PR with the appropriate model value.

The proxy also needs a **serial**, which is usually just the MAC address of the device, eg `00AABBCCDDEE`.  The official apps don't actually care what the value is, except that they will only show one device with the same IP address and serial.  If you restart the proxy with a different serial it will briefly appear more than once in the UI, so using a consistent serial is advised.  It's safe to use the same serial for the proxy as for the target device, and for that reason the proxy will send a discovery request to try to learn it automatically if you don't explicitly set a serial.

The final information needed is a **name**.  The proxy distinguishes between the name of the device, which can be passed with `--name` and the name of the proxy, which can be passed with `--alias`.  The alias name is what is shown in the UI of the official apps.  The proxy will send a discovery request to try to learn the device's name if you don't explicitly set it.  It will also use the device's name as its alias if you don't explicitly set one.  That may be confusing if the real device is also visible on your network, so consider setting an alias.

If you don't know your device's model, name or serial, you will need to run the proxy once in discovery mode to learn them, then specify them explicitly when starting the proxy, or start the proxy and allow it to send a discovery request and learn the values.  Both options, however, require the proxy to be on the same subnet as the device, which may not be what you want in the long run.

## Protocols

Both the discovery protocol and the control protocol are documented by Anthem and are simple to understand.  A brief overview follows, though the main goal of section is to explain the implementation.

### Discovery protocl

Anthem devices listen for UDP packets of the following form:

* 4 octets magic string: PARC
* 2 octets reserved: always 0x00
* 1 octet discovery flag: 1 if this is a discovery packet, 0 if it is a response
* 1 octet reserved: always 0x1
* 4 octets packet version: always 0x0001
* 4 octets TCP port on which the control protocol listens: default 14999
* 16 octets device name string
* 16 octets device model string
* 16 octets device serial string

Note that some devices, such as the MRX 720, allow changing the control protocol's port and some, such as the STR preamplifier, do not.

Note also that "strings" will be null-padded if their length is less than the space allocated to them, but a null octet is NOT required, ie a device name can be 16 characters long.

In `discover` mode, or when started without all details of the target device being specified, this proxy sends discovery packets with the magic string set, reserved octets set to the values described above, discovery flag set to 1, version set to 1, TCP port set according to the `--bind` flag, device name and serial empty, and device model set to the magic string `Anthem Proxy`.  Another proxy receiving the packet will not respond unless the `--force` flag was used.

In `proxy` mode, this proxy responds to discovery packets as above, but with the discovery flag set to 0, device name set to the proxy's `--alias` name, and model and serial as configured or discovered.

### Control protocol

Anthem devices accept TCP connections and listen for commands which typically take the form `ZnXXXm` where `n` is the zone number (and is just 1 for devices which don't have multiple zones), `XXX` is some property and `m` is either `?` to query the property or a desired value.  For example, `Z1VOL?` queries the zone 1 volume, while `Z1VOL-37` sets the zone 1 volume to -37dB.

The device will send status messages to a connected client, such as `Z1VOL-37` reporting the zone 1 volume.

As discussed earlier in this document, only one client connection is maintained at a time, and each new connection will disconnect the existing client.

Note that, whilst it is tempting to think of the control protocol as being like any other command/response protocol, and that for example, the `Z1VOL?` request would be followed by the `Z1VOL-37` reply, that is not technically correct.

Commands sent to the device are validated and acted upon where possible, but any subsequent status messages are not actually replies to commands, but rather updates which are sent as a result of the device's status changing.  If you use the IR remote control or front panel to change the volume, for instance, a connected client will also receive status messages without having to poll the device periodically.  Thus, for example, you can see the volume indicator change in the official app when adjusting the volume via a physical control.

In `proxy` mode, this proxy opens a connection to the target device and immediately begins listening for status messages.  Whenever a client connects to the proxy, any commands it sends are relayed directly to the device without any validation, and any messages the device sends back to the proxy are passed on to all clients.

The proxy will automatically attempt to reconnect to the target device if it is disconnected, for example because another client connected, or the device was reset.
