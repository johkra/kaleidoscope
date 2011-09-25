#!/usr/bin/env python3
# Python 3 translation of the C++ code from LLVM's Kaleidoscope tutorial

import re
import sys

#===----------------------------------------------------------------------===//
# Lexer
#===----------------------------------------------------------------------===//

# The lexer returns tokens [0-255] if it is an unknown character, otherwise one
# of these for known things.
Token = {
  "tok_eof": -1,

  # commands
  "tok_def": -2, "tok_extern": -3,

  # primary
  "tok_identifier": -4, "tok_number": -5
}

IdentifierStr = "" # Filled in if tok_identifier
NumVal = 0.0       # Filled in if tok_number
LastChar = ' '
  
def getchar():
  return sys.stdin.read(1)

# gettok - Return the next token from standard input.
def gettok():
  global IdentifierStr
  global NumVal
  global LastChar

  # Skip any whitespace.
  while (re.match("\s", LastChar)):
    LastChar = getchar();

  if (re.match("[a-zA-Z]", LastChar)): # identifier: [a-zA-Z][a-zA-Z0-9]*
    IdentifierStr = LastChar;
    LastChar = getchar()
    while (re.match("[a-zA-Z0-9]", LastChar)):
      IdentifierStr += LastChar;
      LastChar = getchar()

    if (IdentifierStr == "def"): return Token["tok_def"]
    if (IdentifierStr == "extern"): return Token["tok_extern"]
    return Token["tok_identifier"]

  if (re.match("[0-9]", LastChar) or LastChar == '.'): # Number: [0-9.]+
    NumStr = ""
    while True:
      NumStr += LastChar
      LastChar = getchar()
      if not (re.match("[0-9]", LastChar) or LastChar == '.'):
        break

    NumVal = float(NumStr);
    return Token["tok_number"]

  if (LastChar == '#'):
    # Comment until end of line.
    while True:
      LastChar = getchar()
      if not (LastChar != None and LastChar != '\n' and LastChar != '\r'):
        break
    
    if (LastChar != ''):
      return gettok();
  
  # Check for end of file.  Don't eat the EOF.
  if (LastChar == ''):
    return Token["tok_eof"]

  # Otherwise, just return the character as its ascii value.
  ThisChar = LastChar
  LastChar = getchar()
  return ThisChar

#===----------------------------------------------------------------------===//
# Abstract Syntax Tree (aka Parse Tree)
#===----------------------------------------------------------------------===//

# ExprAST - Base class for all expression nodes.
class ExprAST:
  pass

# NumberExprAST - Expression class for numeric literals like "1.0".
class NumberExprAST(ExprAST):
  def __init__(self, val):
    self.val = val

# VariableExprAST - Expression class for referencing a variable, like "a".
class VariableExprAST(ExprAST):
  def __init__(self, name):
     self.name = name

# BinaryExprAST - Expression class for a binary operator.
class BinaryExprAST(ExprAST):
  def __init__(self, op, lhs = None, rhs = None):
    self.op = op
    self.lhs = lhs
    self.rhs = rhs

# CallExprAST - Expression class for function calls.
class CallExprAST(ExprAST):
  def __init__(self, callee, args):
    self.callee = callee
    self.args = args

# PrototypeAST - This class represents the "prototype" for a function,
# which captures its name, and its argument names (thus implicitly the number
# of arguments the function takes).
class PrototypeAST:
  def __init__(self, name, args):
    self.name = name
    self.args = args

# FunctionAST - This class represents a function definition itself.
class FunctionAST:
  def __init__(self, proto, body):
    self.proto = proto
    self.body = body

#===----------------------------------------------------------------------===//
# Parser
#===----------------------------------------------------------------------===//

# CurTok/getNextToken - Provide a simple token buffer.  CurTok is the current
# token the parser is looking at.  getNextToken reads another token from the
# lexer and updates CurTok with its results.
CurTok = 0
def getNextToken():
  global CurTok
  CurTok = gettok()
  return CurTok

# BinopPrecedence - This holds the precedence for each binary operator that is
# defined.
BinopPrecedence = {}

# GetTokPrecedence - Get the precedence of the pending binary operator token.
def GetTokPrecedence():
#  if (!isascii(CurTok))
  if type(CurTok) != str:
    return -1
  
  # Make sure it's a declared binop.
  TokPrec = BinopPrecedence.get(CurTok, -1)
  if (TokPrec <= 0): return -1
  return TokPrec

# Error* - These are little helper functions for error handling.
def error(string):
  print("Error: " + string, file=sys.stderr)
  return None

def errorP(string):
  error(string)
  return None

def errorF(string):
  error(string)
  return None

# identifierexpr
#   ::= identifier
#   ::= identifier '(' expression* ')'
def ParseIdentifierExpr():
  IdName = IdentifierStr;
  
  getNextToken() # eat identifier.
  
  if (CurTok != '('): #Simple variable ref.
    return VariableExprAST(IdName)
  
  # Call.
  getNextToken() # eat (
  args = []
  if (CurTok != ')'):
    while True:
      arg = ParseExpression()
      if  not arg: return None
      args.append(arg)

      if (CurTok == ')'): break

      if (CurTok != ','):
        return error("Expected ')' or ',' in argument list")
      getNextToken()

  # Eat the ')'.
  getNextToken()
  
  return CallExprAST(IdName, args)

# numberexpr ::= number
def ParseNumberExpr():
  result = NumberExprAST(NumVal)
  getNextToken() # consume the number
  return result


# parenexpr ::= '(' expression ')'
def ParseParenExpr():
  getNextToken() # eat (.
  v = ParseExpression()
  if not V: return None
  
  if (CurTok != ')'):
    return error("expected ')'")
  getNextToken()  # eat ).
  return V

# primary
#   ::= identifierexpr
#   ::= numberexpr
#   ::= parenexpr
def ParsePrimary():
  if CurTok == Token["tok_identifier"]:
    return ParseIdentifierExpr()
  elif CurTok == Token["tok_number"]:
    return ParseNumberExpr()
  elif CurTok == "(":
    return ParseParenExpr()
  else:
    return error("unknown token when expecting an expression")

# binoprhs
#   ::= ('+' primary)*
def ParseBinOpRHS(ExprPrec, LHS):
  # If this is a binop, find its precedence.
  while True:
    TokPrec = GetTokPrecedence()
    
    # If this is a binop that binds at least as tightly as the current binop,
    # consume it, otherwise we are done.
    if (TokPrec < ExprPrec):
      return LHS
    
    # Okay, we know this is a binop.
    BinOp = CurTok
    getNextToken() # eat binop
    
    # Parse the primary expression after the binary operator.
    RHS = ParsePrimary()
    if not RHS: return None
    
    # If BinOp binds less tightly with RHS than the operator after RHS, let
    # the pending operator take RHS as its LHS.
    NextPrec = GetTokPrecedence()
    if (TokPrec < NextPrec):
      RHS = ParseBinOpRHS(TokPrec+1, RHS)
      if (RHS == 0): return 0

    
    # Merge LHS/RHS.
    LHS = BinaryExprAST(BinOp, LHS, RHS)

# expression
#   ::= primary binoprhs
#
def ParseExpression():
  LHS = ParsePrimary()
  if not LHS: return 0
  
  return ParseBinOpRHS(0, LHS)

# prototype
#   ::= id '(' id* ')'
def ParsePrototype():
  if (CurTok != Token['tok_identifier']):
    return errorP("Expected function name in prototype")

  FnName = IdentifierStr
  getNextToken()
  
  if (CurTok != '('):
    return errorP("Expected '(' in prototype")
  
  ArgNames = []
  while (getNextToken() == Token['tok_identifier']):
    ArgNames.append(IdentifierStr)
  if (CurTok != ')'):
    return errorP("Expected ')' in prototype")
  
  # success.
  getNextToken()  # eat ')'.
  
  return PrototypeAST(FnName, ArgNames)


# definition ::= 'def' prototype expression
def ParseDefinition():
  getNextToken() # eat def.
  Proto = ParsePrototype()
  if not Proto: return None

  E = ParseExpression()
  if E:
    return FunctionAST(Proto, E)
  return None

# toplevelexpr ::= expression
def ParseTopLevelExpr():
  E = ParseExpression()
  if E:
    # Make an anonymous proto.
    Proto = PrototypeAST("", [])
    return FunctionAST(Proto, E)
  return None

# external ::= 'extern' prototype
def ParseExtern():
  getNextToken() # eat extern.
  return ParsePrototype()

#===----------------------------------------------------------------------===//
# Top-Level parsing
#===----------------------------------------------------------------------===//

def HandleDefinition():
  if (ParseDefinition()):
    print("Parsed a function definition.", file=sys.stderr)
  else:
    # Skip token for error recovery.
    getNextToken()

def HandleExtern():
  if (ParseExtern()):
    print("Parsed an extern", file=sys.stderr)
  else:
    # Skip token for error recovery.
    getNextToken()

def HandleTopLevelExpression():
  # Evaluate a top-level expression into an anonymous function.
  if (ParseTopLevelExpr()):
    print("Parsed a top-level expr", file=sys.stderr)
  else:
    # Skip token for error recovery.
    getNextToken()

# top ::= definition | external | expression | ';'
def MainLoop():
  while True:
    print("ready> ", end="", file=sys.stderr)
    sys.stderr.flush()
    if CurTok == Token["tok_eof"]:
      return
    elif CurTok == ";":
      getNextToken()
    elif CurTok == Token["tok_def"]:
      HandleDefinition()
    elif CurTok == Token["tok_extern"]:
      HandleExtern()
    else:
      HandleTopLevelExpression()

#===----------------------------------------------------------------------===//
# Main driver code.
#===----------------------------------------------------------------------===//

def main():
  # Install standard binary operators.
  # 1 is lowest precedence.
  BinopPrecedence['<'] = 10
  BinopPrecedence['+'] = 20
  BinopPrecedence['-'] = 20
  BinopPrecedence['*'] = 40  # highest.

  # Prime the first token.
  print("ready> ", end="", file=sys.stderr)
  sys.stderr.flush()
  getNextToken()

  # Run the main "interpreter loop" now.
  MainLoop()

if __name__ == "__main__":
  main()
