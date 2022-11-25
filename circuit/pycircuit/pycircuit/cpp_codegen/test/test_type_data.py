from pycircuit.cpp_codegen.test.test_common import basic_annotated
from pycircuit.cpp_codegen.type_data import get_class_declaration_type_for


# TODO move to higher level test directory
def test_get_class_declaration_type_for():
    annotated = basic_annotated()

    assert (
        get_class_declaration_type_for(annotated)
        == annotated.component.definition.class_name
    )

    annotated.class_generics = "<T>"

    assert (
        get_class_declaration_type_for(annotated)
        == f"{annotated.component.definition.class_name}<T>"
    )
