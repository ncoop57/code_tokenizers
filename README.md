code_tokenizers
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

This library is built on top of the awesome
[transformers](https://github.com/huggingface/transformers) and
[tree-sitter](https://github.com/tree-sitter/py-tree-sitter) libraries.
It provides a simple interface to align the tokens produced by a BPE
tokenizer with the tokens produced by a tree-sitter parser.

## Install

``` sh
pip install code_tokenizers
```

## How to use

First you need to make sure you have the tree-sitter grammars for the
languages you want to use. To simplify this process, we’ve built a CLI
tool that will download the grammars for you that comes with this
library:

``` python
!download_grammars --help
```

    usage: download_grammars [-h] [--languages LANGUAGES [LANGUAGES ...]]

    Download Tree-sitter grammars

    options:
      -h, --help                            show this help message and exit
      --languages LANGUAGES [LANGUAGES ...]
                                            Languages to download (default: all)

This will download the grammars to the `grammars` directory in the
directory where this library is installed. Let’s continue this example
with the Python grammar:

``` python
!download_grammars --languages python
```

Now, we can create a
[`CodeTokenizer`](https://ncoop57.github.io/code_tokenizers/core.html#codetokenizer)
object:

``` python
from code_tokenizers.core import CodeTokenizer

py_tokenizer = CodeTokenizer.from_pretrained("gpt2", "python")
```

You can specify any pretrained BPE tokenizer from the [huggingface
hub](hf.co/models) or a local directory and the language to parse the
AST for.

Now, we can tokenize some code:

``` python
from pprint import pprint

code = """
def foo():
    print("Hello world!")
"""

encoding = py_tokenizer(code)
pprint(encoding, depth=1)
```

    {'ast_ids': [...],
     'attention_mask': [...],
     'input_ids': [...],
     'is_builtins': [...],
     'is_internal_methods': [...],
     'merged_ast': [...],
     'offset_mapping': [...],
     'parent_ast_ids': [...]}

And we can print out the associated AST types:

<div>

> **Note**
>
> Note: Here the N/As are the tokens that are not part of the AST, such
> as the spaces and the newline characters. Their IDs are set to -1.

</div>

``` python
for ast_id, parent_ast_id in zip(encoding["ast_ids"], encoding["parent_ast_ids"]):
    if ast_id != -1:
        print(py_tokenizer.node_types[parent_ast_id], py_tokenizer.node_types[ast_id])
    else:
        print("N/A")
```

    N/A
    function_definition def
    function_definition identifier
    parameters (
    N/A
    N/A
    N/A
    N/A
    call identifier
    argument_list (
    argument_list string
    argument_list string
    argument_list string
    argument_list )
    N/A
