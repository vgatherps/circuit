Starting work on a project to implement a sort of dataflow circuit.

The circuit exposes a set of inputs and the ability to load views of the output.
One writes a set of inputs, and then calls all dependencies as long as at least one output
was triggered. This is generated from an intermediate representation, and then exposed
to the application at runtime.

Translating to rust and currently making into a standalone library
