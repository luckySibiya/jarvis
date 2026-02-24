"""Calculator — evaluate math expressions safely."""

import ast
import math
import operator

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)

# Safe operators for math evaluation
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(expr: str) -> float:
    """Safely evaluate a math expression without exec/eval."""
    # Clean up common spoken math
    expr = expr.replace("^", "**")
    expr = expr.replace("×", "*").replace("÷", "/")
    expr = expr.replace("plus", "+").replace("minus", "-")
    expr = expr.replace("times", "*").replace("divided by", "/")
    expr = expr.replace("to the power of", "**")
    expr = expr.replace(",", "")

    tree = ast.parse(expr, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPS:
                raise ValueError(f"Unsupported operator: {op_type}")
            return _SAFE_OPS[op_type](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPS:
                raise ValueError(f"Unsupported operator: {op_type}")
            return _SAFE_OPS[op_type](_eval(node.operand))
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in _SAFE_FUNCS and callable(_SAFE_FUNCS[func_name]):
                args = [_eval(arg) for arg in node.args]
                return _SAFE_FUNCS[func_name](*args)
            raise ValueError(f"Unsupported function: {func_name}")
        elif isinstance(node, ast.Name):
            if node.id in _SAFE_FUNCS and not callable(_SAFE_FUNCS[node.id]):
                return _SAFE_FUNCS[node.id]
            raise ValueError(f"Unknown variable: {node.id}")
        else:
            raise ValueError(f"Unsupported expression: {type(node)}")

    return _eval(tree)


@register("system", "calculate")
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        result = _safe_eval(expression)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"The answer is {result}."
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return f"I couldn't calculate that: {e}"
