# DEWETRON pyOxygenStream

pyOxygenStream is a Python wrapper for DataStream feature from Dewetron Oxygen Measurement Software.
A valid license must be installed on OXYGEN instance. Otherwise, the stream may be stop after a short time.

# Installation
## Directly from GitHub
You can install the Dewetron Oxygen SCPI and Datastream packages directly using
```bash
pip install git+https://github.com/DEWETRON/pyOxygenSCPI.git
pip install git+https://github.com/DEWETRON/pyOxygenStream.git
```

## From local repository
1. Clone GIT repository \
`git clone https://github.com/DEWETRON/pyOxygenStream.git`

2. Change to directory \
`cd pyOxygenStream`

3. Install \
`python setup.py install`
or
`python -m pip install .`

# Example usage

1. Start OXYGEN
2. Adapt the channels to be streamed in dst_minimum_example.py
3. Run the example

# About


**For technical questions please contact:**

Thomas Kastner 

thomas.kastner@dewetron.com

Gunther Laure

gunther.laure@dewetron.com




# License
MIT License

Copyright (c) 2022-2025 DEWETRON

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSE (END)
