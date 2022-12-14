# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_helpers.ipynb.

# %% auto 0
__all__ = ['get_query', 'get_internal_methods']

# %% ../nbs/02_helpers.ipynb 4
def get_query(language, program_lang):
    "Get a query based on the language"
    if program_lang == "python":
        return language.query("""
            (function_definition
                name: (identifier) @func.name)

            (class_definition
                name: (identifier) @class.name)
            """
        )

# %% ../nbs/02_helpers.ipynb 5
def get_internal_methods(file_contents, tokenizer):
    """
    Get all the internal methods in a set of files
    """
    project_content = "\n\n".join(file_contents)
    tree = tokenizer.parser.parse(project_content.encode())
    root_node = tree.root_node
    query = get_query(tokenizer.language, tokenizer.program_lang)
    captures = query.captures(root_node)
    # make sure to ignore dunders
    internal_methods = {node.text.decode() for node, _ in captures if not node.text.decode().startswith("__")}
    return internal_methods
