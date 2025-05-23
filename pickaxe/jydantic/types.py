from __future__ import print_function
from functools import wraps
from datetime import date, datetime
from java.util import Date
from java.lang import Exception as JavaException
from java.text import ParseException



# ---------------- TYPES -----------------


class BaseMeta(type):
	"""Base class for all meta classes that closes the classes
	for modification by default.
	"""
	
	def __setattr__(cls, name, value):
		msg = '{} has no attribute {}'
		msg = msg.format(cls, name)
		raise AttributeError(msg)


class AnyMeta(BaseMeta):
	"""Meta-class for the Any class that returns true when performing
	and instance check as long as the value is not None.
	"""
	
	def __instancecheck__(cls, other):
		"""Overloads the isinstance behavior for the Any class
		Args:
			cls, type
			self, type, left hand of the isinstance call
			other, value, right hand of the isinstance call
		"""
		return other is not None


class Any(object):
	"""Any class that returns true when performing
	and instance check as long as the value is not None.
	This is useful for fields where a value is required,
	but can be of any data type.
	Example:
		class Model(BaseModel):
			x0 = Field(int)
			x1 = Field(Any)
			...
	"""

	__metaclass__ = AnyMeta
	
	def __init__(self, *args, **kwargs):
		raise NotImplementedError('Any type cannot be instanced')


class UnionMeta(BaseMeta):
	"""Meta-class for the Union class.
	"""
	pass


class Union(object):
	"""Union class that constrains a field type to one of
	several sub-types.
		
	Example:
		class Magician(BaseModel):
			name = Field(str, defaultValue='David Copperfield')
			favoriteTrickId = Field(int)
			
		class Wizard(BaseModel):
			name = Field(str, defaultValue='Dumbledor the White')
			staffColorCode = Field(str, defaultValue='gold')
		
		class SantaClause(BaseModel):
			bestDescribedAs = Field(Union(Magician, Wizard))
		...
	"""
	
	__metaclass__ = UnionMeta
	
	def __new__(cls, *types):
		"""Builds a new union class definition using the Union
		base as a templete.
		
		Args:
			types: list[<T>], list of allowed types for the new union class
		"""
		
		if not types:
			raise ValueError('Cannot create a Union without types')
		
		# compute the name
		name = 'Union{}'.format(types)
			
		# override the default implementation for the new class
		def __new__(cls, value):
			msg = 'Cannot create second generation {}'.format(cls)
			raise NotImplementedError(msg)
		
		# build the new class
		newCls = type.__new__(
			type(cls),
			name,
			(cls,),
			{
				'__new__': __new__,
				'types': tuple(types)
			}
		)
		return newCls


class EnumMember(object):
	"""Enum member class that is initiated with a value.
	Example:
		class COLORS(Enum):
			RED = EnumMember(0)
			BLUE = EnumMember(1)
			GREEN = EnumMember(2)
			
		c = COLORS.RED
		isinstance(c, COLORS)
		>>> True
		c == COLORS.RED:
		>>> True
	"""
	
	def __init__(self, value):
		object.__setattr__(self, 'value', value)
		
	def __eq__(self, other):
		return self is other
		
	def __setattr__(self, name, value):
		raise AttributeError('Cannot overwrite or create attributes for EnumMembers')
		
	def __repr__(self):
		return '{}.{}: {}'.format(self._enum, self.name, self.value)


class EnumMeta(type):
	"""Enum metaclass that parses enum members
	"""
	
	def __init__(cls, name, bases, attrs):
		mcls = type(cls)
		members = {k: v for k, v in attrs.items() if isinstance(v, EnumMember)}
		for k, v in members.items():
			object.__setattr__(v, '_enum', cls)
			object.__setattr__(v, 'name', k)
			object.__setattr__(cls, k, v)
			
	def __setattr__(cls, name, value):
		raise AttributeError('Cannot overwrite or create attributes for Enums')
			
	def __instancecheck__(cls, other):
		try: 
			return other._enum is cls
		except:
			return False


class Enum(object):
	"""Base class for creating enums:
	Example:
		class COLORS(Enum):
			RED = EnumMember(0)
			BLUE = EnumMember(1)
			GREEN = EnumMember(2)
			
		c = COLORS.RED
		isinstance(c, COLORS)
		>>> True
		c == COLORS.RED:
		>>> True
	"""
	
	__metaclass__ = EnumMeta
	
	def __init__(self):
		raise NotImplementedError('Cannot instance enums')
	
	@classmethod
	def forValue(cls, value):
		for k, v in cls.__dict__.items():
			if isinstance(v, EnumMember) and v.value == value:
				return v
		msg = 'Cannot get enum member from value = {}'
		msg = msg.format(value)
		raise ValueError(msg)
					
	@classmethod
	def forName(cls, name):
		member = getattr(cls, name, None)
		if isinstance(member, EnumMember):
			return member
		msg = 'Cannot get enum member from name = {}'
		msg = msg.format(name)
		raise ValueError(msg)


class LiteralMeta(BaseMeta):
	"""Meta class for Literal types.
	"""
	pass


class Literal(object):
	"""Literal class used to constrain field inputs to a specific value,
	not just a specific type as is the case with the Union type.
	
	Example:
		class ChartOptions(BaseModel):
			mode = Field(Literal('historical', 'realtime'))
			
		options = ChartOptions(mode='historical')
		
	"""
	
	__metaclass__ = LiteralMeta
	
	def __new__(cls, *options):
		if not options:
			raise ValueError('Cannot create a Literal without options')
		
		# compute the name
		name = 'Literal{}'.format(options)
			
		# override the default implementation for the new class
		def __new__(cls, value):
			raise NotImplementedError('Cannot create second generation {}'.format(cls))
		
		# build the new class
		newCls = type.__new__(
			type(cls),
			name,
			(cls,),
			{
				'__new__': __new__,
				'options': tuple(options)
			}
		)
		return newCls


class ValidatedMeta(BaseMeta):
	"""Meta class for Validated types.
	"""
	
	__validatedRef = None
	
	@classmethod
	def _buildValidated(mcls, cls, type_, *validationFunctions):
		if not validationFunctions:
			raise ValueError('Cannot create a Validated type without validationFunctions')
		
		# compute the name
		name = 'Validated{}{}'.format(type_, validationFunctions)
			
		# override the default implementation for the new class
		def __new__(cls, *args, **kwargs):
			raise NotImplementedError('Cannot create second generation {}'.format(cls))
			
		validationFunctions = [vf if isinstance(vf, staticmethod) else staticmethod(vf) for vf in validationFunctions]
		validationFunctionNames = tuple([vf.__func__.__name__ for vf in validationFunctions])
		attrs = {vfn: vf for (vfn, vf) in zip(validationFunctionNames, validationFunctions)}
		
		attrs['validationFunctionNames'] = validationFunctionNames
		attrs['__new__'] = __new__
		attrs['type'] = type_
		
		# build the new class
		newCls = type.__new__(
			mcls,
			name,
			(cls,),
			attrs
		)
		return newCls
	
	def __new__(mcls, *args, **kwargs):
		if mcls.__validatedRef is not None:
			name, bases, attrs = args
			if len(bases) > 1 or bases[0] != mcls.__validatedRef:
				raise NotImplementedError('Cannot subclass subclasses of Validated')
			type_ = attrs['type']
			validationFunctions = [obj for obj in attrs.values() if isinstance(obj, staticmethod)]
			cls = ValidatedMeta._buildValidated(mcls.__validatedRef, type_, *validationFunctions)
		else:
			cls = BaseMeta.__new__(mcls, *args, **kwargs)
			mcls.__validatedRef = cls
		return cls


class Validated(object):
	"""Validated class used to bind validation logic to types instead of fields.
	
	Example:
		from pickaxe.jydantic.types import Validated
		
		def withinRange(x):
			if not (0 <= x <= 10):
				raise ValueError('value = {} is not within range'.format(x))
		
		LinearScale = Validated(int, withinRange)
		
		...
		class Model(BaseModel):
			score = Field(LinearScale, defaultValue=0)
		...
	"""
	
	__metaclass__ = ValidatedMeta
	
	def __new__(cls, type_, *validationFunctions):
		return ValidatedMeta._buildValidated(cls, type_, *validationFunctions)


class ContainerMeta(BaseMeta):
	"""Meta class for creating Container data types.
	"""
	pass


class Container(object):
	"""A class that tells the base model to try and 
	build child models of the given type when passed a container.
	
	Example
		class Child(BaseModel):
			id = Field(int)
		
		class Parent(BaseModel):
			id = Field(int)
			children = Container(Child)
			
		parent = Parent(
			id = 1,
			children = [
				Child(
					id = 1
				),
				Child(
					id = 2
				),
				Child(
					id = 3
				)
			]
		)
	"""
	
	__metaclass__ = ContainerMeta
	
	def __new__(cls, itemType, containerType=None):
		# compute the class name
		name = 'Container{}'.format((itemType, containerType))
		
		# override default __new__ method
		def __new__(cls, itemType, containerType=None):
			raise NotImplementedError('Cannot create second generation {}'.format(cls))
			
		newCls = type.__new__(
			type(cls),
			name,
			(cls,),
			{
				'__new__': __new__,
				'itemType': itemType,
				'containerType': containerType
			}
		)
		return newCls


class DictMeta(BaseMeta):
	"""Meta class for creating Dict data types.
	"""
	pass


class Dict(object):
	"""A that defines dictionary parameters for a model
	"""
	
	__metaclass__ = DictMeta
	
	def __new__(cls, keyType, valueType):
		# compute the class name
		name = 'Dict{}'.format((keyType, valueType))
		
		# override default __new__ method
		def __new__(cls, keyType, valueType):
			raise NotImplementedError('Cannot create second generation {}'.format(cls))
			
		newCls = type.__new__(
			type(cls),
			name,
			(cls,),
			{
				'__new__': __new__,
				'keyType': keyType,
				'valueType': valueType
			}
		)
		return newCls
		
		
# -------------------- Type Checkers --------------------

class TypeCheckerRegistry(object):
	"""Registers functions to provied specialized type checking implementations.
	Note that the class is not meant to be instanced. It instead uses class methods.
	
	Example1:
		from ... import TypeCheckerRegistry
		
		TypeCheckerRegistry.registerForType(complex)
		def complexTypeChecker(registry, complexClass, value, strict):
			if not strict:
				return type(value) == complexClass
			else:
				return isinstance(value, complexClass
				
				
		def someFunction(coordinate):
			if TypeCheckerRegistry.checkType(complex, value, strict=False):
				...
			else:
				raise TypeError('coordinate must be of type complex')
				
	Example2:
		from ... import TypeCheckerRegsitry
		
		class MyMetaClass(type):
			pass
		
		@TypeCheckerRegistry.registerForType(MyMetaClass)
		def myMetaClassTypeChecker(registry, myBaseClass, value, strict):
			... check logic
		
		# myMetaClassTypeChecker will now get called when MyBaseClass, 
		# or any class that inherits from it is type checked.
		
		class MyBaseClass(object):
			__metaclass__ = MyMetaClass
			...
	"""
	
	__metaclass__ = BaseMeta
	
	__typeCheckerMap = {}
	
	def __new__(cls, *args, **kwargs):
		raise NotImplemented('Cannot create instances of {}'.format(cls))
		
	@staticmethod
	def defaultTypeChecker(registry, fieldType, value, strict):
		"""Provides default type checking, and is an example for the
		creating type checkers for <x>TypeChecker functions.
		
		Args:
			registry: TypeCheckerRegistry object that is passed in. This is useful for implementing recursive checks.
			fieldType: <T>, generic type that can be any type/class definition to be used for type checking.
			value: Any, value that is to be type checked.
			strict: bool, tells the checker to use strict checking or not:
				- strict, types must match exactly
				- not strict, types must return isinstnace(value, fieldType)
		
		Returns: bool
		"""
		return type(value) == fieldType if strict else isinstance(value, fieldType)
		
	@classmethod
	def getTypeChecker(cls, fieldType):
		"""Returns the type checker for the type passed in.
		The order or precedence is the type's metatype, then
		the type, then a fallback to the default type checker.
		
		Note that the registry & fieldType are bound to the checker returned
		so only the value & strict need to be passed into the checker.
		
		Args:
			fieldType: <T>, type used to look up checking function
			
		Returns: callable, function with signiture(value: Any, strict: bool)
		"""
		
		# look up the checker, using the default as a fallback
		metaType = type(fieldType)
		method = cls.__typeCheckerMap.get(
			metaType,
			cls.__typeCheckerMap.get(
				fieldType,
				cls.defaultTypeChecker
			)
		)
		
		# wrap it to bind the type to the checker
		@wraps(method)
		def wrapper(v, strict):
			return method(cls, fieldType, v, strict)
		
		return wrapper
		
	@classmethod
	def checkType(cls, fieldType, value, strict):
		"""Checks the type of a value that is supposed to be
		of type fieldType, can check strictly or loosely.
		
		Args:
			fieldType: <T>, type that the value should be
			value: Any, value that is being type checked
			strict: bool, how to check it, see defaultTypeChecker for more info.
		"""
		checker = cls.getTypeChecker(fieldType)
		return checker(value, strict)
		
	@classmethod
	def registerForType(cls, forType):
		"""Decorator that registers a checking function with the registry.
		Note that it will throw an exception if there is already an entry
		in the registry for the passed in type.
		
		The wrapped function should have the signiture (registry: TypeCheckerRegistry, forType: <T>, value: Any, strict: bool)
		
		Args:
			forType: <T>, type that the wrapped function should be used to check.
		"""
		def registerForType(checker):
			cls.registerTypeChecker(forType, checker)
			return checker
		return registerForType
			
	@classmethod
	def registerTypeChecker(cls, forType, checker):
		"""Registers a checker for the given type.
		Raises an error if attempting to add a duplicate type.
		
		Args:
			forType: <T>, type that the checker is for.
			checker: callable, with the same signiture as the defaultTypeChecker method
		"""
		if forType in cls.__typeCheckerMap.keys():
			msg = 'Cannot add duplicate entry for type {} to the TypeCheckerRegistry'
			msg += '\nTo remove the existing checker, please call TypeCheckerRegistry.removeTypeChecker'
			msg = msg.format(forType)
			raise ValueError(msg)
		cls.__typeCheckerMap[forType] = checker
		
	@classmethod
	def hasTypeCheckerFor(cls, forType):
		"""Return a boolean indicating if the type has an entry in the registry.
		
		Args:
			forType: <T>, type used to check the registry.
			
		Returns: bool
		"""
		return forType in cls.__typeCheckerMap.keys()
		
	@classmethod
	def removeTypeChecker(cls, forType):
		"""Removes a the checking function and type from the registry.
		
		Args:
			forType: <T>, type used to remove entry from registry.
		"""
		del cls.__typeCheckerMap[forType]


@TypeCheckerRegistry.registerForType(AnyMeta)
def anyTypeChecker(registry, anyType, value, strict):
	#this will return true for any value that is not None
	return isinstance(value, Any)


@TypeCheckerRegistry.registerForType(UnionMeta)
def unionTypeChecker(registry, unionType, value, strict):
	# returns true if is instance when not strict, or if type
	# is in the union classes types tuple.
	return any((registry.checkType(t, value, strict) for t in unionType.types))


@TypeCheckerRegistry.registerForType(EnumMeta)
def enumTypeChecker(registry, enumType, value, strict):
	try:
		if strict:
			return isinstance(value, enumType)
		else:
			try:
				value = enumType.forValue(value)
				return isinstance(value, enumType)
			except ValueError as e:
				value = enumType.forName(value)
				return isinstance(value, enumType)
	except (Exception, JavaException) as e:
		return False


@TypeCheckerRegistry.registerForType(LiteralMeta)
def literalTypeChecker(registry, literalType, value, strict):
	# checks values for literal types, not strict forces the
	# values and  types to be equal, not just the values to be equivelent.
	if not strict:
		return any((value == o for o in literalType.options))
	else:
		return any((value == o and type(value) == type(o) for o in literalType.options))


@TypeCheckerRegistry.registerForType(ValidatedMeta)
def validatedTypeChecker(registry, validatedType, value, strict):
	try:
		for vfn in validatedType.validationFunctionNames:
			getattr(validatedType, vfn)(value)
		return registry.checkType(validatedType.type, value, strict)
	except Exception as e:
		return False


@TypeCheckerRegistry.registerForType(ContainerMeta)
def containerTypeChecker(registry, containerType, value, strict):
	if not strict:
		return ( 
			all([registry.checkType(containerType.itemType, v, strict) for v in value]) 
			and ((containerType.containerType is None) or registry.checkType(containerType.containerType, value, strict)) 
		)
	else:
		return (
			((containerType.containerType is None) or (registry.checkType(containerType.containerType, value, strict)))
			and all((registry.checkType(containerType.itemType, v, strict) for v in value))
		)


@TypeCheckerRegistry.registerForType(DictMeta)
def dictTypeChecker(registry, dictType, value, strict):
	return all((registry.checkType(dictType.keyType, k, strict) and registry.checkType(dictType.valueType, v, strict) for k, v in value.items()))


# -------------------- Type Converters --------------------

class TypeConverterRegistry(object):
	"""Registers functions to provied specialized type converting implementations.
	Note that the class is not meant to be instanced. It instead uses class methods.
	
	Example1:
		from ... import TypeConverterRegistry
		
		TypeConverterRegistry.registerForType(complex)
		def complexTypeConverter(registry, complexClass, value):
			if isinstance(value, (int, long, float)):
				value = complex(value, 0)
			if isinstance(value, complexClass):
				return value
			msg = 'Could not convert value = {} or type {} to type {}'
			msg = msg.format(value, type(value), complexClass)
			raise TypeError(msg)
				
		def someFunction(coordinate):
			if not isinstance(coordinate, complex):
				coordinate = TypeConverterRegistry.convertType(complex, coordinate)
			...
				
	Example2:
		from ... import TypeConverterRegsitry
		
		class MyMetaClass(type):
			pass
		
		@TypeConverterRegistry.registerForType(MyMetaClass)
		def myMetaClassTypeConverter(registry, myBaseClass, value):
			if isinstance(value, dict):
				... code to convert from dict
			elif isinstance(value, BasicDataset):
				... code to convert from dict
			if isinstance(value, myBaseClass):
				return value
			msg = 'Could not convert value = {} or type {} to type {}'
			msg = msg.format(value, type(value), myBaseClass)
			raise TypeError(msg)
		
		# myMetaClassTypeConverter will now get called when MyBaseClass, 
		# or any class that inherits from it is type checked.
		
		class MyBaseClass(object):
			__metaclass__ = MyMetaClass
			...
	"""
	
	__metaclass__ = BaseMeta
	
	__typeConverterMap = {}
	
	def __new__(cls, *args, **kwargs):
		raise NotImplemented('Cannot create instances of {}'.format(cls))
	
	@staticmethod
	def defaultTypeConverter(registry, fieldType, value):
		"""Provides default type converting, and is an example for the
		creating type converter for <x>TypeChecker functions. 
		
		Note that all type converters should throw an exception if they fail to convert
		the type. The check should usually be done using isinstance(value, fieldType),
		rather than type(value) == fieldType.
		
		Args:
			registry: TypeConverterRegistry object that is passed in. This is useful for implementing recursive convertions.
			fieldType: <T>, generic type that can be any type/class definition to be used for type converting.
			value: Any, value that is to be type converted.
		
		Returns: bool
		"""
		e = None
		try:
			value = fieldType(value)
			if isinstance(value, fieldType):
				return value
		except (Exception, JavaException) as e:
			pass
		msg = 'Cannot convert value = {} of type {} to type = {} with exception:\n\t{}'
		msg = msg.format(value, type(value), fieldType, e) 
		raise TypeError(msg)
		
	@classmethod
	def getTypeConverter(cls, fieldType):
		"""Returns the type converter for the type passed in.
		The order or precedence is the type's metatype, then
		the type, then a fallback to the default type converter.
		
		Note that the converter returned is bound to the fieldType
		passed in so to use the converter only the value has to to be 
		passed in as an argument.
		
		Args:
			fieldType: <T>, type used to look up checking function
			
		Returns: callable, function with signiture(value: Any, strict: bool)
		"""
		metaType = type(fieldType)
		method = cls.__typeConverterMap.get(
			metaType, 
			cls.__typeConverterMap.get(
				fieldType,
				cls.defaultTypeConverter
			)
		)
		
		@wraps(method)
		def wrapper(v):
			return method(cls, fieldType, v)
		
		return wrapper
	
	@classmethod
	def convertType(cls, fieldType, value):
		"""Attemps to convert the type of value to the type of fieldType.
		
		Args:
			fieldType: <T>, type used to look up converter internally.
			value: Any, value that needs the type converted.
		"""
		converter = cls.getTypeConverter(fieldType)
		return converter(value)
		
	@classmethod
	def registerForType(cls, forType):
		"""Decorator that registers a converting function with the registry.
		Note that it will throw an exception if there is already an entry
		in the registry for the passed in type.
		
		The wrapped function should have the signiture (registry: TypeConverterRegistry, forType: <T>, value: Any)
		
		Args:
			forType: <T>, type that the wrapped function should be used to converter.
		"""
		def registerForType(converter):
			cls.registerTypeConverter(forType, converter)
			return converter
		return registerForType
		
	@classmethod
	def hasConverterForType(cls, fieldType):
		"""Returns a bool indicating if the fieldType is already in the registry.
		Useful for replacing type converters.
		
		Args:
			fieldType: <T>, type to check for in registry.
		
		Returns: bool
		"""
		return fieldType in cls.__typeConverterMap.keys()
		
	@classmethod
	def registerTypeConverter(cls, forType, converter):
		"""Registers a converter for the given type.
		Raises an error if attempting to add a duplicate type.
		
		Args:
			forType: <T>, type that the checker is for.
			converter: callable, with the same signiture as the defaultTypeConverter method
		"""
		if forType in cls.__typeConverterMap.keys():
			msg = 'Cannot add duplicate entry for type {} to the TypeConverterRegistry'
			msg += '\nTo remove the existing checker, please call TypeConverterRegistry.removeTypeConverter'
			msg = msg.format(forType)
			raise ValueError(msg)
		cls.__typeConverterMap[forType] = converter
		
	@classmethod
	def removeTypeConverter(cls, forType):
		"""Removes a the converting function and type from the registry.
		
		Args:
			forType: <T>, type used to remove entry from registry.
		"""
		del cls.__typeConverterMap[forType]
	
	
@TypeConverterRegistry.registerForType(UnionMeta)
def unionTypeConverter(registry, unionType, value):
	# try to convert the value to one of the union types
	for t in unionType.types:
		try:
			value = registry.convertType(t, value)
			if TypeCheckerRegistry.checkType(t, value, strict=False):
				return value
		except: 
			pass
	# if failed to convert the value, raise an exception
	msg = 'Cannot convert value = {} for union.types = {}'
	msg = msg.format(value, unionType.types) 
	raise TypeError(msg)
	
	
@TypeConverterRegistry.registerForType(EnumMeta)
def enumTypeConverter(registry, enumType, value):
	try:
		try:
			value = enumType.forValue(value)
			return value
		except ValueError as e:
			pass
		try:
			value = enumType.forName(value)
			return value
		except ValueError as e:
			pass
	except (Exception, JavaException) as e:
		pass
	msg = 'Cannot convert value = {} of type {} to type {}'
	msg = msg.format(value, type(value), enumType)
	raise ValueError(msg)
		
		
@TypeConverterRegistry.registerForType(LiteralMeta)
def literalTypeConverter(registry, literalType, value):
	msg = 'Cannot convert value = {} to one of {}'
	msg = msg.format(value, ' | '.join(literalType.options))
	raise ValueError(msg)
	
@TypeConverterRegistry.registerForType(ValidatedMeta)
def validatedTypeConverter(registry, validatedType, value):
	value = registry.convertType(validatedType.type, value)
	exceptions = []
	for vfn in validatedType.validationFunctionNames:
		try:
			getattr(validatedType, vfn)(value)
		except (Exception, JavaException) as e:
			exceptions.append(e)
	if not exceptions:
		return value
	msg = 'Cannot convert value = {} of type {} to type {} with the following exceptions:\n{}'
	msg = msg.format(value, type(value), validatedType, exceptions)
	raise ValueError(msg)


@TypeConverterRegistry.registerForType(ContainerMeta)
def containerTypeConverter(registry, containerType, value):
	items = []
	# for value in the container, convert to the item type
	checker = TypeCheckerRegistry.getTypeChecker(containerType.itemType)
	converter = registry.getTypeConverter(containerType.itemType)
	for v in value:
		if not checker(v, strict=False):
			v = converter(v)
		items.append(v)
	# convert the container to the appropriate type
	containerType = containerType.containerType or type(value)
	value = registry.convertType(containerType, items)
	if TypeCheckerRegistry.checkType(containerType, value, strict=False):
		return value
	msg = 'Cannot convert value = {} of type {} for container type = {}'
	msg = msg.format(value, type(value), containerType) 
	raise TypeError(msg)


@TypeConverterRegistry.registerForType(DictMeta)
def dictTypeConverter(registry, dictType, value):
	keyChecker = TypeCheckerRegistry.getTypeChecker(dictType.keyType)
	keyConverter = registry.getTypeConverter(dictType.keyType)
	valueChecker = TypeCheckerRegistry.getTypeChecker(dictType.valueType)
	valueConverter = registry.getTypeConverter(dictType.valueType)
	dict_ = {}
	for k, v in value.items():
		if not keyChecker(k, strict=False):
			k = keyConverter(k)
		if not valueChecker(v, strict=False):
			v = valueConverter(v)
		dict_[k] = v
	if TypeCheckerRegistry.checkType(dictType, dict_, strict=False):
		return dict_
	msg = 'Cannot convert value = {} of type {} for dict type = {}'
	msg = msg.format(value, type(value), dictType) 
	raise TypeError(msg)
		


@TypeConverterRegistry.registerForType(Date)
def javaDateTypeConverter(registry, dateClass, value):
	if isinstance(value, (str, unicode)):
		try:
			value = system.date.parse(value[:23], 'yyyy-MM-dd HH:mm:ss.SSS')
		except ParseException:
			value = system.date.parse(value)
		if isinstance(value, Date):
			return value
	msg = 'Cannot convert value = {} of type {} to java.util.Date'
	msg = msg.format(value, type(value), date) 
	raise TypeError(msg)
	
@TypeConverterRegistry.registerForType(date)
def pythonDateTypeConverter(registry, dateClass, value):
	if isinstance(value, (str, unicode)):
		value = datetime.strptime(value, '%Y-%m-%d').date()
		if isinstance(value, date):
			return value
	msg = 'Cannot convert value = {} of type {} to datetime.date'
	msg = msg.format(value, type(value), date) 
	raise TypeError(msg)
		
		