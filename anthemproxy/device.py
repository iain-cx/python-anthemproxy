from anthemproxy.protocol import AnthemProtocol
import json

# An Anthem device.
class AnthemDevice(object):
  def __init__(self, *, host = None, port = None, proxy = None, alias = None, name = None, model = None, serial = None, version = None):
    self.alias = AnthemProtocol.decode(alias)
    self.name = AnthemProtocol.decode(name)
    self.host = host
    self.port = port or AnthemProtocol.PORT
    self.version = version or AnthemProtocol.VERSION
    self.serial = AnthemProtocol.decode(serial)
    if proxy is not None:
      self.proxy = proxy
      self.model = AnthemProtocol.MODEL if proxy else AnthemProtocol.decode(model)
    else:
      self.model = AnthemProtocol.decode(model)
      self.proxy = AnthemProtocol.check_model(self.model)

  @property
  def json(self):
    return json.dumps({
      'alias': self.alias if self.alias is not None else '',
      'host': self.host,
      'port': self.port,
      'name': self.name,
      'model': self.model,
      'serial': self.serial
    })

  @classmethod
  def from_json(self, s):
    try:
      data = json.loads(s)
      name = data.get('name')
      alias = data.get('alias') or name
      return AnthemDevice(host = data.get('host'), port = data.get('port'), alias = alias, name = name, model = data.get('model'), serial = data.get('serial'))
    except json.decoder.JSONDecodeError:
      raise Exception('Invalid JSON representation of AnthemDevice')

  @property
  def valid(self):
    return bool(self.host) and bool(self.port)

  @property
  def usable(self):
    try:
      return self.valid and len(self.name) and len(self.model) and len(self.serial)
    except TypeError:
      return False
