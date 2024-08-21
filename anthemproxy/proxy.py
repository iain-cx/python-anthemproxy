from anthemproxy.client import AnthemProxyClient
from anthemproxy.connection import AnthemProxyConnection
from anthemproxy.packet import AnthemDiscoveryPacket
from anthemproxy.protocol import AnthemProtocol
import asyncio
import logging

# A proxy for an AnthemDevice.
class AnthemProxy(asyncio.Protocol):
  def __init__(self, device, host = None, port = None, forward = None):
    self.loop = asyncio.get_running_loop()
    self.clients = set()
    self.connection = None
    self.device = device
    self.host = host or AnthemProtocol.LISTEN
    self.port = port or AnthemProtocol.PORT
    self.transport = None
    self.protocol = None
    self.discovery = None
    self.listen = True
    self.forward = forward or False
    self.server = None

  async def run(self):
    self.transport, self.protocol = await self.loop.create_datagram_endpoint(lambda: self, local_addr = (self.host, self.port), reuse_port = True, allow_broadcast = True)
    try:
      self.connection = AnthemProxyConnection(self)
      self.server = await self.loop.create_server(lambda: AnthemProxyClient(self), self.host, self.port, reuse_port = True, start_serving = False)
      while self.listen:
        await self.server.start_serving()
    except Exception as e:
      logging.error('Creating TCP endpoint: %s', e)
      raise e
    finally:
      self.listen = False
      if self.connection:
        self.connection.close()
      if not self.transport.is_closing():
        self.transport.close()

  def client_connected(self, client):
    logging.debug('Adding client %s:%u.', client.host, client.port)
    self.clients.add(client)

  def client_disconnected(self, client):
    logging.debug('Removing disconnected client %s:%u.', client.host, client.port)
    self.clients.remove(client)

  def connection_made(self, transport):
    logging.debug('Discovery transport ready for proxy: %s', self.device.alias)
    self.discovery = transport

  def connection_lost(self, e):
    logging.info('Shutting down.')
    self.listen = False
    for client in self.clients:
      client.close()
    self.connection.close()

  def on_discovery_request(self, host, port):
    addr = (host, port)
    if not self.device.name or not self.device.host:
      logging.debug("Can't respond yet.")
      return
    packet = AnthemDiscoveryPacket(device = self.device)
    try:
      logging.debug('Responding to %s:%u', host, port)
      packet.send(self.discovery, addr)
    except Exception as e:
      logging.error('Sending discovery packet to %s:%u: %s', host, port, e)
      self.discovery.close()

  def on_discovery_reply(self, host, port, version, name, model, serial):
    if self.device.host and host != self.device.host:
      logging.debug('Ignoring reply from %s not %s.', host, self.device.host)
      return
    if self.device.port and port != self.device.port:
      logging.debug('Ignoring reply from port %s not %s.', port, self.device.port)
      return
    self.device.host = host
    self.device.port = port
    logging.debug('Device: %s; model: %s; serial: %s', AnthemProtocol.decode(name), AnthemProtocol.decode(model), AnthemProtocol.decode(serial))
    if not self.device.name:
      self.device.name = AnthemProtocol.decode(name)
      if len(self.device.name) < 10:
        self.device.name += ' proxy'
      elif len(self.device.name) < 16:
        self.device.name += '*'
    self.device.version = version
    self.device.model = AnthemProtocol.decode(model)
    self.device.serial = AnthemProtocol.decode(serial)

  def datagram_received(self, data, addr):
    packet = None
    try:
      packet = AnthemDiscoveryPacket.receive(data, addr)
    except:
      return
    host, port = addr
    if packet.discover:
      if packet.proxy and not self.forward:
        logging.debug('Ignoring proxy discovery packet')
        return
      return self.on_discovery_request(host, port)
    else:
      return self.on_discovery_reply(host, port, packet.device.version, packet.device.name, packet.device.model, packet.device.serial)

  def client_request(self, data):
    if not self.device.host or not self.device.port:
      logging.debug("Can't reply without proxy")
      return

    self.connection.write(data)

  def proxy_response(self, data):
    for client in self.clients:
      client.write(data)
