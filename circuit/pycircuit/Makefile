TREE_PATH = pycircuit/example
DUMP_TAIL = example/example_gen
DUMP = pycircuit/$(DUMP_TAIL)
TREE_NAME = "Tree"

$(DUMP)/:
	cd pycircuit && mkdir -p $(DUMP_TAIL)

tree_circuit: $(DUMP)/
	python3 -m pycircuit.example.tree | python -m json.tool > $(DUMP)/circuit.json

root_call: $(DUMP)/circuit.json
	python3 -m pycircuit.loader.write_circuit_call \
	--loader-config $(TREE_PATH)/loader.json \
	--circuit-json $(DUMP)/circuit.json \
	--call-name root_call \
	--struct-name Tree \
	| clang-format \
	> $(DUMP)/root_call.cc
        