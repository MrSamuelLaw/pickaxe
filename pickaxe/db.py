from __future__ import print_function
import re



class TransactionManager(object):
	"""Context manager for a legacy query. Note that it does
	not work for named queries.
	Args:
		database: str, database the transaction should be begun for
		isolationLevel: enum, optional, defaults to system.db.SERIALIZABLE
		timeout: int, duration in milliseconds the connection should be held for
	Returns: str
	
	Example:
		from pickaxe.db import QueryTransaction
		...
		
		# automagically creates a transaction
		db = 'myDbName'
		with QueryTransaction(db) as tx:
		
			# do an insert
			query = "insert into myTable values (:arg1)"
			params = {'arg1': value1} 
			key = pickaxe.db.runPrepUpdate(query, params, db, getKey=True)
			
			# check if it was a duplicate
			query = "select * from myTable where pk = :key"
			params = {'key': key}
			result = pickaxe.db.runPrepQuery(query, params, db)
			
			if result.getRowCount() > 1:
				system.db.rollbackTransaction(tx)
		# automagically closes a transaction
	"""
	
	_logger = system.util.getLogger('pickaxe.db.TransactionManager')
	
	def __init__(self, databaseOrTxId, isolationLevel=system.db.REPEATABLE_READ, timeout=2000):
		self._databaseOrTxId = databaseOrTxId
		self._isolationLevel = isolationLevel
		self._timeout = timeout
		
	@property
	def tx(self):
		return self._tx
	
	def __enter__(self):
		match = re.search(r'\w+-\w+-\w+-\w+-\w+', self._databaseOrTxId)
		self.isTransactionOwner = bool(match is None)
		self.committedOrRolledBack = False
		if self.isTransactionOwner:
			self._tx = system.db.beginTransaction(
				self._databaseOrTxId,
				self._isolationLevel, 
				self._timeout
			)
			
			msg = '''
				began query transaction for with paramaters:
				database = {}
				isolationLevel = {}
				timeout = {}
				tx = {}
			'''.strip().format(
				self._databaseOrTxId,
				self._isolationLevel,
				self._timeout,
				self._tx
			)
		else:
			self._tx = self._databaseOrTxId
			msg = '''
				continuing existing transaction with tx id = {}
			'''.format(self._databaseOrTxId)
		
		self._logger.debug(msg)
		return self
		
	def __exit__(self, exceptionType, exceptionValue, exceptionTraceback):
		if self.isTransactionOwner:
			if (exceptionType is not None):
				system.db.rollbackTransaction(self._tx)
				msg = '''
					rolled back query transation for with paramaters:
					database = {}
					isolationLevel = {}
					timeout = {},
					tx = {}
				'''.strip().format(
					self._databaseOrTxId,
					self._isolationLevel,
					self._timeout,
					self._tx
				)
				self._logger.debug(msg)
				pickaxe.util.logException(self._logger.error, exceptionValue)
				
			system.db.closeTransaction(self._tx)
			msg = '''
				closed query transation for with paramaters:
				database = {}
				isolationLevel = {}
				timeout = {},
				tx = {}
			'''.strip().format(
				self._databaseOrTxId,
				self._isolationLevel,
				self._timeout,
				self._tx
			)
			self._logger.debug(msg)
			
			if (exceptionType is None and not self.committedOrRolledBack):
				raise AttributeError('transaction was never committed or rolled back')
	
	def commitTransaction(self):
		if self.isTransactionOwner:
			self.committedOrRolledBack = True
			system.db.commitTransaction(self._tx)
		else:
			raise AttributeError('Cannot commit transactions if not the transaction owner')
			
	def rollbackTransaction(self):
		if self.isTransactionOwner:
			self.committedOrRolledBack = True
			system.db.rollbackTransaction(self._tx)
		else:
			raise AttributeError('Cannot rollback transactions if not the transaction owner')


def buildBatchedQuery(query, injectionTemplates, items, sep=', '):
	"""Takes a query an injection template, and items to "build" a query
	that will perform a batch operation.
	
	Args:
		query: str, a query with curly brackets with the word "injection" between them.
		injectionTemplate: list[str] | dict[str, str], a string representing part of a query with the keys using the :format.
		items: iterable[dict], iterable container of items where each item is a dictionary of key, value pairs.
	Returns: tuple(query, params)
		query: str, fully defined query
		params: dict, params to use with the query
	
	Example:
		... code here
		query = '''
			insert into shingle_instantiation_log 
			(
				serialCode,
				isExtruderSide,
				btShingleNumber,
				ttShingleNumber,
				instantiatedTimestamp,
				loggedTimestamp
			) values
			{}
		''''
		injectionTemplate = '''
			(
				:serialCode,
				:isExtruderSide,
				:btShingleNumber,
				:ttShingleNumber,
				:instantiatedTimestamp,
				:loggedTimestamp
			)
		'''
		items = [m.modelDump() for m in models]
		query, params = buildBatchedQuery(query, [injectionTemplate], items)
		with TransactionManager(tx or database) as tx:
			pickaxe.db.runPrepUpdate(query, params, database, tx)
			...
			system.db.commitTransaction(tx)
	"""
	if isinstance(injectionTemplates, (str, unicode)):
		injectionTemplates = [injectionTemplates]
		
	isDict = isinstance(injectionTemplates, dict)
	if not isDict:
		injectionTemplates = {i: t for i, t in enumerate(injectionTemplates)}
	
		
		
	# create a formattable string from the template
	pattern = re.compile(r'(?<=\:)([^0-9]\w+)', flags=re.IGNORECASE)
	for k, injectionTemplate in injectionTemplates.items():
		offset = 0
		for match in pattern.finditer(injectionTemplate):
			group = match.group
			key = group(0)
			start = match.start() - 1
			end = match.end()
			injectionTemplate = injectionTemplate[:start - offset] + '{{{}}}'.format(key) + injectionTemplate[end - offset:]
			offset += ((end - start) - 2 - len(key))
		injectionTemplates[k] = injectionTemplate

	# build the params from the items
	params = {}
	injections = {}
	for k, injectionTemplate in injectionTemplates.items():
		injectionParts = []
		for idx, item in enumerate(items):
			injectionParts.append(injectionTemplate.format(**{k: ':{}{}'.format(k, idx) for k in item.keys()}))
			params.update(**{k + str(idx): v for k, v in item.items()})
		injection = sep.join(injectionParts)
		injections[k] = injection
	
	if isDict:
		query = query.format(**injections)
	else:
		injections = [injections[k] for k in sorted(injections.keys())]
		query = query.format(*injections)
	return query, params


def makePrepQuery(query):
	"""Function that sanitizes a query by replacing keyword args with a "?" character.
	Args:
		query, str, query to sanitize where arguments to inject are formatted ":<argName>"
	
	Returns: Tuple[str, Tuple[str]], where the first string is is the sanitized query and
									 the tuple is a list of the parameter names in order of
									 occurance, including duplicates. The parameter names
									 can then be used to extract values from a dictionary 
									 to pass into a prepared query
	"""
	sanitizedQuery = query
	keys = []
	offset = 0
	pattern = re.compile(r'(?<=\:)([^0-9]\w+)', flags=re.IGNORECASE)
	for match in pattern.finditer(query):
		group = match.group
		key = group(0)
		keys.append(key)
		start = match.start() - 1
		end = match.end()
		sanitizedQuery = sanitizedQuery[:start - offset] + '?' + sanitizedQuery[end - offset:]
		offset += ((end - start) - 1)
	return (sanitizedQuery, keys)


def runPrepQuery(query, args, database, tx=None):
	"""A modified version of runPrepQuery that allows users to pass in a dictionary of
	key value pairs or a list of arguments. When using a dictionary the query needs
	to be formated with the parameter name after a colon. For example "...where id = :id'
		
	Args:
		query: str, query to run.
		args: List[Any] | Dict [str, Any], arguments to pass into the query.
		database: str, The name of the database connection to execute against.
		tx: str | None, default=None, A transaction identifier.
		
	Returns: pyDataSet
	
	Example:
		query = '''
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between :start and :end
			limit 5
		'''
	
		end = system.date.now()
		start = system.date.addHours(end, -1)
		params = {
			'end': system.date.toMillis(end)*1000,
			'start':  system.date.toMillis(start)*1000 
		}
		
		result = runPrepQuery(query, params, database='shingle_tracking')
		...
	"""
	if	isinstance(args, dict):
		query, keys = makePrepQuery(query)
		args = [args[k] for k in keys]
	return system.db.runPrepQuery(query, args, database=database, tx=tx)


def runPrepUpdate(query, args, database, tx=None, getKey=False, skipAudit=False):
	"""A modified version of runPrepUpdate that allows users to pass in a dictionary of
	key value pairs or a list of arguments. When using a dictionary the query needs
	to be formated with the parameter name after a colon. For example "...where id = :id'
		
	Args:
		query: str, query to run.
		args: List[Any] | Dict [str, Any], arguments to pass into the query.
		database: str, The name of the database connection to execute against.
		tx: str | None, default=None, A transaction identifier.
		getKey: bool, default=False, A flag indicating whether or not the result should be 
									 the number of rows returned (getKey=0) or the newly generated 
									 key value that was created as a result of the update (getKey=1). 
									 Not all databases support automatic retrieval of generated keys.
		skipAudit: bool, default=False, A flag which, if set to true, will cause the prep update to 
										skip the audit system. Useful for some queries that have fields 
										which won't fit into the audit log.
		
	Returns: int | Any, number of rows effected or primaryKey if getKey=True
	
	Example:
		Example:
			shingle = CFTShingle(...)
			query = '''
				insert into shingle_instantiation_log (
					serialCode
				) values (
					:serialCode
				)
			'''
			params = shingle.modelDump()  # returns a dict
			result = runPrepQuery(query, params, database='shingle_tracking')
			...
	"""
	if	isinstance(args, dict):
		query, keys = makePrepQuery(query)
		args = [args[k] for k in keys]
	return system.db.runPrepUpdate(query, args, database=database, tx=tx, getKey=getKey, skipAudit=skipAudit)
 