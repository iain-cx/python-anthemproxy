# Helper class to filter protocol messages.
class AnthemProtocol(object):
  LISTEN = '0.0.0.0'
  BROADCAST = '255.255.255.255'
  PORT = 14999
  VERSION = 1
  MODEL = 'Anthem Proxy'

  EMPTY = str.maketrans({ ' ': '', ';': '' })

  @classmethod
  def decode(self, b):
    if b is None:
      return None
    if not b:
      return ''
    if type(b) is str:
      return b.rstrip()
    return b.decode('utf-8').rstrip('\0').rstrip()

  @classmethod
  def encode(self, s):
    if type(s) is str and s:
      return s.encode('utf-8')
    return b''

  @classmethod
  def check_model(self, model):
    canon = AnthemProtocol.decode(model)
    return canon == self.MODEL

  @classmethod
  def empty(self, data):
    return not data.translate(AnthemProtocol.EMPTY)
