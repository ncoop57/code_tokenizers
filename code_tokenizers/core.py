# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['unroll_node_types', 'traverse', 'get_token_type', 'CodeTokenizer']

# %% ../nbs/00_core.ipynb 2
import code_tokenizers
import json

from transformers import AutoTokenizer
from tree_sitter import Language, Parser

# %% ../nbs/00_core.ipynb 4
def unroll_node_types(
    nested_node_types: dict, # node_types from tree-sitter
) -> list: # list of node types
    """Unroll nested node types into a flat list of node types. This includes subtypes as well."""
    node_types = [node_type["type"] for node_type in nested_node_types]
    node_subtypes = [
        node_subtype["type"]
        for node_type in node_types
        if "subtypes" in node_type
        for node_subtype in node_type["subtypes"]
    ]
    return list(set(node_types + node_subtypes))

# %% ../nbs/00_core.ipynb 5
# From: https://github.com/github/CodeSearchNet/tree/master/function_parser
def traverse(
    node,       # tree-sitter node
    results,    # list to append results to
) -> None:
    """Traverse in a recursive way, a tree-sitter node and append results to a list."""
    if node.type == 'string':
        results.append(node)
        return
    for n in node.children:
        traverse(n, results)
    if not node.children:
        results.append(node)

# %% ../nbs/00_core.ipynb 6
def get_token_type(
    tok_span: tuple,        # (start, end) position of a token
    nodes: list,            # list of tree-sitter nodes
    lines: list,            # list of lines in the code
    internal_methods: list, # list of internal methods
) -> tuple:                 # (parent_type, token_type) of the token
    """Get the parent AST type and token AST type of a token."""
    def get_node_span(node):
        def convert_to_offset(point):
            row, column = point
            chars_in_rows = sum(map(len, lines[:row])) + row
            chars_in_columns = len(lines[row][:column])

            offset = chars_in_rows + chars_in_columns
            return offset
        start_span = convert_to_offset(node.start_point)
        end_span = convert_to_offset(node.end_point)
        return start_span, end_span
    
    node_spans = [get_node_span(node) for node in nodes]
    for i, span in enumerate(node_spans):
        if (span[0] <= tok_span[0] and tok_span[0] < span[1]) or (span[0] < tok_span[1] and tok_span[1] <= span[1]):
            is_internal = nodes[i].text.decode() in internal_methods
            return nodes[i].parent.type, nodes[i].type, is_internal

# %% ../nbs/00_core.ipynb 7
class CodeTokenizer():
    """A tokenizer for code, which aligns the tokens with the AST nodes."""
    def __init__(
        self,
        tokenizer,          # transformers tokenizer
        parser,             # tree-sitter parser
        language,           # tree-sitter language
        node_types,         # list of node types
        name_or_path,       # name or path of the tokenizer
        program_lang,       # programming language of the tokenizer
        padding_token,  # whether to add a padding token
    ):
        self.tokenizer = tokenizer
        self.parser = parser
        self.language = language
        self.node_types = node_types
        self.name_or_path = name_or_path
        self.program_lang = program_lang
        self.padding_token = padding_token
    
    def parse_tree(
        self,
        code,               # code to parse
        offset_mapping,     # offset mapping from the tokenizer to align the tokens with the AST nodes
        internal_methods,   # internal methods to parse the code
    ):                      # returns a list of AST ids and a list of parent AST ids
        tree = self.parser.parse(bytes(code, "utf8"))
        nodes = []
        traverse(tree.root_node, nodes)

        ast_ids = []
        parent_ast_ids = []
        is_internal_methods = []
        for i, (start, end) in enumerate(offset_mapping):
            if start == None or end == None:
                ast_ids.append(-1)
                parent_ast_ids.append(-1)
                continue
            type_info = get_token_type(
                (start, end),
                nodes,
                code.split("\n"),
                internal_methods
            )
            if type_info is None:
                ast_ids.append(-1)
                parent_ast_ids.append(-1)
                is_internal_methods.append(False)
            else:
                parent_node_type, node_type, is_internal = type_info
                try:
                    ast_ids.append(self.node_types.index(node_type))
                    parent_ast_ids.append(self.node_types.index(parent_node_type))
                    is_internal_methods.append(is_internal)
                except Exception as e:
                    print(type_info)
                    print(code)
                    ast_ids.append(-1)
                    parent_ast_ids.append(-1)
                    is_internal_methods.append(False)
                    raise e

        return ast_ids, parent_ast_ids, is_internal_methods
    
    def __call__(
        self,
        code,                   # code or list of code to tokenize
        internal_methods=[],    # list of internal methods to check against
        return_merged=True,     # whether to string representations of the merged ASTs and parent ASTs
        **kwargs                # kwargs for the underlying transformers tokenizer
    ):                          # returns a dictionary of token ids, attention masks, AST ids, parent AST ids, and optionally the string representations of the merged ASTs and parent ASTs
        encoding = self.tokenizer(code, return_offsets_mapping=True, **kwargs)
        if isinstance(code, list):
            encoding["ast_ids"] = []
            encoding["parent_ast_ids"] = []
            encoding["is_internal_methods"] = []
            for i, c in enumerate(code):
                ast_ids, parent_ast_ids, is_internal_methods = self.parse_tree(c, encoding["offset_mapping"][i], internal_methods)
                encoding["ast_ids"].append(ast_ids)
                encoding["parent_ast_ids"].append(parent_ast_ids)
                encoding["is_internal_methods"].append(is_internal_methods)
        else:
            encoding["ast_ids"], encoding["parent_ast_ids"], encoding["is_internal_methods"] = self.parse_tree(code, encoding["offset_mapping"], internal_methods)
        
        if return_merged:
            # Merge the AST ids with their parent AST ids and use the names instead of the ids
            if isinstance(code, list):
                encoding["merged_ast"] = []
                for parent_ast_ids, ast_ids, is_internals in zip(encoding["parent_ast_ids"], encoding["ast_ids"], encoding["is_internal_methods"]):
                    merged_ast = []
                    for i, (parent_ast_id, ast_id, is_internal) in enumerate(zip(parent_ast_ids, ast_ids, is_internals)):
                        if parent_ast_id == -1 or ast_id == -1:
                            merged_ast.append("< N/A >")
                        else:
                            if is_internal:
                                merged_ast.append(
                                    f"<{self.node_types[parent_ast_id]} -> {self.node_types[ast_id]} (internal)>"
                                )
                            else:
                                merged_ast.append(
                                    f"<{self.node_types[parent_ast_id]} -> {self.node_types[ast_id]}>"
                                )

                    encoding["merged_ast"].append(merged_ast)
            else:
                encoding["merged_ast"] = []
                for parent_ast_id, ast_id, is_internal in zip(encoding["parent_ast_ids"], encoding["ast_ids"], encoding["is_internal_methods"]):
                    if parent_ast_id == -1 or ast_id == -1:
                        encoding["merged_ast"].append("< N/A >")
                    else:
                        if is_internal:
                            encoding["merged_ast"].append(
                                f"<{self.node_types[parent_ast_id]} -> {self.node_types[ast_id]} (internal)>"
                            )
                        else:
                            encoding["merged_ast"].append(
                                f"<{self.node_types[parent_ast_id]} -> {self.node_types[ast_id]}>"
                            )

        return encoding
    
    def decode(self, *args, **kwargs):
        return self.tokenizer.decode(*args, **kwargs)

    @staticmethod
    def from_pretrained(
        name_or_path: str,          # name or path of the tokenizer
        program_lang: str,          # language of the tokenizer
        padding_token: str = None,  # padding token to use
    ):                              # CodeTokenizer for the given language
        """Create a CodeTokenizer from a pretrained tokenizer for a given language."""
        tokenizer = AutoTokenizer.from_pretrained(name_or_path)
        if padding_token:
            tokenizer.add_special_tokens({"pad_token": padding_token})

        # Grab the node types from the tree-sitter language
        language = Language(f"{code_tokenizers.__path__[0]}/grammars/tree-sitter-languages.so", program_lang)
        node_path = f"{code_tokenizers.__path__[0]}/grammars/tree-sitter-{program_lang}/src/node-types.json"
        with open(node_path) as f:
            node_types = json.load(f)
        node_types = unroll_node_types(node_types)
        if program_lang == "python":
            node_types.append("as_pattern_target")
            node_types.append("ERROR")

        # Create a parser for the language
        parser = Parser()
        parser.set_language(language)
        
        return CodeTokenizer(tokenizer, parser, language, node_types, name_or_path, program_lang, padding_token)
    
    def __reduce__(self):
        return (CodeTokenizer.from_pretrained, (self.name_or_path, self.program_lang, self.padding_token))
    
    def __eq__(self, other):
        return self.name_or_path == other.name_or_path and self.program_lang == other.program_lang and self.padding_token == other.padding_token
