# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.
import math
import slycat.web.client
import StringIO
import sys

parser = slycat.web.client.option_parser()
parser.add_option("--bundling", type="int", default=10, help="Maximum number of rows to bundle into a single request.  Default: %default")
parser.add_option("--file", default="-", help="Input CSV file.  Use - for stdin.  Default: %default")
parser.add_option("--input", default=[], action="append", help="Input column.  Use an --input argument for each input column.")
parser.add_option("--marking", default="", help="Marking type.  Default: %default")
parser.add_option("--model-description", default="", help="New model description.  Default: %default")
parser.add_option("--model-name", default="CSV-to-CCA", help="New model name.  Default: %default")
parser.add_option("--output", default=[], action="append", help="Input column.  Use an --input argument for each input column.")
parser.add_option("--project", default=None, help="Name of an existing project.  Default: create a new project.")
parser.add_option("--project-description", default="", help="New project description.  Default: %default")
parser.add_option("--project-name", default="CSV-to-CCA", help="New project name.  Default: %default")
parser.add_option("--scale-inputs", default=False, action="store_true", help="Enable input scaling.")
options, arguments = parser.parse_args()

stream = sys.stdin if options.file == "-" else open(options.file, "r")
rows = [row.split(",") for row in stream]
column_names = [name.strip() for name in rows[0]]
column_types = ["double" for name in column_names]
column_count = len(column_names)
rows = rows[1:]

skip_rows = set()
for row_index, row in enumerate(rows):
  for index, field in enumerate(row[:column_count]):
    try:
      value = float(field)
      if math.isnan(value):
        skip_rows.add(row_index)
    except:
      column_types[index] = "string"

rows = [row for row_index, row in enumerate(rows) if row_index not in skip_rows]

for index, type in enumerate(column_types):
  if type == "string":
    continue
  for row in rows:
    row[index] = float(row[index])

inputs = [column_names.index(input) for input in options.input]
outputs = [column_names.index(output) for output in options.output]
if len(inputs) < 1:
  raise Exception("You must specify at least one input column.")
if len(outputs) < 1:
  raise Exception("You must specify at least one output column.")
for input in inputs:
  if not (0 <= input and input < column_count):
    raise Exception("Input column out of range: %s" % input)
  if column_types[input] != "double":
    raise Exception("Cannot analyze non-numeric input: %s" % input)
for output in outputs:
  if not (0 <= output and output < column_count):
    raise Exception("Output column out of range: %s" % output)
  if column_types[output] != "double":
    raise Exception("Cannot analyze non-numeric output: %s" % output)

connection = slycat.web.client.connect(options)

pid = connection.find_or_create_project(options.project, options.project_name, options.project_description)
mwid = connection.create_cca_model_worker(pid, options.model_name, options.marking, options.model_description)
connection.start_table(mwid, "data-table", column_names,column_types)
for row_start in range(0, len(rows), options.bundling):
  connection.send_table_rows(mwid, "data-table", rows[row_start:row_start + options.bundling])
connection.finish_table(mwid, "data-table")
connection.set_parameter(mwid, "input-columns", inputs)
connection.set_parameter(mwid, "output-columns", outputs)
connection.set_parameter(mwid, "scale-inputs", options.scale_inputs)
mid = connection.finish_model(mwid)
#connection.delete_worker(mwid, stop=False)

sys.stderr.write("Your new model will be at %s/models/%s when complete.\n" % (options.host, mid))
