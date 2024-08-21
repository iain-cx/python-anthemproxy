from anthemproxy.protocol import AnthemProtocol
import asyncio
import logging

# Connection from the proxy to the target.
class AnthemProxyConnection(asyncio.Protocol):
  def __init__(self, proxy = None):
    self.proxy = proxy
    if self.proxy is None:
      raise Exception('AnthemProxyConnection needs an AnthemProxy!')
    self.transport = None
    self.protocol = None
    self.connected = False
    self.reconnect()

  async def connect(self, data = None):
    if not self.transport or self.transport.is_closing():
      logging.info('Connecting to proxied device: %s', self.proxy.device.name)
      try:
        self.transport, self.protocol = await self.proxy.loop.create_connection(lambda: self, self.proxy.device.host, self.proxy.device.port)
        if not self.transport.is_closing():
          self.connected = True
          if data is not None:
            self.write(data)
      except Exception as e:
        logging.error('Connecting to proxied device: %s', e)
        self.close()

  def reconnect(self, data = None):
    asyncio.ensure_future(self.connect(data))

  def close(self):
    if self.transport and not self.transport.is_closing():
      self.transport.close()
    self.transport = None
    self.connected = False

  def write(self, data):
    if self.connected:
      try:
        logging.debug('Writing to device %s: %s', self.proxy.device.name, AnthemProtocol.decode(data))
        self.transport.write(data)
        return
      except Exception as e:
        logging.error('Writing to device %s: %s', self.proxy.device.name, e)
    self.reconnect(data)

  def connection_made(self, transport):
    host, port = transport.get_extra_info('peername')
    logging.debug('Connected to proxied device %s at %s:%u', self.proxy.device.name, host, port)

  def connection_lost(self, e):
    if e is not None:
      logging.debug('Disconnected from proxied device %s: %s', self.proxy.device.name, e)
    else:
      logging.debug('Disconnected from proxied device %s.', self.proxy.device.name)
    self.transport = None
    self.protocol = None
    self.connected = False
    if self.proxy.listen:
      self.reconnect()

  def data_received(self, data):
    message = AnthemProtocol.decode(data)
    if AnthemProtocol.empty(message):
      logging.debug('Empty message from device.')
    else:
      logging.debug('Message from device: %s', message)
      self.proxy.proxy_response(data)
