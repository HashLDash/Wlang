patterns = {
  ('hashtag',): comment,
  ('singleQuote',): string,
  ('doubleQuote',): string,
  ('type', 'beginBlock', 'num'): arrayType,
  ('var', 'beginBlock', 'num'): arrayType,
  ('type', 'beginBlock', 'type'): mapType,
  ('type', 'beginBlock', 'var'): mapType,
  ('var', 'beginBlock', 'type'): mapType,
  ('var', 'beginBlock', 'var'): mapType,
  ('var', 'var'): typeDeclaration,
  ('type', 'var'): typeDeclaration,
  ('var', 'underline', 'var'): var,
  ('underline', 'var'): var,
  ('var', 'underline'): var,
  ('underline',): var,
  ('num', 'dot', 'num'): floatNumber,
  ('num', 'dot'): floatNumber,
  ('expr', 'dot', 'expr'): dotAccess,
  ('lparen', 'expr', 'rparen'): group,
  ('equal', 'equal'): operator,
  ('equal', 'operator'): operator,
  ('operator', 'equal'): operator,
  ('operator', 'operator'): operator,
  ('expr', 'lparen', 'rparen'): call,
  ('expr', 'lparen', 'expr', 'rparen'): call,
  ('expr', 'lparen', 'args', 'rparen'): call,
  ('num',): expr,
  ('floatNumber',): expr,
  ('var',): expr,
  ('dotAccess',): expr,
  ('group',): expr,
  ('num', 'operator', 'num'): expr,
  ('num', 'operator', 'var'): expr,
  ('num', 'operator', 'expr'): expr,
  ('var', 'operator', 'num'): expr,
  ('var', 'operator', 'var'): expr,
  ('var', 'operator', 'expr'): expr,
  ('expr', 'operator', 'num'): expr,
  ('expr', 'operator', 'var'): expr,
  ('expr', 'operator', 'expr'): expr,
  ('operator', 'expr'): expr,
  ('expr', 'lbracket', 'expr', 'rbracket'): indexAccess,
  ('lbracket', 'args', 'rbracket'): array,
  ('lbracket', 'rbracket'): array,
  ('returnStatement',): funcReturn,
  ('returnStatement', 'expr'): funcReturn,
  ('importStatement', 'expr'): imports,
  ('expr', 'dot', 'dot', 'expr'): rangeExpr,
  ('expr', 'dot', 'dot', 'expr', 'dot', 'dot', 'expr'): rangeExpr,
  ('ifStatement', 'expr', 'beginBlock'): ifelif,
  ('elifStatement', 'expr', 'beginBlock'): ifelif,
  ('forStatement', 'expr', 'inStatement', 'range', 'beginBlock'): forLoop,
  ('forStatement', 'expr', 'inStatement', 'expr', 'beginBlock'): forLoop,
  ('whileStatement', 'expr', 'beginBlock'): whileLoop,
  ('args', 'comma', 'args'): args,
  ('args', 'comma', 'expr'): args,
  ('expr', 'comma', 'args'): args,
  ('expr', 'comma', 'expr'): args,
  ('expr', 'operator', 'equal', 'expr'): augAssign,
  ('expr', 'equal', 'expr'): assign,
  ('defStatement', 'expr', 'lparen', 'expr', 'rparen', 'beginBlock'): function,
  ('defStatement', 'expr', 'lparen', 'args', 'rparen', 'beginBlock'): function,
  ('defStatement', 'expr', 'lparen', 'rparen', 'beginBlock'): function,
  ('classStatement', 'expr', 'lparen', 'rparen', 'beginBlock'): classDefinition,
  ('classStatement', 'expr', 'lparen', 'expr', 'rparen', 'beginBlock'): classDefinition,
  ('classStatement', 'expr', 'lparen', 'args', 'rparen', 'beginBlock'): classDefinition,
  ('print', 'lparen', 'expr', 'rparen'): printFunc,
  ('print', 'lparen', 'rparen'): printFunc,
  ('input', 'lparen', 'expr', 'rparen'): inputFunc,
  ('input', 'lparen', 'rparen'): inputFunc,
}