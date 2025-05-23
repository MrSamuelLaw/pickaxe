from __future__ import print_function
from inspect import isclass
import functools
from pickaxe.jydantic.types import (TypeCheckerRegistry,
									TypeConverterRegistry)


def forTypes(*types, **kwargs):
	"""Decorator that can type check a model type on an Adaptor method.
	This is useful for preventing the wrong model type from getting passed 
	into an adapter.
	Args:
		*types: Any, types that the adapters second argument will be checked against.
		**kwargs:
			strict: bool, Optional, if strict is True, the will check the model using type(model) in types
					if False, the checking will be done using isinstance(model, types). Defaults to True.
	Returns:
		callable
		
	Example:
		from ... import BaseModel
		from ... import BaseDbAdapter
		
		class Employee(BaseModel):
			...
			
		class Boss(Employee):
			...
		
		class EmployeeDbAdapter(BaseDbAdapter):
			
			@forTypes(Employee, strict=False)
			@classmethod
			def create(cls, model, database='employeeDatabase', tx=None):
				# This would work for both an Employee model and a
				# Boss record as strict=False and Boss is a subclass
				# of Employee.
				...<code that can create an employee record here>
				return model
				
		class BossDbAdapter(BaseDbAdapter):
			
			@forTypes(Boss, strict=True)
			@classmethod
			def create(cls, model, database='bossDatabase', tx=None):
				try:
					# start a transaction so we can do multiple creates and rollback if one fails
					_tx = tx or system.db.beginTransaction(database, system.db.SERIALIZABLE, 2000)
					# create the boss in the employee table
					model = EmployeeDbAdapter.create(model, tx=_tx)
					# dump boss data
					data = model.modelDump()
					# perform a create query for the boss
					query = "insert into table bosses values (:bossField1, :bossField2)"
					key = pickaxe.db.runPrepUpdate(query, data, database, _tx, getKey=True)
					# update the primary key assuming no exceptions were raised up to this point
					model.pk = key
					
					if tx is None:
						# auto commit if no user tx was provided
						system.db.commitTransaction(_tx)
					
				except:
					# roll back if an exception was raised
					system.db.rollbackTransaction(_tx)
				
				finally:
					# close the transaction no matter what if tx is none
					if tx is None:
						system.db.closeTransaction(_tx)
				
				return model
	"""
	strict = kwargs.get('strict', True)
	def forTypes(clsMethod):
		if isinstance(clsMethod, classmethod):
			# wrapper for classmethod
			@functools.wraps(clsMethod.__func__)
			def wrapper(clsOrInstance, *args, **kwargs):
				model = args[0]
				if not any((TypeCheckerRegistry.checkType(t, model, strict) for t in types)):
					msg = 'model of type {} not of types {}'
					msg = msg.format(type(model), types)
					raise TypeError(msg)
				params = (None, clsOrInstance) if isclass(clsOrInstance) else (clsOrInstance, )
				return clsMethod.__get__(*params)(*args, **kwargs)
			newClsMethod = classmethod(wrapper)
			return newClsMethod
		else:
			msg = 'Cannot only use forTypes on classmethod, received type {}'
			msg = msg.format(type(clsMethod))
			raise TypeError(msg)
	return forTypes
	
	
class BasePlcAdapter(object):

	@classmethod
	def read(cls, root, readMethod=system.tag.readBlocking):
		"""This method reads a either a complete or partial model from the plc, 
		using the tag path "root" as a starting point for the read opertation. 
		An optional read method can be specified, for example, pickaxe.tag.readOpc
		Args:
			cls: definition of the adapter class
			root: str, tag path to use for the read operation
			readMethod: callable, method that will be used for read operations. 
						Must have the same call signiture as system.tag.readBlocking
		Returns:
			model: BaseModel, model that that adapter is for
		"""
		raise NotImplementedError('read method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedRead(cls, roots, readMethod=system.tag.readBlocking):
		raise NotImplementedError('batchedRead method not implemented for type {}'.format(cls))
	
	@classmethod
	def update(cls, model, root, writeMethod=system.tag.writeBlocking):
		"""This method takes a model and writes it to tags.
		The starting point for the writes will be the "root" tag path provided.
		Args:
			cls: definition of the adapter class
			model: BaseModel, instance of a model that will be modified
			root: str, tag path to use for the read operation
			writeMethod: callable, method that will be used for write operations. 
						Must have the same call signiture as system.tag.writeBlocking
		Returns:
			List[QualityCode], one QualityCode object for each tag written to
		"""
		raise NotImplementedError('update method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedUpdate(cls, roots, readMethod=system.tag.readBlocking):
		raise NotImplementedError('batchedUpdate method not implemented for type {}'.format(cls))
	
	
class BaseDbAdapter(object):

	@classmethod
	def create(cls, model, database=None, tx=None):
		"""This method creates a complete model record in the database. It is best
		practice to assign a sensible default database to the database keyword argument.
		The method also take a transaction id "tx". This is usefull when multiple
		create calls need to be done sequentially and rolled back if they fail at any point.
		Args:
			cls: definition of the adapter class
			model: BaseMode, model to be persisted in the database
			database: str, optional, database connection that will be used for the create operation
			tx: str, optional, transaction id that will be used for the create operation
		Returns:
			model: BaseModel, model that was persisted.
				   It is best practice to return auto generated primay keys from 
				   the create query and set the corresponding fields on the model
		"""
		raise NotImplementedError('create method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedCreate(cls, models, database=None, tx=None):
		raise NotImplementedError('batchedCreate method not implemented for type {}'.format(cls))

	@classmethod
	def read(cls, pk, database=None, tx=None):
		"""This method reads either a complete or partial model record in the database. 
		It is best practice to assign a sensible default database to the database keyword argument.
		The method also take a transaction id "tx". This is usefull when a read is necessary that depends
		on a write that may its self be created using a transaction.
		Args:
			cls: definition of the adapter class
			pk: Any, primary key used to read in the model, a data structure with multiple keys can be
				passed in if the model must be read from multiple tables in the database
			database: str, optional, database connection that will be used for the read operation
			tx: str, optional, transaction id that will be used for the read operation
		Returns:
			model: BaseModel, model that was read from the DB.
		"""
		raise NotImplementedError('read method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedRead(cls, pks, database=None, tx=None):
		raise NotImplementedError('batchedRead method not implemented for type {}'.format(cls))
		
	@classmethod
	def update(cls, model, database=None, tx=None):
		"""This method updates a model record in the database. It is best
		practice to assign a sensible default database to the database keyword argument.
		The method also take a transaction id "tx". This is usefull when multiple
		update calls need to be done sequentially and rolled back if they fail at any point.
		Args:
			cls: definition of the adapter class
			model: BaseMode, model to be persisted in the database
			database: str, optional, database connection that will be used for the create operation
			tx: str, optional, transaction id that will be used for the create operation
		Returns:
			model: BaseModel, model that was used to update the database.
		"""
		raise NotImplementedError('update method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedUpdate(cls, models, database=None, tx=None):
		raise NotImplementedError('batchedUpdate method not implemented for type {}'.format(cls))
		
	@classmethod
	def delete(cls, model, database=None, tx=None):
		"""This method deletes a model record in the database. It is best
		practice to assign a sensible default database to the database keyword argument.
		The method also take a transaction id "tx". This is usefull when the delete 
		is operation is one of several delete statements and may need to be rolled back
		if a single delete fails at any point.
		Args:
			cls: definition of the adapter class
			model: BaseMode, model to be deleted in the database
			database: str, optional, database connection that will be used for the delete operation
			tx: str, optional, transaction id that will be used for the delete operation
		Returns:
			None
		"""
		raise NotImplementedError('delete method not implemented for type {}'.format(cls))
		
	@classmethod
	def batchedDelete(cls, models, database=None, tx=None):
		raise NotImplementedError('batchedDelete method not implemented for type {}'.format(cls))