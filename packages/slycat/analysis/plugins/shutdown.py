# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

def shutdown(connection):
  """Request that the connected coordinator and all workers shut-down.

  Signature: shutdown()

  Note that this is currently an experimental feature, which does not enforce
  any access controls.  Shutting down while other clients are working will
  make you very unpopular!
  """
  connection.coordinator._pyroOneway.add("shutdown")
  connection.coordinator.shutdown()

def register_client_plugin(context):
  context.register_plugin_function("shutdown", shutdown)
