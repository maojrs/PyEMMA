'''
This module is used to initialize a global Java VM instance, to run the python
wrapper for the stallone library
Created on 15.10.2013

@author: marscher
'''
from emma2.util.log import getLogger
from scipy.sparse.base import issparse
_log = getLogger(__name__)
# need this for ipython!!!
_log.setLevel(50)
import numpy as _np

"""is the stallone python binding available?"""
stallone_available = False

try:
    _log.debug('try to initialize stallone module')
    from stallone import *
    # TODO: store and read jvm parameters in emma2.cfg
    jenv = initVM(initialheap='32m', maxheap='512m')
    stallone_available = True
    _log.info('stallone initialized successfully.')
except ImportError as ie:
    _log.error('stallone could not be found: %s' % ie)
except ValueError as ve:
    _log.error('java vm initialization for stallone went wrong: %s' % ve)
except BaseException as e:
    _log.error('unknown exception occurred: %s' %e)


def ndarray_to_stallone_array(pyarray):
    """
        Parameters
        ----------
        pyarray : numpy.ndarray or scipy.sparse type one or two dimensional
        
        Returns
        -------
        IDoubleArray or IIntArray depending on input type
        
        Note:
        -----
        scipy.sparse types will be currently converted to dense, before passing
        them to the java side!
    """
    if issparse(pyarray):
        pyarray = pyarray.todense()
    
    shape = pyarray.shape
    dtype = pyarray.dtype
    factory = None
    cast_func = None
    
    if dtype == _np.float32 or dtype == _np.float64:
        factory = API.doublesNew
        cast_func = 'double'
    elif dtype == _np.int32 or dtype == _np.int64:
        factory = API.intsNew
        cast_func = 'int'
    else:
        raise TypeError('unsupported datatype:', dtype)

    if len(shape) == 1:
        # create a JArray wrapper
        jarr = JArray(cast_func)(pyarray)
        if cast_func is 'double':
            return factory.array(jarr[:])
        if cast_func is 'int':
            return factory.arrayFrom(jarr[:])
        raise TypeError('type not mapped to a stallone factory')

    elif len(shape) == 2:
        # TODO: use linear memory layout here, when supported in stallone
        jrows = [ JArray(cast_func)(row[:]) for row in pyarray ]
        jobjectTable = JArray('object')(jrows)
        try:
            # for double arrays
            A = factory.array(jobjectTable)
        except AttributeError:
            # for int 2d arrays
            A = factory.table(jobjectTable)
        return A
    else:
        raise ValueError('unsupported shape:', shape)


def IDoubleArray2ndarray(d_arr):
    rows = d_arr.rows()
    cols = d_arr.columns()
    order = d_arr.order() 
    
    if order < 2:
        arr = _np.array(d_arr.getArray()[:], copy=False)
    elif order == 2:
        arr = _np.array(d_arr.getArray()[:], copy=False)
        arr = arr.reshape((rows, cols))
    else:
        raise NotImplemented
    
    return arr


def stallone_array_to_ndarray(stArray):
    """
    Returns
    -------
    ndarray : 
    
    
    This subclass of numpy multidimensional array class aims to wrap array types
    from the Stallone library for easy mathematical operations.
    
    Currently it copies the memory, because the Python Java wrapper for arrays
    JArray<T> does not suggerate continuous memory layout, which is needed for
    direct wrapping.
    """
    # if first argument is of type IIntArray or IDoubleArray
    if not isinstance(stArray, (IIntArray, IDoubleArray)):
        raise TypeError('can only convert IDouble- or IIntArrays')
    
    dtype = None

    from platform import architecture
    arch = architecture()[0]
    if type(stArray) == IDoubleArray:
        dtype = _np.float64
    elif type(stArray) == IIntArray:
        if arch == '64bit':
            dtype = _np.int64 # long int?
        else:
            dtype = _np.int32

    d_arr = stArray
    rows = d_arr.rows()
    cols = d_arr.columns()
    order = d_arr.order() 
    
    # TODO: support sparse
    #isSparse = d_arr.isSparse()
    
    # construct an ndarray using a slice onto the JArray
    # make sure to always use slices, if you want to access ranges (0:n), else
    # an getter for every single element will be called and you can you will wait for ages.
    if order < 2:
        arr = _np.array(d_arr.getArray()[:], dtype=dtype, copy=False)
    elif order == 2:
        arr = _np.array(d_arr.getArray()[:], dtype=dtype, copy=False)
    else:
        raise NotImplemented
        
    arr = arr.reshape((rows, cols))
    return arr


def list1d_to_java_array(a):
    """
    Converts python list of primitive int or double to java array
    """
    if type(a) is list:
        if type(a[0]) is int:
            return JArray_int(a)
        else:
            return JArray_double(a)
    else:
        raise TypeError("Not a list: "+str(a))


def list_to_jarray(a):
    """
    Converts 1d or 2d python list of primitve int or double to
    java array or nested array
    """
    if type(a) is list:
        if type(a[0]) is int or type(a[0]) is float:
            return list1d_to_java_array(a)
        if type(a[0]) is list:
            n = len(a)
            ja = JArray_object(n)
            for i in range(n):
                ja[i] = list1d_to_java_array(a[i])
            return ja


def jarray(a):
    """
    Converts array-like (python list or ndarray) to java array
    """
    if type(a) is list:
        return list_to_jarray(a)
    elif isinstance(a, _np.ndarray):
        return list_to_jarray(a.tolist())
    else:
        raise TypeError("Type is not supported for conversion to java array")
    
