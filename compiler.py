import parsimonious
import sys

from contextlib import contextmanager
from collections import defaultdict
from parsimonious.nodes import NodeVisitor


class ByteType:
    def __init__(self, compiler):
        self.compiler = compiler

    def new(self):
        return Byte(self, self.compiler, self.compiler.allocate())

    def __eq__(self, other):
        return isinstance(other, ByteType)

    def __hash__(self):
        return 0

class Byte:
    def __init__(self, type, compiler, pointer):
        self.type = type
        self.compiler = compiler
        self.pointer = pointer

    def copy(self):
        a1 = self.compiler.allocate()
        a2 = self.compiler.allocate()
        self.compiler.move_cell(self.pointer, a1, a2)
        self.compiler.move_cell(a2, self.pointer)
        self.compiler.free_cell(a2)
        return Byte(self.compiler, a1)

    def free(self):
        self.compiler.free_cell(self.pointer)

class ListType:
    def __init__(self, type, size):
        self.type = type
        self.size = size

    def new(self):
        return List(self, [self.type.new() for _ in range(self.lsize)])

    def __eq__(self, other):
        if not isinstance(other, ListType):
            return False
        return self.type == other.type

    def __hash__(self):
        return hash(self.type) + 1

class List:
    def __init__(self, type, values):
        self.type = type
        self.values = values
        self.size = len(values)

class VirtualIntegerType:
    def __init__(self, compiler):
        self.compiler = compiler

    def new(self):
        return VirtualInteger(self, 0)

    def __eq__(self, other):
        return type(other) == VirtualInteger

    def __hash__(self):
        return 1000

class VirtualInteger:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def copy(self):
        return VirtualInteger(self.type, self.value)

    def free(self):
        pass

class VirtualListType:
    def __init__(self, compiler):
        self.compiler = compiler

    def new(self):
        return VirtualInteger(self, [])

    def __eq__(self, other):
        return type(other) == VirtualListType

    def __hash__(self):
        return 100

class VirtualList:
    def __init__(self, type, values):
        self.type = type
        self.values = values

    def copy(self):
        return VirtualList(self.type, self.values)

    def free(self):
        pass

class FunctionCall:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters

    def evaluate(self, compiler):
        parameters = [param.evaluate(compiler) for param in self.parameters]
        return compiler.functions[(self.name, tuple(param.type for param in parameters))].call(compiler, parameters)

class Copy:
    def __init__(self, expr):
        self.expr = expr

    def evaluate(self, compiler):
        return self.expr.evaluate(compiler).copy()

class BuiltinFunction:
    def __init__(self, func):
        self.func = func

    def call(self, compiler, args):
        return self.func(*args)

class Function:
    def __init__(self, param_names, code, return_expr=None):
        self.param_names = param_names
        self.code = code
        self.return_expr = return_expr

    def call(self, compiler, args):
        compiler.variables = dict(zip(self.param_names, args))
        self.code.execute(compiler)
        if self.return_expr:
            return self.return_expr.evaluate(compiler)

class Code:
    def __init__(self, statements):
        self.statements = statements

    def execute(self, compiler):
        for statement in self.statements:
            statement.evaluate(compiler)

class Get:
    def __init__(self, name):
        self.name = name

    def evaluate(self, compiler):
        return compiler.variables[self.name]

class Getitem:
    def __init__(self, expr, index):
        self.expr = expr
        self.index = index

    def evaluate(self, compiler):
        return self.expr.evaluate(compiler).values[self.index]

class Declaration:
    def __init__(self, type, name):
        self.type = type
        self.name = name

    def evaluate(self, compiler):
        compiler.variables[self.name] = self.type.new()

class If:
    def __init__(self, condition, code):
        self.condition = condition
        self.code = code

    def evaluate(self, compiler):
        cond = self.condition.evaluate(compiler)
        compiler.goto(cond.pointer)
        with compiler.loop():
            self.code.execute(compiler)
            compiler.goto(cond.pointer)
            compiler.execute("[-]")

class While:
    def __init__(self, condition, code):
        self.condition = condition
        self.code = code

    def evaluate(self, compiler):
        cond = self.condition.evaluate(compiler)
        compiler.goto(cond.pointer)
        with compiler.loop():
            self.code.execute(compiler)
            cond = self.condition.evaluate(compiler)
            compiler.goto(cond.pointer)

class Compiler:
    def __init__(self, functions, types):
        self.program = []
        self.current_index = 0
        self.non_allocated = 0
        self.gaps = []
        self.void = None
        self.byte = ByteType(self)
        self.virtual_integer = VirtualIntegerType(self)
        self.virtual_list = VirtualListType(self)
        self.types = {
            "byte": self.byte,
            "virtual integer": self.virtual_integer,
            "virtual list": self.virtual_list,
            **types
        }
        self.functions = functions

    def function(self, name, return_type, *params):
        def function_wrapper(func):
            self.functions[(name, params)] = BuiltinFunction(func)
        return function_wrapper

    def compile(self):
        FunctionCall("main", ()).evaluate(self)
        return self.program

    def allocate(self):
        if self.gaps:
            return self.gaps[0]
        else:
            result = self.non_allocated
            self.non_allocated += 1
            return result

    def execute(self, code):
        self.program.append(code)

    def goto(self, index):
        if self.current_index < index:
            self.execute(">" * (index - self.current_index))
        else:
            self.execute("<" * (self.current_index - index))
        self.current_index = index

    def move_cell(self, source, *targets, multiplier=1):
        self.goto(source)
        with self.loop():
            self.execute("-")
            for target in targets:
                self.goto(target)
                self.execute("+" * multiplier)
            self.goto(source)

    def free_cell(self, index):
        if index + 1 == self.non_allocated:
            self.non_allocated -= 1
        else:
            self.gaps.append(index)

    @contextmanager
    def loop(self):
        save = self.current_index
        self.execute("[")
        yield
        self.execute("]")
        if save != self.current_index:
            raise Exception("unbalanced loop")

compiler = Compiler({}, {})

@compiler.function("=", compiler.byte, compiler.byte, compiler.byte)
def assign(x, y):
    compiler.goto(x.pointer)
    compiler.execute("[-]")
    compiler.move_cell(y.pointer, x.pointer)

@compiler.function("=", compiler.byte, compiler.byte, compiler.virtual_integer)
def assign_virtual(x, y):
    compiler.goto(x.pointer)
    compiler.execute("[-]")
    compiler.execute("+" * y.value)

@compiler.function("++", compiler.byte, compiler.byte)
def succ(x):
    compiler.goto(x.pointer)
    compiler.execute("+")
    return x

@compiler.function("--", compiler.byte, compiler.byte)
def pred(x):
    compiler.goto(x.pointer)
    compiler.execute("-")
    return x

@compiler.function("+=", compiler.byte, compiler.byte, compiler.byte)
def iadd(x, y):
    compiler.move_cell(y.pointer, x.pointer)
    y.free()
    return x

@compiler.function("+=", compiler.byte, compiler.byte, compiler.virtual_integer)
def iadd_virtual(x, y):
    compiler.goto(x.pointer)
    compiler.execute("+" * y.value)
    return x

@compiler.function("-=", compiler.byte, compiler.byte, compiler.byte)
def isub(x, y):
    self.goto(y)
    with self.loop():
        self.execute("-")
        self.goto(x)
        self.execute("-")
        self.goto(y)
    y.free()
    return x

@compiler.function("-=", compiler.byte, compiler.byte, compiler.virtual_integer)
def isub_virtual(x, y):
    compiler.goto(x.pointer)
    compiler.execute("-" * y.value)
    return x

@compiler.function("*=", compiler.byte, compiler.byte, compiler.byte)
def imul(x, y):
    x_prime = x.copy()
    compiler.goto(x.pointer)
    compiler.execute("[-]")
    compiler.goto(y.pointer)
    with compiler.loop():
        compiler.execute("-")
        x_prime_prime = x_prime.copy()
        compiler.move_cell(x_prime_prime.pointer, x.pointer)
        x_prime_prime.free()
        compiler.goto(y.pointer)
    y.free()
    return x

@compiler.function("*=", compiler.byte, compiler.byte, compiler.virtual_integer)
def imul_virtual(x, y):
    x_prime = compiler.byte.new()
    compiler.move_cell(x.pointer, x_prime.pointer, multiplier=y.value)
    compiler.move_cell(x_prime.pointer, x.pointer)
    return x

@compiler.function("!", compiler.byte, compiler.byte)
def nnot(x):
    y = compiler.byte.new()
    compiler.goto(y.pointer)
    compiler.execute("[-]+")
    compiler.goto(x.pointer)
    with compiler.loop():
        compiler.execute("[-]")
        compiler.goto(y.pointer)
        compiler.execute("-")
        compiler.goto(x.pointer)
    return y

@compiler.function("==", compiler.byte, compiler.byte, compiler.byte)
def eq(x, y):
    compiler.goto(y.pointer)
    with compiler.loop():
        compiler.execute("-")
        compiler.goto(x.pointer)
        compiler.execute("-")
        compiler.goto(y.pointer)
    z = compiler.byte.new()
    compiler.goto(z.pointer)
    compiler.execute("[-]+")
    compiler.goto(x.pointer)
    with compiler.loop():
        compiler.execute("[-]")
        compiler.goto(z.pointer)
        compiler.execute("-")
        compiler.goto(x.pointer)
    x.free()
    y.free()
    return z

@compiler.function("read", compiler.byte)
def read():
    x = compiler.allocate()
    compiler.goto(x)
    compiler.execute(",")
    return Byte(compiler.byte, compiler, x)

@compiler.function("write", compiler.void, compiler.byte)
def write(x):
    compiler.goto(x.pointer)
    compiler.execute(".")

grammar = parsimonious.grammar.Grammar(r"""
program = (_ function)* _
function = typedname _ "(" _ (typedname (_ "," _ typedname)* _)? ")" _ codeblock
codeblock = "{" (_ statement)* _ "}"
statement = (bareexpression _ ";") / declaration / if / while
declaration = typedname _ ";"
if = "if" paramblock
while = "while" paramblock
paramblock = _ parenexpression _ codeblock
e = parenexpression / call / integer / char / string / list / identifier
bareexpression = e / opcall
expression = e / ("(" opcall ")")
call = identifier _ "(" _ (bareexpression (_ "," _ bareexpression)* _)? ")"
prefix = "++" / "--" / "!" / "~"
infix = "+=" / "-=" / "*=" / "/=" / "//=" / "%=" / "+" / "-" / "*" / "/" / "//" / "%" / "==" / "!=" / "<" / ">" / "<=" / ">=" / "="
opcall = (expression _ infix _ expression) / (prefix _ expression)
parenexpression = "(" _ bareexpression _ ")"
typedname = type _ identifier
type = identifier (_ "[" _ e _ "]")?
identifier = ~"(?:[A-Za-z_][A-Za-z_0-9]*)?"
integer = ~"(?:[1-9][0-9]*)"
char = "'" ~"\\\\n|." "'"
string = ~"\"(?:\\\\n|\\\\\"|[^\"])*\""
list = "[" _ (expression (_ "," _ expression)* _)? "]"
_ = ~"\s*"
""")

with open(sys.argv[1]) as f:
    parse = grammar.parse(f.read())
    print(parse)

class Visitor(NodeVisitor):
    def visit_program(self, this, below):
        return below

    def visit_function(self, this, below):
        pass

    def visit_codeblock(self, this, below):
        pass

    def visit_statement(self, this, below):
        pass

    def visit_declaration(self, this, below):
        pass

    def visit_if(self, this, below):
        pass

    def visit_while(self, this, below):
        pass

    def visit_paramblock(self, this, below):
        pass

    def visit_e(self, this, below):
        pass

    def visit_bareexpression(self, this, below):
        pass

    def visit_expression(self, this, below):
        pass

    def visit_call(self, this, below):
        pass

    def visit_prefix(self, this, below):
        pass

    def visit_infix(self, this, below):
        pass

    def visit_opcall(self, this, below):
        pass

    def visit_parenexpression(self, this, below):
        pass

    def visit_typedname(self, this, below):
        pass

    def visit_type(self, this, below):
        pass

    def visit_identifier(self, this, below):
        pass

    def visit_integer(self, this, below):
        return VirtualInteger(compiler.virtual_integer, int(this.expr))

    def visit_char(self, this, below):
        return VirtualInteger(compiler.virtual_integer, ord(this.children[1].expr))

    def visit_string(self, this, below):
        pass

    def visit_list(self, this, below):
        return VirtualList(compiler.virtual_list, below)

    def visit__(self, this, below):
        return None
NZ
