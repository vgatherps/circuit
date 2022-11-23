TREE_PATH = pycircuit/example
DUMP_TAIL = example/example_gen
DUMP = pycircuit/$(DUMP_TAIL)
TREE_NAME = "Tree"

$(DUMP)/:
	cd pycircuit && mkdir -p $(DUMP_TAIL)

$(DUMP)/circuit.json: $(DUMP)/
	python3 -m pycircuit.example.tree | python -m json.tool > $(DUMP)/circuit_temp.json && mv $(DUMP)/circuit_temp.json $(DUMP)/circuit.json

$(DUMP)/tree.hh: $(DUMP)/circuit.json
	python3 -m pycircuit.loader.write_circuit_struct \
	--loader-config $(TREE_PATH)/loader.json \
	--circuit-json $(DUMP)/circuit.json \
	--struct-name Tree \
	| clang-format \
	> $(DUMP)/tree.hh

$(DUMP)/root_call.cc: $(DUMP)/circuit.json
	python3 -m pycircuit.loader.write_circuit_call \
	--loader-config $(TREE_PATH)/loader.json \
	--circuit-json $(DUMP)/circuit.json \
	--call-name root_call \
	--struct-name Tree \
	--struct-header tree.hh \
	| clang-format \
	> $(DUMP)/root_call.cc
        
.PHONY: tree
tree: $(DUMP)/tree.hh $(DUMP)/root_call.cc $(DUMP)/circuit.json
	echo