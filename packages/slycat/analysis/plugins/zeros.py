# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

def register_client_plugin(context):
  import slycat.analysis.plugin.client

  def zeros(connection, shape, chunk_sizes=None, attributes="val"):
    """Return an array of all zeros.

    Signature: zeros(shape, chunk_sizes=None, attributes="val")

    Creates an array with the given shape and chunk sizes, with one-or-more
    attributes filled with zeros.

    The shape parameter must be an int or a sequence of ints that specify the
    size of the array along each dimension.  The chunk_sizes parameter must an int
    or sequence of ints that specify the maximum size of an array chunk along
    each dimension, and must match the number of dimensions implied by the
    shape parameter.  If the chunk_sizes parameter is None (the default), the chunk
    sizes will be identical to the array shape, i.e. the array will have a
    single chunk.  This may be impractical for large arrays, and prevents the
    array from being distributed across multiple remote workers.

    The attributes parameter may be a string attribute name, a tuple containing
    attribute name and type, a sequence of attribute names, or a sequence of
    name/type tuples.

      >>> scan(attributes(zeros(4)))
        {i} name,type
      * {0} val,float64

      >>> scan(dimensions(zeros(4)))
        {i} name,type,begin,end,chunk-size
      * {0} d0,int64,0,4,4

      >>> scan(zeros(4))
        {d0} val
      * {0} 0.0
        {1} 0.0
        {2} 0.0
        {3} 0.0

      >>> scan(zeros(4, 2))
        {d0} val
      * {0} 0.0
        {1} 0.0
      * {2} 0.0
        {3} 0.0

      >>> scan(dimensions(zeros((4, 4), (2, 2))))
        {i} name,type,begin,end,chunk-size
      * {0} d0,int64,0,4,2
        {1} d1,int64,0,4,2

      >>> scan(zeros((4, 4), (2, 2)))
        {d0,d1} val
      * {0,0} 0.0
        {0,1} 0.0
        {1,0} 0.0
        {1,1} 0.0
      * {0,2} 0.0
        {0,3} 0.0
        {1,2} 0.0
        {1,3} 0.0
      * {2,0} 0.0
        {2,1} 0.0
        {3,0} 0.0
        {3,1} 0.0
      * {2,2} 0.0
        {2,3} 0.0
        {3,2} 0.0
        {3,3} 0.0
    """
    shape = slycat.analysis.plugin.client.require_shape(shape)
    chunk_sizes = slycat.analysis.plugin.client.require_chunk_sizes(shape, chunk_sizes)
    attributes = slycat.analysis.plugin.client.require_attributes(attributes)
    if len(attributes) < 1:
      raise slycat.analysis.plugin.client.InvalidArgument("zeros() requires at least one attribute.")
    return connection.create_remote_array("zeros", [], shape, chunk_sizes, attributes)
  context.register_plugin_function("zeros", zeros)

def register_worker_plugin(context):
  import numpy
  import slycat.analysis.plugin.worker

  def zeros(factory, worker_index, shape, chunk_sizes, attributes):
    return factory.pyro_register(zeros_array(worker_index, shape, chunk_sizes, attributes))

  class zeros_array(slycat.analysis.plugin.worker.array):
    def __init__(self, worker_index, shape, chunk_sizes, attributes):
      slycat.analysis.plugin.worker.array.__init__(self, worker_index)
      self.shape = shape
      self.chunk_sizes = chunk_sizes
      self._attributes = attributes
    def dimensions(self):
      return [{"name":"d%s" % index, "type":"int64", "begin":0, "end":dimension, "chunk-size":chunk_size} for index, (dimension, chunk_size) in enumerate(zip(self.shape, self.chunk_sizes))]
    def attributes(self):
      return self._attributes
    def iterator(self):
      return self.pyro_register(zeros_array_iterator(self))

  class zeros_array_iterator(slycat.analysis.plugin.worker.array_iterator):
    def __init__(self, owner):
      slycat.analysis.plugin.worker.array_iterator.__init__(self, owner)
      self.iterator = slycat.analysis.plugin.worker.worker_chunks(owner.shape, owner.chunk_sizes, len(owner.siblings))
    def next(self):
      while True:
        chunk_index, worker_index, begin, end = self.iterator.next()
        if worker_index == self.owner.worker_index:
          self._coordinates = begin
          self._shape = end - begin
          break
    def coordinates(self):
      return self._coordinates
    def shape(self):
      return self._shape
    def values(self, index):
      return numpy.ma.zeros(self._shape, dtype=self.owner._attributes[index]["type"])
  context.register_plugin_function("zeros", zeros)


