# Programs
Programs are made up of function definitions and virtual variables. The `main` function is the only one immediately executed by default.

# Code
Code is made up of multiple statements seperated by semicolons. Each statement is a single expression, which can be a literal, function call or operator. Expressions evaluate either to nothing or to a pointer.

When code needs to be executed, the statements are evaluated sequentially.

# Compilation
There is a global BF program which is initially empty.

The compiler goes through the program evaluating expressions and adding code to the BF program.

It keeps track of what memory each variable has allocated, as well as scopes and what the tape pointer is.

# Poiers
A pointer is a compile-time construct that refers to a cell in BF memory. As the compiler always knows where the tape pointer is, it can always move to any arbitrary pointer.

Poiers are the main type of value in CF and are what variables hold. They have a *type*.

# Function definition
Function definition takes the form of `returntype functionname(type 1 name 1, type 2 name 1, ..., type n name n) { code }`.

When called, the code inside the function definition will be executed.

# Special statements

There are some statements that do not consist of expressions. These are the `if`, `whilevar`, `while`, `free` and `return` expressions.

# `free` statement

Takes the form of `free var;`.

The free statement is used to explicitly say that you wish for a variable to be freed. It acts at compile-time and removes the allocation under the given variable.

Note that if `free` is used inside an if statement, it will not be affected by the condition and the variable will be freed if the if statement fired or not.

Also note that it is illegal to free a variable from outside of a while loop inside that while loop.

# `return` statement

Takes the form of `return expr;`.

The return statement is used to return a pointer. It must be placed at the end of a function, if present at all.

When reached, the expression is evaluated, and the pointer it returns is returned from the function.

# Declaring variables
Variables can be declared like `type name;`. This will immediately allocate space on the tape for the variable, but will not change the value of it. Trying to use an undeclared variable, or a declared variable with no value, will raise a compiler error.

You can also build-in a declaration for the variable in the declaration, like `type name = value;`. This is equivalent to `type name; name = value;`.

# Virtual pointers
Literals such as `4`, `69387938793` and `6.2` have the type of *virtual pointers*, which do not refer to real variables on the stack.

There are four types of virtual pointer, `virtual integer` (like 1),
                                         `virtual float` (like 1.2),
                                         `virtual char` (like 'a'),
                                         `virtual string` (like "abc"),
                                         `virtual list` (like [1, 2, 3]),
                                         `virtual tuple` (like (1,), (1, 2, 3) or (), but not (1))

You can set virtual pointers to variables (which will not allocate anything on the tape) like `virtual integer name = value;`.

Virtual pointers are supported by all operators standalone. Trying to assign one to a variable of a non-virtual type will trigger a *construction*.

# Structs


# Function calls
Function calls take the form of `name(expr 1, expr 2, ..., expr n)`. The expressions in the call are evaluated in order, the code inside the called function is executed and the call evaluates to the returned pointer.

# Operators
Operator usage takes the form of `expr1 <operator> expr2`. It is otherwise essentially the same as a function call. The valid operators are listed below.

# `if` statement
The `if` statement takes the form of `if (expr) { code }`.

To execute the statement, first the expression in the parentheses is evaluated. The pointer it returns is moved to and stored for the end of the statement, and the `[` instruction is added to the code.

Then, the code inside the block is executed as normal.

At the end of the loop, the pointer is moved back to the stored location, and `[-]]` is added to the code. Note that this destroys the pointer returned by the if condition.

# `whilevar` statement
The `whilevar` statement takes the form of `whilevar (expr) { code }`.

It is equal to `if`, but `]` is added at the end instead of `[-]]` (leaving `expr` non-destroyed).

# Copying
The `&` unary operator is used to copy values. It takes the form of `&expr`.

First, the expression is evaluated. Then, two cells are anonymously allocated and the evaluated expression is moved to both cells. The first allocated cell is moved back to the place it was before, freeing that location, while the second's location is returned.

# `while` statement
The `while` statement takes the form of `while (expr) { code }`.

It is equivalent to `j = &expr; whilevar (j) {code; j = &expr;}

# Memory
Fixed slices of the memory are allocated for each variable of fixed size. These sizes are listed in the Types section.

When a new variable needs allocation, the first spot with space from the left has all of the memory inside allocated to that variable.

When a variable needs to be freed, all the memory it is taking up is marked as free, but BF code is not written to clear the spaces.

# Types
- byte, 1 byte, 0 to 255
- type[n], n bytes, fixed size array

# Built-in operators

- `++`, increments an integer by one
  - takes a pointer and increments the value it points to by one with a basic algorithm
- `--`, decrements an integer by one
- `+=`, adds two numbers
  - takes two values (that is, pointers that refer to values) `x` and `y`, and, while `y` is still nonzero, decrements `y` and increments `x`, finally returning a pointer to `x`
  - mutates `x` and destroys (frees) `y`
- `-=`, subtracts two numbers
- `+`, adds two numbers
  - equal to `&x += &y`
- `-`, subtracts two numbers
- `/=`, divides two numbers and returns a f
  - mutates the dividend
- `//=`, divides two numbers and returns the quotient
  - removes the dividend by the divisor while incrementing the quotient until `dividend < divisor`, then sets the dividend to the quotient and returns the dividend
  - mutates the dividend
- `%=`, divides two numbers and returns the remainder
  - `//`, but returns `dividend` at the end instead of `quotient`
  - mutates the dividend
- `*=`, muliply two numbers
  - add the multiplicand to the result while decrementing the multiplier until the multiplier is 0, then set the multiplicand to the result
  - destroys the multiplier
  - mutates the multiplicand
- `/`
  - equal to `&x /= y`
- `//`
  - equal to `&x //= y`
- `%`
  - equal to `&x /= y`
- `*`
  - equal to `&x * &y`
- `==`, are two things equal?
  - decrement `x` and `y` until one is 0, then return whether the other one is 0, destroys x and y
  - if one of x or y is virtual, offsets the other by the amount that would be needed to make it 0 were it that both values are the same, then returns whether the result is 0, destroys the other
  - if both are virtual, evaluates directly to the result as a virtual pointer, destroys x and y
- `!=`, are two things different?
  - decrement `x` and `y` until one is 0, then return whether the other one is nonzero, destroys x and y
  - if one of x or y is virtual, offsets the other by the amount that would be needed to make it 0 were it that both values are the same, then runs `!` and returns whether the result is nonzero, destroys the other
  - if both are virtual, evaluates directly to the result as a virtual pointer
- `!`, negate a boolean
  - move to the given pointer and run `[[-]-]+`
- `<=`, leq
  - destroys x and y
- `>=`, geq
  - destroys x and y
- `<`, less than
  - destroys x and y
- `>`, greater than
  - destroys x and y
- `=`, assignment
  - if x is a real type, allocates the memory under y to x, freeing y
  - if x is a virtual tuple and y is a virtual tuple, assign everything in x to the corrosponding field in y
  - if y is virtual, calls the constructor for the type that x is on y, and uses the result
  - destroys y
  - mutates x

# Built-in functions

- `u8 read()`, take a single byte of input
  - allocates a byte anonymously, moves to it, adds `,` to the program, and returns the pointer to the allocated byte
- `void write(u8 char)`, output a single byte
  - moves to the taken pointer and adds `.` to the program
