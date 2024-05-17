from __future__ import print_function
import unittest
from functools import partial
from java.lang import Integer, String
from java.util import Date
from com.inductiveautomation.ignition.common import BasicDataset
from jydantic.core import BaseModel, Field, ValidationError, ModelInitError, FrozenError
from jydantic.core import fieldValidator, computedField, modelValidator, configDict


class TestBaseModel(unittest.TestCase):
	
	def test_raiseErrorWhenInstantiatingBaseModelDirectly(self):
		with self.assertRaises(NotImplementedError) as ct:
			model = BaseModel()
			
	def test_doesDeepcopyDataStructures(self):
		class Model(BaseModel):
			pass
		
		# make sure that class level structures are deep copied. The easiest way
		# to do this is by modifyng one class var and seeing if the change is reflected
		# in the other class var
		
		Model.__fields__['foo'] = 'bar'
		self.assertTrue('foo' in Model.__fields__.keys())
		self.assertFalse('foo' in BaseModel.__fields__.keys())
		
		Model.__computed_fields__['foo'] = 'bar'
		self.assertTrue('foo' in Model.__computed_fields__.keys())
		self.assertFalse('foo' in BaseModel.__computed_fields__.keys())
		
		Model.__field_validators__['foo'] = 'bar'
		self.assertTrue('foo' in Model.__field_validators__.keys())
		self.assertFalse('foo' in BaseModel.__field_validators__.keys())
		
		Model.__model_validators__.add('foo')
		self.assertTrue('foo' in Model.__model_validators__)
		self.assertFalse('foo' in BaseModel.__model_validators__)
		
		Model._config_dict_['foo'] = 'bar'
		self.assertTrue('foo' in Model._config_dict_.keys())
		self.assertFalse('foo' in BaseModel._config_dict_.keys())
		
		
class TestFields(unittest.TestCase):

	def test_fieldsMustHaveTypeObj(self):
			
		with self.assertRaises(ModelInitError) as ct:
			class Model(BaseModel):
				pk = Field
				
	def test_fieldsWithPrimatives(self):
		
		class Model(BaseModel):
			
			pk = Field(int)
			name = Field(str)
			
		model = Model(pk=1, name='foo')
		self.assertTrue(type(model.pk) == int)
		self.assertTrue(type(model.name) == str)
		
	def test_fieldsWithNestedModels(self):
		
		class Parent(BaseModel):
			pk = Field(str)
	
		class Child(BaseModel):
			pk = Field(int)
			parent = Field(Parent)
			
		parent = Parent(pk='1')
		child = Child(pk=1, parent=parent)
		self.assertTrue(type(child.parent) == Parent)
		
	def test_fieldsCanCoerceTypes(self):
		class Model(BaseModel):
					
			pk = Field(int)
			name = Field(str)
			
		model = Model(pk='1', name=5)
		self.assertTrue(type(model.pk) == int)
		self.assertTrue(type(model.name) == str)
		
	def test_fieldsCanBeStrict(self):
		class Model(BaseModel):
							
			pk = Field(int, strict=True)
			name = Field(str)
		
		model = Model(pk=1, name='5')
		with self.assertRaises(TypeError) as ct:
			model = Model(pk='1', name=5)
			
	def test_modelCanBeStrict(self):
		class Model(BaseModel):
			_config_dict_ = configDict(strict=True)
											
			pk = Field(int)
			name = Field(str)
		
		with self.assertRaises(TypeError) as ct:
			model = Model(pk='1', name=5)
			
	def test_canFreezeField(self):
		class Model(BaseModel):
			pk = Field(int)
			fk = Field(int, frozen=True)
			 
		model = Model(pk=5, fk=3)
		model.pk = 3
		with self.assertRaises(FrozenError) as ct:
			model.fk = 5
		
	def test_canDumpFields(self):
		class Model(BaseModel):
			pk = Field(int)
			fk = Field(str)
		
		model = Model(pk=5, fk=3)
		data = model.modelDump()
		self.assertEqual(data['pk'], 5)
		self.assertEqual(data['fk'], '3')
		
	def test_canValidatFields(self):
		class Model(BaseModel):
			pk = Field(int)
			fk = Field(str)
			
			@fieldValidator('fk')
			@classmethod
			def isNumber(cls, value):
				int(value)
		
		model = Model(pk=5, fk=3)
		with self.assertRaises(ValueError) as ct:
			model.fk = 'a'
			
	def test_canValidateFieldsOnlyAtInit(self):
		class Model(BaseModel):
			_config_dict_ = configDict(validateAssignment=False)
			
			pk = Field(int)
			fk = Field(str)
			
			@fieldValidator('fk')
			@classmethod
			def isNumber(cls, value):
				int(value)
		
		
		with self.assertRaises(ValueError) as ct:
			model = Model(pk=5, fk='a')
		
		model = Model(pk=5, fk=3)
		model.fk = 'a'
		self.assertEqual(model.fk, 'a')
		
	def test_canBypassValidation(self):
		class Model(BaseModel):
			
			pk = Field(int)
			fk = Field(str)
			
			@fieldValidator('fk')
			@classmethod
			def isNumber(cls, value):
				int(value)
		
		with self.assertRaises(ValueError) as ct:
			model = Model(pk=5, fk='a')
		
		model = Model.modelConstruct(pk=5, fk='a')
		
	def test_extraFieldOptions(self):
		class ForbidModel(BaseModel):
			_config_dict_ = configDict(extraFields='FORBID')
			
			pk = Field(int)
			
		class IgnoreModel(BaseModel):
			_config_dict_ = configDict(extraFields='IGNORE')
			
			pk = Field(int)
			
		class AllowModel(BaseModel):
			_config_dict_ = configDict(extraFields='ALLOW')
			
		with self.assertRaises(ValidationError) as ct:
			model = ForbidModel(pk=3, fk=6)
		
		with self.assertRaises(ValidationError) as ct:
			model = ForbidModel(pk=3)
			model.fk = 7
			
		with self.assertRaises(AttributeError) as ct:
			model = IgnoreModel(pk=3, fk=6)
			self.assertEqual(model.fk, 6)
		
		with self.assertRaises(AttributeError) as ct:
			model = IgnoreModel(pk=3)
			model.fk = 7
			
		model = AllowModel(pk=3, fk=6)
		model.tk = 7
		self.assertEqual(model.fk, 6)
		self.assertEqual(model.tk, 7)
		

class TestComputedFields(unittest.TestCase):
	
	def test_canReadComputedField(self):
		class Model(BaseModel):
			
			pk = Field(int)
			
			@computedField()
			@property
			def name(self):
				return 'self' + str(self.pk)
				
		model = Model(pk=3)
		self.assertEqual(model.name, 'self3')
		
	def test_canWriteComputedField(self):
		class Model(BaseModel):
			
			pk = Field(int)
			prefix = Field(str, defaultValue='self')
			
			@computedField()
			@property
			def name(self):
				return self.prefix + str(self.pk)
				
			@name.setter
			def name(self, newValue):
				prefix = newValue[:-1]
				pk = newValue[-1]
				self.prefix = prefix
				self.pk = pk
				
		model = Model(pk=5)
		model.name = 'foo2'
		self.assertEqual(model.prefix, 'foo')
		self.assertEqual(model.pk, 2)
		
	def test_canFreezeComputedField(self):
		class Model(BaseModel):
					
			pk = Field(int)
			prefix = Field(str, defaultValue='self')
			
			@computedField(frozen=True)
			@property
			def name(self):
				return self.prefix + str(self.pk)
				
			@name.setter
			def name(self, newValue):
				self.prefix = newValue[:-1]
				self.pk = newValue[-1]
				
		model = Model(pk=5)
		with self.assertRaises(FrozenError) as ct:
			model.name = 'foo2'
			
	def test_canValidateComputedField(self):
		class Model(BaseModel):
							
			pk = Field(int)
			prefix = Field(str, defaultValue='self')
			
			@computedField()
			@property
			def name(self):
				return self.prefix + str(self.pk)
				
			@name.setter
			def name(self, newValue):
				self.prefix = newValue[:-1]
				self.pk = newValue[-1]
				
			@fieldValidator('name')
			@classmethod
			def validateName(cls, value):
				if 'foo' in value:
					raise ValueError('Cannot set name to foo')
				
		model = Model(pk=5)
		with self.assertRaises(ValueError) as ct:
			model.name = 'foo2'
			
	def test_canDumpComputedFields(self):
		class Model(BaseModel):
							
			pk = Field(int)
			prefix = Field(str, defaultValue='self')
			
			@computedField()
			@property
			def name(self):
				return self.prefix + str(self.pk)
				
			@name.setter
			def name(self, newValue):
				self.prefix = newValue[:-1]
				self.pk = newValue[-1]
				
		model = Model(pk=5)
		data = model.modelDump()
		self.assertEqual(data['name'], 'self5')
		
		
class TestModelValidator(unittest.TestCase):
	
	def test_canValidateModel(self):
		class Model(BaseModel):
									
			pk = Field(int, allowNone=True)
			fk = Field(int, allowNone=True)
			
			@modelValidator
			def validatFk(self):
				if (self.pk is not None) and (self.fk is None):
					raise ValueError('Cannot set pk if fk is None')
				
		model = Model(pk=5, fk=3)
		with self.assertRaises(ValueError) as ct:
			model = Model(pk=3)
			
	def test_canValidateOnlyAtInit(self):
		class Model(BaseModel):
			_config_dict_ = configDict(validateAssignment=False)
											
			pk = Field(int, allowNone=True)
			fk = Field(int, allowNone=True)
			
			@modelValidator
			def validatFk(self):
				if (self.pk is not None) and (self.fk is None):
					raise ValueError('Cannot set pk if fk is None')
		
		with self.assertRaises(ValueError) as ct:
			model = Model(pk=3)
		
		model = Model()
		model.pk = 5
		self.assertEqual(model.pk, 5)
		
	def test_canBypassValidation(self):
		class Model(BaseModel):
									
			pk = Field(int, allowNone=True)
			fk = Field(int, allowNone=True)
			
			@modelValidator
			def validatFk(self):
				if (self.pk is not None) and (self.fk is None):
					raise ValueError('Cannot set pk if fk is None')
				
		with self.assertRaises(ValueError) as ct:
			model = Model(pk=3)
		
		model = Model.modelConstruct(pk=3)
		
	def test_writingToPropsDuringModelValidationCausesRecurssionError(self):
		class Model(BaseModel):
											
			pk = Field(int, allowNone=True)
			fk = Field(int, allowNone=True)
			
			@modelValidator
			def validatFk(self):
				# trying to write values should cause an issue
				self.pk = self.pk + 1
		
		with self.assertRaises(ValidationError) as ct:
			model = Model(pk=3, fk=3)
		
		
def runTests():
	testing.testing_utils.runTests(
		TestBaseModel,
		TestFields,
		TestComputedFields,
		TestModelValidator
	)
	
	
	
	