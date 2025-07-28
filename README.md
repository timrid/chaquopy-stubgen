# chaquopy-stubgen
This tool is a python type stub generator from java classes. It is optimized for the usage with Android via [chaquopy](https://github.com/chaquo/chaquopy) and [briefcase](https://github.com/beeware/).

This is based on [stubgenj](https://gitlab.cern.ch/scripting-tools/stubgenj).

# Usage
1. Create new venv: `uv venv`
2. Call e.g. `python -m chaquopy_stubgen android java --classpath examples/android-35.jar --output-dir examples`
