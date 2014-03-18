# scala_imports #

A simple tool for automatically adding required imports to your scala files, by using your existing ctags definitions.

Doesn't work perfectly, but is designed to do the heavy lifting for you in 95% of the cases. For ease of use, scala_imports may use some simplifying assumptions about how your code is structured/written.

## How to use ##

1. Initialize a git repository for your scala code.
2. Generate a tags file with `ctags -R .`
3. Make edits to your code.
4. Run `scala_imports.py` to update all affected files.
5. If desired, use another tool to cleanup/sort the added imports.

## Args ##

- You can specify the files you want scala_imports to run on. By default it
  will run on everything you have changed since origin/master
- Use --dry-run to just output what would be added.
- Use --debug to debug

## Dependencies ##

- scala
- git
- ctags
- pygments
