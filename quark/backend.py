# Copyright 2015 datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .ast import Function, Interface, Method, Package
from collections import OrderedDict

class Backend(object):

    def __init__(self):
        self.files = {}

class Java(Backend):

    def __init__(self):
        Backend.__init__(self)
        self.classr = ClassRenderer()
        self.functions = []

    def visit_Class(self, c):
        pkg = self.classr.namer.package(c)
        if pkg:
            self.files["%s/%s.java" % (pkg, c.name.text)] = c.apply(self.classr)
        else:
            self.files["%s.java" % c.name.text] = c.apply(self.classr)

    def visit_Function(self, f):
        if not isinstance(f, Method):
            self.functions.append(f)

    def leave_Root(self, r):
        if self.functions:
            packages = OrderedDict()
            for f in self.functions:
                pkg = self.classr.namer.package(f)
                if pkg in packages:
                    functions = packages[pkg]
                else:
                    functions = []
                    packages[pkg] = functions
                functions.append(f.apply(self.classr))
                if f.name.text == "main":
                    functions.append("public static void main(String[] args) {\n    main();\n}")
            for pkg, functions in packages.items():
                cls = "public class Functions {%s}" % indent("\n".join(functions))
                if pkg:
                    self.files["%s/Functions.java" % pkg.replace(".", "/")] = "package %s;\n\n%s" % (pkg, cls)
                else:
                    self.files["Functions.java"] = cls

    def visit_Primitive(self, p):
        pass

def indent(st, level=4):
    if st:
        spaces = " "*level
        return ("\n" + st).replace("\n", "\n%s" % spaces) + "\n"
    else:
        return ""

class NameRenderer(object):

    def Name(self, n):
        return n.text

    def Type(self, t):
        if t.parameters:
            params = [p.apply(self) for p in t.parameters]
            return "%s<%s>" % (".".join([p.apply(self) for p in t.path]), ",".join(params))
        else:
            return ".".join([p.apply(self) for p in t.path])

    def Var(self, v):
        return v.name.apply(self)

    def package(self, node):
        if isinstance(node, Package):
            me = node.name.apply(self)
            parent = self.package(node.parent)
            if parent:
                return "%s.%s" % (parent, me)
            else:
                return me
        elif node.parent:
            return self.package(node.parent)
        else:
            return None

class SubstitutionNamer(NameRenderer):

    def __init__(self, env):
        self.env = env

    def Name(self, n):
        if n.text in self.env:
            return self.env[n.text]
        else:
            return n.text

class VarRenderer(object):

    def __init__(self, var, namer):
        self.var = var
        self.namer = namer

    def Definition(self, d):
        return self.var.apply(self.namer)

    def Function(self, d):
        pkg = self.namer.package(d)
        if pkg:
            return "%s.Functions.%s" % (pkg, self.var.apply(self.namer))
        else:
            return "Functions.%s" % self.var.apply(self.namer)

    def Declaration(self, d):
        return self.var.apply(self.namer)

class ExprRenderer(object):

    def __init__(self, namer):
        self.namer = namer

    def Number(self, n):
        return n.text

    def String(self, s):
        return s.text

    def List(self, l):
        return "new java.util.ArrayList(java.util.Arrays.asList(new Object[]{%s}))" % \
            (", ".join([e.apply(self) for e in l.elements]))

    def Call(self, c):
        type = c.expr.resolved.type
        return type.apply(Invoker(c, self.namer))

    def Attr(self, a):
        type = a.expr.resolved.type
        return type.apply(Getter(a, self))

    def Type(self, t):
        return t.apply(self.namer)

    def Var(self, v):
        return v.definition.apply(VarRenderer(v, self.namer))

    def Native(self, n):
        return "".join([c.apply(self) for c in n.children])

    def Fixed(self, f):
        return f.text

class Getter(object):

    def __init__(self, attr, exprr):
        self.attr = attr
        self.exprr = exprr

    def Class(self, c):
        expr = self.attr.expr
        attr = self.attr.attr.text
        return "(%s).%s" % (expr.apply(self.exprr), attr)

    def Package(self, p):
        expr = self.attr.expr
        attr = self.attr.attr.text
        if isinstance(self.attr.resolved.type, Function):
            return "%s.Functions.%s" % (expr.apply(self.exprr), attr)
        else:
            return "%s.%s" % (expr.apply(self.exprr), attr)

class Invoker(object):

    def __init__(self, call, namer):
        self.call = call
        self.namer = namer

    @property
    def expr(self):
        return self.call.expr.apply(ExprRenderer(self.namer))

    @property
    def args(self):
        return [a.apply(ExprRenderer(self.namer)) for a in self.call.args]

    def Class(self, c):
        return "new %s(%s)" % (self.expr, ", ".join(self.args))

    def Function(self, f):
        return "%s(%s)" % (self.expr, ", ".join(self.args))

    @property
    def self_(self):
        return self.call.expr.expr.apply(ExprRenderer(self.namer))

    def Method(self, m):
        return "(%s).%s(%s)" % (self.self_, m.name.text, ", ".join(self.args))

    def Macro(self, m):
        # macros are evaluated at compile time, so we don't use expr
        env = {}
        idx = 0
        args = self.args
        for p in m.params:
            env[p.name.text] = args[idx]
            idx += 1
        return m.body.apply(ExprRenderer(SubstitutionNamer(env)))

    def MethodMacro(self, mm):
        # for method macros we use expr to access self
        env = {"self": self.self_}
        idx = 0
        args = self.args
        for p in mm.params:
            env[p.name.text] = args[idx]
            idx += 1
        return mm.body.apply(ExprRenderer(SubstitutionNamer(env)))

class ClassRenderer(object):

    def __init__(self):
        self.namer = SubstitutionNamer({"self": "this", "int": "Integer",
                                        "List": "java.util.ArrayList",
                                        "Map": "java.util.HashMap"})
        self.exprr = ExprRenderer(self.namer)

    def Class(self, c):
        name = c.name.apply(self.namer)
        params = ""
        if c.parameters:
            params = "<%s>" % (", ".join([p.apply(self) for p in c.parameters]))
        body = "\n".join([d.apply(self) for d in c.definitions])
        kw = "interface" if isinstance(c, Interface) else "class"
        cls = "public %s %s%s {%s}" % (kw, name, params, indent(body))
        pkg = self.namer.package(c)
        if pkg:
            return "package %s;\n\n%s" % (pkg, cls)
        else:
            return cls

    def TypeParam(self, p):
        return p.name.apply(self.namer)

    def Block(self, b):
        return "\n".join([s.apply(self) for s in b.statements])

    def Function(self, m):
        type = "%s " % m.type.apply(self.namer) if m.type else ""
        name = m.name.apply(self.namer)
        params = ", ".join([p.apply(self) for p in m.params])
        body = " {%s}" % indent(m.body.apply(self)) if m.body else ";"
        if isinstance(m, Method):
            mods = "public"
        else:
            mods = "public static"
        return "%s %s%s(%s)%s" % (mods, type, name, params, body)

    def MethodMacro(self, mm):
        return ""

    def Declaration(self, d):
        type = d.type.apply(self.namer)
        name = d.name.apply(self.namer)
        if d.value:
            value = d.value.apply(self.exprr)
            return "%s %s = %s" % (type, name, value)
        else:
            return "%s %s" % (type, name)

    def Field(self, f):
        return "%s;" % self.Declaration(f)

    def Return(self, r):
        return "return %s;" % r.expr.apply(self.exprr)

    def Local(self, stmt):
        return "%s;" % stmt.declaration.apply(self)

    def ExprStmt(self, stmt):
        return "%s;" % stmt.expr.apply(self.exprr)

    def Assign(self, a):
        return "%s = %s;" % (a.lhs.apply(self), a.rhs.apply(self.exprr))

    def Attr(self, a):
        return "(%s).%s" % (a.expr.apply(self.exprr), a.attr.text)

    def Var(self, v):
        return v.apply(self.namer)

    def If(self, i):
        result = "if (%s) {%s}" % (i.predicate.apply(self.exprr),
                                   indent(i.consequence.apply(self)))
        if i.alternative:
            result += " else {%s}" % indent(i.alternative.apply(self))
        return result
