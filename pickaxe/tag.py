from __future__ import print_function
import re
from itertools import chain
from collections import OrderedDict
from pickaxe.util import getScope


if getScope() in ('designer', 'client'):
	from com.inductiveautomation.ignition.common.tags.paths.parser import TagPathParser
	from com.inductiveautomation.ignition.common.tags.config import BasicTagConfiguration
	from com.inductiveautomation.ignition.common.tags.config.properties import WellKnownTagProps
	from com.inductiveautomation.ignition.common.tags.model import SecurityContext
	from com.inductiveautomation.ignition.common.tags.config import CollisionPolicy
	from com.inductiveautomation.ignition.client.tags.impl import ClientTagManagerImpl


LOGGER = system.util.getLogger('pickaxe_tag')



def readOpc(tagPaths):
	"""Reads tags using system.tag.readBlocking
	and then reads again using system.opc.readValues if the tags
	have an opcServer and an opcItemPath
	
	Args:
		tagPaths: List[str], paths used to read values
	
	Returns: 
		List[QualifiedValue]
	"""
	# create a mapping from the given tagPaths	
	mapping = OrderedDict( ( (p, {'value': None, 'opcServer': None, 'opcItemPath': None}) for p in tagPaths) )
	nodePaths = list( chain(* ((p, p+'.opcServer', p+'.opcItemPath') for p in mapping.keys()) ) )
	nodeValues = system.tag.readBlocking(nodePaths)
	
	# for every node that is not OPC, accept the value and move on
	n = len(nodePaths)/len(mapping)
	for i, (p, m) in enumerate(mapping.items()):
		j = i*n
		qv, opcServer, opcItemPath = nodeValues[j:j+n]
		# log if the quality is bad
		if not qv.getQuality().isGood():
			msg = 'Not good qualified value = {} read using system.tag.readBlocking on tagpath = {}'
			msg = msg.format(qv, p)
			LOGGER.warn(msg)
		if opcServer.value and opcItemPath.value:
			m['opcServer'] = opcServer.value
			m['opcItemPath'] = opcItemPath.value
		else:
			m['value'] = qv
	
	# read the opc server values		
	servers = set((m['opcServer'] for m in mapping.values()))
	if None in servers:
		servers.remove(None)
	for opcServer in servers:
		mapArray = [(p, m) for (p, m) in mapping.items() if m['opcServer'] == opcServer and m['opcItemPath'] is not None]
		qvs = system.opc.readValues(opcServer, [m['opcItemPath'] for (p, m) in mapArray])
		for (p, m), qv in zip(mapArray, qvs):
			if not qv.getQuality().isGood():
				msg = 'Not good qualified value = {} read using system.opc.readValues on server path {} found on tag {}'
				serverPath = '[{}]{}'.format(m['opcServer'], m['opcItemPath'])
				msg = msg.format(qv, serverPath, p)
				LOGGER.warn(msg)
			m['value'] = qv
	
	msg = 'mapping = {}\nnodePaths = {}\nnodeValues = {}'.format(mapping, nodePaths, nodeValues)
	LOGGER.trace(msg)
	
	return [m['value'] for m in mapping.values()]


def writeOpc(tagPaths, values, timeout=45000):
	"""Writes to tags, bypassing the actual tag write in favor of
	writing direction to the opc when possible
	
	Args:
		tagPaths: list[str], paths used to write value
		values: list[any], values to write to the tagpaths
		timeout: ing, duration in milliseconds to write before timing out.
	Returns:
		list[QualityCode], quality code objects, one for each tagpath
	"""
	# create a mapping from the given tagPaths
	mapping = OrderedDict( ( (p, {'value': v, 'opcServer': None, 'opcItemPath': None}) for p, v in zip(tagPaths, values)) )
	nodePaths = list( chain(* ((p+'.opcServer', p+'.opcItemPath') for p in mapping.keys()) ) )
	nodeValues = system.tag.readBlocking(nodePaths)
	
	# get the opc locations
	n = len(nodePaths)/len(mapping)
	for i, m in enumerate(mapping.values()):
		j = i*n
		opcServer, opcItemPath = nodeValues[j:j+n]
		if opcServer.value and opcItemPath.value:
			m['opcServer'] = opcServer.value
			m['opcItemPath'] = opcItemPath.value
	
	# write the opc locations
	qualityCodes = []
	servers = set((m['opcServer'] for m in mapping.values()))
	if None in servers:
		servers.remove(None)
	for opcServer in servers:
		tups = [(m['opcItemPath'], m['value']) for m in mapping.values() if m['opcServer'] == opcServer and m['opcItemPath'] is not None]
		qualityCodes.extend(system.opc.writeValues(opcServer, *zip(*tups)))
		
	# write normal tags
	tups = [(p, m['value']) for p, m in mapping.items() if m['opcServer'] is None]
	if tups:
		qualityCodes.extend(system.tag.writeBlocking(*zip(*tups), timeout=timeout))
	
	return qualityCodes


def readStructuresBlocking(roots, relativeTagPaths, readMethod=system.tag.readBlocking):
	"""Reads tags relative to the roots provided to create datastructures and returns them
	Very useful for reading tag arrays.
	
	Args:
		roots: list[str], root nodes that the relativeTagPaths will be read from.
		relativeTagPaths: list[str], tags that will be read relative to each root node.
		readMethod: callable, must have same call signiture as system.tag.readBlocking
	Returns: 
		list[dict[Any]]
	
	Example:
		roots = ['path/to/my/folder1', 'path/to/my/folder2']
		relativeTagPaths = [
				'fatalBits',
				'serialCode',
				'isExtruderSide',
				'btShingleNumber',
				'ttShingleNumber',
				'instantiatedTimestamp',
		]
		items = readStructuresBlocking(roots, relativeTagPaths)
		print(items[0]['fatalBits'].value)  # note, we have to call .value as the items are qualified values
	"""
	paths = [r + '/' + rtp for r in roots for rtp in relativeTagPaths]
	qvals = readMethod(paths)
	stride = len(relativeTagPaths)
	objects = [{rtp: qv for rtp, qv in zip(relativeTagPaths, qvals[i*stride: (i+1)*stride])} for i, r in enumerate(roots)]
	return objects
	
	
def writeStructuresBlocking(roots, dicts, writeMethod=system.tag.writeBlocking):
	"""Writes object to tags using dicts that map relative tag paths to values
	Args:
		roots: list[str], root nodes for writing data strucuctures
		dicts: list[dict[tagpath, Any]], list of tagpath: value mappings for each structure
		writeMethod: callable, must have the same call signiture as system.tag.writeBlocking
		
	Examples:
		roots = ['path/to/folder1', 'path/to/folder2']
		relativeTagPaths = ['x1', 'x2']
		objects = pickaxe.tag.readStructuresBlocking(roots, relativeTagPaths)
		
		# modify the value
		objects[0]['x1'].value = 0
		
		# write it back
		pickaxe.tag.writeStructuresBlocking(roots, objects)
	"""
	relativeTagPaths = dicts[0].keys()
	paths = [r + '/' + rtp for r in roots for rtp in relativeTagPaths]
	values = list(chain(*[[obj[rtp] for rtp in relativeTagPaths] for obj in objects]))
	return writeMethod(paths, values)


def getContext():
	"""Returns the current context object it the context is either the designer or vision client. 
	Code originally found at https://forum.inductiveautomation.com/t/project-properties-in-python/7762/2
	"""
		
	def resolveDesignerContext():
		"""Return designer context.
		"""
		from com.inductiveautomation.ignition.designer import IgnitionDesigner
		# Note, there is an error in the documentation, getFrame returns an instance of IgnitionDesigner
		return IgnitionDesigner.getFrame().getContext()
		
	def resolveClientContext():
		"""Attempt to resolve client context.
		By creating a frame it prevents the need to
		traverse the object heirarchy. i.e. parent.parent....
		"""
		from com.inductiveautomation.factorypmi.application.runtime import ClientPanel
		# acquire project name.
		projName = system.util.getProjectName()
		# Frame title.
		frame_name = 'ThrowAway'
		# Create disposable top level frame object.
		frm = JFrame(frame_name)
		# Adjust close behavior.
		frm.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
		# get the windows.
		windows = frm.getWindows()
		# cleanup frame.
		frm.dispose()
		# iterate windows, filter on the title containing the project name.
		for window in windows:
			if projName in window.getTitle():
				pane =  window.getContentPane()
				# Compare the content pane instance 
				# to the ClientPanel object.
				if isinstance(pane, ClientPanel):
					if hasattr(pane, 'getClientContext'):
						return pane.getClientContext()
	
	scope = getScope()
	if scope == 'client':
		context = resolveClientContext()
	elif scope == 'designer':
		context = resolveDesignerContext()
	else:
		msg = "Cannot get context for current scope {}. Supported scopes are 'designer' or 'client'."
		msg = msg.format(scope)
		raise RuntimeError(msg)
	
	return context


def createMemoryTag(path, tagObjectType, dataType, collisionPolicy=None):
	"""Creates a new tag at the given path location.
	Args:
		path: str
		tagObjectType: com.inductiveautomation.ignition.common.tags.config.types.TagObjectType
		dataType: com.inductiveautomation.ignition.common.sqltags.model.types.DataType
	"""
	if collisionPolicy is None:
		collisionPolicy = CollisionPolicy.Abort
	
	manager = ClientTagManagerImpl(getContext())
	path = TagPathParser.parse(path)
	tagConfig = BasicTagConfiguration.createNew(path)
	tagConfig.setType(tagObjectType)
	tagConfig.set(WellKnownTagProps.ValueSource, WellKnownTagProps.MEMORY_TAG_TYPE)
	tagConfig.set(WellKnownTagProps.DataType, dataType)
	manager.saveTagConfigsAsync([tagConfig], collisionPolicy, SecurityContext.emptyContext())


def getProvider(tagPath):
	"""Returns the provider name in the tag path.
	Raises and exception if the provider is not in the tag path
	
	Args:
		tagPath: str | TagPath, path to the tag
	
	Returns:
		str
	"""
	provider = re.search(r'(?<=^\[)\w+(?=\])', str(tagPath)).group(0)
	return provider


def getParentPath(path):
	"""Returns the parent for a path
	Args:
		path: str, must contain a provider
	Returns: path: str
	"""
	path = TagPathParser.parse(path)
	return str(path.getParentPath())
