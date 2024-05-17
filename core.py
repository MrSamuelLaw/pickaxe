from __future__ import print_function
import copy
from inspect import isclass
from fwave.jydantic.types import Any


"""
Author: Samuel Law
Description: Module that contains the core functionality for jydantic
"""

# --------------- LOGGER ---------------
JYDANTIC_LOGGER = system.util.getLogger('jydantic')


# --------------- EXCEPTIONS ---------------

class ValidationError(Exception):
	"""Error type returned when validation fails.
	Primarly used when other error types are not descriptive
	enough or when grouping multiple child errors.
	"""
	def __init__(self, msg, errors=[]):
		Exception.__init__(self, msg)
		self.msg = msg
		self.errors = errors
	
	def __str__(self):
		strings = [self.msg]
		for e in self.errors:
			if isinstance(e, Exception):
				strings.append('{}: {}'.format(type(e).__name__, e))
			else:
				strings.append(str(e))
		return '\n'.join(strings)


class ModelInitError(Exception):
	"""Error type returned when a model cannot be created
	"""
	def __init__(self, msg, errors=[]):
		Exception.__init__(self, msg)
		self.msg = msg
		self.errors = errors
		
	def __str__(self):
		strings = [self.msg]
		for e in self.errors:
			if isinstance(e, Exception):
				strings.append('{}: {}'.format(type(e).__name__, e))
			else:
				strings.append(str(e))
		return '\n'.join(strings)


class FrozenError(Exception):
	"""Error type returned when trying to modify 
	a frozen field.
	"""
	pass


# --------------- DECORATORS ---------------

class classProperty(property):
	"""Utility read only property class"""
	
	def __get__(self, ownerInstance, ownerType):
		if ownerInstance is None:
			return self.fget(ownerType)
		else:
			return self.fget(ownerInstance)


def fieldValidator(*names):
	"""This method marks a function as a validator
	to be applied when the class is instantiated.
	
	Args:
		*names: Field names for which the validator applies
		
	Example:
		
		class ConcreteModel(BaseModel):
		
			pk = Field(int)
			
			@fieldValidator('pk')
			@classmethod
			def pkNotEqualToZero(cls, value):
				if value == 0:
					raise ValueError('pk cannot equal zero')
					
		c = ConcreteModel(pk=1)
		c.pk = 0
		
		>>> Validation failed with the following errors:
		['error setting field pk to 0 with the following error: pk cannot equal zero']
	"""
	def wrapper(classMethod):
		def wrapped(clsOrInstance, *args, **kwargs):
			params = (None, clsOrInstance) if isclass(clsOrInstance) else (clsOrInstance, )
			return classMethod.__get__(*params)(*args, **kwargs)
		wrapped.__field_names__ = names
		newClassMethod = classmethod(wrapped)
		return newClassMethod
	return wrapper

	
def computedField(frozen=False, exclude=False, alias=None):
	"""This method marks a function wrapped with a property
	as a field of the object so validation and freezing can
	occure.
	
	Args:
		frozen: bool, used to dynamically prevent editing the field
		exclude: bool, used to prevent the field from being output during serialization
		alias: str | None, used to change the name when serializing
	
	Example:
		class Foo(BaseModel):
			... your code here
		
			@computedField(alias='Bar')
			@property
			def bar(self):
				return self._bar
			...
	"""
	def wrapper(propertyMethod):
		try:
			fget = propertyMethod.fget
			fget.__computed_field__ = True
			fget.__frozen__ = frozen
			fget.__exclude__ = exclude
			fget.__alias__ = alias
			return propertyMethod
		except AttributeError as e:
			raise AttributeError('computedField must wrap a function decorated with a property.')
	return wrapper


def modelValidator(instanceMethod):
	"""This method marks a function as a model validator
.
	Model validators validate an instance of a model, rather
	than the field definitions.
	
	Args:
		instanceMethod: Callable(self), method to call when validating
	
	Example:
		class Foo(BaseModel):
			
			pk = Field(int, allowNone=True)
			parentPk = Field(int, allowNone=True)
		
			... your code here
			
			@modelValidator
			def requirePkIfParentPkExists(self):
				if (self.parentPk is not None) and (self.pk is not None):
					raise ValidationError("pk cannot be None if parentPk is not None")
			...
	"""
	instanceMethod.__model_validator__ = True
	return instanceMethod
	
	
# --------------- UTILITY FUNCTIONS ---------------

def configDict(**kwargs):
	"""Returns a default dictionary with any fields overwritten by **kwargs.
	
	Note that configDict supports a user first mentality in that you can provide
	your own items for use in custom classes. In otherwords, users are not locked in
	to the library authors choices.
	"""
	
	defaults = {
		'strict': False,				  # if true, types must match exactly rather than being coerced
		'validateAssignment': True,  	  # if true, _validateModels the fields on assignment
		'extraFields': 'FORBID',		  # options are ALLOW, IGNORE, & FORBID, defaults to IGNORE
 
	}
	defaults.update(kwargs)
	return defaults


# --------------- CLASSES ---------------

class Field(object):
	"""Object that defines a field on a base model.
	Args:
		typeObj, field type, for example int, can also be a class
		defaultValue=None, value the field will default to if not provided
		allowNone=False, if true allows the field to be None, i.e. makes a field optional
		frozen=False, frozen, freezes the field from changes
		alias=None, name that the field will have when the model is dumped
		exclude=False, if true excludes the field when the model is dumped
		strict=False, if true prevents type coercion
	
	Example:
		class Foo(BaseModel):
			... your code here
			name = Field(str)
			alias = Field(str, allowNone=True)
			...
			
		foo1 = Foo(name='bar')
		foo2 = Foo(name='bar', alias='baz')
	"""
	
	def __init__(self, 
				 typeObj, 			 # field type, for example int, can also be a class
				 defaultValue=None,  # value the field will default to if not provided
				 allowNone=False,    # if true allows the field to be None, i.e. makes a field optional
				 frozen=False, 		 # frozen, freezes the field from changes
				 alias=None, 		 # name that the field will have when the model is dumped
				 exclude=False, 	 # if true excludes the field when the model is dumped
				 strict=False		 # if true prevents type coercion
				 ):
		self.typeObj = typeObj
		self.defaultValue = defaultValue
		self.allowNone = allowNone
		self.frozen = frozen
		self.alias = alias
		self.exclude = exclude
		self.strict = strict


class ComputedField(object):
	"""Object that defines a computed field on a base model.
	Args:
		frozen=False, frozen, freezes the field from changes
		alias=None, name that the field will have when the model is dumped
		exclude=False, if true excludes the field when the model is dumped
	
	Example:
		class Foo(BaseModel):
			... your code here
			name = Field(str)
			
			@computedField(alias='long_name')
			@property
			def longName(self):
				return self.name + '_ofClassFoo'
			...
			
		foo = Foo(name='bar')
		foo.longName
		>>>
			bar_ofClassFoo
	"""
	
	def __init__(self, frozen=False, exclude=False, alias=None):
		self.frozen = frozen
		self.alias = alias
		self.exclude = exclude


class BaseModelMetaclass(type):
	"""This class implemnts the magic that users experience when using BaseModel"""


	def __init__(cls, *args, **kwargs):
		"""This performs additional setup when the class is defined."""
		# loop over all the class level items
		
		# make sure each class gets a independent copy of the containers to prevent weird bugs
		cls._config_dict_ = copy.deepcopy(cls._config_dict_)
		cls.__fields__ = copy.deepcopy(cls.__fields__)
		cls.__computed_fields__ = copy.deepcopy(cls.__computed_fields__)
		cls.__field_validators__ = copy.deepcopy(cls.__field_validators__)
		cls.__model_validators__ = copy.deepcopy(cls.__model_validators__)
		exceptions = []
		
		# ingest the fields
		fieldTuples = []
		for key, obj in cls.__dict__.items():
			if isinstance(obj, Field):
				field = copy.deepcopy(obj)
				fieldTuples.append((key, field))
				cls.__fields__[key] = field
			elif isinstance(obj, property) and hasattr(obj.fget, '__computed_field__'):
				key = str(obj.fget.__name__)
				frozen = obj.fget.__frozen__
				exclude = obj.fget.__exclude__
				alias = obj.fget.__alias__
				cls.__computed_fields__[key] = ComputedField(frozen, exclude, alias)
			elif obj == Field:
				error = ValueError('Fields must be instantiated, for example x = Field(int) not x = Field')
				exceptions.append(error)
		
		# define the class validators
		for key, obj in cls.__dict__.items():
			# if the function has been marked with the attribute __field_names__
			# move it into the classes __field_validators__ attributes
			# note, __field_validators__ is a dict where each value is a 
			# set object. The reason for having sets instead of a list
			# is sets prevent duplicates.
			if type(obj) == classmethod and  hasattr(obj.__func__, '__field_names__'):
				for name in obj.__func__.__field_names__:
					if name in cls.__field_validators__.keys():
						cls.__field_validators__[name].add(obj)
					else:
						cls.__field_validators__[name] = {obj}
			elif hasattr(obj, '__model_validator__'):
				cls.__model_validators__.add(obj)
		
		if exceptions:
			raise ModelInitError('Failed to initialize model with the following exceptions:', exceptions)


class BaseModel(object):
	"""Base class that user Models should inherit from.
	
	Example1:
		class Model(BaseModel):
			
			id = Field(int)
			serial = Field(str)
			
			@fieldValidator('id')
			@classmethod
			def greaterThanZero(cls, value):
				if value < 1:
					raise ValueError('id must be greater than zero')
			
			@fieldValidator('serial')
			@classmethod
			def validateSerial(cls, value):
				match = re.match('\d{5}', value)
				if (not match) or (match.string != value):
					raise ValueError('serial format is incorrect')
		
		
		model = Model(id=5, serial='12345') 
		model.id
		
		try:
			model = Model(id=0, serial='12345')
		except Exception as e:
			print(e)
		
		try:
			model = Model(id=1, serial='a1234')
		except Exception as e:
			print(e)
				
		>>> 
		5
		Validation failed with the following errors:
		['error setting field id to 0 with the following error: id must be greater than zero']
		Validation failed with the following errors:
		['error setting field serial to a1234 with the following error: serial format is incorrect']
	"""
	
	__metaclass__ = BaseModelMetaclass
	__fields__ = {}
				  # fields that the model has
	__computed_fields__ = {}
	  # computed fields that the model has
	__field_validators__ = {}
	  # validators for fields (works with computed as well)
	__model_validators__ = set()
  # validators for the model
	_config_dict_ = configDict()
  # config for the model
	
	def __init__(self, **data):
		"""This performs additional setup when an instance of a class is created"""
		if type(self) == BaseModel:
			raise NotImplementedError('Cannot instantiate BaseModel directly.')
		self._setWithoutSideEffects('__validate_data__', True)
		self._modelConstruct(**data)
		
	@classmethod
	def modelConstruct(cls, **data):
		"""Creates a new model without validation"""
		# clone the class fields into the instance so it has an independent copy
		self = object.__new__(cls)
		self._setWithoutSideEffects('__validate_data__', False)
		self._modelConstruct(**data)
		return self
		
	def _setWithoutSideEffects(self, name, value):
		"""Sets a model attribute without causing validation"""
		object.__setattr__(self, name, value)
		
	def _modelConstruct(self, **data):
		# needed for processing
		self._setWithoutSideEffects('__jydantic_complete__', False)
		
		# setup the fields
		self._setWithoutSideEffects('__fields__', copy.deepcopy(self.__fields__))
		for key, obj in type(self).__dict__.items():
			if isinstance(obj, Field):
				field = copy.deepcopy(obj)
				self.__fields__[key] = field
				setattr(self, key, data.get(key, field.defaultValue))
		
		# read in any extra fields
		extraFields = self._config_dict_['extraFields']
		diff = {key for key in data.keys() if key not in set(self.__fields__.keys())}
		if diff:
			if extraFields == 'FORBID':
				msg = 'cannot create defaults field for {}, extra fields forbidden'.format(diff)
				raise ValidationError(msg)
			elif extraFields == 'IGNORE':
				pass
			elif extraFields == 'ALLOW':
				for key in diff:
					field = Field(Any, allowNone=True)
					self.__fields__[key] = field
					setattr(self, key, data.get(key, field.defaultValue))
			else:
				raise ValueError('extraFields is not "FORBID" | "IGNORE" | "ALLOW"')
				
		self._setWithoutSideEffects('__jydantic_complete__', True)
				
		if self.__validate_data__:
			self._validateModel()
			
		self._setWithoutSideEffects('__validate_data__', self._config_dict_['validateAssignment'])
		
	def _setNonFieldValue(self, name, value):
		"""Handler for setting non field values
		Args:
			name: str, name of property to set
			value: any, value to set the property to
		"""
		extraFields = self._config_dict_['extraFields']
		if hasattr(self, name):
			self._setWithoutSideEffects(name, value)
		elif extraFields == 'FORBID':
			raise ValidationError('Cannot set new field when extraFields is False')
		elif extraFields == 'IGNORE':
			raise AttributeError('{} has no field {}'.format(type(self).__name__, name))
		elif extraFields == 'ALLOW':
			if isinstance(value, (Field, ComputedField)):
				value = value.value
			else:
				field = Field(Any)
				self.__fields__[name] = field
				self._setWithoutSideEffects(name, value)
		else:
			msg = "_config_dict_['extraFields'] must be literal 'FORBID' | 'ALLOW' | 'IGNORE' not {}"
			msg = msg.format(extraFields)
			raise ValueError(msg)
			
	def _validateFieldValue(self, name, field, value):
		# handle field
		if isinstance(field, Field):
			# handle None values
			if value is None:
				if not field.allowNone:
					raise ValueError('cannot set field {} to None'.format(name))
				# we use this as an excape hatch to break out of the upper if statement
				else:
					pass
			# handle strict modes
			elif ((self._config_dict_['strict'] or field.strict) 
					and (type(field.typeObj) != Any) and (type(value) != field.typeObj)):
				msg = 'Value {} of type {} does not match field type {}'
				msg = msg.format(value, type(value), field.typeObj)
				raise TypeError(msg)
			# try to coerce the type of the value
			else:
				if not isinstance(value, (field.typeObj, Any)):
					try:
						value = field.typeObj(value)
					except:
						msg = 'Could not cast {} to type {}'
						msg = msg.format(value, field.typeObj)
						raise TypeError(msg)
						
		# run the user defined validators
		if self.__validate_data__:
			for func in self.__field_validators__.get(name, set()):
				func.__get__(self)(value)
				
		# if no errors raised, return the value
		return value
			
	def _setFieldValue(self, name, field, value):
		# check if frozen
		if bool(field.frozen) and self.__jydantic_complete__:
			raise FrozenError('cannot set field {}, it is frozen'.format(field.alias))
		
		# raises error if not valid
		if self.__validate_data__:
			value = self._validateFieldValue(name, field, value)
			
		self._setWithoutSideEffects(name, value)
		
	def __setattr__(self, name, value):
		# handle non-field values
		field = self.__fields__.get(name, self.__computed_fields__.get(name))
		if field is None:
			self._setNonFieldValue(name, value)
		
		# run checks on Field & ComputedField
		if isinstance(field, (Field, ComputedField)):
			self._setFieldValue(name, field, value)
				
		# _validateModel the model
		if self.__jydantic_complete__ and self.__validate_data__:
			self._validateModel()
				
	def _validateModel(self):
		"""_validateModels the model"""
		for mv in self.__model_validators__:
			try:
				mv(self)
			except RuntimeError as e:
				if 'recursion' in e.message.lower():
					msg = '{}, make sure not to set model values inside of a modelValidator'
					msg = msg.format(e.message.splitlines()[-1])
					raise ValidationError(msg)
				else:
					raise e
	
	@classProperty
	def modelFields(instanceOrCls):
		"""Returns a copy of the fields for this class/instance""" 
		return copy.copy(instanceOrCls.__fields__)
		
	@classProperty
	def modelComputedFields(instanceOrCls):
		"""Returns a copy of the computed fields for this class"""
		return copy.copy(instanceOrCls.__computed_fields__)
	
	def modelDump(self):
		"""Converts the model to a dictionary recurrsively"""
		dump = {}
		# collect the model fields
		for key, field in self.__fields__.items():
			if not field.exclude:
				alias = key if field.alias is None else field.alias
				value = getattr(self, key)
				if isinstance(value, BaseModel):
					dump[alias] =  value.model_dump()
				else:
					dump[alias] = value
		# collect the computed fields
		for key, computed_field in self.__computed_fields__.items():
			if not computed_field.exclude:
				alias = key if computed_field.alias is None else computed_field.alias
				dump[alias] = getattr(self, key)
		return dump
		