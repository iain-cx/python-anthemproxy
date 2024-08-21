from anthemproxy.device import AnthemDevice
from anthemproxy.packet import AnthemDiscoveryPacket
from anthemproxy.protocol import AnthemProtocol
import asyncio
import logging

# A discovery client.
class AnthemDiscovery(asyncio.Protocol):
  CONTINUE = True
  STOP = False

  def __init__(self, *, host = None, port = None, broadcast = None, on_receive = None, forward = None):
    self.host = host or AnthemProtocol.LISTEN
    self.port = port or AnthemProtocol.PORT
    self.broadcast = broadcast or AnthemProtocol.BROADCAST
    self.packet = AnthemDiscoveryPacket(discover = True)
    self.on_receive = on_receive if on_receive is not None else lambda packet: False
    self.transport = None
    self.protocol = None
    self.listen = True
    self.forward = forward or False
    self.server = None

  async def run(self):
    loop = asyncio.get_running_loop()
    self.transport, self.protocol = await loop.create_datagram_endpoint(lambda: self, local_addr = (self.host, self.port), reuse_port = True, allow_broadcast = True)

    logging.debug('Sending discovery packets to %s:%u.', self.broadcast, AnthemProtocol.PORT)
    logging.debug('Listening for responses to %s:%u.', self.host, self.port)
    try:
      while self.listen:
        self.transport.sendto(self.packet.buffer, (self.broadcast, AnthemProtocol.PORT))
        await asyncio.sleep(0.5)
    except Exception as e:
      logging.error('Creating UDP endpoint: %s', e)
      raise e
    finally:
      self.transport.close()

  def datagram_received(self, data, addr):
    packet = None
    try:
      packet = AnthemDiscoveryPacket.receive(data, addr)
    except:
      raise
      return

    if not packet:
      return
    if packet.discover:
      return
    if not packet.device:
      return
    if self.on_receive(packet) == self.STOP:
      self.listen = False

async def discover(bind, port, broadcast, forward = False):
  seen = {}

  def show_device(packet):
    output = packet.json
    if not seen.get(output):
      print(output)
    seen[output] = True
    return AnthemDiscovery.CONTINUE

  discovery = AnthemDiscovery(host = bind, port = port, broadcast = broadcast, on_receive = show_device, forward = forward)
  return await discovery.run()

async def proxy(bind, listen, host, port, alias, name, model, serial, forward = False):
  def query_device(packet):
    if packet.discover:
      return AnthemDiscovery.CONTINUE
    serialised.value = packet.device.json
    return AnthemDiscovery.STOP

  target_host = multiprocessing.Value(ctypes.c_wchar_p, '')
  target_port = multiprocessing.Value('i', 0)

  target = AnthemDevice(host = host, port = port, alias = alias, name = name, model = model, serial = serial)
  announced = False
  while not target.name or not target.usable:
    if target.valid:
      target_host.value = target.host
      target_port.value = target.port
    serialised = multiprocessing.Value(ctypes.c_wchar_p, '')
    if not announced:
      logging.info('Discovering target device details.')
      announced = True
    discovery = AnthemDiscovery(host = bind, port = listen, broadcast = host, on_receive = query_device, forward = forward)
    await discovery.run()

    canon = AnthemDevice.from_json(serialised.value)
    if not target.host or target.host != canon.host:
      target.host = canon.host
      target.port = canon.port
      logging.debug('Discovered host: %s', target.host)
    if not target.name:
      target.name = canon.name
      logging.debug('Discovered name: %s', target.name)
    if not target.model:
      target.model = canon.model
      logging.debug('Discovered model: %s', target.model)
    if not target.serial:
      target.serial = canon.serial
      logging.debug('Discovered serial: %s', target.serial)

  logging.info('Proxying: %s', target.json)
  proxy = AnthemProxy(target, bind, listen, forward = forward)
  return await proxy.run()
