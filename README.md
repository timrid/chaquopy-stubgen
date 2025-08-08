# chaquopy-stubgen
This tool is a python type stub generator from java classes. It is optimized for the usage with Android via [chaquopy v16.1](https://github.com/chaquo/chaquopy) and [briefcase](https://github.com/beeware/).

This is based on [stubgenj](https://gitlab.cern.ch/scripting-tools/stubgenj). Although the tool generates stubs optimized for  `chaquopy`, it still uses [`jpype`](https://github.com/jpype-project/jpype) internally to parse the Java files.

The generated stubs can be used with Python 3.8 or higher.

# CLI Usage
Example call `python -m chaquopy_stubgen java android --classpath android.jar`

```
$ python -m chaquopy_stubgen --help
usage: __main__.py [-h] [--jvmpath JVMPATH] [--classpath CLASSPATH] [--output-dir OUTPUT_DIR] [--no-javadoc] prefixes [prefixes ...]

Generate Python Type Stubs for Java classes that are optimized for chaquopy.

positional arguments:
  prefixes              package prefixes to generate stubs for (e.g. org.myproject)

options:
  -h, --help            show this help message and exit
  --jvmpath JVMPATH     path to the JVM ("libjvm.so", "jvm.dll", ...) (default: use system default JVM)
  --classpath CLASSPATH
                        java class path to use, separated by ":". glob-like expressions (e.g. dir/*.jar) are supported (default: .)
  --output-dir OUTPUT_DIR
                        path to write stubs to (default: .)
  --no-javadoc          do not generate docstrings from JavaDoc where available
```



# Development
- Create venv: `uv sync`
- Test: `uv run pytest`
