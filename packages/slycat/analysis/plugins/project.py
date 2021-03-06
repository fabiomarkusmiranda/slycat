# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

def register_client_plugin(context):
  import slycat.analysis.plugin.client

  def project(connection, source, *attributes):
    """Return an array with fewer attributes.

    Signature: project(source, *attributes)

    Creates an array that contains a subset of a source array's attributes.
    Specify the attributes to be retained by passing one-or-more attribute
    indices / names as parameters to project().  Attributes may be specified in
    any order.

    Note that it is also possible to duplicate attributes with project(),
    although working with idenically-named attributes downstream can be
    confusing.

      >>> autos = load("../data/automobiles.csv", schema="csv-file", chunk_size=100)

      >>> scan(attributes(autos))
        {i} name, type
      * {0} Model, string
        {1} Origin, string
        {2} Year, string
        {3} Cylinders, string
        {4} Acceleration, string
        {5} Displacement, string
        {6} Horsepower, string
        {7} MPG, string

      >>> project(autos, "Year", "MPG")
      <406 element remote array with dimension: i and attributes: Year, MPG>

      >>> project(autos, 1, 3, 2)
      <406 element remote array with dimension: i and attributes: Origin, Cylinders, Year>
    """
    source = slycat.analysis.plugin.client.require_array(source)
    if not len(attributes):
      raise slycat.analysis.plugin.client.InvalidArgument("project() operator requires at least one attribute.")
    return connection.create_remote_array("project", [source], attributes)
  context.register_plugin_function("project", project)

def register_worker_plugin(context):
  import slycat.analysis.plugin.worker
  def project(factory, worker_index, source, attributes):
    return factory.pyro_register(project_array(worker_index, factory.require_object(source), attributes))

  class project_array(slycat.analysis.plugin.worker.array):
    def __init__(self, worker_index, source, attributes):
      slycat.analysis.plugin.worker.array.__init__(self, worker_index)
      self.source = source
      source_attributes = self.source.attributes()
      source_map = dict([(i, i) for i in range(len(source_attributes))] + [(attribute["name"], index) for index, attribute in enumerate(source_attributes)])
      self.indices = [source_map[attribute] for attribute in attributes if attribute in source_map]
    def dimensions(self):
      return self.source.dimensions()
    def attributes(self):
      source_attributes = self.source.attributes()
      return [source_attributes[index] for index in self.indices]
    def iterator(self):
      return self.pyro_register(project_array_iterator(self, self.source, self.indices))

  class project_array_iterator(slycat.analysis.plugin.worker.array_iterator):
    def __init__(self, owner, source, indices):
      slycat.analysis.plugin.worker.array_iterator.__init__(self, owner)
      self.iterator = source.iterator()
      self.indices = indices
    def __del__(self):
      self.iterator.release()
    def next(self):
      self.iterator.next()
    def coordinates(self):
      return self.iterator.coordinates()
    def shape(self):
      return self.iterator.shape()
    def values(self, attribute):
      return self.iterator.values(self.indices[attribute])
  context.register_plugin_function("project", project)
