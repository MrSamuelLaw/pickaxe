import json
import urllib
from java.net import URI
from java.net.http import HttpClient, HttpRequest, HttpResponse


def appendQueryParameters(url, queryObj):
	"""Returns the url with the query obj serialized and attached
	Args:
		url: str,
		queryObj: Dict | str
	Returns: url with http safe query params
	"""
	if isinstance(queryObj, (str,)):
		query = urllib.urlencode(queryObj)
	elif isinstance(queryObj, (dict,)):
		query = urllib.urlencode({k: json.dumps(v) for k, v in queryObj.items()})
	return url + "?" + query


def buildRequest(url, headers={}, jsonPayload=None, requestType=None):
	"""Builds a java request object
	Args:
		url: str
		header: Dict[str, str]
		jsonPayload: valid json string
		requestType: str, GET | POST | PATCH | DELETE, defaults to GET if jsonPayload is None otherwise POST
		NOTE, manually specifying the requestType is not yet implemented.
	Returns: java.net.http.HttpRequest
	"""
	# create a request from a url, headers, and a json payload
	url = URI.create(url)
	builder = HttpRequest.newBuilder(url)
	for k, v in headers.items():
		builder.header(k, v)
	
	# modify the request type based on payload and requestType	
	if jsonPayload is not None:
		if requestType == 'PATCH':
			builder.method(requestType, HttpRequest.BodyPublishers.ofString(jsonPayload))
		else:
			builder.POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
	elif requestType == 'DELETE':
		raise NotImplementedError('Deleting via scripting is not implemented!')
		
	request = builder.build()
	return request


def sendRequestsAsync(requests, client=HttpClient.newHttpClient(), bodyHandlerFunc=HttpResponse.BodyHandlers.ofString):
	"""Returns a List[CompletableFuture] after starting them
	Args:
		requests: List[java.net.http.HttpRequest]
		client: java.net.http.HttpClient, defaults to HttpClient.newHttpClient()
		bodyHandler: java.net.http.HttpResponse.BodyHandler.<func>, default to HttpResponse.BodyHandlers.ofString
	Returns: List[java.util.concurrent.CompletableFuture]
	"""
	return [client.sendAsync(req, bodyHandlerFunc()) for req in requests]