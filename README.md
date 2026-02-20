# chaquopy-stubgen
This tool is a python type stub generator from java classes. It is optimized for the usage with Android via [chaquopy v16.1](https://github.com/chaquo/chaquopy) and [briefcase](https://github.com/beeware/).

The generated stubs can be used with Python 3.10 or higher.

# CLI Usage
Example call `uv run -m chaquopy_stubgen "$ANDROID_HOME/platforms/android-35/android.jar"`

```
$ uv run -m chaquopy_stubgen --help
usage: __main__.py [-h] [--jvmpath JVMPATH] [--output-dir OUTPUT_DIR]
                   jars [jars ...]

Generate Python Type Stubs for Java classes that are optimized for chaquopy.

positional arguments:
  jars                  List of .jar or .aar files to generate stubs for.

options:
  -h, --help            show this help message and exit
  --jvmpath JVMPATH     path to the JVM ("libjvm.so", "jvm.dll", ...) (default:
                        use system default JVM)
  --output-dir OUTPUT_DIR
                        path to write stubs to (default: ./dist/stubs)
```

# Development
- Create venv: `uv sync`
- Test: `uv run pytest`


# Credits
This is based on [stubgenj](https://gitlab.cern.ch/scripting-tools/stubgenj), but generates stubs optimized for `chaquopy` and is internally reworked to use [ASM](https://asm.ow2.io/) instead of Java Reflection.

