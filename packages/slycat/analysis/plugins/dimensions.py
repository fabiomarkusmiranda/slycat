# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

def register_client_plugin(context):
  import slycat.analysis.plugin.client

  def dimensions(connection, source):
    """Return an array that describe's another array's dimensions.

    Signature: dimensions(source)

    Creates a 1D array with attributes "name", "type", "begin", "end", and
    "chunk-size" and one cell for each of the source array's dimensions.  It is
    particularly useful when working with an array with a large number of
    dimensions.

      >>> scan(dimensions(random((1000, 2000, 3000), (100, 100, 100))))
        {i} name, type, begin, end, chunk-size
      * {0} d0, int64, 0, 1000, 100
        {1} d1, int64, 0, 2000, 100
        {2} d2, int64, 0, 3000, 100
    """
    source = slycat.analysis.plugin.client.require_array(source)
    return connection.create_remote_array("dimensions", [source])
  context.register_plugin_function("dimensions", dimensions)

def register_worker_plugin(context):
  import numpy
  import slycat.analysis.plugin.worker
  def dimensions(factory, worker_index, source):
    return factory.pyro_register(dimensions_array(worker_index, factory.require_object(source)))

  class dimensions_array(slycat.analysis.plugin.worker.array):
    def __init__(self, worker_index, source):
      slycat.analysis.plugin.worker.array.__init__(self, worker_index)
      self.source = source
      self.source_dimensions = None
    def update_dimensions(self):
      if self.source_dimensions is None:
        self.source_dimensions = self.source.dimensions()
    def dimensions(self):
      self.update_dimensions()
      return [{"name":"i", "type":"int64", "begin":0, "end":len(self.source_dimensions), "chunk-size":len(self.source_dimensions)}]
    def attributes(self):
      return [{"name":"name", "type":"string"}, {"name":"type", "type":"string"}, {"name":"begin", "type":"int64"}, {"name":"end", "type":"int64"}, {"name":"chunk-size", "type":"int64"}]
    def iterator(self):
      if self.worker_index == 0:
        return self.pyro_register(dimensions_array_iterator(self))
      else:
        return self.pyro_register(slycat.analysis.plugin.worker.null_array_iterator(self))

  class dimensions_array_iterator(slycat.analysis.plugin.worker.array_iterator):
    def __init__(self, owner):
      slycat.analysis.plugin.worker.array_iterator.__init__(self, owner)
      self.iterations = 0
    def next(self):
      if self.iterations:
        raise StopIteration()
      self.iterations += 1
    def coordinates(self):
      return numpy.array([0], dtype="int64")
    def shape(self):
      self.owner.update_dimensions()
      return numpy.array([len(self.owner.source_dimensions)], dtype="int64")
    def values(self, attribute):
      self.owner.update_dimensions()
      if attribute == 0:
        return numpy.ma.array([dimension["name"] for dimension in self.owner.source_dimensions], dtype="string")
      elif attribute == 1:
        return numpy.ma.array([dimension["type"] for dimension in self.owner.source_dimensions], dtype="string")
      elif attribute == 2:
        return numpy.ma.array([dimension["begin"] for dimension in self.owner.source_dimensions], dtype="int64")
      elif attribute == 3:
        return numpy.ma.array([dimension["end"] for dimension in self.owner.source_dimensions], dtype="int64")
      elif attribute == 4:
        return numpy.ma.array([dimension["chunk-size"] for dimension in self.owner.source_dimensions], dtype="int64")

  context.register_plugin_function("dimensions", dimensions)
