from __future__ import print_function
from inspect import isclass



def forTypes(*types, **kwargs):
	"""Decorator that can type check a class method on an Adaptor.
	Args:
		*types
	"""
	strict = kwargs.get('strict', True)
	def decorator(classMethod):
		def wrapper(clsOrInstance, *args, **kwargs):
			model = args[0]
			if strict and (type(model) not in types):
				msg = 'model of type {} not on of the allowed types {}'
				msg = msg.format(type(model), types)
				raise TypeError(msg)
			elif (not strict) and (not isinstance(model, types)):
				msg = 'model of type {} not an type or subtype of the allowed types {}'
				msg = msg.format(type(model), types)
				raise TypeError(msg)
			params = (None, clsOrInstance) if isclass(clsOrInstance) else (clsOrInstance, )
			return classMethod.__get__(*params)(*args, **kwargs)
		newClassMethod = classmethod(wrapper)
		return newClassMethod
	return decorator
	
	
class BasePlcAdapter(object):

	@classmethod
	def read(cls, root, readMethod=system.tag.readBlocking):
		raise NotImplementedError('read method not implemented for type {}'.format(cls))
	
	@classmethod
	def update(cls, model, root, writeMethod=system.tag.writeBlocking):
		raise NotImplementedError('update method not implemented for type {}'.format(cls))
	
	
class BaseDbAdapter(object):

	@classmethod
	def create(cls, model, database=None, tx=None):
		raise NotImplementedError('create method not implemented for type {}'.format(cls))

	@classmethod
	def read(cls, pk, database=None, tx=None):
		raise NotImplementedError('read method not implemented for type {}'.format(cls))
		
	@classmethod
	def update(cls, model, database=None, tx=None):
		raise NotImplementedError('update method not implemented for type {}'.format(cls))
		
	@classmethod
	def delete(cls, model, database=None, tx=None):
		raise NotImplementedError('delete method not implemented for type {}'.format(cls))