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
                if isinstance(token, Module):
                    self.currentScope[token.name] = token

    def update(self, scope):
        self.currentScope.update(scope.currentScope)
        for localScope in scope.localScope:
            self.localScope[-1].update(localScope)

    def values(self, namespace=None):
        vals = []
        for token in self.currentScope.values():
            if token.namespace == namespace:
                vals.append(deepcopy(token))
        for localScope in self.localScope:
            for token in localScope.values():
                if token.namespace == namespace:
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
    def __init__(self, filename, target='web', module=False, standardLibs='', debug=False):
        self.debug = debug
        self.standardLibs = standardLibs
        self.target = target
        self.libExtension = 'photonExt'
        self.filename = filename.split('/')[-1].replace('.w','.photon')
        self.moduleName = self.filename.replace('.photon','')
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
        self.importedModules = []

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

    def processVar(self, token):
        namespace = self.currentNamespace
        indexAccess = self.preprocess(token['indexAccess']) if 'indexAccess' in token else None
        elementType = token.get('elementType', None)
        tokenType = token.get('type', 'unknown')
        # type can be an expression. E.g. dotAccess
        if elementType is not None and isinstance(elementType, dict):
            typeExpr = self.preprocess(elementType)
            token['elementType'] = self.currentScope.get(repr(typeExpr)).type.type
        elif tokenType is not None and isinstance(tokenType, dict):
            typeExpr = self.preprocess(tokenType)
            token['type'] = self.currentScope.get(repr(typeExpr)).type.type
        varType = Type(**token)

        #TODO: do the same for map
        if varType.type == 'array':
            if varType.elementType.isClass:
                try:
                    if not isinstance(elementType, dict):
                        # elementType was not a token and not already processed, proceed
                        typeName = Var(varType.elementType.type, namespace=self.moduleName)
                        # if this doesn't fail it's because the type is a class
                        c = self.currentScope.get(typeName.index)
                        varType = Type('array', elementType=c.index)
                        self.listTypes.add(c.index)
                    else:
                        self.listTypes.add(varType.elementType.type)
                except KeyError as e:
                    varType.native = True
        elif varType.isClass:
            try:
                typeName = Var(token['type'], namespace=self.moduleName)
                # if this doesn't fail it's because the type is a class
                c = self.currentScope.get(typeName.index)
                varType = Type(c.index)
            except KeyError:
                varType.native = True

        # correct namespace if this token was imported
        var = Var(value=token['name'], namespace=self.currentNamespace)
        try:
            var = self.currentScope.get(var.index)
            namespace = var.namespace
            varType = var.type
        except KeyError:
            # Not already processed, continue
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
        target = token['target'].lower()
        if target in [self.lang, self.target]:
            block = self.processTokens(token['block'], addToScope=True)
        else:
            block = []
        return Sequence(block)

    def processCall(self, token, className=None):
        name = self.preprocess(token['name'])
        namespace = self.currentNamespace
        try:
            call = self.currentScope.get(name.index)
        except KeyError:
            call = None
        signature = []
        if call:
            if not call.type.isModule:
                namespace = call.name.namespace
                if call.type.isClass:
                    call = self.currentScope.get(call.index).new
                if getattr(call, 'args', None) is not None and (call.args or call.kwargs):
                    for arg in call.args.args:
                        arg.namespace = ''
                        signature.append(arg)
                    for kwarg in call.kwargs.kwargs:
                        kwarg.namespace = ''
                        signature.append(kwarg)
            else:
                call.namespace = namespace
                call = self.currentScope.get(call.index)
                if not call.type.isModule:
                    signature = call.signature
                    name = call.name
                else:
                    namespace = ''
        return Call(
            name=name,
            args=self.processTokens(token['args']),
            kwargs=self.processTokens(token['kwargs']),
            signature=signature,
            namespace=namespace,
        )

    def processDotAccess(self, token):
        initialType = self.preprocess(token['dotAccess'][0]).type
        oldNamespace = self.currentNamespace
        chain = self.processTokens(token['dotAccess'])
        chain[0].type = initialType
        currentType = initialType
        parsedChain = [chain[0]]
        for n, c in enumerate(chain[1:]):
            c.namespace = ''
            c.prepare()
            if currentType.isClass:
                try:
                    scope = self.currentScope.get(currentType.type).__dict__
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
            elif currentType.type == 'module':
                module = self.currentScope.get(currentType.name)
                if isinstance(c, Call):
                    c.name.namespace = module.namespace
                    if module.native:
                        c.type = Type('unknown', native=True)
                        c.name.namespace = ''
                    else:
                        #TODO: maybe the class should have a signature precomputed
                        # instead of doing this here and in processCall
                        cOriginal = self.currentScope.get(c.name.index)
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
                    c.namespace = module.namespace
                    if module.native:
                        c.type = Type('unknown', native=True)
                        c.namespace = ''
                    else:
                        c.type = self.currentScope.get(c.index).type
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
        new = None
        newArgs = []
        newKwargs = []
        args = self.processTokens(token['args'])
        parentMethods = {}
        # First pass for type inference
        parentClass = None
        for arg in args:
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
        #TODO: relative path and package imports
        #TODO: this method and processImport need to be refactored
        folder = None
        native = False
        moduleExpr = self.preprocess(token['module'])
        moduleExpr.namespace = ''
        name = f'{moduleExpr}'
        moduleExpr.namespace = self.currentNamespace
        if len(token['symbols']) == 1 and token['symbols'][0].get('operator') == '*':
            symbols = '*'
        else:
            symbols = self.processTokens(token['symbols'])
        if f"{name}.w" in os.listdir(folder) + os.listdir(self.standardLibs):
            if f"{name}.w" in os.listdir(folder):
                # Local module import
                moduleExpr.namespace = ''
                filename = f'{name}.w'
                moduleExpr.namespace = self.currentNamespace
            else:
                filename = f'{self.standardLibs}/{name}.w'
                # Photon module import
                # Inject assets folder
                #raise SyntaxError('Standard lib import not implemented yet.')
            if filename in self.importedModules:
                return
            self.importedModules.append(filename)
            interpreter = Interpreter(
                    filename=filename,
                    lang=self.lang,
                    target=self.target,
                    module=True,
                    standardLibs=self.standardLibs,
                    transpileOnly=True,
                    debug=self.debug)
            interpreter.engine.importedModules = deepcopy(self.importedModules)
            interpreter.run()
            self.classes.update(interpreter.engine.classes)
            self.currentScope.update(interpreter.engine.currentScope)
            self.imports = self.imports.union(interpreter.engine.imports)
            self.links = self.links.union(interpreter.engine.links)
            self.sequence = self.sequence + interpreter.engine.sequence
            self.importedModules = interpreter.engine.importedModules
            namespace = name
            if symbols == '*':
                symbols = interpreter.engine.currentScope.values(namespace=namespace)
            for symbol in symbols:
                symbol.namespace = name
                t = self.currentScope.get(symbol.index)
                symbol.namespace = self.currentNamespace
                self.currentScope.addAlias(symbol.index, t)
        elif f"{name}.{self.libExtension}" in os.listdir(self.standardLibs + f'/native/{self.lang}/'):
            # Native Photon lib module import
            raise SyntaxError('Native Photon lib module import not implemented yet.')
        elif f"{name}.{self.libExtension}" in os.listdir():
            # Native Photon local module import
            raise SyntaxError('Native Photon local module import not implemented yet.')
        else:
            raise RuntimeError(f'Cannot import {name}.')
            #raise SyntaxError('System library import not implemented yet.')
        module = Module(moduleExpr, name, namespace, native=native)
        for i in module.imports:
            self.imports.add(i)
        for i in module.links:
            self.links.add(i)
        return module

    def processImport(self, token):
        #TODO: relative path and package imports
        folder = None
        native = token['native']

        moduleExpr = self.preprocess(token['expr'])
        moduleExpr.namespace = ''
        if token['expr']['args'][0]['token'] == 'dotAccess':
            names = [n['name'] for n in token['expr']['args'][0]['dotAccess']]
            name = '/'.join(names)
            moduleExpr = Var(value=names[-1], namespace='')
        else:
            name = f'{moduleExpr}'
        moduleExpr.namespace = self.currentNamespace
        if native:
            # System library import
            namespace = ''
        elif f"{name}.w" in os.listdir(folder) + os.listdir(self.standardLibs):
            if f"{name}.w" in os.listdir(folder):
                # Local module import
                moduleExpr.namespace = ''
                filename = f'{name}.w'
                moduleExpr.namespace = self.currentNamespace
            else:
                filename = f'{self.standardLibs}/{name}.w'
                # Photon module import
                # Inject assets folder
                #raise SyntaxError('Standard lib import not implemented yet.')
            if filename in self.importedModules:
                return
            self.importedModules.append(filename)
            interpreter = Interpreter(
                    filename=filename,
                    lang=self.lang,
                    target=self.target,
                    module=True,
                    standardLibs=self.standardLibs,
                    transpileOnly=True,
                    debug=self.debug)
            interpreter.engine.importedModules = deepcopy(self.importedModules)
            interpreter.run()
            self.classes.update(interpreter.engine.classes)
            self.currentScope.update(interpreter.engine.currentScope)
            self.imports = self.imports.union(interpreter.engine.imports)
            self.links = self.links.union(interpreter.engine.links)
            self.sequence = self.sequence + interpreter.engine.sequence
            self.importedModules = interpreter.engine.importedModules
            namespace = name
        elif f"{name}.{self.libExtension}" in os.listdir(self.standardLibs + f'/native/{self.lang}/'):
            # Native Photon lib module import
            raise SyntaxError('Native Photon lib module import not implemented yet.')
        elif f"{name}.{self.libExtension}" in os.listdir():
            # Native Photon local module import
            raise SyntaxError('Native Photon local module import not implemented yet.')
        else:
            raise RuntimeError(f'Cannot import {name}.')
            #raise SyntaxError('System library import not implemented yet.')
        module = Module(moduleExpr, name, namespace, native=native)
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
