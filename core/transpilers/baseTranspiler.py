class BaseTranspiler():
    def __init__(self, filename, target='web', module=False, standardLibs=''):
        self.standardLibs = standardLibs
        self.target = target
        self.filename = filename.split('/')[-1].replace('.w','.d')
        self.module = module

        self.operators = ['**','*','%','/','-','+','andnot','and','or','==','!=','>','<','>=','<=','is','in','&', '<<', '>>'] # in order 
        self.instructions = {
            'printFunc': self.printFunc,
            'expr': self.processVarInit,
            'assign': self.processAssign,
            '+': self.add,
        }
        self.currentScope = {}
        self.source = []
        self.outOfMain = []
        self.nativeTypes = {
            'int':'int',
            'float':'float',
            'unknown':'auto',
        }

    def process(self, token):
        self.instructions[token['opcode']](token)

    def nativeType(self, varType):
        if varType in self.nativeTypes:
            return self.nativeTypes[varType]
        else:
            raise NotImplemented

    def inferType(self, expr):
        if self.typeKnown(expr['type']):
            return expr['type']
        else:
            input(expr)
            return 'unknown'
            raise NotImplemented

    def typeKnown(self, varType):
        if varType in {'unknown', self.nativeType('unknown')}:
            return False
        return True

    def processVarInit(self, token):
        name = token['args'][0]['name']
        varType = token['args'][0]['type']
        if self.typeKnown(varType):
            self.currentScope[name] = {'type':varType}
        self.source.append(self.formatVarInit(name, varType))

    def processVar(self, token):
        name = token['name']
        if self.typeKnown(token['type']):
            varType = token['type']
        elif name in self.currentScope:
            varType = self.currentScope[name]['type']
        else:
            varType = 'unknown'
        return {'value':token['name'], 'type':varType}

    def getValAndType(self, token):
        if 'value' in token and 'type' in token and self.typeKnown(token['type']):
            # Already processed, return
            return token

    def processExpr(self, token):
        #TODO: To be implemented
        args = token['args']
        ops = token['ops']
        if not ops:
            tok = args[0]
            if tok['token'] == 'var':
                return self.processVar(tok)
        elif len(args) == 1 and len(ops) == 1:
            # modifier operator
            return {'value':ops[0]+token['args'][0]['value'],'type':'unknown'}
        else:
            for op in self.operators:
                while op in ops:
                    index = ops.index(op)
                    arg1 = args[index]
                    arg2 = args[index+1]
                    arg1 = self.getValAndType(arg1)
                    arg2 = self.getValAndType(arg2)
                    result = self.instructions[op](arg1, arg2)
                    args[index] = result
                    del ops[index]
                    del args[index+1]
            return args[0]

        return token['args'][0]

    def processAssign(self, token):
        target = token['target']
        if target['token'] == 'var':
            variable = self.processVar(target)
        else:
            raise SyntaxError(f'Assign with variable {target} no supported yet.')
        expr = self.processExpr(token['expr'])
        self.source.append(self.formatAssign(target, expr))
        if self.typeKnown(variable['type']):
            self.currentScope[variable['value']] = {'type':variable['type']}
        else:
            varType = self.inferType(expr)
            if self.typeKnown(varType):
                self.currentScope[variable['value']] = {'type':varType}

    def printFunc(self, token):
        value = self.processExpr(token['expr'])
        self.source.append(self.formatPrint(value))

    def add(self, arg1, arg2):
        t1 = arg1['type']
        t2 = arg2['type']
        if t1 == 'int' and t2 == 'int':
            varType = 'int'
        elif t1 in {'float','int'} and t2 in {'float','int'}:
            varType = 'float'
        return {'value':f'{arg1["value"]} + {arg2["value"]}', 'type':varType}

    def isBlock(self, line):
        for b in self.block:
            if b in line and not line.startswith(self.commentSymbol):
                return True
        return False

    def run(self):
        print('Running')
