import math


def constrain(x, xLow, xHigh):
    """Returns a number constrained between two values.
    Args:
    	x: int | float
    	xLow: int | float
    	xHigh: int | float
    Returns: int | float
    """
    return min(xHigh, max(xLow, x))


def trapz(xvec, yvec):
    """Performs trapizoidal integration
    Args:
    	xval: List | Tuple [int | float]
    	yval: List | Tuple [int | float]
    Returns: float
    """
    if (len(yvec) == len(xvec)):
        summation = 0
        for i in range(1, len(yvec)):
           y1, y2 = yvec[i-1], yvec[i]
           x1, x2 = xvec[i-1], xvec[i]
           area = (y1 + y2)*(x2-x1)*0.5
           summation += area
        return summation
    else:
        raise ValueError('Vectors must equal length to use trapz')
        
        
def dist(v1, v2):
	"""
	Args:
		v1: List[int | float] where each index represents a coordinate in that direction
		v2: List[int | float] same as v1
	Returns: float
	"""
	
	if (len(v1) == len(v2)):
		return math.sqrt( sum( [abs((x2 - x1))**2 for x2, x1 in zip(v2, v1)] ) )
	else:
		raise ValueError('Vectors must equal length to compute euclidean distance')
		
