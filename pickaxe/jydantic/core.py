from __future__ import print_function
import copy
import functools
from inspect import isclass
from pickaxe.jydantic.types import (Any, 
									TypeCheckerRegistry,
									TypeConverterRegistry)


# --------------- LOGGER ---------------
LOGGER = system.util.getLogger('jydantic')


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
		# note, we have to wrap it as classmethod does not support
		# dynamic attibute assignment, such as field names
		@functools.wraps(classMethod.__func__)
		def fieldValidator(clsOrInstance, *args, **kwargs):
			params = (None, clsOrInstance) if isclass(clsOrInstance) else (clsOrInstance, )
			return classMethod.__get__(*params)(*args, **kwargs)
		fieldValidator.__field_names__ = names
		newClassMethod = classmethod(fieldValidator)
		return newClassMethod
	return wrapper

	
def computedField(frozen=False, exclude=False, serializationAlias=None):
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
			fget.__serializationAlias__ = serializationAlias
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
 
		'frozen': False,				  # option to freeze the model
	}
	defaults.update(kwargs)
	return defaults


# --------------- CLASSES ---------------

class Field(object):
	"""Object that defines a field on a base model.
	Args:
		type_: <T>, field type, for example int, can also be a class
		typeConverter=None, callable that takes a value and returns a converted value
		defaultValue=None, value the field will default to if not provided
		allowNone=False, if true allows the field to be None, i.e. makes a field optional
		frozen=False, frozen, freezes the field from changes
		readonly=False, causes the frozen bit to be set automatically once the field is set to a non-null value
		alias=None, name that the field is created from when parsing datadata and when the model is dumped
		validationAlias=None, name the field will be created from when parsing data
		serializationAlias=None, name the field will have when dumping the model
		exclude=False, if true excludes the field when the model is dumped
		strict=False, if true prevents type coercion
	Example:
		class Foo(BaseModel):
			... your code here
			name = Field(str)
			type = Field(str, allowNone=True, alias='_type')
			...
			
		foo1 = Foo(name='bar')
		foo2 = Foo(name='bar', _type='baz')  # used alias for _type
	"""
	
	def __init__(self, 
				 type_, 			 		# field type, for example int, can also be a class
				 typeConverter=None,		# converter that attempts to convert incoming data to the field type
				 defaultValue=None,  		# value the field will default to if not provided
				 allowNone=False,    		# if true allows the field to be None, i.e. makes a field optional
				 frozen=False, 		 		# frozen, freezes the field from changes
				 readonly=False,			# like frozen, but locks in the first non-null value
				 alias=None, 		 		# name that the field is created from when parsing datadata and when the model is dumped
				 validationAlias=None,  	# name the field will be created from when parsing data
				 serializationAlias=None, 	# name the field will have when dumping the model
				 exclude=False, 	 		# if true excludes the field when the model is dumped
				 strict=False		 		# if true prevents type coercion
				 ):
		self.type = type_
		self.typeConverter = typeConverter
		self.defaultValue = defaultValue
		self.allowNone = allowNone
		self.frozen = frozen
		self.readonly = readonly
		self.exclude = exclude
		self.strict = strict
		self.validationAlias = alias or validationAlias
		self.serializationAlias = alias or serializationAlias
		
		
class ComputedField(object):
	"""Object that defines a computed field on a base model.
	Args:
		frozen=False, frozen, freezes the field from changes
		serializationAlias=None, name the field will have when dumping the model
		exclude=False, if true excludes the field when the model is dumped
		
	Example:
		class Foo(BaseModel):
			... your code here
			name = Field(str)
			
			@computedField(serializationAlias='long_name')
			@property
			def longName(self):
				return self.name + '_ofClassFoo'
			...
			
		foo = Foo(name='bar')
		foo.longName
		>>>
			bar_ofClassFoo
	"""
	
	def __init__(self, frozen=False, exclude=False, serializationAlias=None):
		self.frozen = frozen
		self.serializationAlias = serializationAlias
		self.exclude = exclude


class BaseModelMeta(type):
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
				serializationAlias = obj.fget.__serializationAlias__
				cls.__computed_fields__[key] = ComputedField(frozen, exclude, serializationAlias)
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
						cls.__field_validators__[name].add(obj.__func__.__name__)
					else:
						cls.__field_validators__[name] = {obj.__func__.__name__}
			elif hasattr(obj, '__model_validator__'):
				cls.__model_validators__.add(obj.__name__)
		
		if exceptions:
			raise ModelInitError('Failed to initialize model with the following exceptions:', exceptions)
			
			
# define the type checking & converting
@TypeCheckerRegistry.registerForType(BaseModelMeta)
def baseModelValueTypeChecker(registry, model, value, strict):
	if not strict:
		return isinstance(value, model)
	else:
		return type(value) == model

@TypeConverterRegistry.registerForType(BaseModelMeta)
def baseModelValueTypeConverter(registry, model, value):
	if isinstance(value, dict):
		return model(**value)
	elif isinstance(type(value), BaseModelMeta):
		return model(**value.modelDump())
	else:
		msg = 'Cannot convert value = {} of type {} to type {}'
		msg = msg.format(value, type(value), model)
		raise TypeError(msg)		


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
	
	__metaclass__ = BaseModelMeta
	__fields__ = {}
				  # fields that the model has
	__computed_fields__ = {}
	  # computed fields that the model has
	__field_validators__ = {}
	  # validators names for fields (works with computed as well)
	__model_validators__ = set()  # validators names for the model
	_config_dict_ = configDict()
  # config for the model
	
	def __init__(self, **data):
		"""Creates an instance of a model class with validation.
		"""
		if type(self) == BaseModel:
			raise NotImplementedError('Cannot instantiate BaseModel directly.')
		super(BaseModel, self).__init__(**data)
		self._setWithoutSideEffects('__validate_data__', True)
		self._modelConstruct(**data)
		
	@classmethod
	def modelConstruct(cls, **data):
		"""Creates a new model without validation.
		"""
		# clone the class fields into the instance so it has an independent copy
		self = object.__new__(cls)
		self._setWithoutSideEffects('__validate_data__', False)
		self._modelConstruct(**data)
		return self
	
	def _setWithoutSideEffects(self, name, value):
		"""Sets a model attribute without causing validation.
		"""
		object.__setattr__(self, name, value)
	
	def _modelConstruct(self, **data):
		# needed for processing
		self._setWithoutSideEffects('__jydantic_complete__', False)
		
		# setup the fields
		self._setWithoutSideEffects('__fields__', copy.deepcopy(self.__fields__))
		self._setWithoutSideEffects('_config_dict_', copy.deepcopy(self._config_dict_))
		fields = dict(self.__fields__)
		fields.update({key: obj for key, obj in type(self).__dict__.items() if isinstance(obj, Field)})
		for key, obj in fields.items():
			field = copy.deepcopy(obj)
			self.__fields__[key] = field
			value = data.get(field.validationAlias or key, field.defaultValue)
			setattr(self, key, value)
		
		# read in any extra fields
		extraFields = self._config_dict_['extraFields']
		expectedKeys = {f.validationAlias or k for k, f in self.__fields__.items()}
		diff = {key for key in data.keys() if key not in expectedKeys}
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
			field = Field(Any, allowNone=True)
			self.__fields__[name] = field
			self._setWithoutSideEffects(name, value)
		else:
			msg = "_config_dict_['extraFields'] must be literal 'FORBID' | 'ALLOW' | 'IGNORE' not {}"
			msg = msg.format(extraFields)
			raise ValueError(msg)
			
	def _ensureFieldValue(self, name, field, value):
		if self.__validate_data__:
			if isinstance(field, Field):
				if value is None:
					if not field.allowNone:
						raise ValueError('cannot set field {} to None'.format(name))
				elif field.type is not Any:
					strict = self._config_dict_['strict'] or field.strict
					checker = TypeCheckerRegistry.getTypeChecker(field.type)
					if not checker(value, strict):
						if not strict:
							converter = field.typeConverter or TypeConverterRegistry.getTypeConverter(field.type)
							value = converter(value)
							if not checker(value, strict):
								msg = 'Could not convert data type for value = {} of type {} for field {} of type {}'
								msg = msg.format(value, type(value), name, field.type)
								raise TypeError(msg)
						else:
							msg = 'Incorrect data type for value = {} or type {} for field {} of type {}'
							msg = msg.format(value, type(value), name, field.type)
							raise TypeError(msg)
			
			# this allows models to have validators 
			for funcName in self.__field_validators__.get(name, set()):
				getattr(self, funcName)(value)
			
		return value
			
	def _setFieldValue(self, name, field, value):
		# check if frozen
		if (bool(field.frozen) or self._config_dict_['frozen']) and self.__jydantic_complete__:
			raise FrozenError('cannot set field {}, it is frozen/readonly'.format(name))
		value = self._ensureFieldValue(name, field, value)	
		self._setWithoutSideEffects(name, value)
		
		# latch the frozen bit if readonly
		if getattr(field, 'readonly', False) and (value is not None):
			field.frozen = True
		
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
		for name in self.__model_validators__:
			try:
				mv = getattr(self, name)
				mv()  # self is implicitly bound to the function call already
			except RuntimeError as e:
				if 'recursion' in e.message.lower():
					msg = '{}, make sure not to set model values inside of a modelValidator'
					msg = msg.format(e.message.splitlines()[-1])
					raise ValidationError(msg)
				else:
					raise e
	
	def update(self, other):
		# convert model to dict if needed
		if isinstance(other, BaseModel):
			other = {k: getattr(other, k, None) for k in other.__fields__.keys()}
		elif type(other) != dict:
			msg = 'Can only update from dict or subclass of BaseModel, not {}'
			msg = msg.format(other)
			raise TypeError(msg)
		
		# save config
		validateData = self.__validate_data__
		
		# apply the changes with __validate_data__ off to defer modelValidator
		# note that only fields where the values don't match are updated
		self.__validate_data__ = False
		[setattr(self, k, v) for k, v in other.items() if getattr(self, k, None) != v]
		
		# re-apply config and run modelValidators if necessary
		self.__validate_data__ = validateData
		if self.__validate_data__:
			self._validateModel()
		
	@classProperty
	def modelFields(instanceOrCls):
		"""Returns a copy of the fields for this class/instance""" 
		return copy.copy(instanceOrCls.__fields__)
		
	@classProperty
	def modelComputedFields(instanceOrCls):
		"""Returns a copy of the computed fields for this class"""
		return copy.copy(instanceOrCls.__computed_fields__)
	
	def modelDump(self, byAlias=False, excludeNone=False, serializers={}):
		"""Converts the model to a dictionary recurrsively
		Args:
			byAlias: bool, defaults to false, flag indicating if fields should be dumped using serialization alias, more field name.
			excludeNone: bool, default to false, flag indicating if only fields with a non-None value should be dumped.
		"""
		dumpParams = dict(
			byAlias=byAlias,
			excludeNone=excludeNone,
		)
		dump = {}
		fields = self.__fields__
		fields.update(self.__computed_fields__)
		
		# collect the model fields
		for key, field in fields.items():
			if (not field.exclude):
				alias = field.serializationAlias or key if byAlias else key
				value = getattr(self, key)
				serializer = serializers.get(key)
				if (value is not None) or (not excludeNone):
					if isinstance(value, BaseModel):
						if isinstance(serializer, (dict, type(None))):
							_dumpParams = {}
							_dumpParams.update(dumpParams)
							_dumpParams['serializers'] = serializer or {}
							value = value.modelDump(**_dumpParams)
						else:
							value = serializer(value)
					elif serializer is not None:
						value = serializer(value)
					elif hasattr(value, '__iter__'):
						if not isinstance(value, dict):
							value = [v.modelDump(**dumpParams) if isinstance(v, BaseModel) else v for v in value]
						else:
							value = {k.modelDump(**dumpParams) if isinstance(k, BaseModel) else k: 
									v.modelDump(**dumpParams) if isinstance(v, BaseModel) else v 
									for k, v in value.items()}
					dump[alias] = value
		return dump
		