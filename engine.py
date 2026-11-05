"""engine.py - the safe calculator brain for Lumen. No eval() anywhere."""

import math


class CalcError(Exception):
    """Raised when an expression cannot be calculated."""


FUNCTIONS = ("asin", "acos", "atan", "sin", "cos", "tan", "log", "ln", "sqrt", "abs")
CONSTANTS = {"π": math.pi, "pi": math.pi, "e": math.e}


def _tokenize(text):
    text = (text.replace("×", "*").replace("÷", "/").replace("−", "-")
                .replace("√", " sqrt ").replace("**", "^"))
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or c == ".":
            j = i
            while j < len(text) and (text[j].isdigit() or text[j] == "."):
                j += 1
            part = text[i:j]
            if part.count(".") > 1 or part == ".":
                raise CalcError("Invalid number")
            tokens.append(("num", float(part)))
            i = j
        elif c in "+-*/^()%!":
            tokens.append((c, c))
            i += 1
        elif c == "π":
            tokens.append(("const", math.pi))
            i += 1
        elif c.isalpha():
            j = i
            while j < len(text) and text[j].isalpha():
                j += 1
            word = text[i:j]
            if word in FUNCTIONS:
                tokens.append(("func", word))
            elif word in CONSTANTS:
                tokens.append(("const", CONSTANTS[word]))
            else:
                raise CalcError("Unknown: " + word)
            i = j
        else:
            raise CalcError("Bad symbol: " + c)
    return tokens


class _Parser:
    def __init__(self, tokens, degrees):
        self.t = tokens
        self.pos = 0
        self.deg = degrees

    def peek(self):
        return self.t[self.pos][0] if self.pos < len(self.t) else None

    def take(self):
        tok = self.t[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        if not self.t:
            raise CalcError("Empty")
        value = self.expr()
        if self.pos != len(self.t):
            raise CalcError("Invalid expression")
        return value

    def expr(self):
        value = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()[0]
            right = self.term()
            value = value + right if op == "+" else value - right
        return value

    def term(self):
        value = self.unary()
        while True:
            kind = self.peek()
            if kind in ("*", "/"):
                self.take()
                right = self.unary()
                if kind == "/":
                    if right == 0:
                        raise CalcError("Cannot divide by 0")
                    value = value / right
                else:
                    value = value * right
            elif kind in ("num", "const", "func", "("):
                value = value * self.unary() # implicit multiply: 2π, 3(4+1)
            else:
                return value

    def unary(self):
        if self.peek() == "-":
            self.take()
            return -self.unary()
        if self.peek() == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == "^":
            self.take()
            exp = self.unary()
            try:
                result = base ** exp
            except ZeroDivisionError:
                raise CalcError("Cannot divide by 0")
            except OverflowError:
                raise CalcError("Number too big")
            if isinstance(result, complex):
                raise CalcError("Math error")
            return result
        return base

    def postfix(self):
        value = self.primary()
        while self.peek() in ("%", "!"):
            if self.take()[0] == "%":
                value = value / 100
            else:
                if value < 0 or value != int(value) or value > 170:
                    raise CalcError("Math error")
                value = float(math.factorial(int(value)))
        return value

    def primary(self):
        kind = self.peek()
        if kind == "num" or kind == "const":
            return self.take()[1]
        if kind == "(":
            self.take()
            value = self.expr()
            if self.peek() == ")":
                self.take()
            return value # a missing ) at the end is forgiven
        if kind == "func":
            name = self.take()[1]
            if self.peek() == "(":
                self.take()
                arg = self.expr()
                if self.peek() == ")":
                    self.take()
            else:
                arg = self.unary() # allows sqrt 9 and √9
            return self.apply(name, arg)
        raise CalcError("Invalid expression")

    def apply(self, name, x):
        try:
            if name == "sin":
                return math.sin(math.radians(x) if self.deg else x)
            if name == "cos":
                return math.cos(math.radians(x) if self.deg else x)
            if name == "tan":
                a = math.radians(x) if self.deg else x
                if abs(math.cos(a)) < 1e-12:
                    raise CalcError("Math error")
                return math.tan(a)
            if name in ("asin", "acos", "atan"):
                r = getattr(math, name)(x)
                return math.degrees(r) if self.deg else r
            if name == "log":
                return math.log10(x)
            if name == "ln":
                return math.log(x)
            if name == "sqrt":
                return math.sqrt(x)
            if name == "abs":
                return abs(x)
        except ValueError:
            raise CalcError("Math error")
        raise CalcError("Unknown function")


def format_number(x):
    """Turn a float into a tidy string like 72, 0.3, 1.5E20."""
    if x != x or x in (float("inf"), float("-inf")):
        raise CalcError("Math error")
    if abs(x) < 1e-12:
        return "0"
    text = "%.12g" % x
    if "e" in text:
        mantissa, exp = text.split("e")
        text = mantissa + "E" + str(int(exp))
    return text


def calculate(expression, degrees=True):
    """Main function: give it text, get back the answer as text. Raises CalcError."""
    try:
        value = _Parser(_tokenize(expression), degrees).parse()
        return format_number(value)
    except CalcError:
        raise
    except (OverflowError, ZeroDivisionError):
        raise CalcError("Math error")
    except RecursionError:
        raise CalcError("Too complex")