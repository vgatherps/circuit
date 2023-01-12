file(GLOB generated_md_types_HEADERS
        "*.h"
        )
target_sources(cppcuit_lib PRIVATE ${generated_md_types_HEADERS})