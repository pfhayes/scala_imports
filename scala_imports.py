#!/usr/bin/env python

import os, sys, subprocess, pygments, itertools, string
from pygments import lexers

debug = ("--debug" in sys.argv[1:])
dry_run = ("--dry-run" in sys.argv[1:])

def is_declaration(token) :
  return token in [
      "class", "trait", "def", "val",
      "type", "var", "package", "object"]

def get_used_tokens(filename) :
  lines = [line for line in open(filename, 'r')]
  lexer = lexers.get_lexer_for_filename(filename)
  seen = set([])

  used_tokens = []
  declared_tokens = set([])

  token_iter = lexer.get_tokens('\n'.join(lines))
  two_prev_iter, prev_iter, curr_iter = itertools.tee(token_iter, 3)
  # we miss the first two tokens here... whatever
  next(prev_iter)
  next(curr_iter)
  next(curr_iter)

  for (two_prev, prev, curr) in itertools.izip(two_prev_iter, prev_iter, curr_iter) :
    if str(prev[0]) in ['Token.Operator', 'Token.Keyword.Type'] and prev[1] == '.' :
      continue
    if str(curr[0]) in ['Token.Name.Class', 'Token.Keyword.Type'] and curr[1][0].isupper() :
      if is_declaration(two_prev[1]) :
        declared_tokens.add(curr[1])
      elif curr not in seen :
        seen.add(curr)
        used_tokens.append(curr[1])

  return [t for t in used_tokens if t not in declared_tokens]

def get_unimported_tokens(filename) :
  imported_tokens = get_imported_tokens(filename)
  used_tokens = get_used_tokens(filename)
  if debug :
    print '%d imported tokens: %s' % (len(imported_tokens), imported_tokens)
    print '%d used tokens: %s' % (len(used_tokens), used_tokens)
  as_set = set(imported_tokens)
  return [t for t in used_tokens if t not in as_set and needs_import(t)]

# Copied from the "scala" package, and also from Predef.scala
known_tokens = set([
  'AbstractMethodError',
  'Any',
  'AnyVal',
  'Array',
  'ArrayIndexOutOfBoundsException',
  'BigDecimal',
  'BigInt',
  'Boolean',
  'BufferedIterator',
  'Byte',
  'Char',
  'Class',
  'ClassCastException',
  'ClassManfiest',
  'Cloneable',
  'Console',
  'DelayedInit',
  'Double',
  'Dynamic',
  'Either',
  'Enumeration',
  'Equals',
  'Error',
  'Exception',
  'Float',
  'Function',
  'IllegalArgumentException',
  'Immutable',
  'IndexOutOfBoundsException',
  'IndexedSeq',
  'Int',
  'Integer',
  'Integral',
  'InterruptedException',
  'Iterable',
  'Iterator',
  'Left',
  'List',
  'Long',
  'Manifest',
  'Map',
  'MatchError',
  'Nil',
  'NoManifest',
  'NoSuchElementException',
  'None',
  'Numeric',
  'NullPointerException',
  'OptManifest',
  'Option',
  'Ordered',
  'Ordering',
  'Pair',
  'PartialFunction',
  'Product',
  'Range',
  'Right',
  'Set',
  'Seq',
  'Serializable',
  'Short',
  'Some',
  'Stream',
  'String',
  'StringBuilder',
  'Throwable',
  'Triple',
  'Unit',
  'Vector',
] + list(string.uppercase)
  + ['Function' + str(i) for i in range(0,23)]
  + ['Tuple' + str(i) for i in range(0,23)]
  + ['Product' + str(i) for i in range(0,23)])

def needs_import(token) :
  return token not in known_tokens

def token_valid(token) :
  if token == '_' or token == '' :
    return False
  return True

def token_sanitize(token) :
  if "=>" in token :
    real = token.split("=>")[-1]
  else :
    real = token
  return real.strip()

def get_imported_tokens(filename) :
  with open(filename, 'r') as f :
    imported_tokens = []
    in_import = False
    for line in f :
      to_add = []
      if line.startswith('import') :
        assert not in_import, "Unclosed import"
        if "{" not in line :
          to_add = [line.split(".")[-1]]
        elif "}" in line :
          r = line[(line.rfind("{") + 1) : line.rfind("}")]
          to_add = r.replace(" ","").split(",")
        else :
          r = line[(line.rfind("{") + 1):]
          to_add = r.replace(" ","").split(",")
          in_import = True
      elif in_import :
        if "}" in line :
          to_add = line[:line.find("}")].replace(" ","").split(",")
          in_import = False
        else :
          to_add = line.replace(" ","").split(",")
      imported_tokens.extend(to_add)

    assert not in_import, "Unclosed import"
    return [token_sanitize(t) for t in imported_tokens
        if token_valid(token_sanitize(t)) > 0]

def get_package(filename) :
  if filename.endswith('.scala') or filename.endswith('.thrift') :
    for line in open(filename, 'r') :
      if line.startswith('package') and filename.endswith('.scala') :
        return line.strip().split(" ")[-1]
      if line.startswith('namespace java') and filename.endswith('.thrift') :
        return line.strip().split(" ")[-1]
    print 'Error. %s has no package declaration' % filename
    return None
  return None

def get_imports(current_filename, new_tokens) :
  in_tokens = set(new_tokens)
  toks = []
  used_toks = {}
  for line in open('tags', 'r') :
    fields = line.split("\t")
    tag = fields[0]
    kind = fields[-1].strip()
    if kind in ['C', 'c', 'o', 't'] and tag in in_tokens :
      filename = line.split("\t")[1]
      previous_filename = used_toks.get(tag)
      if previous_filename and previous_filename != filename :
        print 'Warning: Duplicate definitions for token %s' % tag
      else :
        toks.append((tag, filename))
        used_toks[tag] = filename

  imports = []
  for token, filename in toks :
    package = get_package(filename)
    if package is not None :
      imports.append(package + "." + token)

  for n in new_tokens :
    if n not in used_toks :
      print "Warning: Couldn't import %s in %s" % (n, current_filename)

  if debug :
    print '%d imports: %s' % (len(imports), imports)

  return imports

def add_imports(filename, imports) :
  write_lines = []
  has_added_imports = False

  def do_add_imports() :
    for i in imports :
      print 'Adding import to %s: %s' % (filename, i)
    write_lines.extend(["import " + i + "\n" for i in imports])

  with open(filename, 'r') as f :
    for line in f :
      write_lines.append(line)
      if not has_added_imports :
        if line.startswith('import') or line.startswith('package') :
          write_lines.append('\n')
          do_add_imports()
          has_added_imports = True
  if not dry_run :
    with open(filename, 'w') as f :
      for line in write_lines :
        f.write(line)

if __name__ == "__main__" :
  lines = subprocess.check_output(["git", "diff", "origin/master", "--numstat"]).split("\n")
  files = [line.split("\t")[2] for line in lines if len(line) > 0]
  scala_files = [f for f in files if f.endswith('.scala')]

  for f in scala_files:
    if debug :
      print 'Scanning %s' % f
    current_package = get_package(f)
    new_tokens = get_unimported_tokens(f)
    imports = get_imports(f, new_tokens)
    useful_imports = [i for i in imports if not i.startswith(current_package)]
    add_imports(f, useful_imports)
    
