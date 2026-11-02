"""Contiguous, growable numeric streams with stable exported snapshots.

Keep float64 construction and int64 topology until the existing native encoder
chooses its engine formats. No quantization, vertex welding or seam changes.
"""
from array import array
import numpy as np


class Stream:
    def __init__(self,code,dtype):
        self.code,self.dtype=code,np.dtype(dtype)
        self.data=array(code)
        self.shared=False
        if self.data.itemsize!=self.dtype.itemsize:raise RuntimeError('numeric stream item size mismatch')

    def _writable(self):
        if self.shared:
            self.data=array(self.code,self.data)
            self.shared=False

    def extend(self,values):
        self._writable()
        if isinstance(values,np.ndarray):
            source=np.ascontiguousarray(values,self.dtype)
            self.data.frombytes(memoryview(source).cast('B'))
        else:self.data.extend(values)

    def append(self,value):
        self._writable();self.data.append(value)

    def reserve(self,count):
        self._writable();start=len(self.data)
        self.data.frombytes(bytes(count*self.dtype.itemsize))
        return start

    def write(self,offsets,values):
        self._writable()
        np.frombuffer(self.data,dtype=self.dtype)[offsets]=values

    def view(self):
        self.shared=True
        return np.frombuffer(self.data,dtype=self.dtype)

    def __iadd__(self,values):self.extend(values);return self
    def __len__(self):return len(self.data)
    def __iter__(self):return iter(self.data)
    def __getitem__(self,key):return self.data[key]
    def __eq__(self,other):
        if isinstance(other,Stream):return self.dtype==other.dtype and self.data==other.data
        return NotImplemented
