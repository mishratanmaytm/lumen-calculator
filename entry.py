"""entry.py - what happens when you press a key (no graphics in here)."""

from engine import calculate, CalcError

OPERATORS = ("+", "-", "×", "÷", "^")
FUNCTION_STARTS = ("asin(", "acos(", "atan(", "sin(", "cos(", "tan(",
                   "log(", "ln(", "sqrt(", "abs(")
MAX_LENGTH = 200


def plain_number(text):
    """1.5E20 -> (1.5×10^20) so it can be typed back into an expression."""
    return "(" + text.replace("E", "×10^") + ")" if "E" in text else text


class Entry:
    def __init__(self, history):
        self.history = history
        self.degrees = True
        self.expr = ""
        self.status = "typing" # "typing", "result" or "error"
        self.answer = "" # last good answer, as text
        self.error = "" # error message when status == "error"
        self.last_line = "" # e.g. "9×8 = 72" shown small at the top

    def press(self, key):
        """Handle one key. Returns True if the answer was just calculated."""
        if key == "AC":
            self.expr, self.status, self.error = "", "typing", ""
            return False
        if key == "DEL":
            self.delete()
            return False
        if key == "=":
            return self.equals()
        if key == "ANS":
            if not self.answer:
                return False
            key = plain_number(self.answer)
        if key in ("^2", "^3"): # the x² and x³ buttons
            self.insert("^")
            if self.expr.endswith("^"):
                self.insert(key[1])
            return False
        self.insert(key)
        return False

    # ---- typing -------------------------------------------------------
    def insert(self, key):
        if self.status == "result":
            # operators continue from the answer, anything else starts fresh
            self.last_line = self.expr + " = " + self.answer
            self.expr = plain_number(self.answer) if key in ("+", "-", "×", "÷", "^", "%", "!") else ""
        self.status, self.error = "typing", ""
        if len(self.expr) >= MAX_LENGTH:
            return
        e = self.expr
        last = e[-1:]

        if key in ("+", "×", "÷", "^"):
            if not e or last == "(":
                return
            if last in OPERATORS:
                if last == "-" and e[-2:-1] in ("×", "÷", "^", "("):
                    e = e[:-2] # e.g. "5×-" then × -> "5×"
                else:
                    e = e[:-1]
            self.expr = e + key
        elif key == "-":
            if last in ("+", "-"):
                self.expr = e[:-1] + "-"
            else:
                self.expr = e + "-"
        elif key == ".":
            i = len(e)
            while i > 0 and (e[i - 1].isdigit() or e[i - 1] == "."):
                i -= 1
            segment = e[i:]
            if "." in segment:
                return
            self.expr = e + ("0." if segment == "" else ".")
        elif key in ("%", "!"):
            if not e or last in OPERATORS or last == "(":
                return
            self.expr = e + key
        elif key == ")":
            if e.count("(") <= e.count(")") or last in OPERATORS or last == "(":
                return
            self.expr = e + key
        else:
            self.expr = e + key

    def delete(self):
        if self.status == "result":
            self.last_line = ""
        self.status, self.error = "typing", ""
        for start in FUNCTION_STARTS: # remove "sin(" in one go
            if self.expr.endswith(start):
                self.expr = self.expr[:-len(start)]
                return
        self.expr = self.expr[:-1]

    # ---- calculating --------------------------------------------------
    def closed(self):
        """The expression with any missing ')' added."""
        return self.expr + ")" * max(0, self.expr.count("(") - self.expr.count(")"))

    def equals(self):
        if not self.expr or self.status == "result":
            return False
        full = self.closed()
        try:
            result = calculate(full, self.degrees)
        except CalcError as err:
            self.status, self.error = "error", str(err)
            return False
        self.history.add(full, result)
        self.expr, self.answer, self.status = full, result, "result"
        self.last_line = ""
        return True

    def preview(self):
        """Quiet live answer shown while typing ('' if nothing sensible)."""
        if self.status != "typing" or not self.expr:
            return ""
        if not any(c in self.expr for c in "+-×÷^%!(") and not any(
                f[:-1] in self.expr for f in FUNCTION_STARTS):
            return ""
        try:
            value = calculate(self.closed(), self.degrees)
        except CalcError:
            return ""
        return "" if value == self.expr else value