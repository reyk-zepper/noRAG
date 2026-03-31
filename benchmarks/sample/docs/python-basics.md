# Python Programming Basics

## Variables and Data Types

Python supports several built-in data types: integers, floats, strings, booleans, lists, tuples, dictionaries, and sets. Variables are dynamically typed — you don't need to declare types explicitly.

```python
name = "Alice"        # string
age = 30              # integer
height = 1.75         # float
is_active = True      # boolean
scores = [95, 87, 92] # list
```

## Functions

Functions are defined using the `def` keyword. Python supports default arguments, keyword arguments, and variable-length arguments.

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
```

## Classes and OOP

Python supports object-oriented programming with classes, inheritance, and polymorphism.

```python
class Animal:
    def __init__(self, name, species):
        self.name = name
        self.species = species

    def speak(self):
        raise NotImplementedError

class Dog(Animal):
    def speak(self):
        return f"{self.name} says Woof!"
```

## Error Handling

Python uses try/except blocks for error handling. You can catch specific exceptions or use a general except clause.

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero")
finally:
    print("Cleanup complete")
```

## List Comprehensions

List comprehensions provide a concise way to create lists based on existing sequences.

```python
squares = [x**2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
```
