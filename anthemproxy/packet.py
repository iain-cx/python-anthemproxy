from anthemproxy.device import AnthemDevice
from anthemproxy.protocol import AnthemProtocol
import json
import logging
import struct

# A discovery or response packet.
class AnthemDiscoveryPacket(object):
  MAGIC = 'PARC'
  FORMAT = '!4s2xbbLL16s16s16s'

  def __init__(self, *, discover = False, shutting_down = False, port = None, device = None):
    if device is None:
      device = AnthemDevice(proxy = True, port = port)
    elif type(device) is not AnthemDevice:
      raise Exception('AnthemDiscoveryPacket device parameter must be None or instance of AnthemDevice')

    self.discover = discover
    self.shutting_down = shutting_down
    self.device = device
    self.proxy = device.proxy if device is not None else False
    self.buffer = struct.pack(self.FORMAT, self.MAGIC.encode('utf-8'), 1 if self.discover else 0, 1 if self.shutting_down else 0, self.device.version, self.device.port, AnthemProtocol.encode(self.device.alias), AnthemProtocol.encode(self.device.model), AnthemProtocol.encode(self.device.serial))

  @classmethod
  def check_magic(self, magic):
    canon = magic.decode() if type(magic) is bytes else magic
    return canon == self.MAGIC

  @classmethod
  def receive(self, buffer, addr):
    host = None
    discover = None
    packet_type = 'Discovery'
    try:
      magic, discover, shutting_down, version, port, name, model, serial = struct.unpack(self.FORMAT, buffer)
      discover = bool(discover)
      if not discover:
        packet_type = 'Response'
      if addr is not None:
        host, port = addr
        logging.debug('%s packet received from %s:%u.', packet_type, host, port)
      else:
        logging.debug('%s packet received.', packet_type)
    except Exception as e:
      logging.error('Receiving discovery packet from %s:%u: %s', host, port, e)
      raise Exception('AnthemDiscoveryPacket.receive requires a valid packed buffer')

    if not AnthemDiscoveryPacket.check_magic(magic):
      logging.debug('Bad magic in discovery packet.')
      raise Exception('AnthemDiscoveryPacket.receive got bad magic')

    shutting_down = bool(shutting_down)
    device = AnthemDevice(host = host, port = port, name = name, model = model, serial = serial)
    if not discover and not device.usable:
      logging.error('Bad device in %s packet from %s:%u: %s', packet_type.lower(), host, port, buffer)
      raise Exception('AnthemDiscoveryPacket with invalid device')

    return AnthemDiscoveryPacket(discover = discover, shutting_down = shutting_down if not discover else False, port = port, device = device)

  def send(self, transport, addr):
    try:
      transport.sendto(self.buffer, addr)
    except Exception as e:
      logging.error('Sending %s: %s', self.buffer, e)

  @property
  def json(self):
    if self.device is None:
      return ''
    return json.dumps({
      'host': self.device.host,
      'port': self.device.port,
      'name': self.device.name,
      'model': self.device.model,
      'serial': self.device.serial
    })
