from anthemproxy.protocol import AnthemProtocol
import asyncio
import logging

# Connection from a client to the proxy.
class AnthemProxyClient(asyncio.Protocol):
  def __init__(self, proxy):
    self.proxy = proxy
    if self.proxy is None:
      raise Exception('AnthemProxyClient needs an AnthemProxy!')
    self.transport = None
    self.host = None
    self.port = None
    self.connected = True

  def connection_made(self, transport):
    self.transport = transport
    try:
      self.host, self.port = transport.get_extra_info('peername')
      logging.debug('New connection from %s:%u', self.host, self.port)
      self.proxy.client_connected(self)
    except:
      self.connected = False
      logging.error('Failed to accept new connection!')

  def connection_lost(self, e):
    self.connected = False
    if e is not None:
      logging.debug('Client %s:%u disconnected: %s', self.host, self.port, e)
    else:
      logging.debug('Client %s:%u disconnected.', self.host, self.port)
    self.proxy.client_disconnected(self)

  def data_received(self, data):
    message = AnthemProtocol.decode(data)
    if AnthemProtocol.empty(message):
      logging.debug('Empty request from client %s:%u.', self.host, self.port)
    else:
      logging.debug('Request from client %s:%u: %s', self.host, self.port, AnthemProtocol.decode(data))
      self.proxy.client_request(data)

  def write(self, data):
    if self.connected:
      logging.debug('Writing to client %s:%u: %s', self.host, self.port, AnthemProtocol.decode(data))
      self.transport.write(data)
