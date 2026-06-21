"""
MAHOUN Contract Compiler
========================
Automatically extracts potential invariants from existing pytest files using AST analysis.
"""

import ast
import os
import json
import argparse
from typing import List, Dict, Any

class TestVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.invariants = []
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_Assert(self, node: ast.Assert):
        # Extract the source code of the assertion
        try:
            assertion_code = ast.unparse(node.test)
        except AttributeError:
            # Fallback for older python versions if needed
            assertion_code = "complex_assertion"
            
        self.invariants.append({
            "test_function": self.current_function,
            "assertion": assertion_code,
            "file": self.file_path
        })

def compile_tests_to_contracts(input_dir: str) -> List[Dict[str, Any]]:
    extracted_data = []
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                        visitor = TestVisitor(file_path)
                        visitor.visit(tree)
                        if visitor.invariants:
                            extracted_data.append({
                                "source_file": file,
                                "invariants": visitor.invariants
                            })
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
    
    return extracted_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAHOUN Contract Compiler")
    parser.add_argument("--input", required=True, help="Input tests directory")
    parser.add_argument("--output", required=True, help="Output contracts JSON file")
    parser.add_argument("--mode", default="strict", help="Compilation mode")
    
    args = parser.parse_args()
    
    print(f"Compiling tests in {args.input}...")
    contracts = compile_tests_to_contracts(args.input)
    
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(contracts, f, indent=2)
    
    print(f"Successfully compiled {len(contracts)} test files into contract candidates at {args.output}")
