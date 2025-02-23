# Photon Interpreter
#
# This script funcion is:
#   - Get lines of code from a file or interpreter
#   - Call the parser to generate tokens and the struct   
#   - Call the engine to Process the struct
#   - Run the processed struct

from photonParser import parse, assembly, showError
from photonParser import debug as debugFunc
import sys

class Interpreter():
    def __init__(self, filename='', lang='c', platform=sys.platform, framework='', module=False, standardLibs='', debug=False, transpileOnly=False):
        self.debug = debug
        if lang == 'c':
            from transpilers.cTranspiler import Transpiler
        elif lang in {'py', 'python'}:
            from transpilers.pyTranspiler import Transpiler
        elif lang == 'dart':
            from transpilers.dartTranspiler import Transpiler
        elif lang in ['js', 'javascript']:
            from transpilers.jsTranspiler import Transpiler
        elif lang == 'ts':
            from transpilers.tsTranspiler import Transpiler
        elif lang == 'haxe':
            from transpilers.haxeTranspiler import Transpiler
        elif lang == 'd':
            from transpilers.dTranspiler import Transpiler
        else:
            print(f'Invalid language {lang}')
            sys.exit()
        self.filename = filename
        if filename:
            self.engine = Transpiler(filename=filename, platform=platform, framework=framework, module=module, standardLibs=standardLibs, debug=debug)
            self.input = self.file
            try:
                # Read utf8 but write as the default on the OS
                with open(filename,'r',encoding='utf8') as f:
                    self.source = [line for line in f]
            except UnicodeDecodeError:
                with open(filename,'r') as f:
                    self.source = [line for line in f]
            except FileNotFoundError as e:
                print(f"File not found: can't open file {filename}: {e}")
                sys.exit()
        else:
            try:
                import readline
            except ModuleNotFoundError:
                # Windows doesn't have readline
                try:
                    import pyreadline
                except ModuleNotFoundError:
                    # Run without history and arrow key functionality
                    pass
            from engines.pyEngine import Engine
            self.engine = Engine(filename=filename, platform=platform, framework=framework, module=module, standardLibs=standardLibs)
            self.input = self.console
        self.end = False
        self.processing = True
        self.transpileOnly = transpileOnly
        self.lineNumber = 0

    def console(self, glyph='>>> '):
        return input(glyph)

    def file(self, *args):
        try:
            line = self.source.pop(0)
            self.lineNumber += 1
            while line.strip() == '':
                line = self.source.pop(0)
                self.lineNumber += 1
            rest = ''
            count = 1 # checking where is the end of the function call. When it ends, count is 0
            while line[-2:] in {'(\n',',\n','{\n','[\n'} or rest.lstrip() in  {')\n',']\n','}\n'} and count > 0:
                line = line.replace('\n','')
                rest = self.source.pop(0).lstrip()
                self.lineNumber += 1
                while rest.strip() == '':
                    rest = self.source.pop(0)
                    self.lineNumber += 1
                if rest.lstrip() in {')\n',']\n','}\n'}:
                    if ')' in rest:
                        count -= 1
                    if line[-1] == ',':
                        line = line[:-1]
                    rest = rest.lstrip()
                line += rest
            return line
        except IndexError:
            if self.processing:
                return ''
            else:
                if not self.transpileOnly:
                    self.engine.run()
                    sys.exit()
                else:
                    self.engine.write()
                    self.classes = self.engine.classes
                    return 'exit'
    
    def getBlock(self, indent):
        ''' Return a list of code corresponding to the indentation level
        '''
        self.line = self.input('... ')
        debugFunc('In a block', center=True)
        blockTokenized = parse(self.line, filename=self.filename,
                no=self.lineNumber, debug=self.debug)
        blockIndent = blockTokenized[0]['indent']
        block = []
        if blockIndent > indent:
            struct, nextLine = self.handleTokenized(blockTokenized)
            block.append(struct)
            if not nextLine:
                self.line = self.input('... ')
            blockTokenized = parse(self.line, filename=self.filename,
                    no=self.lineNumber, debug=self.debug)
            while blockTokenized[0]['indent'] == blockIndent:
                struct, nextLine = self.handleTokenized(blockTokenized)
                block.append(struct)
                if not nextLine:
                    self.line = self.input('... ')
                blockTokenized = parse(self.line, filename=self.filename,
                        no=self.lineNumber, debug=self.debug)
            debugFunc('Out of a block', center=True)
            return block, blockTokenized
        else:
            debugFunc('Out of a block', center=True)
            return block, blockTokenized
            raise SyntaxError(f'Expecting an indented block here.\nLine: {self.line}')

    def handleBlock(self, tokenized):
        ''' Return a struct with a block and possibly modifiers '''
        indent = tokenized[0]['indent']
        block, nextTokenized = self.getBlock(indent)
        tokenized = assembly(tokenized, block=block)
        if len(nextTokenized) > 1:
            while nextTokenized[1]['token'] in {'elifStatement','elseStatement'} and nextTokenized[0]['indent'] == indent:
                block, afterTokenized = self.getBlock(indent)
                nextTokenized = assembly(nextTokenized, block=block)
                tokenized = assembly(tokenized, modifier=nextTokenized)
                nextTokenized = afterTokenized
                if len(nextTokenized) == 1:
                    break
        struct = assembly(tokenized)
        return struct

    def handleTokenized(self, tokenized):
        ''' Return a struct to be processed by the VM '''
        ''' And if there is a line to be processed in the buffer (self.line) '''
        if tokenized[-1]['token'] == 'beginBlock':
            struct = self.handleBlock(tokenized)
            return struct, True
        else:
            struct = assembly(tokenized)
            return struct, False

    def run(self):
        nextLine = False
        while True:
            if not nextLine or self.line == '':
                self.line = self.input('>>> ')
            self.processing = True
            if self.line == 'exit':
                break
            try:
                tokenized = parse(self.line, filename=self.filename, no=self.lineNumber, debug=self.debug)
                struct, nextLine = self.handleTokenized(tokenized)
            except Exception as e:
                showError(e)
            self.engine.process(struct)
            self.processing = False

if __name__ == "__main__":
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = ''
    Interpreter(filename).run()
