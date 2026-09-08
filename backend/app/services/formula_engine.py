"""PRCP 公式引擎 — 纯 Python，支持四则运算 + 基础函数
公式语法示例:
    100 * (rpt:001001 + rpt:001002) / rpt:001003
    SUM(rpt:001001, rpt:001002, rpt:001003)
    AVG(rpt:001001, rpt:001002)
    IF(rpt:001001 > 0, rpt:001002, 0)
    ABS(rpt:001001 - 100)
变量以"rpt:"或"node:"前缀引用报表表项 / 账户册节点
"""
import re
from typing import Dict, Optional


# 自定义异常
class FormulaError(Exception):
    pass


# ---------- Token ----------
TOKEN_PAT = re.compile(r"""
    \s+                                    # 空白
    | (?P<NUM>\d+(?:\.\d+)?)               # 数字
    | (?P<ID>[A-Za-z_][A-Za-z0-9_]*)       # 标识符
    | (?P<OP>[\+\-\*\/\(\)\,])             # 运算符 / 括号 / 逗号
    | (?P<CMP><=|>=|<>|!=|==|<|>)         # 比较
""", re.VERBOSE)


def tokenize(expr: str):
    tokens = []
    pos = 0
    while pos < len(expr):
        m = TOKEN_PAT.match(expr, pos)
        if not m:
            raise FormulaError(f"无法识别的字符: {expr[pos:pos+10]!r} 在位置 {pos}")
        if m.lastgroup != "WHITESPACE" if hasattr(m, "WHITESPACE") else True:
            if m.group():
                # 跳过纯空白
                pass
        if m.group().strip():
            tokens.append((m.lastgroup, m.group().strip()))
        pos = m.end()
    return tokens


# ---------- 简单求值（递归下降） ----------
def _eval_expr(tokens, pos, ctx):
    """处理 + -"""
    left, pos = _eval_term(tokens, pos, ctx)
    while pos < len(tokens) and tokens[pos][0] == "OP" and tokens[pos][1] in ("+", "-"):
        op = tokens[pos][1]
        right, pos = _eval_term(tokens, pos + 1, ctx)
        left = left + right if op == "+" else left - right
    return left, pos


def _eval_term(tokens, pos, ctx):
    """处理 * /"""
    left, pos = _eval_factor(tokens, pos, ctx)
    while pos < len(tokens) and tokens[pos][0] == "OP" and tokens[pos][1] in ("*", "/"):
        op = tokens[pos][1]
        right, pos = _eval_factor(tokens, pos + 1, ctx)
        if op == "*":
            left = left * right
        else:
            if right == 0:
                raise FormulaError("除数不能为 0")
            left = left / right
    return left, pos


def _eval_factor(tokens, pos, ctx):
    """处理括号 / 数字 / 标识符 / 比较 / 函数"""
    if pos >= len(tokens):
        raise FormulaError("公式意外结束")
    typ, val = tokens[pos]
    # 一元负号
    if typ == "OP" and val == "-":
        v, pos = _eval_factor(tokens, pos + 1, ctx)
        return -v, pos
    if typ == "OP" and val == "+":
        return _eval_factor(tokens, pos + 1, ctx)
    # 数字
    if typ == "NUM":
        return float(val), pos + 1
    # 括号
    if typ == "OP" and val == "(":
        v, pos = _eval_expr(tokens, pos + 1, ctx)
        if pos >= len(tokens) or tokens[pos] != ("OP", ")"):
            raise FormulaError("括号不匹配")
        return v, pos + 1
    # 函数或变量
    if typ == "ID":
        # 函数: ID(...)
        if pos + 1 < len(tokens) and tokens[pos + 1] == ("OP", "("):
            fname = val
            args, pos = _eval_args(tokens, pos + 2, ctx)
            return _call_func(fname, args), pos
        # 变量
        if pos + 1 < len(tokens) and tokens[pos + 1][0] == "CMP":
            op = tokens[pos + 1][1]
            right, pos = _eval_expr(tokens, pos + 2, ctx)
            left = ctx.get(val, 0)
            ops = {
                ">": lambda a, b: 1.0 if a > b else 0.0,
                "<": lambda a, b: 1.0 if a < b else 0.0,
                "==": lambda a, b: 1.0 if abs(a - b) < 1e-9 else 0.0,
                "!=": lambda a, b: 0.0 if abs(a - b) < 1e-9 else 1.0,
                ">=": lambda a, b: 1.0 if a >= b else 0.0,
                "<=": lambda a, b: 1.0 if a <= b else 0.0,
            }
            return ops[op](ctx.get(val, 0), right), pos
        return ctx.get(val, 0), pos + 1
    raise FormulaError(f"意外的 token: {val!r}")


def _eval_args(tokens, pos, ctx):
    args = []
    if pos < len(tokens) and tokens[pos] == ("OP", ")"):
        return args, pos + 1
    while True:
        v, pos = _eval_expr(tokens, pos, ctx)
        args.append(v)
        if pos < len(tokens) and tokens[pos] == ("OP", ","):
            pos += 1
        else:
            break
    if pos >= len(tokens) or tokens[pos] != ("OP", ")"):
        raise FormulaError("函数调用括号不匹配")
    return args, pos + 1


def _call_func(name, args):
    name = name.upper()
    if name == "SUM":
        return sum(args)
    if name in ("AVG", "AVERAGE"):
        return sum(args) / len(args) if args else 0
    if name == "MAX":
        return max(args) if args else 0
    if name == "MIN":
        return min(args) if args else 0
    if name == "COUNT":
        return float(len(args))
    if name == "ABS":
        return abs(args[0]) if args else 0
    if name == "ROUND":
        return round(args[0], int(args[1]) if len(args) > 1 else 0)
    if name == "IF":
        return args[1] if (args[0] if args else 0) else (args[2] if len(args) > 2 else 0)
    raise FormulaError(f"未知函数: {name}")


def evaluate(formula: str, ctx: Optional[Dict] = None) -> float:
    """计算公式"""
    if not formula or not formula.strip():
        raise FormulaError("公式为空")
    ctx = ctx or {}
    tokens = tokenize(formula)
    val, pos = _eval_expr(tokens, 0, ctx)
    if pos != len(tokens):
        raise FormulaError(f"公式未完全解析，停在位置 {pos}")
    return val


def validate(formula: str) -> dict:
    """校验公式语法（不求值）"""
    try:
        tokens = tokenize(formula)
        if not tokens:
            return {"ok": False, "error": "公式为空"}
        return {"ok": True, "tokens": len(tokens)}
    except FormulaError as e:
        return {"ok": False, "error": str(e)}
