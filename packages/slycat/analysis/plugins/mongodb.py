# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

from __future__ import division

def register_client_plugin(context):
  try:
    import pymongo
    import slycat.analysis.plugin.client

    def mongodb(connection, database, collection, attributes=None, chunk_size=None, samples=(0, 1000), host="localhost", port=27017):
      """Load an array from a MongoDB database.

      Signature: mongodb(database, collection, attributes=None, chunk_size=None, samples=(0, 1000), host="localhost", port=27017)

      Returns a 1D array containing one-or-more attributes from every record in
      a collection.  Use the required "database" and "collection" parameters to
      specify the collection to load.

      If the "attributes" parameter is None (the default), the collection is
      sampled to determine the names and types of attributes in the output
      array.  Use the "samples" parameter to specify a range of collection
      documents to sample, or "None" to sample from the entire collection.

      Otherwise, the "attributes" parameter defines a set of attributes to be loaded
      from each document in the collection, and may be a single string attribute name,
      a single tuple containing attribute name and type, a sequence of attribute names,
      or a sequence of name/type tuples.

      Note that MongoDB is a "schema-less" database: there is no guarantee that
      a given field will appear in every document, or even that it will have a
      consistent type, so you should be prepared to encounter null and NaN
      values in the output array attributes.

      >>> zips = mongodb("test", "zips")

      >>> zips
      <29467 element remote array with dimension: i and attributes: city, state, _id, pop>

      >>> scan(attributes(zips))
        {i} name, type
      * {0} city, string
        {1} state, string
        {2} _id, string
        {3} pop, int64

      >>> states = mongodb("test", "zips", ("state","string"))

      >>> states
      <29467 element remote array with dimension: i and attribute: state>

      >>> scan(aggregate(states, ["min", "max", "distinct"]))
        {i} min_state, max_state, distinct_state
      * {0} AK, WY, 51
      """
      if not isinstance(database, basestring):
        raise slycat.analysis.plugin.client.InvalidArgument("Database name must be a string.")
      if not isinstance(collection, basestring):
        raise slycat.analysis.plugin.client.InvalidArgument("Collection name must be a string.")
      if attributes is not None:
        attributes = slycat.analysis.plugin.client.require_attributes(attributes)
      if chunk_size is not None:
        chunk_size = slycat.analysis.plugin.client.require_chunk_size(chunk_size)
      if samples is not None:
        if not isinstance(samples, tuple) or len(samples) != 2:
          raise slycat.analysis.plugin.client.InvalidArgument("Samples must be a 2-tuple.")
      if not isinstance(host, basestring):
        raise slycat.analysis.plugin.client.InvalidArgument("Host name must be a string.")
      if not isinstance(port, int):
        raise slycat.analysis.plugin.client.InvalidArgument("Port must be an integer.")
      return connection.create_remote_array("mongodb", [], host, port, database, collection, attributes, chunk_size, samples)
    context.register_plugin_function("mongodb", mongodb)
  except:
    pass

def register_worker_plugin(context):
  try:
    import numpy
    import os
    import pymongo
    import slycat.analysis.plugin.worker

    def mongodb(factory, worker_index, host, port, database, collection, attributes, chunk_size, samples):
      return factory.pyro_register(mongodb_array(worker_index, host, port, database, collection, attributes, chunk_size, samples))

    class mongodb_array(slycat.analysis.plugin.worker.array):
      def __init__(self, worker_index, host, port, database, collection, attributes, chunk_size, samples):
        slycat.analysis.plugin.worker.array.__init__(self, worker_index)
        self.host = host
        self.port = port
        self.database = database
        self.collection = collection
        self.chunk_size = chunk_size
        self.samples = samples

        self.record_count = None
        self.output_attributes = attributes

      def update_dimensions(self):
        if self.record_count is None:
          self.record_count = pymongo.MongoClient(self.host, self.port)[self.database][self.collection].count()

        if self.chunk_size is None:
          self.chunk_size = int(numpy.ceil(self.record_count / self.worker_count))

      def update_attributes(self):
        if self.output_attributes is None:
          keys = set()
          self.output_attributes = []
          cursor = pymongo.MongoClient(self.host, self.port)[self.database][self.collection].find()
          if self.samples is not None:
            cursor = cursor[self.samples[0]:self.samples[1]]
          for document in cursor:
            for key in document:
              if key not in keys:
                value = document[key]
                if isinstance(value, basestring):
                  keys.add(key)
                  self.output_attributes.append({"name":key,"type":"string"})
                elif isinstance(value, float):
                  keys.add(key)
                  self.output_attributes.append({"name":key,"type":"float64"})
                elif isinstance(value, int):
                  keys.add(key)
                  self.output_attributes.append({"name":key,"type":"int64"})
                elif isinstance(value, long):
                  keys.add(key)
                  self.output_attributes.append({"name":key,"type":"int64"})
                elif isinstance(value, bool):
                  keys.add(key)
                  self.output_attributes.append({"name":key,"type":"bool"})

      def dimensions(self):
        self.update_dimensions()
        return [{"name":"i", "type":"int64", "begin":0, "end":self.record_count, "chunk-size":self.chunk_size}]
      def attributes(self):
        self.update_attributes()
        return self.output_attributes
      def iterator(self):
        self.update_attributes()
        self.update_dimensions()
        return self.pyro_register(mongodb_array_iterator(self))

    class mongodb_array_iterator(slycat.analysis.plugin.worker.array_iterator):
      def __init__(self, owner):
        slycat.analysis.plugin.worker.array_iterator.__init__(self, owner)
        self.chunk_index = -1
      def next(self):
        self.chunk_index += 1
        while (self.chunk_index % self.owner.worker_count) != self.owner.worker_index:
          self.chunk_index += 1

        begin = self.chunk_index * self.owner.chunk_size
        if begin > self.owner.record_count:
          raise StopIteration()
        end = (self.chunk_index + 1) * self.owner.chunk_size

        output_values = [[] for attribute in self.owner.output_attributes]
        document_count = 0
        cursor = pymongo.MongoClient(self.owner.host, self.owner.port)[self.owner.database][self.owner.collection].find()[begin:end]
        for document in cursor:
          document_count += 1
          for index, attribute in enumerate(self.owner.output_attributes):
            output_values[index].append(document.get(attribute["name"], None))

        self.output_values = []
        for attribute, raw_values in zip(self.owner.output_attributes, output_values):
          if attribute["type"] == "string":
            self.output_values.append(numpy.ma.array(["" if value is None else value for value in raw_values], mask=[value is None for value in raw_values], dtype="string"))
          elif attribute["type"] == "float64":
            values = numpy.ma.empty(len(raw_values), dtype="float64")
            for index, value in enumerate(raw_values):
              try:
                values[index] = float(value)
              except:
                values[index] = numpy.ma.masked
            self.output_values.append(values)
          elif attribute["type"] == "int64":
            values = numpy.ma.empty(len(raw_values), dtype="int64")
            for index, value in enumerate(raw_values):
              try:
                values[index] = int(value)
              except:
                values[index] = numpy.ma.masked
            self.output_values.append(values)
          elif attribute["type"] == "bool":
            self.output_values.append(numpy.ma.array(raw_values, dtype="bool"))
          else:
            raise Exception("Unsupported attribute type: %s" % attribute["type"])

      def coordinates(self):
        return numpy.array([self.chunk_index * self.owner.chunk_size], dtype="int64")
      def shape(self):
        return numpy.array([self.output_values[0].shape[0]], dtype="int64")
      def values(self, index):
        return self.output_values[index]
    context.register_plugin_function("mongodb", mongodb)
  except:
    pass
