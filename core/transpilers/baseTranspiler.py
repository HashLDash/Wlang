from interpreter import Interpreter
from copy import deepcopy
import os
from pprint import pprint

class CurrentScope():
    def __init__(self):
        self.currentScope = {}
        self.localScope = [{}]
        self.local = [False]

    def startLocalScope(self):
        self.local.append(True)
        self.localScope.append({})

    def endLocalScope(self):
        del self.local[-1]
        del self.localScope[-1]

    def addAlias(self, alias, token):
        if self.local[-1]:
            self.localScope[-1][alias] = token
        else:
            self.currentScope[alias] = token
            if isinstance(token, Module):
                self.currentScope[alias] = token

    def add(self, token):
        if not isinstance(token, Var) and token.index is not None:
            if self.local[-1]:
                self.localScope[-1][token.index] = token
            else:
                self.currentScope[token.index] = token

    def update(self, scope):
        self.currentScope.update(scope.currentScope)
        for localScope in scope.localScope:
            self.localScope[-1].update(localScope)

    def values(self, namespace=None, modules=False):
        vals = []
        for token in self.currentScope.values():
            if token.namespace == namespace:
                if not modules and (token.type.isModule or token.type.isPackage):
                    continue
                vals.append(deepcopy(token))
        for localScope in self.localScope:
            for token in localScope.values():
                if token.namespace == namespace:
                    if not modules and (token.type.isModule or token.type.isPackage):
                        continue
                    vals.append(deepcopy(token))
        return vals

    def __repr__(self):
        s = 'SCOPE DUMP\n'
        for i, t in self.currentScope.items():
            s += f'"{i}" {t.type}\n'
        for scope in self.localScope:
            for i, t in scope.items():
                s += f'"{i}" {t.type}\n'
        return s

    def get(self, index):
        for scope in reversed(self.localScope):
            if index in scope:
                return scope[index]
        return self.currentScope[index]

    def inMemory(self, obj):
        try:
            self.get(obj.index)
            return True
        except KeyError:
            return False
        
    def typeOf(self, obj):
        #TODO CLASS INSTANCE IS NOT BEING FOUND
        try:
            return self.get(obj.index).type
        except KeyError:
            return Type('unknown')

class BaseTranspiler():
    def __init__(self, filename, platform='web', framework='', module=False, standardLibs='', debug=False):
        self.debug = debug
        self.standardLibs = standardLibs
        self.platform = platform
        self.framework = framework
        self.libExtension = 'photonExt'
        self.filename = filename.split('/')[-1].replace('.w','.photon')
        self.moduleName = module if module else self.filename.replace('.photon','')
        self.module = module

        self.instructions = {
            'printFunc': self.processPrint,
            'inputFunc': self.processInput,
            'openFunc': self.processOpen,
            'expr': self.processExpr,
            'assign': self.processAssign,
            'augAssign': self.processAugAssign,
            'if': self.processIf,
            'while': self.processWhile,
            'for': self.processFor,
            'forTarget': self.processForTarget,
            'func': self.processFunc,
            'class': self.processClass,
            'return': self.processReturn,
            'breakStatement': self.processBreak,
            'comment': self.processComment,
            'fromImport': self.processFromImport,
            'import': self.processImport,
            'num': self.processNum,
            'var': self.processVar,
            'floatNumber': self.processNum,
            'str': self.processString,
            'call': self.processCall,
            'array': self.processArray,
            'map': self.processMap,
            'keyVal': self.processKeyVal,
            'dotAccess': self.processDotAccess,
            'range': self.processRange,
            'return': self.processReturn,
            'bool': self.processBool,
            'group': self.processGroup,
            'delete': self.processDelete,
            'null': self.processNull,
            'cast': self.processCast,
        }

        self.sequence = Sequence()
        self.currentScope = CurrentScope()
        self.currentNamespace = self.moduleName
        self.importedModules = {}

    #def __getattribute__(self,name):
    #    attr = object.__getattribute__(self, name)
    #    if hasattr(attr, '__call__'):
    #        def newfunc(*args, **kwargs):
    #            print(f'calling %s' %attr.__name__)
    #            result = attr(*args, **kwargs)
    #            return result
    #        return newfunc
    #    else:
    #        return attr

    def loadTokens(self, lang):
        import importlib
        tokens = importlib.import_module(f'.{lang}Tokens', package=__package__)
        for name, token in tokens.__dict__.items():
            globals()[name] = token

    def typeOf(self, obj):
        if obj.type.known:
            return obj.type
        if isinstance(obj, String):
            return Type('str')
        try:
            return self.currentScope.typeOf(obj)
        except Exception as e:
            print(f'Exception in typeOf {e}')
            return Type('unknown')

    def process(self, token):
        if token is not None:
            processedToken = self.instructions[token['opcode']](token)
            if processedToken is not None:
                self.currentScope.add(processedToken)
                for imp in getattr(processedToken, 'imports', []):
                    self.imports.add(imp)
                if token['opcode'] == 'expr':
                    processedToken.mode = 'declaration'
                self.sequence.add(processedToken)

    def preprocess(self, token):
        processedToken = self.instructions[token['token']](token)
        return processedToken

    def processNull(self, token):
        return Null()

    def processNum(self, token):
        return Num(value=token['value'], type=token['type'])

    def processBool(self, token):
        return Bool(value=token['value'])

    def processGroup(self, token):
        return Group(expr=self.preprocess(token['expr']))

    def processString(self, token):
        for i in String.imports:
            self.imports.add(i)
        expressions = self.processTokens(token['expressions'])
        return String(
            value=token['value'],
            expressions=expressions,
        )

    def processCast(self, token):
        return Cast(
            expr=self.preprocess(token['expr']),
            castTo=Type(token['type'])
        )

    def processInput(self, token):
        return Input(
            expr=self.preprocess(token['expr']),
        )

    def processType(self, token):
        tokenType = token
        native = False
        if isinstance(token, dict):
            typeExpr = self.preprocess(token)
            try:
                tokenType = self.currentScope.get(repr(typeExpr)).type.type
            except KeyError:
                # token was not found, maybe it is a native type
                typeExpr.namespace = ''
                tokenType = repr(typeExpr)
                native = True
        elif isinstance(token, str):
            typeName = Var(token, namespace=self.currentNamespace)
            try:
                varInScope = self.currentScope.get(typeName.index)
                tokenType = varInScope.index
            except KeyError:
                # token was not found, maybe it is a native type
                tokenType = token
                native = True
        return tokenType, native

    def processVar(self, token):
        namespace = self.currentNamespace
        indexAccess = self.preprocess(token['indexAccess']) if 'indexAccess' in token else None
        elementType = token.get('elementType', None)
        keyType = token.get('keyType', None)
        valType = token.get('valType', None)
        tokenType = token.get('type', 'unknown')
        # type can be an expression. E.g. dotAccess
        if elementType is not None:
            token['elementType'], _ = self.processType(elementType)
        if keyType is not None:
            token['keyType'], _ = self.processType(keyType)
        if valType is not None:
            token['valType'], _ = self.processType(valType)
        if tokenType is not None and isinstance(tokenType, dict):
            token['type'], token['native'] = self.processType(tokenType)
        varType = Type(**token)
        if not varType.known:
            try:
                varName = Var(token['name'], namespace=namespace)
                varCorrect = self.currentScope.get(varName.index)
                varType = varCorrect.type
                namespace = varCorrect.namespace
            except Exception as e: 
                print(f'didnt find {e} in scope')
                print(self.currentScope)
                pass

        var = Var(
            value=token['name'],
            type=varType,
            namespace=namespace,
            indexAccess=indexAccess,
            attribute=token.get('attribute', None)
        )
        if not var.type.known:
            var.type = self.typeOf(var)
            if not var.type.known and not var.namespace:
                globalVar = deepcopy(var)
                globalVar.namespace = self.moduleName
                globalVar.type = self.typeOf(globalVar)
                if globalVar.type.known:
                    return globalVar
        return var

    def processDelete(self, token):
        return Delete(expr=self.preprocess(token['expr']))

    def processArray(self, token):
        def inferType():
            types = set()
            for element in elements:
                types.add(element.type.type)
            if len(types) == 1:
                elementType = element.type.type
            elif types == {Type('int'), Type('float')}:
                elementType = 'float'
            else:
                elementType = 'unknown'
            return Type('array', elementType=elementType)

        elements = self.processTokens(token['elements'])
        arrayType = Type(**token)
        if not arrayType.known:
            arrayType = inferType()
        array = Array(
            *elements,
            type=arrayType,
        )
        for i in array.imports:
            self.imports.add(i)
        self.listTypes.add(array.type.elementType.type)
        return array

    def processMap(self, token):
        def inferType():
            keyTypes = set()
            valTypes = set()
            for keyVal in keyVals:
                keyTypes.add(keyVal.key.type)
                valTypes.add(keyVal.val.type)
            if len(keyTypes) == 0:
                return Type('map')
            if len(keyTypes) == 1:
                keyType = keyVal.key.type
            else:
                raise NotImplemented('Keys of different types not implemented yet')
            if len(valTypes) == 1:
                valType = keyVal.val.type
            else:
                raise NotImplemented('Vals of different types not implemented yet')
            return Type('map', keyType=keyType, valType=valType)

        keyVals = self.processTokens(token['elements'])
        mapType = Type(**token)
        if not mapType.known:
            mapType = inferType()
        obj = Map(
            *keyVals,
            type=mapType,
        )
        for i in obj.imports:
            self.imports.add(i)
        if obj.type.known:
            self.dictTypes.add((obj.type.keyType.type, obj.type.valType.type))
        return obj

    def processKeyVal(self, token):
        return KeyVal(
            key=self.preprocess(token['key']),
            val=self.preprocess(token['val'])
        )

    def processExpr(self, token):
        return Expr(
            *[self.preprocess(t) for t in token['args']],
            ops = token['ops']
        )

    def processAssign(self, token):
        target = self.preprocess(token['target'])
        value = self.preprocess(token['expr'])
        inMemory = self.currentScope.inMemory(target)
        if inMemory:
            target.type = self.typeOf(target)

        cast = None
        if target.type.known and value.type.known:
            if target.type != value.type:
                cast = target.type
        if not target.type.known:
            target.type = value.type
        if not value.type.known:
            value.type = target.type
        assign = Assign(
            target=target,
            value=value,
            namespace=self.currentNamespace,
            inMemory=inMemory,
            cast=cast,
        )
        value.prepare()
        for i in value.imports:
            self.imports.add(i)
        if value.type.type == 'map':
            self.dictTypes.add((value.type.keyType.type, value.type.valType.type))
        if value.type.type == 'array':
            self.listTypes.add(value.type.elementType.type)
        return assign

    def processAugAssign(self, token):
        return AugAssign(
            target=self.preprocess(token['target']),
            expr=self.preprocess(token['expr']),
            operator=token['operator']
        )

    def processIf(self, token):
        #TODO: create context manager for localScope
        self.currentScope.startLocalScope()
        ifBlock = self.processTokens(token['block'], addToScope=True)
        self.currentScope.endLocalScope()
        elifs = []
        if 'elifs' in token:
            for e in token['elifs']:
                self.currentScope.startLocalScope()
                elifs.append(
                    Elif(
                        self.preprocess(e['expr']),
                        self.processTokens(e['elifBlock'], addToScope=True)
                    )
                )
                self.currentScope.endLocalScope()
        self.currentScope.startLocalScope()
        elseBlock = None if not 'else' in token else self.processTokens(token['else'], addToScope=True)
        self.currentScope.endLocalScope()
        return If(
            expr = self.preprocess(token['expr']),
            ifBlock = ifBlock,
            elifs = elifs,
            elseBlock = elseBlock,
        )

    def processWhile(self, token):
        return While(
            expr=self.preprocess(token['expr']),
            block=self.processTokens(token['block'], addToScope=True)
        )

    def processFor(self, token):
        iterable = self.preprocess(token['iterable'])
        self.currentScope.startLocalScope()
        args = self.processTokens(token['vars'])
        if isinstance(iterable, Range):
            if len(args) == 1:
                args[0].type = iterable.type
            elif len(args) == 2:
                args[0].type = Type('int')
                args[1].type = iterable.type
            else:
                raise SyntaxError('For with range cannot have more than 2 variables')
        elif isinstance(iterable, Expr):
            if iterable.type.type == 'array':
                if len(args) == 1:
                    args[0].type = Type(iterable.type.elementType)
                elif len(args) == 2:
                    args[0].type = Type('int')
                    args[1].type = Type(iterable.type.elementType)
            elif iterable.type.type == 'map':
                if len(args) == 1:
                    args[0].type = Type(iterable.type.keyType)
                elif len(args) == 2:
                    args[0].type = Type(iterable.type.keyType)
                    args[1].type = Type(iterable.type.valType)
            elif iterable.type.type == 'str':
                if len(args) == 1:
                    args[0].type = Type('str')
                elif len(args) == 2:
                    args[0].type = Type('int')
                    args[1].type = Type('str')
        else:
            raise ValueError(f'Iterable with type {type(iterable)} not supported in processFor')
        for t in args:
            self.currentScope.add(Assign(target=t, value=Num(0, t.type)))
        code=self.processTokens(token['block'], addToScope=True)
        self.currentScope.endLocalScope()
        forToken = For(
            code=code,
            args=args,
            iterable=iterable,
        )
        for i in forToken.imports:
            self.imports.add(i)
        return forToken

    def processForTarget(self, token):
        targets = []
        for t in token['target']['args']:
            targets.append(t['name'].lower() in [self.lang, self.platform])
        ops = token['target']['ops'].copy()
        for op in ['and', 'or']:
            while op in ops:
                index = ops.index(op)
                arg1 = targets[index]
                arg2 = targets[index+1]
                if op == 'and':
                    targets[index] = arg1 and arg2
                elif op == 'or':
                    targets[index] = arg1 or arg2
                else:
                    raise RuntimeError(f'Operator {op} not allowed in forTarget')
                del ops[index]
                del targets[index+1]
            
        if targets[0]:
            block = self.processTokens(token['block'], addToScope=True)
        else:
            block = []
        return Sequence(block)

    def processCall(self, token, className=None):
        name = self.preprocess(token['name'])
        namespace = name.namespace
        try:
            # always search in the current module's scope
            name.namespace = self.moduleName
            callIndex = name.index
            call = self.currentScope.get(callIndex)
        except KeyError:
            call = None
        signature = []
        if call:
            if call.type.isModule:
                module = call
                if not module.native:
                    name.namespace = module.namespace
                    call = module.scope.get(name.index)
                    if not call.type.isModule:
                        signature = call.signature
                        name = call.name
                    else:
                        namespace = ''
                else:
                    namespace = ''
            else:
                namespace = call.name.namespace
                if call.type.isClass:
                    call = call.new
                    name.namespace = namespace
                if getattr(call, 'args', None) is not None and (call.args or call.kwargs):
                    for arg in call.args.args:
                        arg.namespace = ''
                        signature.append(arg)
                    for kwarg in call.kwargs.kwargs:
                        kwarg.namespace = ''
                        signature.append(kwarg)
        return Call(
            name=name,
            args=self.processTokens(token['args']),
            kwargs=self.processTokens(token['kwargs']),
            signature=signature,
            namespace=namespace,
        )

    def processDotAccess(self, token):
        initialType = self.preprocess(token['dotAccess'][0]).type
        chain = self.processTokens(token['dotAccess'])
        if getattr(chain[0], 'indexAccess', None) is not None:
            if initialType.type == 'array':
                initialType = initialType.elementType
            elif initialType.type == 'map':
                initialType = initialType.valType
        else:
            chain[0].type = initialType

        currentType = initialType
        parsedChain = [chain[0]]
        for n, c in enumerate(chain[1:]):
            c.namespace = ''
            c.prepare()
            if currentType.isClass:
                try:
                    #scope = self.currentScope.get(currentType.type).__dict__
                    scope = self.classes[currentType.type].__dict__
                except KeyError:
                    pass
                else:
                    if c.index in scope['parameters']:
                        c.type = scope['parameters'][c.index].type
                        if c.type.type == 'array' and c.indexAccess:
                            currentType = c.type.elementType
                            parsedChain.append(c)
                            continue
                    elif isinstance(c, Call):
                        methodIndex = f'{c.name}'
                        if methodIndex in scope['methods']:
                            c.type = scope['methods'][methodIndex].type
                            c.signature = scope['methods'][methodIndex].signature
                            parsedChain = [DotAccess(parsedChain, currentType)]
                            c.args.args.insert(0, parsedChain[0])
                            currentType = c.type
                            continue
            elif currentType.type == 'map': #TODO: Make this part of the token class
                if f'{c}' == 'len':
                    c.type = Type('int')
            elif currentType.type == 'array': #TODO: Make this part of the token class
                if f'{c}' == 'len':
                    c.type = Type('int')
            elif currentType.type == 'file': #TODO: Make this part of the token class
                if isinstance(c, Call) and f'{c.name}' == 'read':
                    c.type = Type('str')
            elif currentType.type == 'package':
                package = self.currentScope.get(parsedChain[-1].index)
                c = package.get([c.index])
            elif currentType.type == 'module':
                moduleIndex = Var(currentType.name, namespace=self.moduleName).index
                module = self.currentScope.get(moduleIndex)
                if isinstance(c, Call):
                    c.name.namespace = self.moduleName + '__' + module.namespace
                    if module.native:
                        c.type = Type('unknown', native=True)
                        c.name.namespace = ''
                        c.signature = []
                    else:
                        #TODO: maybe the class should have a signature precomputed
                        # instead of doing this here and in processCall
                        input(module.scope)
                        cOriginal = module.scope.get(c.name.index)
                        signature = []
                        if isinstance(cOriginal, Class):
                            for arg in cOriginal.new.args.args:
                                arg.namespace = ''
                                signature.append(arg)
                            for kwarg in cOriginal.new.kwargs.kwargs:
                                kwarg.namespace = ''
                                signature.append(kwarg)
                            c.signature = signature
                        c.type = cOriginal.type
                elif isinstance(c, Var):
                    c.namespace = self.moduleName + '__' + module.namespace
                    if module.native:
                        c.type = Type('unknown', native=True)
                        c.namespace = ''
                    elif c.type.isModule:
                        pass
                    else:
                        c.type = module.scope.get(c.index).type
            parsedChain.append(c)

            currentType = c.type

        dotAccess = DotAccess(
            chain,
            type=currentType,
            namespace=self.currentNamespace,
        )
        for i in dotAccess.imports:
            self.imports.add(i)
        return dotAccess

    def processClass(self, token):
        self.currentScope.startLocalScope()
        className = Var(token['name'], namespace=self.currentNamespace)
        self.currentScope.add(
            Assign(
                target=Var('self', repr(className)),
                value=Call(Var(className.name))))
        parameters = {}
        methods = {}
        newArgs = []
        newKwargs = []
        args = self.processTokens(token['args'])
        parentMethods = {}
        new = Function(name=Var(f'new', namespace=className))
        methods[new.name.value] = new
        self.classes[repr(className)] = Class(
            name=className,
            args=args,
            new=new,
            parameters=parameters
        )
        # First pass for type inference
        parentClass = None
        for arg in args:
            arg.namespace = self.currentNamespace
            parentClass = self.currentScope.get(arg.index)
            parameters.update(parentClass.parameters)
            newArgs = newArgs + parentClass.new.args.args
            newKwargs = newKwargs + parentClass.new.kwargs.kwargs
        if parentClass is not None:
            self.currentScope.add(
                Assign(
                    target=Var('super', repr(parentClass.name)),
                    value=Call(Var(parentClass.name))))
        for t in token['block']:
            try:
                oldNamespace = self.currentNamespace
                oldScope = deepcopy(self.currentScope.localScope[-1])
                nScopes = len(self.currentScope.localScope)
                t = self.preprocess(t)
            except KeyError as e:
                # we must recover the namespace when
                # it breaks in the middle of execution
                # and the scope (discard deeper scopes)
                self.currentNamespace = oldNamespace
                self.currentScope.localScope = self.currentScope.localScope[:nScopes]
                self.currentScope.localScope[-1] = oldScope
                continue
            if isinstance(t, Function):
                if t.name.value == 'new':
                    new = t
                    new.kwargs.kwargs = newKwargs + new.kwargs.kwargs
                    for kw in new.kwargs.kwargs:
                        if kw.target.attribute:
                            parameters[kw.index] = kw
                else:
                    t.args.args.insert(0, Var('self', repr(className)))
                    t.signature.insert(0, Var('self', repr(className)))
                parameters[t.name.value] = t
                t.namespace = className
                t.name.namespace = className
                #t.prepare()
                methods[t.name.value] = t
            elif isinstance(t, Assign):
                t.namespace = ''
                parameters[t.index] = t
            elif isinstance(t, Expr):
                t.namespace = ''
                parameters[repr(t)] = t
        if new is None:
            new = Function(name=Var(f'new', namespace=className))
            methods[new.name.value] = new
        new.name.type = Type(repr(className))
        self.currentScope.add(
            Class(
                name=className,
                args=self.processTokens(token['args']),
                parameters = parameters,
                new = new,
        ))
        # Second pass for code generation
        new = None
        thisClassCode = Scope(self.processTokens(token['block']))
        for t in thisClassCode.sequence:
            if isinstance(t, Function):
                if t.name.value == 'new':
                    new = t
                    new.args.args = newArgs + new.args.args
                    new.kwargs.kwargs = newKwargs + new.kwargs.kwargs
                    for kw in t.kwargs.kwargs:
                        if kw.target.attribute:
                            parameters[kw.index] = kw
                else:
                    t.args.args.insert(0, Var('self', repr(className)))
                    t.signature.insert(0, Var('self', repr(className)))
                parameters[t.name.value] = t
                t.namespace = className
                t.name.namespace = className
                #t.prepare()
                methods[t.name.value] = t
            elif isinstance(t, Assign):
                t.namespace = ''
                parameters[t.index] = t
            elif isinstance(t, Expr):
                t.namespace = ''
                parameters[repr(t)] = t
        if new is None:
            new = Function(
                name=Var(f'new',namespace=className),
                args=newArgs,
                kwargs=newKwargs)
        new.name.type = Type(repr(className))
        methods[new.name.value] = new
        classToken = Class(
            name=className,
            args=self.processTokens(token['args']),
            parameters=parameters,
            methods=methods,
            new=new,
        )
        self.currentScope.endLocalScope()
        self.classes[repr(className)] = classToken
        return classToken

    def processFunc(self, token):
        # kwargs must be processed in the current namespace
        # because the values must be in the namespace
        kwargs=self.processTokens(token['kwargs'])
        for kwarg in kwargs:
            # target namespace must be empty because it's
            # an argument name
            kwarg.namespace = ''
        self.currentScope.startLocalScope()
        oldNamespace = self.currentNamespace
        self.currentNamespace = ''
        args=self.processTokens(token['args'])
        for t in args + kwargs:
            self.currentScope.add(t)
        code=self.processTokens(token['block'], addToScope=True)
        self.currentNamespace = oldNamespace
        self.currentScope.endLocalScope()
        returnType = Type(token['type'])
        if not returnType.known:
            types = []
            for t in code:
                if isinstance(t, Return):
                    types.append(t.type.type)
            if len(set(types)) == 1:
                returnType = t.type
            elif len(set(types)) == 2 and 'int' in types and 'float' in types:
                returnType = Type('float')
        signature = []
        for arg in deepcopy(args):
            arg.namespace = ''
            signature.append(arg)
        for kwarg in deepcopy(kwargs):
            kwarg.value.namespace = oldNamespace
            signature.append(kwarg)
        return Function(
            name=Var(
                token['name'],
                type=returnType,
                namespace=self.currentNamespace,
            ),
            args=args,
            kwargs=kwargs,
            code=code,
            signature=signature,
        )

    def processRange(self, token):
        return Range(
            initial=self.preprocess(token['from']),
            final=self.preprocess(token['to']),
            step=self.preprocess(token['step']) if 'step' in token else Num(1, 'int'),
        )

    def processReturn(self, token):
        return Return(
            expr=self.preprocess(token['expr'])
        )

    def processBreak(self, token):
        return Break()

    def processComment(self, token):
        return Comment()

    def processFromImport(self, token):
        return self.processImport(token, fromImport=True)

    def listdir(self, path=''):
        try:
            return os.listdir(path)
        except FileNotFoundError:
            return []

    def processImport(self, token, fromImport=False):
        folder = './'
        native = token['native']
        scope = CurrentScope()
        moduleExpr = self.preprocess(token['module'])
        moduleExpr.namespace = ''
        isPackage = False
        if token['module']['args'][0]['token'] == 'dotAccess':
            isPackage = True
            names = [n['name'] for n in token['module']['args'][0]['dotAccess']]
            folder = './' + '/'.join(names[:-1]) + '/'
            moduleExpr = Var(value=names[-1], namespace='')
            package = Package(names, namespace=self.currentNamespace)
            self.currentScope.add(package)
        else:
            names = [f'{moduleExpr}']
        moduleExpr.namespace = self.currentNamespace
        symbols = token.get('symbols', [])
        if symbols:
            if len(token['symbols']) == 1 and token['symbols'][0].get('operator') == '*':
                symbols = '*'
            else:
                symbols = self.processTokens(token['symbols'])
        if native:
            # System library import
            filename = repr(moduleExpr)
            namespace = ''
        elif f"{names[-1]}.w" in self.listdir(folder) + self.listdir(f'{self.standardLibs}/{folder}'):
            if f"{names[-1]}.w" in self.listdir(folder):
                # Local module import
                moduleExpr.namespace = ''
                filename = f'{folder}{names[-1]}.w'
                moduleExpr.namespace = self.currentNamespace
            else:
                filename = f'{self.standardLibs}/{folder}{names[-1]}.w'
                # Photon module import
                # Inject assets folder
                #raise SyntaxError('Standard lib import not implemented yet.')
            if filename not in self.importedModules:
                interpreter = Interpreter(
                        filename=filename,
                        lang=self.lang,
                        module=self.moduleName + '__' + '__'.join(names),
                        platform=self.platform,
                        framework=self.framework,
                        standardLibs=self.standardLibs,
                        transpileOnly=True,
                        debug=self.debug)
                interpreter.engine.importedModules = deepcopy(self.importedModules)
                print('Importing module')
                interpreter.run()
                print('Done')
                self.classes.update(interpreter.engine.classes)
                #self.currentScope.update(interpreter.engine.currentScope)
                scope = interpreter.engine.currentScope
                self.imports = self.imports.union(interpreter.engine.imports)
                self.links = self.links.union(interpreter.engine.links)
                self.sequence = self.sequence + interpreter.engine.sequence
                #self.importedModules = interpreter.engine.importedModules
                if symbols == '*':
                    symbols = interpreter.engine.currentScope.values(namespace=self.moduleName + '__' + '__'.join(names))
                for symbol in symbols:
                    symbol.namespace = self.moduleName + '__' + '__'.join(names)
                    t = scope.get(symbol.index)
                    symbol.namespace = self.currentNamespace
                    self.currentScope.addAlias(symbol.index, t)
            else:
                scope = self.importedModules[filename].scope
            namespace = '__'.join(names)
        elif f"{names[-1]}.{self.libExtension}" in self.listdir(self.standardLibs + f'/native/{self.lang}/'):
            # Native Photon lib module import
            raise SyntaxError('Native Photon lib module import not implemented yet.')
        elif f"{names[-1]}.{self.libExtension}" in self.listdir():
            # Native Photon local module import
            raise SyntaxError('Native Photon local module import not implemented yet.')
        else:
            raise RuntimeError(f'Cannot import {names[-1]}.')
        module = Module(
            Var('__'.join(names), namespace=self.currentNamespace),
            '__'.join(names),
            namespace,
            native=native,
            scope=scope,
            filepath=filename
        )
        if filename not in self.importedModules:
            self.importedModules[filename] = module
            print(f'Imported Modules from {self.moduleName}')
            input(self.importedModules)
            if isPackage:
                package.addModule(names, module)
        for i in module.imports:
            self.imports.add(i)
        for i in module.links:
            self.links.add(i)
        return module

    def processTokens(self, tokens, addToScope=False):
        if addToScope:
            processedTokens = []
            for t in tokens:
                processedToken = self.preprocess(t)
                self.currentScope.add(processedToken)
                print(self.currentScope)
                processedTokens.append(processedToken)
            return processedTokens
        return [self.preprocess(t) for t in tokens]

    def processOpen(self, token):
        args = self.processTokens(token['args'])
        return Open(
            args = args,
        )
    
    def processPrint(self, token):
        args = self.processTokens(token['args'])
        return Print(
            args = args,
        )

    def run(self):
        raise RuntimeError('Run not implemented for this target')
